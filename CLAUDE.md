# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tokentap is a Python CLI tool for tracking LLM token usage in real-time. It runs a MITM proxy (mitmproxy) that intercepts HTTPS API traffic between LLM CLI tools (Claude Code, Gemini CLI, OpenAI Codex) and their upstream APIs, parsing both requests and responses to capture token usage.

**Key Features (v0.6.0)**:
- 🔧 **Dynamic Provider Configuration**: Add new LLM providers via JSON config (no code changes)
- 🚀 **Service Management**: Auto-start on boot with health monitoring (macOS/Linux)
- 📊 **Context Tracking**: Track usage by program, project, and custom metadata
- 📱 **Device Tracking**: Auto-detect devices and track token usage per device (v0.5.0)
- 🔒 **Security-First**: Localhost-only binding, debug-mode-only payload capture, admin token auth (NEW in v0.6.0)
- 🐳 **Docker-based**: Isolated MongoDB + Web Dashboard + Proxy

Clients use standard `HTTPS_PROXY` env var -- no provider-specific `*_BASE_URL` vars needed. Data is stored in MongoDB and visualized through a web dashboard.

## Setup & Development Commands

Requires Python 3.10+ and Docker.

```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Docker mode (recommended)
tokentap up                       # Start proxy + web dashboard + MongoDB
tokentap install                  # Add shell integration to .zshrc/.bashrc
tokentap install-cert             # Trust the mitmproxy CA (optional)
tokentap open                     # Open web dashboard in browser
tokentap status                   # Check service status
tokentap logs                     # View service logs
tokentap down                     # Stop all services

# Service management (NEW in v0.4.0)
tokentap service enable           # Enable auto-start on boot
tokentap service disable          # Disable auto-start
tokentap service restart          # Restart service
tokentap service status           # Detailed status with health checks

# Configuration management
tokentap reload-config            # Hot-reload provider configuration
tokentap env -o .env              # Generate .env file for project

# Security management (NEW in v0.6.0)
tokentap network-mode [local|network]  # Configure network binding (default: local)
tokentap debug [on|off]                # Toggle debug mode for payload capture (default: off)
tokentap admin-token                   # Display admin token for DELETE operations

# Legacy mode (no Docker, Rich terminal dashboard)
tokentap start                    # Start proxy + Rich dashboard
tokentap claude                   # Run Claude Code through proxy
tokentap codex                    # Run OpenAI Codex through proxy

# Run tests (pytest is the configured runner)
pytest
```

## Architecture (v0.4.0)

### Docker Mode (Primary)

Three Docker containers orchestrated via `docker-compose.yml`:

```
Claude Code / Codex / Gemini CLI / any tool
    | HTTPS_PROXY=http://127.0.0.1:8080
    v
mitmproxy (port 8080, regular mode)
    | MITM: decrypts HTTPS, filters by domain
    | TokentapAddon:
    |   • Dynamic provider detection (providers.json)
    |   • Generic request/response parsing (JSONPath)
    |   • Context extraction (program, project, tags)
    |   • Async writes to MongoDB
    v
API upstream (api.anthropic.com, api.openai.com, etc.)

MongoDB (mongo:7) <--- Web Dashboard (FastAPI :3000)
```

Shell integration (`tokentap install`) adds `eval "$(tokentap shell-init)"` to the user's shell rc, which exports `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY`, and CA cert env vars (`NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`) pointing to `~/.mitmproxy/mitmproxy-ca-cert.pem`.

### Module Responsibilities

**Core Modules**:
- **`config.py`** -- Constants: `PROVIDERS` dict (backward compat), `DEFAULT_PROXY_PORT`, `DEFAULT_PROVIDERS_PATH`, MongoDB settings, mitmproxy CA paths, shell integration markers.
- **`cli.py`** -- Click-based CLI. Docker commands (`up`, `down`, `status`, `logs`, `open`), service management (`service enable/disable/restart/status`), configuration (`reload-config`, `install`, `uninstall`, `shell-init`, `install-cert`), legacy commands (`start`, `claude`, `gemini`, `codex`, `run`).
- **`proxy.py`** -- mitmproxy addon (`TokentapAddon`). Dynamic provider detection via `ProviderConfig`. Generic parsing with `GenericParser`. Context extraction from HTTP headers. SSE streaming via `flow.response.stream` callable. Async DB writes. Health check at `/health`. Backward compat with legacy parsers.

