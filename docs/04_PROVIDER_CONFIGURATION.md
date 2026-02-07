# Provider Configuration Guide

Tokentap uses a dynamic JSON configuration system that allows you to add new LLM providers without modifying code.

## Quick Start

```bash
# Create user config (overrides defaults)
mkdir -p ~/.tokentap
cp tokentap/providers.json ~/.tokentap/providers.json

# Edit to add your provider
vim ~/.tokentap/providers.json

# Reload configuration (hot reload)
tokentap reload-config
```

## Configuration Files

- **Default**: `tokentap/providers.json` (shipped with package)
- **User Override**: `~/.tokentap/providers.json` (your custom settings)

User config is deep-merged with defaults, so you only need to specify what changes.

## Configuration Schema

### Basic Provider Example

```json
{
  "version": "1.0",
  "capture_mode": "known_only",
  "providers": {
    "my-provider": {
      "name": "My LLM Provider",
      "enabled": true,
      "domains": ["api.example.com"],
      "api_patterns": ["/v1/chat", "/v1/completions"],

      "request": {
        "model_path": "$.model",
        "messages_path": "$.messages[*]",
        "text_fields": ["$.messages[*].content"]
      },

      "response": {
        "json": {
          "input_tokens_path": "$.usage.input_tokens",
          "output_tokens_path": "$.usage.output_tokens"
        }
      },

      "metadata": {
        "tags": ["llm", "chat"],
        "cost_per_input_token": 0.000001,
        "cost_per_output_token": 0.000002
      }
    }
  }
}
```

## JSONPath Syntax

Tokentap uses JSONPath expressions to extract fields from requests/responses:

| Pattern | Description | Example |
|---------|-------------|---------|
| `$.field` | Top-level field | `$.model` → `"gpt-4"` |
| `$.nested.field` | Nested field | `$.usage.input_tokens` → `100` |
| `$.array[0]` | Array index | `$.messages[0]` → first message |
| `$.array[*]` | All array elements | `$.messages[*].content` → all message contents |

### Examples

Given JSON:
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there"}
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20
  }
}
```

Extractions:
- `$.model` → `"gpt-4"`
- `$.messages[*].content` → `["Hello", "Hi there"]`
- `$.usage.prompt_tokens` → `10`

## Request Configuration

```json
"request": {
  "model_path": "$.model",                    // Required: where to find model name
  "messages_path": "$.messages[*]",           // Optional: array of messages
  "system_path": "$.system",                  // Optional: system prompt
  "stream_param_path": "$.stream",            // Optional: streaming flag
  "text_fields": ["$.messages[*].content"]    // Required: text for token counting
}
```

## Response Configuration

### JSON Responses

```json
"response": {
  "json": {
    "input_tokens_path": "$.usage.input_tokens",   // Required
    "output_tokens_path": "$.usage.output_tokens", // Required
    "cache_creation_tokens_path": "$.usage.cache_creation_tokens", // Optional
    "cache_read_tokens_path": "$.usage.cache_read_tokens",         // Optional
    "model_path": "$.model",                        // Optional
    "stop_reason_path": "$.stop_reason"            // Optional
  }
}
```

### SSE (Streaming) Responses

```json
"response": {
  "sse": {
    "event_types": ["message_start", "message_delta"],
    "input_tokens_event": "message_start",
    "input_tokens_path": "$.message.usage.input_tokens",
    "output_tokens_event": "message_delta",
    "output_tokens_path": "$.usage.output_tokens"
  }
}
```

## Fallback Paths

For providers with inconsistent field names:

```json
"input_tokens_path": "$.usage.inputTokens",
"input_tokens_path_alt": ["$.usage.input_tokens", "$.usage.promptTokens"]
```

The parser tries `input_tokens_path` first, then each alternative in order.

## Capture Modes

### known_only (default)

Only captures traffic for configured providers:

```json
{"capture_mode": "known_only"}
```

### capture_all

Captures ALL HTTPS traffic with full request/response logging for analysis:

```json
{"capture_mode": "capture_all"}
```

Use this to experiment with new providers, then create a proper config once you understand the format.

## Adding a New Provider

See [DEBUGGING_NEW_PROVIDERS.md](DEBUGGING_NEW_PROVIDERS.md) for step-by-step guide.

Quick version:

1. Set `capture_mode: "capture_all"` in `~/.tokentap/providers.json`
2. Make test requests to the new provider
3. Query MongoDB to inspect captured data:
   ```bash
   docker exec -it tokentap-client-mongodb-1 mongosh tokentap
   db.events.find({provider:"unknown"}).limit(1).pretty()
   ```
4. Extract field paths from `raw_request` and `raw_response`
5. Create provider config
6. Reload: `tokentap reload-config`

## Examples

### Anthropic (Built-in)

```json
"anthropic": {
  "domains": ["api.anthropic.com"],
  "request": {
    "model_path": "$.model",
    "messages_path": "$.messages[*]",
    "text_fields": ["$.messages[*].content", "$.system"]
  },
  "response": {
    "json": {
      "input_tokens_path": "$.usage.input_tokens",
      "output_tokens_path": "$.usage.output_tokens"
    }
  }
}
```

### Custom Provider Example

```json
"my-custom-llm": {
  "name": "Custom LLM",
  "enabled": true,
  "domains": ["api.custom-llm.com"],
  "request": {
    "model_path": "$.modelId",
    "messages_path": "$.conversation[*]",
    "text_fields": ["$.conversation[*].text"]
  },
  "response": {
    "json": {
      "input_tokens_path": "$.tokens.input",
      "output_tokens_path": "$.tokens.output"
    }
  }
}
```

## Metadata Fields

```json
"metadata": {
  "tags": ["llm", "chat", "custom-tag"],
  "cost_per_input_token": 0.000001,
  "cost_per_output_token": 0.000002
}
```

These are stored in events and used for:
- Filtering by tags
- Cost estimation
- Provider categorization

## Validation

Tokentap validates configs on load using Pydantic. Common errors:

- **Missing required fields**: Add `model_path`, `input_tokens_path`, `output_tokens_path`
- **Invalid JSONPath**: Check syntax, use `$.` prefix
- **Invalid capture_mode**: Must be `"known_only"` or `"capture_all"`

## See Also

- [Debugging New Providers](DEBUGGING_NEW_PROVIDERS.md)
- [Context Metadata](CONTEXT_METADATA.md)
- [Service Management](SERVICE_MANAGEMENT.md)
