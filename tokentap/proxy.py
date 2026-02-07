"""MITM proxy for intercepting LLM API traffic using mitmproxy."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Callable

from mitmproxy import http, options
from mitmproxy.tools import dump

from tokentap.config import DEFAULT_PROXY_PORT, PROVIDERS, DEBUG_MODE
from tokentap.parser import count_tokens, parse_anthropic_request
from tokentap.provider_config import get_provider_config
from tokentap.generic_parser import GenericParser
from tokentap.response_parser import parse_response, parse_sse_stream

logger = logging.getLogger(__name__)

# Domain → provider mapping for MITM interception (DEPRECATED: kept for backward compat)
DOMAIN_TO_PROVIDER = {
    "api.anthropic.com": "anthropic",
    "api.openai.com": "openai",
    "generativelanguage.googleapis.com": "gemini",
    "q.us-east-1.amazonaws.com": "kiro",
    "q.us-west-2.amazonaws.com": "kiro",
    "q.eu-west-1.amazonaws.com": "kiro",
    "q.ap-southeast-1.amazonaws.com": "kiro",
}



class TokentapAddon:
    """mitmproxy addon that intercepts LLM API traffic and records token usage."""

    def __init__(
        self,
        db=None,
        on_request: Callable[[dict], None] | None = None,
        use_dynamic_config: bool = True,
    ):
        self.db = db
        self.on_request = on_request
        self.use_dynamic_config = use_dynamic_config
        # Per-flow data: start time, streaming chunks, provider info, context
        self._flow_data: dict[str, dict] = {}

        # NEW: Dynamic provider configuration
        if use_dynamic_config:
            try:
                self.provider_config = get_provider_config()
                self.generic_parser = GenericParser(self.provider_config)
                logger.info("Dynamic provider configuration loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load dynamic provider config: {e}")
                logger.warning("Falling back to hardcoded providers")
                self.provider_config = None
                self.generic_parser = None
        else:
            self.provider_config = None
            self.generic_parser = None

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept requests: health check, backward compat rewrite, start timer."""
        host = flow.request.host
        path = flow.request.path

        # Health check: respond inline when targeting the proxy itself
        if host in ("localhost", "127.0.0.1") and path == "/health":
            logger.debug("Health check request received")
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
                logger.info("Backward compat request: %s -> %s", path, provider)
                upstream = PROVIDERS[provider]["host"]
                flow.request.host = upstream
                flow.request.port = 443
                flow.request.scheme = "https"
                # FIX v0.6.0: Update host variable after rewrite for correct provider detection
                host = flow.request.host
            else:
                logger.warning("Unknown API path: %s", path)
                flow.response = http.Response.make(
                    400,
                    f"Unknown API path: {path}. Supported: Anthropic, OpenAI, Gemini".encode(),
                    {"Content-Type": "text/plain"},
                )
                return

        # NEW: Dynamic provider detection
        provider_info = None
        provider_name = None

        if self.provider_config:
            provider_info = self.provider_config.get_provider_by_domain(host)
            if provider_info:
                provider_name = provider_info["provider_name"]
                logger.info("Intercepting %s request: %s %s %s", provider_name, flow.request.method, host, path)
            else:
                logger.debug("No provider config for host: %s", host)
        else:
            # Fallback to hardcoded mapping
            provider_name = DOMAIN_TO_PROVIDER.get(host)
            if provider_name:
                logger.info("Intercepting %s request (legacy): %s %s %s", provider_name, flow.request.method, host, path)
            else:
                logger.debug("Proxying unknown host: %s %s %s", flow.request.method, host, path)

        # Extract context metadata from headers
        context_metadata = self._extract_context_metadata(flow)

        # Start timer
        self._flow_data[flow.id] = {
            "start_time": time.monotonic(),
            "chunks": [],
            "is_streaming": False,
            "provider_name": provider_name,
            "provider_info": provider_info,
            "context_metadata": context_metadata,
        }

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Configure streaming for SSE responses."""
        if flow.id not in self._flow_data:
            return

        fdata = self._flow_data[flow.id]
        # Only process if we have a provider
        if not fdata.get("provider_name"):
            return

        content_type = flow.response.headers.get("content-type", "")
        is_sse = "text/event-stream" in content_type
        is_eventstream = "application/vnd.amazon.eventstream" in content_type

        # Also check if the request asked for streaming
        is_request_stream = False
        try:
            body = json.loads(flow.request.content)
            # Body might be a list or dict, only check if it's a dict
            if isinstance(body, dict):
                is_request_stream = body.get("stream", False)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        if is_sse or is_request_stream or is_eventstream:
            logger.debug("Streaming response detected for %s (SSE: %s, EventStream: %s, stream param: %s)",
                        flow.request.host, is_sse, is_eventstream, is_request_stream)
            fdata["is_streaming"] = True
            fdata["stream_type"] = "eventstream" if is_eventstream else "sse"

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

        provider_name = fdata.get("provider_name")
        if not provider_name:
            return

        provider_info = fdata.get("provider_info")
        context_metadata = fdata.get("context_metadata", {})

        host = flow.request.host
        duration_ms = int((time.monotonic() - fdata["start_time"]) * 1000)
        path = flow.request.path

        # For backward compatibility
        provider = provider_name

        # Filter out telemetry requests by header (Kiro-specific)
        if provider == "kiro":
            x_amz_target = flow.request.headers.get("x-amz-target", "")
            if "SendTelemetryEvent" in x_amz_target or "SendTelemetry" in x_amz_target:
                logger.debug("Skipping Kiro telemetry request: %s", x_amz_target)
                return

        # Filter out telemetry/metrics requests by path
        if any(keyword in path.lower() for keyword in ['/telemetry', '/metrics', '/clienttelemetry']):
            logger.debug("Skipping telemetry request: %s %s", provider, path)
            return

        logger.debug("Processing %s response: %s (status: %d, duration: %dms)",
                    provider, path, flow.response.status_code, duration_ms)

        # Parse request body
        body_dict = None
        request_parsed = None
        try:
            body_dict = json.loads(flow.request.content)
        except (json.JSONDecodeError, ValueError, TypeError):
            # NEW v0.6.0: Only log parsing errors in debug mode
            if DEBUG_MODE and provider == "kiro":
                logger.info("KIRO RAW REQUEST (not JSON, DEBUG): %s", flow.request.content[:500])
            pass

        if body_dict:
            # NEW v0.6.0: Only log full request in debug mode
            if DEBUG_MODE and provider == "kiro":
                logger.info("KIRO RAW REQUEST (DEBUG): %s", json.dumps(body_dict, indent=2))

            # Try generic parser first
            if self.generic_parser:
                try:
                    request_parsed = self.generic_parser.parse_request(provider_name, body_dict)

                    # NEW v0.4.1: Validate quality of parsed data
                    if not self._is_parse_quality_acceptable(request_parsed, body_dict):
                        logger.warning(
                            f"Generic parser returned incomplete data for {provider_name}, "
                            f"falling back to legacy parser"
                        )
                        request_parsed = self._parse_request_body(body_dict, provider)

                except Exception as e:
                    logger.warning(f"Generic parser failed for {provider_name}: {e}")
                    request_parsed = self._parse_request_body(body_dict, provider)
            else:
                # Fallback to legacy parser
                request_parsed = self._parse_request_body(body_dict, provider)

        # Parse response for token usage
        is_streaming = fdata["is_streaming"]

        if is_streaming:
            chunks = fdata["chunks"]
            stream_type = fdata.get("stream_type", "sse")
            logger.debug("Parsing %s stream (%d chunks)", stream_type, len(chunks))

            if stream_type == "eventstream" and provider == "kiro":
                # Amazon EventStream format - log full content only in debug mode
                if DEBUG_MODE:
                    full_content = b"".join(chunks)
                    logger.info("KIRO EventStream full content (DEBUG, %d bytes): %s",
                               len(full_content),
                               full_content[:2000].decode('utf-8', errors='replace'))
                # Try to parse as eventstream (for now, no tokens extracted)
                usage = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "model": "kiro",
                    "stop_reason": None,
                }
                response_data = None
            else:
                # NEW: Try generic parser first
                if self.generic_parser:
                    try:
                        usage = self.generic_parser.parse_response(provider_name, chunks, is_streaming=True)
                    except Exception as e:
                        logger.warning(f"Generic parser failed for streaming {provider_name}: {e}")
                        usage = parse_sse_stream(provider, chunks)
                else:
                    usage = parse_sse_stream(provider, chunks)
                response_data = None
        else:
            response_data = None
            # NEW v0.6.0: Only log response details in debug mode
            if DEBUG_MODE and provider == "kiro":
                logger.info("KIRO Response (DEBUG): status=%d, content-length=%d, content-type=%s",
                           flow.response.status_code,
                           len(flow.response.content),
                           flow.response.headers.get("content-type", "unknown"))
                logger.debug("KIRO Response Headers (DEBUG): %s", dict(flow.response.headers))

            try:
                response_data = json.loads(flow.response.content)
                # NEW v0.6.0: Only log full response in debug mode
                if DEBUG_MODE and provider == "kiro":
                    logger.info("KIRO RAW RESPONSE (JSON, DEBUG): %s", json.dumps(response_data, indent=2))
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning("Failed to parse JSON response from %s", provider)
                # NEW v0.6.0: Only log raw content in debug mode
                if DEBUG_MODE and provider == "kiro":
                    raw_preview = flow.response.content[:1000].decode('utf-8', errors='replace')
                    logger.info("KIRO RAW CONTENT (not JSON, first 1000 bytes, DEBUG): %s", raw_preview)
                pass

            if response_data:
                # NEW: Try generic parser first
                if self.generic_parser:
                    try:
                        usage = self.generic_parser.parse_response(provider_name, response_data, is_streaming=False)
                    except Exception as e:
                        logger.warning(f"Generic parser failed for JSON {provider_name}: {e}")
                        usage = parse_response(provider, response_data)
                else:
                    usage = parse_response(provider, response_data)
            else:
                logger.warning("No response data to parse from %s", provider)
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

        # Capture User-Agent to differentiate clients (Kiro IDE vs Kiro CLI, etc.)
        user_agent = flow.request.headers.get("user-agent", "unknown")
        client_type = self._detect_client_type(user_agent, host, provider)

        # Calculate estimated cost
        estimated_cost = 0.0
        if provider_info and provider_info.get("metadata"):
            metadata = provider_info["metadata"]
            cost_per_input = metadata.get("cost_per_input_token", 0)
            cost_per_output = metadata.get("cost_per_output_token", 0)
            estimated_cost = (
                usage.get("input_tokens", 0) * cost_per_input
                + usage.get("output_tokens", 0) * cost_per_output
            )

        # NEW v0.5.0: Extract device information
        device_info = self._extract_device_info(flow, body_dict)

        # NEW v0.6.0: Sanitize messages by default (only full content in debug mode)
        messages_for_event = request_parsed.get("messages", []) if request_parsed else []
        if not DEBUG_MODE and messages_for_event:
            messages_for_event = self._sanitize_messages(messages_for_event)

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "provider": provider,
            "host": host,
            "model": model,
            "path": path,
            "user_agent": user_agent,
            "client_type": client_type,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_tokens", 0),
            "estimated_input_tokens": estimated_input_tokens,
            "messages": messages_for_event,
            "response_status": flow.response.status_code,
            "response_stop_reason": usage.get("stop_reason"),
            "streaming": is_streaming,
            # NEW: Context metadata
            "context": context_metadata,
            "program": context_metadata.get("program_name"),
            "project": context_metadata.get("project_name"),
            # NEW: Provider metadata
            "provider_tags": provider_info.get("metadata", {}).get("tags", []) if provider_info else [],
            "estimated_cost": estimated_cost,
            # NEW: Capture mode
            "capture_mode": "capture_all" if provider_name == "unknown" else "known",
            # NEW v0.5.0: Device tracking
            "device": device_info,
            "device_id": device_info.get("id"),  # Denormalized for fast queries
            # NEW v0.5.0: Smart token detection
            "is_token_consuming": self._is_token_consuming_event(body_dict, provider_name),
            "has_budget_tokens": self._has_budget_tokens(body_dict) if body_dict else False,
        }

        # NEW v0.4.1: Add additional request fields if present (system, tools, thinking, metadata)
        if request_parsed:
            if "system" in request_parsed and request_parsed["system"]:
                event["system"] = request_parsed["system"]
            if "tools" in request_parsed and request_parsed["tools"]:
                event["tools"] = request_parsed["tools"]
            if "thinking" in request_parsed and request_parsed["thinking"]:
                event["thinking"] = request_parsed["thinking"]
            if "metadata" in request_parsed and request_parsed["metadata"]:
                event["request_metadata"] = request_parsed["metadata"]  # Renamed to avoid collision

        logger.info(
            "Recorded %s event: client=%s, model=%s, in=%d, out=%d, cache_read=%d, total=%d tokens",
            provider,
            client_type,
            model,
            event["input_tokens"],
            event["output_tokens"],
            event["cache_read_tokens"],
            event["total_tokens"],
        )

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

            # NEW v0.6.0: Only capture raw payloads in debug mode
            # This prevents accidental capture of sensitive data (API keys, credentials, PII)
            if DEBUG_MODE:
                if body_dict:
                    db_event["raw_request"] = body_dict
                    logger.debug(f"DEBUG MODE: Captured raw request for {provider_name}")

                # Capture full response in debug mode
                should_capture_response = (
                    provider_name == "unknown"
                    or (provider_info and provider_info.get("capture_full_response"))
                    or (self.provider_config and self.provider_config.capture_mode == "capture_all")
                )

                if should_capture_response and response_data:
                    db_event["raw_response"] = response_data
                    logger.debug(f"DEBUG MODE: Captured raw response for {provider_name}")

                # Warn once per startup about debug mode
                if not hasattr(self, "_debug_warning_shown"):
                    logger.warning("⚠️  DEBUG MODE ACTIVE: Capturing raw request/response payloads (may contain sensitive data)")
                    self._debug_warning_shown = True

            try:
                await self.db.insert_event(db_event)
            except Exception:
                logger.exception("Failed to write event to MongoDB")

    # -------------------------------------------------------------------------
    # Context and parsing helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _sanitize_messages(messages: list) -> list:
        """Sanitize message content while preserving structure for categorization.

        Replaces actual content with [REDACTED] but keeps role information.
        This allows analysis of conversation patterns without capturing sensitive data.
        """
        sanitized = []
        for msg in messages:
            if isinstance(msg, dict):
                sanitized_msg = {"role": msg.get("role", "unknown")}
                # Keep content structure but redact actual text
                if "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        sanitized_msg["content"] = "[REDACTED]" if content else ""
                    elif isinstance(content, list):
                        # For multi-part content, keep type info but redact text
                        sanitized_msg["content"] = [
                            {"type": part.get("type", "unknown"), "text": "[REDACTED]"}
                            if part.get("type") == "text" else {"type": part.get("type", "unknown")}
                            for part in content
                        ]
                    else:
                        sanitized_msg["content"] = "[REDACTED]"
                sanitized.append(sanitized_msg)
        return sanitized

    @staticmethod
    def _extract_context_metadata(flow: http.HTTPFlow) -> dict:
        """Extract calling program and project context from headers/environment.

        Looks for custom headers:
        - X-Tokentap-Program: Program name
        - X-Tokentap-Project: Project name
        - X-Tokentap-Context: Full JSON context

        Returns:
            Dict with program_name, project_name, session_id, tags, custom fields
        """
        context = {
            "program_name": flow.request.headers.get("X-Tokentap-Program"),
            "project_name": flow.request.headers.get("X-Tokentap-Project"),
            "session_id": flow.request.headers.get("X-Tokentap-Session"),
            "tags": [],
            "custom": {},
        }

        # Parse full context from X-Tokentap-Context header (JSON)
        context_header = flow.request.headers.get("X-Tokentap-Context")
        if context_header:
            try:
                custom_context = json.loads(context_header)
                # Merge custom context, preserving existing non-None values
                for key, value in custom_context.items():
                    if key in context and context[key] is None:
                        context[key] = value
                    elif key not in context:
                        context["custom"][key] = value
            except json.JSONDecodeError:
                logger.warning("Failed to parse X-Tokentap-Context header")

        # Try to infer from User-Agent if not provided
        if not context["program_name"]:
            ua = flow.request.headers.get("user-agent", "")
            context["program_name"] = TokentapAddon._detect_client_type(ua, flow.request.host, "")

        return context

    @staticmethod
    def _is_parse_quality_acceptable(parsed: dict, original: dict) -> bool:
        """Check if parsed data quality is acceptable.

        Returns False if significant data loss is detected.

        Args:
            parsed: Parsed request data from generic parser
            original: Original request body

        Returns:
            True if quality is acceptable, False if fallback recommended
        """
        # Check if messages array is suspiciously small
        original_messages = original.get("messages", [])
        parsed_messages = parsed.get("messages", [])

        if len(original_messages) > 1 and len(parsed_messages) == 1:
            logger.debug(
                f"Quality check failed: {len(original_messages)} messages in original, "
                f"only {len(parsed_messages)} in parsed"
            )
            return False

        # Check if system prompt exists but wasn't captured
        if "system" in original and original["system"]:
            if not parsed.get("system"):
                logger.debug("Quality check failed: system prompt not captured")
                return False

        # Check if tools array exists but wasn't captured
        if "tools" in original and original["tools"]:
            if not parsed.get("tools"):
                logger.debug("Quality check failed: tools array not captured")
                return False

        return True

    @staticmethod
    def _detect_client_type(user_agent: str, host: str, provider: str) -> str:
        """Detect client type from User-Agent and other context.

        Returns:
            - "kiro-cli" for Kiro CLI
            - "kiro-ide" for Kiro IDE
            - "claude-code" for Claude Code CLI
            - "unknown" for others
        """
        ua_lower = user_agent.lower()

        # Kiro detection (Amazon Q based)
        if "kiro" in ua_lower:
            if "cli" in ua_lower or "command" in ua_lower:
                return "kiro-cli"
            elif "ide" in ua_lower or "editor" in ua_lower or "vscode" in ua_lower:
                return "kiro-ide"
            else:
                return "kiro-cli"  # Default to CLI if ambiguous

        # Claude Code detection
        if "claude" in ua_lower and "code" in ua_lower:
            return "claude-code"

        # If it's Amazon Q domain but not Kiro user-agent, assume CLI
        if provider == "kiro" or "amazonaws.com" in host:
            return "kiro-cli"  # Default assumption

        # Anthropic direct
        if provider == "anthropic":
            return "claude-code"

        return "unknown"

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
        elif provider == "kiro":
            return _parse_amazon_q_request(body_dict)
        return None

    # -------------------------------------------------------------------------
    # NEW v0.5.0: Device tracking and smart filtering
    # -------------------------------------------------------------------------

    def _extract_device_info(self, flow: http.HTTPFlow, body_dict: dict) -> dict:
        """Extract device identification from request.

        Attempts multiple strategies:
        1. Extract from raw_request.events.event_data.device_id (Claude Code)
        2. Extract from raw_request.events.event_data.session_id
        3. Parse User-Agent for OS/platform
        4. Generate fingerprint from IP + hostname
        """
        device_info = {
            "id": None,
            "session_id": None,
            "hostname": None,
            "os_type": None,
            "os_version": None,
            "ip_address": None,
            "user_agent": None,
        }

        # 1. Extract session_id from raw request (Claude Code specific)
        if body_dict and isinstance(body_dict, dict):
            # Check events.event_data.session_id (telemetry events)
            events = body_dict.get("events", [])
            if events and len(events) > 0:
                event_data = events[0].get("event_data", {})
                device_info["session_id"] = event_data.get("session_id")
                device_info["device_id_from_event"] = event_data.get("device_id")

                # Extract platform from env
                env = event_data.get("env", {})
                device_info["os_type"] = env.get("platform")

        # 2. Parse User-Agent for OS details
        user_agent = flow.request.headers.get("user-agent", "")
        device_info["user_agent"] = user_agent

        if user_agent:
            # Use user-agents library to parse
            try:
                from user_agents import parse as parse_ua
                ua = parse_ua(user_agent)
                device_info["os_type"] = device_info["os_type"] or ua.os.family
                device_info["os_version"] = ua.os.version_string
                device_info["browser"] = ua.browser.family
                device_info["is_mobile"] = ua.is_mobile
                device_info["is_bot"] = ua.is_bot
            except Exception as e:
                logger.debug(f"Failed to parse User-Agent: {e}")

        # 3. Get IP address
        if flow.client_conn and flow.client_conn.address:
            device_info["ip_address"] = flow.client_conn.address[0]

        # 4. Generate stable device_id
        # Priority: session_id > device_id_from_event > fingerprint
        device_id = (
            device_info.get("session_id") or
            device_info.get("device_id_from_event") or
            self._generate_device_fingerprint(device_info)
        )
        device_info["id"] = device_id

        return device_info

    @staticmethod
    def _generate_device_fingerprint(device_info: dict) -> str:
        """Generate stable device fingerprint from available info."""
        import hashlib

        # Combine IP + OS + User-Agent to create fingerprint
        components = [
            device_info.get("ip_address", ""),
            device_info.get("os_type", ""),
            device_info.get("user_agent", "")[:50],  # First 50 chars
        ]

        fingerprint_str = "|".join(filter(None, components))
        if not fingerprint_str:
            # Fallback to random ID
            import uuid
            return f"unknown-{uuid.uuid4().hex[:8]}"

        # Generate hash
        hash_obj = hashlib.md5(fingerprint_str.encode())
        return f"device-{hash_obj.hexdigest()[:12]}"

    @staticmethod
    def _is_token_consuming_event(body_dict: dict, provider_name: str) -> bool:
        """Detect if this event represents actual token consumption.

        Returns False for telemetry, logging, health checks.
        Returns True for actual LLM API calls.
        """
        if not body_dict:
            return False

        # Check for budget_tokens (indicates thinking/token budget)
        if TokentapAddon._has_budget_tokens(body_dict):
            return True

        # Check path patterns
        # Token-consuming paths: /v1/messages, /v1/chat/completions, /generateContent
        # Non-consuming: /api/event_logging, /api/hello, /health

        # For now, use provider patterns from config
        if provider_name == "unknown":
            return False

        # If it has messages array, likely token-consuming
        if body_dict.get("messages"):
            return True

        # If it has prompt/contents, likely token-consuming
        if body_dict.get("prompt") or body_dict.get("contents"):
            return True

        return False

    @staticmethod
    def _has_budget_tokens(body_dict: dict) -> bool:
        """Check if request has budget_tokens field."""
        if not body_dict:
            return False

        # Direct field
        if "budget_tokens" in body_dict:
            return True

        # Nested in thinking config
        thinking = body_dict.get("thinking", {})
        if isinstance(thinking, dict) and "budget_tokens" in thinking:
            return True

        return False


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


def _parse_amazon_q_request(body: dict) -> dict:
    """Parse Amazon Q API request body.

    Note: Format is tentative and will be refined once we can intercept actual requests.
    Amazon Q may use various formats depending on the API endpoint.
    """
    result = {
        "provider": "kiro",
        "messages": [],
        "model": body.get("model", "kiro"),
        "total_text": "",
    }

    texts = []

    # Try common AWS formats
    # Format 1: messages array (similar to OpenAI)
    if "messages" in body:
        messages = body.get("messages", [])
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                result["messages"].append({"role": role, "content": content})
                texts.append(content)
            elif isinstance(content, list):
                # Handle structured content
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
                combined = " ".join(text_parts)
                result["messages"].append({"role": role, "content": combined})
                texts.append(combined)

    # Format 2: prompt field (simple format)
    elif "prompt" in body:
        prompt = body.get("prompt", "")
        result["messages"].append({"role": "user", "content": prompt})
        texts.append(prompt)

    # Format 3: inputText field (another AWS format)
    elif "inputText" in body:
        input_text = body.get("inputText", "")
        result["messages"].append({"role": "user", "content": input_text})
        texts.append(input_text)

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