**NEW in v0.4.0**:
- **`providers.json`** -- Dynamic provider configuration (JSONPath-based field extraction). Shipped with package, user overrides at `~/.tokentap/providers.json`.
- **`provider_config.py`** -- `ProviderConfig` class: loads/merges/validates provider configs. JSONPath extraction with fallback paths. Pydantic validation.
- **`generic_parser.py`** -- `GenericParser` class: template-based request/response parsing. Works with any provider config. Handles JSON and SSE responses.

**Existing Modules**:
- **`response_parser.py`** -- Legacy provider-specific parsers (Anthropic, OpenAI, Gemini, Kiro). Used as fallback when generic parser not available.
- **`parser.py`** -- Token counting (tiktoken `cl100k_base`) and Anthropic request parsing.
- **`db.py`** -- `MongoEventStore` (motor async driver). CRUD and aggregation pipelines. NEW: `usage_by_program()`, `usage_by_project()` aggregations. NEW indexes: `context.program_name`, `context.project_name`.
- **`dashboard.py`** -- Legacy Rich terminal UI for `tokentap start`.
- **`web/app.py`** -- FastAPI REST API and static frontend. NEW endpoints: `/api/stats/by-program`, `/api/stats/by-project`.
- **`web/static/`** -- Alpine.js + Chart.js dashboard.
- **`proxy_service.py`** -- Docker entrypoint for proxy container.
- **`web_service.py`** -- Docker entrypoint for web container (uvicorn).

**Scripts (NEW in v0.4.0)**:
- **`scripts/service-manager.sh`** -- Cross-platform service management (macOS launchd / Linux systemd). Functions: start, stop, restart, status, enable, disable, logs.
- **`scripts/tokentap-wrapper.sh`** -- Context injection wrapper. Exports `TOKENTAP_CONTEXT` env var with program/project metadata.

## Key Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| mitmproxy | MITM proxy for HTTPS interception | 10.0+ |
| motor | Async MongoDB driver | 3.3+ |
| fastapi + uvicorn | Web dashboard API + server | 0.100+ |
| tiktoken | Token counting | 0.5+ |
| click | CLI framework | 8.0+ |
| rich | Legacy terminal dashboard | 13.0+ |
| **jsonpath-ng** | **JSONPath field extraction (NEW)** | **1.6+** |
| pydantic | Config validation | 2.0+ |

## Dynamic Provider Configuration (v0.4.0)

### File Locations

- **Default config**: `tokentap/providers.json` (shipped with package)
- **User overrides**: `~/.tokentap/providers.json` (optional, merged with default)

### Configuration Schema

