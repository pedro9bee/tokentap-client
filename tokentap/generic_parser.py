"""Generic request/response parser using provider configuration templates."""

import json
import logging
from typing import Any

from tokentap.provider_config import ProviderConfig

logger = logging.getLogger(__name__)


class GenericParser:
    """Template-based parser for LLM API requests and responses."""

    def __init__(self, provider_config: ProviderConfig):
        """Initialize with provider configuration.

        Args:
            provider_config: ProviderConfig instance with loaded configurations
        """
        self.config = provider_config

    def parse_request(self, provider_name: str, body: dict) -> dict:
        """Extract request metadata using provider config.

        Args:
            provider_name: Name of the provider (e.g., "anthropic")
            body: Request body as dict

        Returns:
            Dict with extracted request metadata
        """
        if provider_name not in self.config.providers:
            logger.warning(f"Unknown provider: {provider_name}")
            return {"provider": provider_name, "model": "unknown", "messages": [], "total_text": ""}

        provider = self.config.providers[provider_name]
        req_config = provider.request

        result = {
            "provider": provider_name,
            "model": self.config.extract_field(body, req_config.model_path, "unknown"),
            "messages": [],
            "total_text": "",
            "system": None,
            "is_streaming": False,
        }

        # Extract messages
        if req_config.messages_path:
            messages = self.config.extract_field(body, req_config.messages_path)
            if messages:
                result["messages"] = messages if isinstance(messages, list) else [messages]

        # Extract system prompt
        if req_config.system_path:
            result["system"] = self.config.extract_field(body, req_config.system_path)

        # Extract streaming flag
        if req_config.stream_param_path:
            result["is_streaming"] = bool(self.config.extract_field(body, req_config.stream_param_path, False))

        # Extract text for token counting
        text_parts = []
        for text_path in req_config.text_fields:
            value = self.config.extract_field(body, text_path)
            if value:
                if isinstance(value, list):
                    text_parts.extend(str(v) for v in value if v)
                else:
                    text_parts.append(str(value))

        result["total_text"] = "\n".join(text_parts)

        logger.debug(f"Parsed {provider_name} request: model={result['model']}, messages={len(result['messages'])}")
        return result

    def parse_response(self, provider_name: str, response_data: dict | list[bytes], is_streaming: bool = False) -> dict:
        """Extract tokens from response using provider config.

        Args:
            provider_name: Name of the provider
            response_data: Response data (dict for JSON, list of bytes for SSE)
            is_streaming: Whether this is a streaming response

        Returns:
            Dict with extracted token usage
        """
        if provider_name not in self.config.providers:
            logger.warning(f"Unknown provider: {provider_name}")
            return self._default_response(provider_name)

        provider = self.config.providers[provider_name]
        resp_config = provider.response

        if is_streaming and resp_config.sse:
            return self._parse_sse_response(provider_name, response_data, resp_config.sse)
        elif resp_config.json:
            return self._parse_json_response(provider_name, response_data, resp_config.json)
        else:
            logger.warning(f"No response config for {provider_name}")
            return self._default_response(provider_name)

    def _parse_json_response(self, provider_name: str, data: dict, json_config: Any) -> dict:
        """Extract tokens from JSON response.

        Args:
            provider_name: Name of the provider
            data: Response JSON data
            json_config: ProviderResponseJsonConfig object

        Returns:
            Dict with extracted token counts
        """
        result = {
            "provider": provider_name,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "model": None,
            "stop_reason": None,
        }

        # Extract input tokens
        result["input_tokens"] = self.config.extract_field_with_fallbacks(
            data, json_config.input_tokens_path, json_config.input_tokens_path_alt, 0
        )

        # Extract output tokens
        result["output_tokens"] = self.config.extract_field_with_fallbacks(
            data, json_config.output_tokens_path, json_config.output_tokens_path_alt, 0
        )

        # Extract cache tokens
        if json_config.cache_creation_tokens_path:
            result["cache_creation_tokens"] = self.config.extract_field(
                data, json_config.cache_creation_tokens_path, 0
            )
        if json_config.cache_read_tokens_path:
            result["cache_read_tokens"] = self.config.extract_field(data, json_config.cache_read_tokens_path, 0)

        # Extract model
        if json_config.model_path:
            result["model"] = self.config.extract_field(data, json_config.model_path)

        # Extract stop reason
        if json_config.stop_reason_path:
            result["stop_reason"] = self.config.extract_field_with_fallbacks(
                data, json_config.stop_reason_path, json_config.stop_reason_path_alt
            )

        logger.debug(
            f"Parsed {provider_name} JSON response: in={result['input_tokens']}, out={result['output_tokens']}"
        )
        return result

    def _parse_sse_response(self, provider_name: str, chunks: list[bytes], sse_config: Any) -> dict:
        """Parse SSE stream using config.

        Args:
            provider_name: Name of the provider
            chunks: List of response chunks
            sse_config: ProviderResponseSseConfig object

        Returns:
            Dict with extracted token counts
        """
        result = {
            "provider": provider_name,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "model": None,
            "stop_reason": None,
        }

        full_text = b"".join(chunks).decode("utf-8", errors="replace")

        # Handle different SSE formats
        format_type = getattr(sse_config, "format", None)

        if format_type == "json_lines" or format_type == "sse_or_json_lines":
            # Try JSON lines format (Gemini, Amazon Q fallback)
            result = self._parse_json_lines(full_text, sse_config, result)
            if result["model"] or result["input_tokens"] > 0:
                return result

        # Try SSE format (Anthropic, OpenAI, Amazon Q)
        for line in full_text.split("\n"):
            line = line.strip()
            if not line.startswith("data: "):
                continue

            json_str = line[6:]

            # Check for done marker
            done_marker = getattr(sse_config, "done_marker", None)
            if done_marker and json_str == done_marker:
                continue

            try:
                data = json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                continue

            # Extract based on event type matching
            event_type = data.get("type", "")

            # Input tokens
            if self._should_extract_for_event(event_type, sse_config.input_tokens_event):
                if sse_config.input_tokens_path:
                    value = self.config.extract_field_with_fallbacks(
                        data, sse_config.input_tokens_path, sse_config.input_tokens_path_alt
                    )
                    if value is not None:
                        result["input_tokens"] = value

            # Output tokens
            if self._should_extract_for_event(event_type, sse_config.output_tokens_event):
                if sse_config.output_tokens_path:
                    value = self.config.extract_field_with_fallbacks(
                        data, sse_config.output_tokens_path, sse_config.output_tokens_path_alt
                    )
                    if value is not None:
                        result["output_tokens"] = value

            # Cache creation tokens
            if self._should_extract_for_event(event_type, sse_config.cache_creation_tokens_event):
                if sse_config.cache_creation_tokens_path:
                    value = self.config.extract_field(data, sse_config.cache_creation_tokens_path)
                    if value is not None:
                        result["cache_creation_tokens"] = value

            # Cache read tokens
            if self._should_extract_for_event(event_type, sse_config.cache_read_tokens_event):
                if sse_config.cache_read_tokens_path:
                    value = self.config.extract_field(data, sse_config.cache_read_tokens_path)
                    if value is not None:
                        result["cache_read_tokens"] = value

            # Model
            if self._should_extract_for_event(event_type, sse_config.model_event):
                if sse_config.model_path:
                    value = self.config.extract_field(data, sse_config.model_path)
                    if value is not None:
                        result["model"] = value

            # Stop reason
            if self._should_extract_for_event(event_type, sse_config.stop_reason_event):
                if sse_config.stop_reason_path:
                    value = self.config.extract_field(data, sse_config.stop_reason_path)
                    if value is not None:
                        result["stop_reason"] = value

        # For use_last_chunk format (Gemini)
        if getattr(sse_config, "use_last_chunk", False):
            result = self._parse_last_chunk(full_text, sse_config, result)

        logger.debug(
            f"Parsed {provider_name} SSE response: in={result['input_tokens']}, out={result['output_tokens']}"
        )
        return result

    def _parse_json_lines(self, full_text: str, sse_config: Any, result: dict) -> dict:
        """Parse JSON lines format (newline-delimited JSON).

        Args:
            full_text: Full response text
            sse_config: SSE configuration
            result: Result dict to update

        Returns:
            Updated result dict
        """
        last_valid = None
        for line in full_text.split("\n"):
            line = line.strip().strip(",[]")
            if not line:
                continue
            try:
                last_valid = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

        if last_valid:
            # Extract from last valid JSON
            if sse_config.input_tokens_path:
                value = self.config.extract_field_with_fallbacks(
                    last_valid, sse_config.input_tokens_path, sse_config.input_tokens_path_alt
                )
                if value is not None:
                    result["input_tokens"] = value

            if sse_config.output_tokens_path:
                value = self.config.extract_field_with_fallbacks(
                    last_valid, sse_config.output_tokens_path, sse_config.output_tokens_path_alt
                )
                if value is not None:
                    result["output_tokens"] = value

            if sse_config.model_path:
                value = self.config.extract_field(last_valid, sse_config.model_path)
                if value is not None:
                    result["model"] = value

        return result

    def _parse_last_chunk(self, full_text: str, sse_config: Any, result: dict) -> dict:
        """Parse last chunk for providers like Gemini.

        Args:
            full_text: Full response text
            sse_config: SSE configuration
            result: Result dict to update

        Returns:
            Updated result dict
        """
        # Try parsing as JSON array first
        try:
            data_list = json.loads(full_text)
            if isinstance(data_list, list) and data_list:
                last = data_list[-1]
                if sse_config.input_tokens_path:
                    value = self.config.extract_field(last, sse_config.input_tokens_path)
                    if value is not None:
                        result["input_tokens"] = value
                if sse_config.output_tokens_path:
                    value = self.config.extract_field(last, sse_config.output_tokens_path)
                    if value is not None:
                        result["output_tokens"] = value
        except (json.JSONDecodeError, ValueError):
            pass

        return result

    def _should_extract_for_event(self, event_type: str, expected_event: str | None) -> bool:
        """Check if we should extract data for this event type.

        Args:
            event_type: Actual event type from SSE
            expected_event: Expected event type from config (or None for all events)

        Returns:
            True if should extract
        """
        if expected_event is None:
            return True  # No event filter, extract from all events
        if expected_event == "*":
            return True  # Wildcard, extract from all events
        return event_type == expected_event

    def _default_response(self, provider_name: str) -> dict:
        """Return default response when parsing fails.

        Args:
            provider_name: Name of the provider

        Returns:
            Dict with default zero values
        """
        return {
            "provider": provider_name,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "model": "unknown",
            "stop_reason": None,
        }
