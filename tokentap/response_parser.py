"""Response parsing utilities for extracting token usage from API responses."""

import json


def parse_anthropic_response(data: dict) -> dict:
    """Extract token usage from an Anthropic API response.

    Handles both regular and streaming responses.
    For streaming, call with the final accumulated message_delta data.
    """
    usage = data.get("usage", {})
    return {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
        "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
        "model": data.get("model", "unknown"),
        "stop_reason": data.get("stop_reason"),
    }


def parse_openai_response(data: dict) -> dict:
    """Extract token usage from an OpenAI API response."""
    usage = data.get("usage", {})
    return {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "model": data.get("model", "unknown"),
        "stop_reason": _get_openai_stop_reason(data),
    }


def _get_openai_stop_reason(data: dict) -> str | None:
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("finish_reason")
    return None


def parse_gemini_response(data: dict) -> dict:
    """Extract token usage from a Gemini API response."""
    usage = data.get("usageMetadata", {})
    return {
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
        "cache_creation_tokens": 0,
        "cache_read_tokens": usage.get("cachedContentTokenCount", 0),
        "model": "gemini",
        "stop_reason": _get_gemini_stop_reason(data),
    }


def _get_gemini_stop_reason(data: dict) -> str | None:
    candidates = data.get("candidates", [])
    if candidates:
        return candidates[0].get("finishReason")
    return None


def parse_amazon_q_response(data: dict) -> dict:
    """Extract token usage from an Amazon Q API response.

    Note: Format is tentative and will be refined once we can intercept actual responses.
    Amazon Q may use various formats depending on the API endpoint.
    """
    # Try common AWS token usage formats
    usage = data.get("usage", {}) or data.get("tokenUsage", {}) or data.get("usage_metadata", {})

    # Try different field names for tokens
    input_tokens = (
        usage.get("inputTokens")
        or usage.get("input_tokens")
        or usage.get("promptTokens")
        or 0
    )
    output_tokens = (
        usage.get("outputTokens")
        or usage.get("output_tokens")
        or usage.get("completionTokens")
        or 0
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "model": data.get("model", "amazon-q"),
        "stop_reason": data.get("stopReason") or data.get("stop_reason"),
    }


def parse_response(provider: str, data: dict) -> dict:
    """Parse a response based on provider type."""
    parsers = {
        "anthropic": parse_anthropic_response,
        "openai": parse_openai_response,
        "gemini": parse_gemini_response,
        "amazon-q": parse_amazon_q_response,
    }
    parser = parsers.get(provider)
    if parser:
        return parser(data)
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "model": "unknown",
        "stop_reason": None,
    }


def parse_sse_stream(provider: str, chunks: list[bytes]) -> dict:
    """Parse accumulated SSE stream chunks to extract final usage data.

    For Anthropic: looks for message_delta event with usage, and message_start for model.
    For OpenAI: looks for final chunk with usage (before [DONE]).
    For Gemini: aggregates from the last chunk (not SSE, just JSON lines).
    For Amazon Q: similar to OpenAI SSE format.
    """
    result = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "model": "unknown",
        "stop_reason": None,
    }

    if provider == "anthropic":
        return _parse_anthropic_stream(chunks, result)
    elif provider == "openai":
        return _parse_openai_stream(chunks, result)
    elif provider == "gemini":
        return _parse_gemini_stream(chunks, result)
    elif provider == "amazon-q":
        return _parse_amazon_q_stream(chunks, result)
    return result


def _parse_anthropic_stream(chunks: list[bytes], result: dict) -> dict:
    """Parse Anthropic SSE stream for usage data."""
    full_text = b"".join(chunks).decode("utf-8", errors="replace")
    for line in full_text.split("\n"):
        line = line.strip()
        if not line.startswith("data: "):
            continue
        json_str = line[6:]
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            continue

        event_type = data.get("type", "")

        if event_type == "message_start":
            message = data.get("message", {})
            result["model"] = message.get("model", result["model"])
            usage = message.get("usage", {})
            result["input_tokens"] = usage.get("input_tokens", 0)
            result["cache_creation_tokens"] = usage.get("cache_creation_input_tokens", 0)
            result["cache_read_tokens"] = usage.get("cache_read_input_tokens", 0)

        elif event_type == "message_delta":
            usage = data.get("usage", {})
            result["output_tokens"] = usage.get("output_tokens", result["output_tokens"])
            result["stop_reason"] = data.get("delta", {}).get("stop_reason", result["stop_reason"])

    return result


def _parse_openai_stream(chunks: list[bytes], result: dict) -> dict:
    """Parse OpenAI SSE stream for usage data."""
    full_text = b"".join(chunks).decode("utf-8", errors="replace")
    for line in full_text.split("\n"):
        line = line.strip()
        if not line.startswith("data: "):
            continue
        json_str = line[6:]
        if json_str == "[DONE]":
            continue
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            continue

        if data.get("model"):
            result["model"] = data["model"]

        usage = data.get("usage")
        if usage:
            result["input_tokens"] = usage.get("prompt_tokens", result["input_tokens"])
            result["output_tokens"] = usage.get("completion_tokens", result["output_tokens"])

        choices = data.get("choices", [])
        if choices and choices[0].get("finish_reason"):
            result["stop_reason"] = choices[0]["finish_reason"]

    return result


def _parse_gemini_stream(chunks: list[bytes], result: dict) -> dict:
    """Parse Gemini streaming response for usage data.

    Gemini streaming returns JSON array or newline-delimited JSON.
    Usage metadata is typically in the last chunk.
    """
    full_text = b"".join(chunks).decode("utf-8", errors="replace")
    # Try parsing as JSON array first
    try:
        data_list = json.loads(full_text)
        if isinstance(data_list, list) and data_list:
            last = data_list[-1]
            return parse_gemini_response(last)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try line-by-line JSON
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
        return parse_gemini_response(last_valid)

    return result


def _parse_amazon_q_stream(chunks: list[bytes], result: dict) -> dict:
    """Parse Amazon Q SSE stream for usage data.

    Note: Format is tentative. Amazon Q may use SSE format similar to OpenAI
    or a custom AWS event stream format.
    """
    full_text = b"".join(chunks).decode("utf-8", errors="replace")

    # Try SSE format (like OpenAI)
    for line in full_text.split("\n"):
        line = line.strip()
        if not line.startswith("data: "):
            continue
        json_str = line[6:]
        if json_str == "[DONE]":
            continue
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            continue

        if data.get("model"):
            result["model"] = data["model"]

        # Try various usage field formats
        usage = data.get("usage") or data.get("tokenUsage")
        if usage:
            result["input_tokens"] = (
                usage.get("inputTokens") or usage.get("input_tokens") or usage.get("promptTokens") or result["input_tokens"]
            )
            result["output_tokens"] = (
                usage.get("outputTokens") or usage.get("output_tokens") or usage.get("completionTokens") or result["output_tokens"]
            )

        # Try to get stop reason
        stop_reason = data.get("stopReason") or data.get("stop_reason")
        if stop_reason:
            result["stop_reason"] = stop_reason

    # If SSE didn't work, try AWS Event Stream format
    if result["model"] == "unknown":
        # Try parsing as newline-delimited JSON
        last_valid = None
        for line in full_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                last_valid = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

        if last_valid:
            return parse_amazon_q_response(last_valid)

    return result