```json
{
  "version": "1.0",
  "capture_mode": "known_only",  // or "capture_all" for debugging
  "providers": {
    "provider-name": {
      "name": "Provider Display Name",
      "enabled": true,
      "domains": ["api.example.com"],
      "api_patterns": ["/v1/chat"],

      "request": {
        "model_path": "$.model",                    // JSONPath
        "messages_path": "$.messages[*]",
        "text_fields": ["$.messages[*].content"]
      },

      "response": {
        "json": {
          "input_tokens_path": "$.usage.input_tokens",
          "output_tokens_path": "$.usage.output_tokens",
          "model_path": "$.model",
          "stop_reason_path": "$.stop_reason"
        },
        "sse": {                                    // For streaming responses
          "event_types": ["message_start", "message_delta"],
          "input_tokens_event": "message_start",
          "input_tokens_path": "$.message.usage.input_tokens",
          "output_tokens_event": "message_delta",
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

### Adding a New Provider

1. **Enable capture mode** in `~/.tokentap/providers.json`:
   ```json
   {"capture_mode": "capture_all"}
   ```

2. **Reload config**: `tokentap reload-config`

3. **Make test request** with the new provider CLI

4. **Inspect captured data**:
   ```bash
   docker exec -it tokentap-client-mongodb-1 mongosh tokentap
   db.events.find({provider:"unknown"}).limit(1).pretty()
   ```

5. **Create provider config** in `~/.tokentap/providers.json` using JSONPath expressions

6. **Reload**: `tokentap reload-config`

See `docs/06_DEBUGGING_NEW_PROVIDERS.md` for detailed guide.

## Context Tracking (v0.4.0)

Track which programs and projects are using LLM tokens.

### Event Schema

```json
{
  "timestamp": "2026-02-07T10:00:00Z",
  "provider": "anthropic",
  "model": "claude-sonnet-4",
  "input_tokens": 100,
  "output_tokens": 200,
  "total_tokens": 300,

  // NEW in v0.4.0
  "context": {
    "program_name": "my-script",
    "project_name": "my-project",
    "session_id": "abc123",
    "tags": ["automated"],
    "custom": {
      "experiment": "v2"
    }
  },
  "program": "my-script",      // Denormalized for fast queries
  "project": "my-project",     // Denormalized for fast queries
  "provider_tags": ["llm", "chat"],
  "estimated_cost": 0.0003,
  "capture_mode": "known"
}
```

### Usage

```bash
# Method 1: Environment variables
export TOKENTAP_PROJECT="my-project"
export TOKENTAP_CONTEXT='{"experiment":"v2"}'
claude "Write code"

# Method 2: Wrapper script
./scripts/tokentap-wrapper.sh "my-automation" python bot.py

# Method 3: HTTP headers (for SDKs)
export HTTP_EXTRA_HEADERS='{"X-Tokentap-Context":"{\"program\":\"bot\"}"}'
```

See `docs/05_CONTEXT_METADATA.md` for full guide.

## Service Management (v0.4.0)

Auto-start tokentap on boot with health monitoring.

### macOS (launchd)

Service file: `~/Library/LaunchAgents/com.tokentap.service.plist`

Features:
- `RunAtLoad: true` (start on login)
- `KeepAlive: {Crashed: true}` (restart on crash)
- `ThrottleInterval: 10` (wait 10s between restarts)

### Linux (systemd)

Service file: `~/.config/systemd/user/tokentap.service`

Features:
- `Type: simple` (foreground mode)
- `Restart: on-failure` (restart on crash)
- `RestartSec: 10` (wait 10s)
- `After: docker.service` (wait for Docker)

### Commands

```bash
tokentap service enable    # Enable auto-start
tokentap service disable   # Disable auto-start
tokentap service restart   # Restart service
tokentap service status    # Detailed status
```

See `docs/03_SERVICE_MANAGEMENT.md` for full guide.

## Security Features (v0.6.0)

Tokentap v0.6.0 introduces security-first defaults to protect sensitive data.

### 1. Localhost-Only Binding (Default)

**What**: Services bind to `127.0.0.1` instead of `0.0.0.0`.

**Why**: Prevents unauthorized access from other devices on your network.

**Management**:
```bash
tokentap network-mode              # Check current mode
tokentap network-mode network      # Enable network access (with warning)
tokentap network-mode local        # Revert to secure default
```

### 2. Debug-Mode-Only Payload Capture (Default OFF)

**What**: Raw request/response payloads NOT captured unless debug mode enabled.

**Why**: Prevents accidental capture of:
- API keys and authentication tokens
- User credentials
- Personal identifiable information (PII)
- Proprietary prompts and data

**What's Still Captured** (always, for categorization):
- ✅ Token counts (input/output/cache)
- ✅ Model names
- ✅ API paths
- ✅ Client types (claude-code, kiro-cli, etc.)
- ✅ Message structure with roles (content: `[REDACTED]`)
- ✅ Device tracking
- ✅ Smart token detection flags
- ✅ Cost estimates

**Management**:
```bash
tokentap debug              # Check current mode
tokentap debug on           # Enable for troubleshooting (with warning)
tokentap debug off          # Disable (secure default)
```

**When to Enable**: Only when debugging new provider integrations or troubleshooting parsing issues.

### 3. Admin Token Authentication

**What**: DELETE endpoints require `X-Admin-Token` header.

**Why**: Prevents accidental or unauthorized data deletion.

**Protected Endpoints**:
- `DELETE /api/events/all`
- `DELETE /api/devices/{id}`

**Management**:
```bash
tokentap admin-token        # Display token

