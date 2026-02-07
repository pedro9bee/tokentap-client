# Architecture

Technical overview of how Tokentap works.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ LLM CLI Tools (Claude Code, Codex, Gemini, etc.)           │
│ Uses: HTTPS_PROXY=http://127.0.0.1:8080                    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS Traffic
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ mitmproxy (Port 8080)                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ TokentapAddon                                           │ │
│ │ • Intercepts HTTPS by domain                            │ │
│ │ • Parses requests (JSONPath + provider config)          │ │
│ │ • Parses responses (JSON + SSE streams)                 │ │
│ │ • Extracts token usage                                  │ │
│ │ • Captures context metadata                             │ │
│ └────────────────┬───────────────────────────────────────┘ │
└──────────────────┼──────────────────────────────────────────┘
                   │ Forward to upstream
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM APIs (api.anthropic.com, api.openai.com, etc.)         │
└─────────────────────────────────────────────────────────────┘
                   │
                   │ Token usage + metadata
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ MongoDB (tokentap.events collection)                        │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API queries
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Web Dashboard (FastAPI + Alpine.js)                         │
│ http://localhost:3000                                       │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. mitmproxy (Proxy)

**Technology**: mitmproxy 10.0+

**Purpose**: HTTPS interception via MITM (Man-In-The-Middle) proxy

**How it works**:
1. Client sets `HTTPS_PROXY=http://127.0.0.1:8080`
2. mitmproxy intercepts HTTPS CONNECT
3. Generates fake certificate (signed by mitmproxy CA)
4. Decrypts HTTPS traffic
5. Applies TokentapAddon for parsing
6. Forwards to upstream API

**Key Features**:
- Regular mode (not reverse proxy)
- Domain-based filtering
- SSE stream capture
- Health check endpoint (`/health`)

### 2. TokentapAddon

**Technology**: Python mitmproxy addon

**Purpose**: Parse LLM API traffic and extract token usage

**Hooks**:
- `request()`: Detect provider, start timer, extract context
- `responseheaders()`: Configure streaming for SSE responses
- `response()`: Parse response, extract tokens, write to DB

**Provider Detection**:
1. Check domain against `providers.json` config
2. Dynamic lookup via `ProviderConfig.get_provider_by_domain()`
3. Fallback to "unknown" if `capture_mode: "capture_all"`

**Parsing**:
1. **Request**: Extract model, messages, text (for token counting)
2. **Response JSON**: Extract input_tokens, output_tokens via JSONPath
3. **Response SSE**: Accumulate stream chunks, parse events

