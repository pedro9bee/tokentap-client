"""MITM proxy for intercepting LLM API traffic using mitmproxy."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Callable

from mitmproxy import http, options
from mitmproxy.tools import dump

from tokentap.config import DEFAULT_PROXY_PORT, PROVIDERS
from tokentap.parser import count_tokens, parse_anthropic_request
from tokentap.response_parser import parse_response, parse_sse_stream

logger = logging.getLogger(__name__)

# Domain → provider mapping for MITM interception
DOMAIN_TO_PROVIDER = {
    "api.anthropic.com": "anthropic",
    "api.openai.com": "openai",
    "generativelanguage.googleapis.com": "gemini",
}



class TokentapAddon:
    """mitmproxy addon that intercepts LLM API traffic and records token usage."""

    def __init__(
        self,
        db=None,
        on_request: Callable[[dict], None] | None = None,
    ):
        self.db = db
        self.on_request = on_request
        # Per-flow data: start time, streaming chunks
        self._flow_data: dict[str, dict] = {}

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept requests: health check, backward compat rewrite, start timer."""
        host = flow.request.host
        path = flow.request.path

        # Health check: respond inline when targeting the proxy itself
        if host in ("localhost", "127.0.0.1") and path == "/health":
            status = {"status": "ok", "proxy": True}
            flow.response = http.Response.make(
                200,
                json.dumps(status).encode(),
                {"Content-Type": "application/json"},
            )
            return

        # Backward compat: requests sent directly to the proxy (via *_BASE_URL)
        # Rewrite them to the real upstream HTTPS endpoint.
        if host in ("localhost", "127.0.0.1"):
            provider = self._detect_provider_from_path(path)
            if provider:
                upstream = PROVIDERS[provider]["host"]
                flow.request.host = upstream
                flow.request.port = 443
                flow.request.scheme = "https"
            else:
                flow.response = http.Response.make(
                    400,
                    f"Unknown API path: {path}. Supported: Anthropic, OpenAI, Gemini".encode(),
                    {"Content-Type": "text/plain"},
                )
                return

        # Start timer
        self._flow_data[flow.id] = {
            "start_time": time.monotonic(),
            "chunks": [],
            "is_streaming": False,
        }

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Configure streaming for SSE responses."""
        if flow.id not in self._flow_data:
            return

        content_type = flow.response.headers.get("content-type", "")
        is_sse = "text/event-stream" in content_type

        # Also check if the request asked for streaming
        try:
            body = json.loads(flow.request.content)
            is_request_stream = body.get("stream", False)
        except (json.JSONDecodeError, ValueError, TypeError):
            is_request_stream = False

        if is_sse or is_request_stream:
            fdata = self._flow_data[flow.id]
            fdata["is_streaming"] = True

            # Use a stream function that captures chunks while forwarding them
            def stream_chunks(data: bytes) -> bytes:
                if data:
                    fdata["chunks"].append(data)
                return data

            flow.response.stream = stream_chunks

    async def response(self, flow: http.HTTPFlow) -> None:
        """Parse response for token usage and record event."""
        fdata = self._flow_data.pop(flow.id, None)
        if fdata is None:
            return

        host = flow.request.host
        provider = DOMAIN_TO_PROVIDER.get(host)
        if not provider:
            return

        duration_ms = int((time.monotonic() - fdata["start_time"]) * 1000)
        path = flow.request.path

        # Parse request body
        body_dict = None
        request_parsed = None
        try:
            body_dict = json.loads(flow.request.content)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        if body_dict:
            request_parsed = self._parse_request_body(body_dict, provider)

        # Parse response for token usage
        is_streaming = fdata["is_streaming"]

        if is_streaming:
            chunks = fdata["chunks"]
            usage = parse_sse_stream(provider, chunks)
            response_data = None
        else:
            response_data = None
            try:
                response_data = json.loads(flow.response.content)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            if response_data:
                usage = parse_response(provider, response_data)
            else:
                usage = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "model": "unknown",
                    "stop_reason": None,
                }

        # Build event
        estimated_input_tokens = 0
        if request_parsed:
            estimated_input_tokens = count_tokens(request_parsed.get("total_text", ""))

        model = usage.get("model", "unknown")
        if model == "unknown" and request_parsed:
            model = request_parsed.get("model", "unknown")

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "provider": provider,
            "model": model,
            "path": path,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_tokens", 0),
            "estimated_input_tokens": estimated_input_tokens,
            "messages": request_parsed.get("messages", []) if request_parsed else [],
            "response_status": flow.response.status_code,
            "response_stop_reason": usage.get("stop_reason"),
            "streaming": is_streaming,
        }

        # Legacy callback for Rich dashboard
        if self.on_request:
            legacy_event = {
                "timestamp": event["timestamp"],
                "provider": provider,
                "model": model,
                "tokens": estimated_input_tokens,
                "messages": event["messages"],
                "raw_body": body_dict,
                "path": path,
            }
            self.on_request(legacy_event)

        # Write to MongoDB
        if self.db:
            db_event = {**event}
            if body_dict:
                db_event["raw_request"] = body_dict
            if response_data:
                db_event["raw_response"] = response_data
            try:
                await self.db.insert_event(db_event)
            except Exception:
                logger.exception("Failed to write event to MongoDB")

    # -------------------------------------------------------------------------
    # Request parsing helpers (same logic as before)
    # -------------------------------------------------------------------------

    @staticmethod
    def _detect_provider_from_path(path: str) -> str | None:
        """Detect provider from the request path (backward compat)."""
        if "/v1/messages" in path:
            return "anthropic"
        elif "/v1/chat/completions" in path or "/v1/responses" in path:
            return "openai"
        elif "generateContent" in path or "streamGenerateContent" in path:
            return "gemini"
        return None

    @staticmethod
    def _parse_request_body(body_dict: dict, provider: str) -> dict | None:
        """Parse request body for token counting."""
        if provider == "anthropic":
            return parse_anthropic_request(body_dict)
        elif provider == "openai":
            return _parse_openai_request(body_dict)
        elif provider == "gemini":
            return _parse_gemini_request(body_dict)
        return None


def _parse_openai_request(body: dict) -> dict:
    """Parse OpenAI API request body."""
    result = {
        "provider": "openai",
        "messages": [],
        "model": body.get("model", "unknown"),
        "total_text": "",
    }

    texts = []
    messages = body.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            result["messages"].append({"role": role, "content": content})
            texts.append(content)
        elif isinstance(content, list):
            text_parts = [
                p.get("text", "") for p in content if p.get("type") == "text"
            ]
            combined = " ".join(text_parts)
            result["messages"].append({"role": role, "content": combined})
            texts.append(combined)

    result["total_text"] = "\n".join(texts)
    return result


def _parse_gemini_request(body: dict) -> dict:
    """Parse Gemini API request body."""
    result = {
        "provider": "gemini",
        "messages": [],
        "model": "gemini",
        "total_text": "",
    }

    texts = []
    contents = body.get("contents", [])
    for content in contents:
        role = content.get("role", "user")
        parts = content.get("parts", [])
        text_parts = [p.get("text", "") for p in parts if "text" in p]
        combined = " ".join(text_parts)
        result["messages"].append({"role": role, "content": combined})
        texts.append(combined)

    system_instruction = body.get("systemInstruction", {})
    if system_instruction:
        parts = system_instruction.get("parts", [])
        text_parts = [p.get("text", "") for p in parts if "text" in p]
        if text_parts:
            system_text = " ".join(text_parts)
            result["messages"].insert(0, {"role": "system", "content": system_text})
            texts.insert(0, system_text)

    result["total_text"] = "\n".join(texts)
    return result


async def start_mitmproxy(
    port: int = DEFAULT_PROXY_PORT,
    db=None,
    on_request: Callable[[dict], None] | None = None,
) -> None:
    """Start mitmproxy with the TokentapAddon."""
    opts = options.Options(
        listen_host="0.0.0.0",
        listen_port=port,
    )

    master = dump.DumpMaster(
        opts,
        with_termlog=False,
        with_dumper=False,
    )

    # Allow connections from any IP (needed inside Docker where client IP
    # is the Docker bridge, not 127.0.0.1)
    master.options.update(block_global=False)
    master.addons.add(TokentapAddon(db=db, on_request=on_request))

    logger.info("mitmproxy listening on 0.0.0.0:%d", port)
    await master.run()