# Use with API:
curl -X DELETE \
  -H "X-Admin-Token: YOUR_TOKEN" \
  http://localhost:3000/api/events/all
```

**Token Storage**: Auto-generated in `~/.tokentap/admin.token` with 0600 permissions.

### Security Best Practices

1. **Keep debug mode OFF** in production environments
2. **Use network mode sparingly** - only in trusted networks
3. **Treat admin token like a password** - don't commit to git
4. **Review existing MongoDB data** - may contain sensitive info from pre-v0.6.0
5. **Use TLS/SSL** for production MongoDB connections
6. **Limit MongoDB access** - configure firewall rules if exposing externally

### Migration from v0.5.0

See `MIGRATION_v0.6.0.md` for detailed upgrade guide including breaking changes.

## Data Flow

1. **CLI Tool** → Sets `HTTPS_PROXY`, makes HTTPS request
2. **mitmproxy** → Intercepts, decrypts, calls `TokentapAddon.request()`
3. **TokentapAddon** →
   - Detects provider via `ProviderConfig.get_provider_by_domain()`
   - Extracts context from HTTP headers (`_extract_context_metadata()`)
   - Starts timer
4. **mitmproxy** → Forwards request to upstream API
5. **Upstream API** → Returns response
6. **mitmproxy** → Calls `TokentapAddon.response()`
7. **TokentapAddon** →
   - Parses request via `GenericParser.parse_request()` (with fallback to legacy)
   - Parses response via `GenericParser.parse_response()` (with fallback to legacy)
   - Builds event with context, metadata, cost estimation
   - Writes to MongoDB async (doesn't block)
8. **mitmproxy** → Returns response to CLI tool

## Documentation

Comprehensive documentation in `docs/` directory:

1. **[Quick Start](docs/01_QUICK_START.md)** - 5-minute getting started
2. **[Installation](docs/02_INSTALLATION.md)** - Detailed installation
3. **[Service Management](docs/03_SERVICE_MANAGEMENT.md)** - Auto-start configuration
4. **[Provider Configuration](docs/04_PROVIDER_CONFIGURATION.md)** - JSON config reference
5. **[Context Tracking](docs/05_CONTEXT_METADATA.md)** - Metadata tracking
6. **[Debugging New Providers](docs/06_DEBUGGING_NEW_PROVIDERS.md)** - Adding providers
7. **[Troubleshooting](docs/07_TROUBLESHOOTING.md)** - Common issues
8. **[CLI Reference](docs/10_CLI_REFERENCE.md)** - Command reference
9. **[Architecture](docs/11_ARCHITECTURE.md)** - Technical details
10. **[CHANGES.md](docs/CHANGES.md)** - Changelog with decision log

## Development Guidelines

### Adding a New Feature

1. **Plan**: Consider impact on existing features, backward compatibility
2. **Implement**: Write code following existing patterns
3. **Test**: Add unit tests, integration tests
4. **Document**: Update relevant docs in `docs/`
5. **Update CHANGES.md**: Add entry with decision rationale

### Code Style

- **Python**: Follow PEP 8, use type hints
- **Docstrings**: Google style
- **CLI**: Use Click, provide `--help` for all commands
- **Logging**: Use `logging` module, appropriate levels (DEBUG, INFO, WARNING, ERROR)

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_provider_config.py

# Run with coverage
pytest --cov=tokentap

# Run integration tests (requires Docker)
pytest -m integration
```