**Database Write**:
- Async write to MongoDB via motor driver
- Fire-and-forget (doesn't block request)

### 3. Dynamic Provider Configuration

**Technology**: JSON + JSONPath + Pydantic validation

**Files**:
- `tokentap/providers.json` (default, shipped)
- `~/.tokentap/providers.json` (user overrides, merged)

**Components**:
- `provider_config.py`: Loader, validator, JSONPath extractor
- `generic_parser.py`: Template-based request/response parser

**Provider Config Schema**:
```json
{
  "providers": {
    "provider-name": {
      "domains": ["api.example.com"],
      "request": {
        "model_path": "$.model",
        "text_fields": ["$.messages[*].content"]
      },
      "response": {
        "json": {
          "input_tokens_path": "$.usage.input_tokens",
          "output_tokens_path": "$.usage.output_tokens"
        }
      }
    }
  }
}
```

**Fallback Chain**:
1. Try generic parser with provider config
2. Fall back to hardcoded parsers (Anthropic, OpenAI, Gemini, Kiro)
3. Fall back to zero tokens with warning

### 4. MongoDB

**Technology**: MongoDB 7.0 (Docker)

**Database**: `tokentap`
**Collection**: `events`

**Event Schema**:
```json
{
  "timestamp": ISODate,
  "duration_ms": int,
  "provider": string,
  "model": string,
  "input_tokens": int,
  "output_tokens": int,
  "total_tokens": int,
  "cache_creation_tokens": int,
  "cache_read_tokens": int,
  "estimated_input_tokens": int,
  "messages": array,
  "response_status": int,
  "response_stop_reason": string,
  "streaming": boolean,
  "user_agent": string,
  "client_type": string,

  // NEW in v0.4.0
  "context": {
    "program_name": string,
    "project_name": string,
    "session_id": string,
    "tags": array,
    "custom": object
  },
  "program": string,
  "project": string,
  "provider_tags": array,
  "estimated_cost": float,
  "capture_mode": string,
  "raw_request": object,   // if capture_mode="capture_all"
  "raw_response": object   // if capture_mode="capture_all"
}
```

**Indexes**:
- `timestamp`
- `(provider, timestamp)`
- `(model, timestamp)`
- `context.program_name`
- `context.project_name`
- `(program, timestamp)`
- `(project, timestamp)`

**Aggregations**:
- `aggregate_usage()`: Total tokens
- `usage_by_model()`: By provider + model
- `usage_over_time()`: Time series
- `usage_by_program()`: By program (NEW)
- `usage_by_project()`: By project (NEW)

### 5. Web Dashboard

**Technology**: FastAPI + Alpine.js + Chart.js

**Backend** (`web/app.py`):
- FastAPI REST API
- Endpoints: `/api/events`, `/api/stats`, `/api/stats/by-program`, etc.
- Static file serving for frontend

**Frontend** (`web/static/`):
- Alpine.js for reactivity
- Chart.js for visualizations
- Vanilla JS + Tailwind CSS

**API Endpoints**:
- `GET /api/events` - List events (paginated, filtered)
- `GET /api/events/:id` - Get single event
- `GET /api/stats` - Aggregate usage stats
- `GET /api/stats/by-model` - Usage by model
- `GET /api/stats/by-program` - Usage by program
- `GET /api/stats/by-project` - Usage by project
- `GET /api/stats/over-time` - Time series
- `DELETE /api/events` - Clear all events
- `GET /health` - Health check

### 6. Service Management

**Technology**: launchd (macOS) / systemd (Linux)

**macOS** (`~/Library/LaunchAgents/com.tokentap.service.plist`):
- `RunAtLoad: true` (start on login)
- `KeepAlive: {SuccessfulExit: false, Crashed: true}` (restart on crash)
- `ThrottleInterval: 10` (wait 10s between restarts)

**Linux** (`~/.config/systemd/user/tokentap.service`):
- `Type: simple` (foreground)
- `Restart: on-failure` (restart on crash)
- `RestartSec: 10` (wait 10s)
- `After: docker.service` (wait for Docker)

**Script** (`scripts/service-manager.sh`):
- Platform detection
- Service creation
- Health monitoring
- Log viewing

## Data Flow

### Request Flow

1. **CLI Tool** → Sets `HTTPS_PROXY`, makes HTTPS request
2. **mitmproxy** → Intercepts, decrypts, calls `TokentapAddon.request()`
3. **TokentapAddon** → Detects provider, starts timer, extracts context
4. **mitmproxy** → Forwards request to upstream API
5. **Upstream API** → Processes request, returns response
6. **mitmproxy** → Calls `TokentapAddon.responseheaders()` (for SSE setup)
7. **mitmproxy** → Calls `TokentapAddon.response()` (for parsing)
8. **TokentapAddon** → Parses tokens, writes to MongoDB async
9. **mitmproxy** → Returns response to CLI tool

### Configuration Reload Flow

1. User edits `~/.tokentap/providers.json`
2. User runs `tokentap reload-config`
3. CLI sends SIGHUP to proxy container
4. proxy_service.py handles signal (future: reload config)
5. Currently: Manual restart required for full reload

## Design Decisions

### Why mitmproxy?

- **Real HTTPS interception**: Not just a relay proxy
- **Domain-based filtering**: Intercept only LLM APIs
- **SSE streaming support**: Handle streaming responses
- **Mature**: Battle-tested, well-documented

### Why Docker?

- **Isolated MongoDB**: No system MongoDB installation needed
- **Consistent environment**: Works same on all platforms
- **Easy updates**: Pull new images
- **Volume persistence**: Data survives container restarts

### Why JSONPath?

- **Flexible**: Handle varying API formats
- **No code changes**: Configure via JSON
- **Fallback support**: Try multiple paths

### Why Dynamic Config?

- **Extensibility**: Add providers without code changes
- **User customization**: Override defaults
- **Debug mode**: `capture_all` for unknown providers

## Performance Considerations

- **Async MongoDB writes**: Don't block proxy
- **Stream forwarding**: Chunks streamed to client immediately
- **Index strategy**: Optimize for time-based queries
- **Memory**: ~200MB per container (proxy, web, mongo)

## Security Considerations

- **CA certificate trust**: Required for HTTPS interception
- **Local only**: Proxy binds to 127.0.0.1 by default
- **MongoDB**: No authentication (local only)
- **API keys**: Captured in events (don't share database dumps)

## See Also

- [Provider Configuration](04_PROVIDER_CONFIGURATION.md)
- [Service Management](03_SERVICE_MANAGEMENT.md)
