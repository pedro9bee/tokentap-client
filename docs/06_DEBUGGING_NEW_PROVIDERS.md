# Debugging and Adding New Providers

This guide walks you through adding support for a new LLM provider to tokentap without writing code.

## Overview

Adding a new provider involves:

1. Enable "capture all" mode to log full requests/responses
2. Make test requests to the new provider
3. Inspect captured data in MongoDB
4. Extract JSONPath expressions for field locations
5. Create provider configuration
6. Test and refine

## Step 1: Enable Capture All Mode

Create or edit `~/.tokentap/providers.json`:

```json
{
  "version": "1.0",
  "capture_mode": "capture_all"
}
```

Reload configuration:

```bash
tokentap reload-config
```

## Step 2: Make Test Requests

Use your new LLM CLI tool through the tokentap proxy:

```bash
# Make sure proxy is running
tokentap status

# Configure environment
eval "$(tokentap shell-init)"

# Make test request
your-new-llm-cli "Write hello world"
```

## Step 3: Inspect Captured Data

Query MongoDB to view captured requests/responses:

```bash
# Connect to MongoDB
docker exec -it tokentap-client-mongodb-1 mongosh tokentap

# Find recent unknown provider events
db.events.find({provider: "unknown"}).sort({timestamp: -1}).limit(1).pretty()

# or filter by host
db.events.find({host: /your-api-domain/}).sort({timestamp: -1}).limit(1).pretty()
```

Example output:

```json
{
  "provider": "unknown",
  "host": "api.newprovider.com",
  "capture_mode": "capture_all",
  "raw_request": {
    "model": "new-model-v1",
    "messages": [
      {"role": "user", "content": "Write hello world"}
    ]
  },
  "raw_response": {
    "model": "new-model-v1",
    "usage": {
      "promptTokens": 10,
      "completionTokens": 20
    },
    "choices": [
      {"text": "print('Hello, World!')"}
    ]
  }
}
```

## Step 4: Extract Field Paths

Identify where fields are located using JSONPath:

### Request Fields

From `raw_request`, find:

- **Model**: `$.model` → `"new-model-v1"`
- **Messages**: `$.messages[*]` → array of messages
- **Text content**: `$.messages[*].content` → `["Write hello world"]`

### Response Fields

From `raw_response`, find:

- **Input tokens**: `$.usage.promptTokens` → `10`
- **Output tokens**: `$.usage.completionTokens` → `20`
- **Model** (if echoed): `$.model` → `"new-model-v1"`

## Step 5: Create Provider Configuration

Add to `~/.tokentap/providers.json`:

```json
{
  "version": "1.0",
  "capture_mode": "known_only",
  "providers": {
    "newprovider": {
      "name": "New Provider",
      "enabled": true,
      "domains": ["api.newprovider.com"],
      "api_patterns": ["/v1/completions", "/v1/chat"],

      "request": {
        "model_path": "$.model",
        "messages_path": "$.messages[*]",
        "text_fields": ["$.messages[*].content"]
      },

      "response": {
        "json": {
          "input_tokens_path": "$.usage.promptTokens",
          "output_tokens_path": "$.usage.completionTokens",
          "model_path": "$.model"
        }
      },

      "metadata": {
        "tags": ["llm", "chat", "newprovider"],
        "cost_per_input_token": 0.000001,
        "cost_per_output_token": 0.000002
      }
    }
  }
}
```

## Step 6: Test and Refine

Reload configuration:

```bash
tokentap reload-config
```

Make another test request:

```bash
your-new-llm-cli "Test message"
```

Verify it's captured correctly:

```bash
docker exec -it tokentap-client-mongodb-1 mongosh tokentap
db.events.find({provider: "newprovider"}).sort({timestamp: -1}).limit(1).pretty()
```

Check that:
- `provider` is `"newprovider"` (not `"unknown"`)
- `input_tokens` and `output_tokens` have correct values
- `model` is populated
- `capture_mode` is `"known"` (not `"capture_all"`)

## Handling Streaming Responses

If the provider uses SSE (Server-Sent Events) streaming:

### Capture Streaming Data

With `capture_mode: "capture_all"`, make a streaming request:

```bash
your-new-llm-cli --stream "Write hello world"
```

Inspect the captured data:

```bash
db.events.find({provider: "unknown", streaming: true}).limit(1).pretty()
```

Look at `raw_response` which will contain accumulated stream chunks.

### Configure SSE Parsing

Example for SSE format like Anthropic:

```json
"response": {
  "json": { /* ... */ },
  "sse": {
    "event_types": ["chunk_start", "chunk_delta", "chunk_end"],
    "input_tokens_event": "chunk_start",
    "input_tokens_path": "$.usage.input_tokens",
    "output_tokens_event": "chunk_delta",
    "output_tokens_path": "$.usage.output_tokens"
  }
}
```

### Testing Streaming

1. Make streaming request
2. Check MongoDB event
3. Verify `streaming: true` and tokens captured correctly

## Fallback Paths for Inconsistent APIs

If the provider uses different field names in different scenarios:

```json
"input_tokens_path": "$.usage.inputTokens",
"input_tokens_path_alt": [
  "$.usage.input_tokens",
  "$.usage.promptTokens",
  "$.tokenUsage.input"
]
```

The parser tries each path in order until one succeeds.

## Common Issues

### Issue: Tokens Always Zero

**Cause**: Wrong JSONPath

**Solution**:
1. Look at `raw_response` in MongoDB
2. Find exact location of token counts
3. Update paths in config
4. Reload and test

### Issue: Provider Not Detected

**Cause**: Domain mismatch

**Solution**:
1. Check `host` field in captured events
2. Add exact host to `domains` array:
   ```json
   "domains": ["api.provider.com", "api-eu.provider.com"]
   ```

### Issue: Streaming Not Working

**Cause**: Stream detection or parsing config

**Solution**:
1. Check `streaming` field in event (should be `true`)
2. Verify SSE config event types match actual events
3. Look at raw stream data format

## Examples

### Example 1: Simple JSON API

API format:
```json
// Request
{"model": "simple-v1", "prompt": "Hello"}

// Response
{"tokens_in": 5, "tokens_out": 10}
```

Config:
```json
"simple-provider": {
  "domains": ["api.simple.com"],
  "request": {
    "model_path": "$.model",
    "text_fields": ["$.prompt"]
  },
  "response": {
    "json": {
      "input_tokens_path": "$.tokens_in",
      "output_tokens_path": "$.tokens_out"
    }
  }
}
```

### Example 2: Nested Usage Object

API format:
```json
// Response
{
  "result": { /* ... */ },
  "metadata": {
    "tokenUsage": {
      "request": 100,
      "response": 200
    }
  }
}
```

Config:
```json
"response": {
  "json": {
    "input_tokens_path": "$.metadata.tokenUsage.request",
    "output_tokens_path": "$.metadata.tokenUsage.response"
  }
}
```

## Sharing Your Configuration

Once you have a working config, consider:

1. **Contributing** to tokentap: Submit a PR to add it to `providers.json`
2. **Documenting** edge cases and tips
3. **Testing** with multiple model types

## See Also

- [Provider Configuration Reference](PROVIDER_CONFIGURATION.md)
- [Context Metadata](CONTEXT_METADATA.md)
- [Service Management](SERVICE_MANAGEMENT.md)