### Common Patterns

**Reading configuration**:
```python
from tokentap.provider_config import get_provider_config
config = get_provider_config()
```

**Parsing with fallback**:
```python
if self.generic_parser:
    try:
        result = self.generic_parser.parse_request(provider, body)
    except Exception as e:
        logger.warning(f"Generic parser failed: {e}")
        result = self._parse_request_legacy(provider, body)
else:
    result = self._parse_request_legacy(provider, body)
```

**Async DB operations**:
```python
if self.db:
    try:
        await self.db.insert_event(event)
    except Exception:
        logger.exception("Failed to write to MongoDB")
```

## Testing & Validation

### Quick Smoke Test

After installation, verify the system is working:

```bash
# 1. Check services are running
tokentap status
# Expected: 3 containers running (proxy, web, mongodb)

# 2. Check proxy health
curl -x http://127.0.0.1:8080 http://localhost/health
# Expected: {"status":"ok","proxy":true}

# 3. Verify HTTPS_PROXY is set
echo $HTTPS_PROXY
# Expected: http://127.0.0.1:8080
# If not set: eval "$(tokentap shell-init)"

# 4. Make a test LLM call
claude "Say only 'test successful'"

# 5. Check if proxy captured the request
docker logs tokentap-client-proxy-1 | grep "Intercepting"
# Expected: Lines showing "Intercepting anthropic request"

# 6. Verify event in MongoDB
docker exec tokentap-client-mongodb-1 mongosh tokentap --quiet \
  --eval 'db.events.find().sort({timestamp:-1}).limit(1).pretty()'
# Expected: Recent event with tokens captured

# 7. Check web dashboard
curl -s http://localhost:3000/api/stats/summary | python3 -m json.tool
# Expected: JSON with request_count > 0
```

### Integration Tests

```bash
# Test dynamic provider config
python3 -c "
from tokentap.provider_config import get_provider_config
config = get_provider_config()
print(f'Providers: {list(config.providers.keys())}')
"

# Test generic parser
python3 -c "
from tokentap.provider_config import get_provider_config
from tokentap.generic_parser import GenericParser
config = get_provider_config()
parser = GenericParser(config)
result = parser.parse_request('anthropic', {
    'model': 'claude-3',
    'messages': [{'role': 'user', 'content': 'test'}]
})
print(f'Model: {result[\"model\"]}, Messages: {len(result[\"messages\"])}')
"
```

### MongoDB Indexes Verification

```bash
docker exec tokentap-client-mongodb-1 mongosh tokentap --quiet \
  --eval 'db.events.getIndexes().forEach(idx => print(JSON.stringify(idx.key)))'
```

Expected indexes:
```json
{"_id":1}
{"timestamp":1}
{"provider":1,"timestamp":-1}
{"model":1,"timestamp":-1}
{"context.program_name":1}
{"context.project_name":1}
{"program":1,"timestamp":-1}
{"project":1,"timestamp":-1}
```

## Known Limitations

### 1. Context Wrapper in Docker Environment

**Issue**: `scripts/tokentap-wrapper.sh` has an architectural limitation when proxy runs in Docker.

**Problem**:
- Wrapper exports `TOKENTAP_CONTEXT` as environment variable
- Proxy runs in Docker (isolated environment)
- Docker container doesn't have access to host shell's environment variables
- Most LLM CLIs (including Claude Code) don't send custom HTTP headers by default

**Result**: Context tracking via wrapper doesn't work out-of-the-box with Docker setup.

**Workarounds**:
1. **Use basic context tracking** (already works):
   - Proxy automatically detects `client_type` from User-Agent
   - Program auto-detected: "claude-code", "kiro-cli", etc.
   - Sufficient for most use cases

2. **Pass env vars via docker-compose** (requires configuration):
   ```yaml
   # docker-compose.yml
   services:
     proxy:
       environment:
         - TOKENTAP_CONTEXT=${TOKENTAP_CONTEXT}
   ```

