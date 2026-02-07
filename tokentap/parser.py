"""Request parsing and token counting utilities."""

from typing import Any

import tiktoken


def get_encoding():
    """Get the tiktoken encoding for token counting."""
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken cl100k_base encoding."""
    if not text:
        return 0
    encoding = get_encoding()
    return len(encoding.encode(text))


def extract_text_from_content(content: Any) -> str:
    """Extract text from various content formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    texts.append(item["text"])
                elif "content" in item:
                    texts.append(extract_text_from_content(item["content"]))
        return " ".join(texts)
    if isinstance(content, dict):
        if "text" in content:
            return content["text"]
        if "content" in content:
            return extract_text_from_content(content["content"])
    return ""


def parse_anthropic_request(body: dict) -> dict:
    """Parse Anthropic API request body.

    Returns dict with:
        - messages: list of message dicts with role and content
        - model: model name
        - system: system prompt if present
        - total_text: concatenated text for token counting
    """
    result = {
        "provider": "anthropic",
        "messages": [],
        "model": body.get("model", "unknown"),
        "system": None,
        "total_text": "",
    }

    texts = []

    # Extract system prompt
    system = body.get("system")
    if system:
        system_text = extract_text_from_content(system)
        result["system"] = system_text
        texts.append(system_text)
        result["messages"].append({"role": "system", "content": system_text})

    # Extract messages
    messages = body.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = extract_text_from_content(msg.get("content", ""))
        result["messages"].append({"role": role, "content": content})
        texts.append(content)

    result["total_text"] = "\n".join(texts)
    return result