3. **Run proxy on host** (non-Docker mode):
   ```bash
   tokentap down
   python -m tokentap.proxy_service  # Run directly on host
   ```

### 2. HTTPS_PROXY Must Be Set

**Critical**: The proxy ONLY captures requests when `HTTPS_PROXY` is set in the shell.

**Symptoms**:
- Services running, health check passes
- But no LLM requests being captured
- Logs only show health check messages

**Solution**:
```bash
# Check if set
echo $HTTPS_PROXY

# If not set, configure shell
eval "$(tokentap shell-init)"

# Or add to shell permanently
tokentap install
source ~/.zshrc  # or ~/.bashrc
```

### 3. Streaming Response Token Counting

**Issue**: For SSE (Server-Sent Events) streaming responses, token counts depend on provider sending usage data in the stream.

**Impact**: Some providers may not include token counts in streaming mode, resulting in 0 tokens recorded even though tokens were consumed.

**Workaround**: Use non-streaming mode where possible, or rely on estimated tokens via tiktoken.

## Troubleshooting

### Proxy Not Capturing Requests

1. **Verify HTTPS_PROXY is set**: `echo $HTTPS_PROXY`
2. **Check services are running**: `tokentap status`
3. **Test health endpoint**: `curl -x http://127.0.0.1:8080 http://localhost/health`
4. **Check proxy logs**: `docker logs tokentap-client-proxy-1 | tail -50`
5. **Make test request**: `eval "$(tokentap shell-init)" && claude "test"`

### No Events in MongoDB

1. **Check MongoDB connection**: `docker exec tokentap-client-mongodb-1 mongosh tokentap --eval 'db.stats()'`
2. **Verify proxy is writing**: Check logs for "insert" commands
3. **Check event count**: `docker exec tokentap-client-mongodb-1 mongosh tokentap --eval 'db.events.countDocuments()'`

### Indexes Not Created

Indexes are created automatically on first event insert. If you see events but no indexes:

```bash
# Manually create indexes
docker exec tokentap-client-mongodb-1 mongosh tokentap --eval '
db.events.createIndex({timestamp: 1});
db.events.createIndex({provider: 1, timestamp: -1});
db.events.createIndex({model: 1, timestamp: -1});
db.events.createIndex({"context.program_name": 1});
db.events.createIndex({"context.project_name": 1});
db.events.createIndex({program: 1, timestamp: -1});
db.events.createIndex({project: 1, timestamp: -1});
'
```

## CI/CD

`.github/workflows/publish.yml` -- Publishes to PyPI on GitHub release using trusted publisher.

## Version History

- **0.6.0** (2026-02-08): Security fixes, admin token auth, localhost-only binding, debug-mode payload capture - **IMPLEMENTED ✅**
- **0.5.0** (2026-02-08): Device tracking, smart token detection, inline device rename - **VALIDATED ✅**
- **0.4.0** (2026-02-07): Dynamic provider config, service management, context tracking - **VALIDATED ✅**
- **0.3.0** (2026-02-06): mitmproxy migration, Docker support, web dashboard
- **0.2.0**: Multi-provider support, MongoDB storage
- **0.1.0**: Initial release

## Validation Status (v0.6.0)

**Last validated**: 2026-02-08

**Major Changes**:
- ✅ Security-first defaults: localhost-only binding
- ✅ Debug-mode-only payload capture (prevents data leakage)
- ✅ Admin token authentication for DELETE operations
- ✅ Provider detection bug fixed (backward compat rewrite)
- ✅ Missing API endpoints added (`/api/stats/by-program`, `/api/stats/by-project`)
- ✅ PyPI packaging fixed (Docker files included)

**Breaking Changes**:
- ⚠️ Services bind to `127.0.0.1` by default (use `tokentap network-mode network` for network access)
- ⚠️ Raw payloads NOT captured by default (use `tokentap debug on` when needed)
- ⚠️ DELETE endpoints require admin token (`tokentap admin-token`)

**System Status**: Production-ready with enhanced security
