# Tokentap Changelog

All notable changes to Tokentap are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.4.1] - 2026-02-07

### Fixed - Complete Request Capture (Critical Bug Fix)

**Issue**: Tokentap was only capturing the **first message** from multi-turn conversations instead of the complete message history. System prompts, tool definitions, and other array fields were also incomplete or missing.

**Root Cause**: The JSONPath `extract_field()` method in `provider_config.py` was returning only `matches[0].value` instead of extracting all matches when wildcard patterns like `$.messages[*]` were used.

**Impact**:
- **Before**: 1 message captured from 35-message conversations (97% data loss)
- **After**: All 35 messages captured correctly (100% fidelity)
- **Scope**: All providers using generic parser (Anthropic, OpenAI, Gemini, Kiro)

#### Changes Made

1. **Fixed JSONPath Array Extraction** (`provider_config.py`)
   - Now returns full array when `[*]` or `[@]` wildcards are present
   - Preserves single-value behavior for non-wildcard paths
   - Added `force_list` parameter for explicit list returns
   - Filters out empty/null values from results

2. **Enhanced Generic Parser** (`generic_parser.py`)
   - Added `tools`, `thinking`, `metadata` fields to request parsing
   - Implemented `_extract_text_from_object()` for recursive text extraction
   - Preserves original structure of system prompts (string or array)
   - Better handling of nested content in messages

3. **Always Capture Raw Request** (`proxy.py`)
   - Changed from conditional to **always** saving `raw_request`
   - Ensures data can be reprocessed if parsing improves later
   - Storage overhead: ~10-50KB per event (acceptable trade-off)

4. **Quality Validation with Fallback** (`proxy.py`)
   - Added `_is_parse_quality_acceptable()` method
   - Detects incomplete message arrays (e.g., 1 of 35 captured)
   - Detects missing system prompts or tools
   - Automatically falls back to legacy parser when quality is poor

5. **Include Additional Fields in Events** (`proxy.py`)
   - Event now includes `system`, `tools`, `thinking`, `request_metadata`
   - Fields only added if present in request (not breaking)
   - Preserves original formats (arrays stay arrays, strings stay strings)

6. **Updated Provider Configuration** (`providers.json`)
   - Changed Anthropic `system_path` from `$.system[*]` to `$.system`
   - Added `tools_path`, `thinking_path`, `metadata_path`
   - Set `capture_full_request: true` for Anthropic
   - Enhanced `text_fields` with deep extraction paths

7. **Extended Request Config Schema** (`provider_config.py`)
   - Added `tools_path`, `thinking_path`, `metadata_path` to `ProviderRequestConfig`
   - Maintains backward compatibility (all new fields are optional)

#### Validation Results

```
=== BEFORE (v0.4.0) ===
Messages: 1           ❌ Only first message
System: missing       ❌ Not captured
Tools: missing        ❌ Not captured
raw_request: optional ❌ Data loss risk

=== AFTER (v0.4.1) ===
Messages: 35          ✅ Complete conversation
System: 3 items       ✅ Full CLAUDE.md + MEMORY.md
Tools: 43 tools       ✅ All available tools
raw_request: always   ✅ Perfect safety net
```

#### Test Coverage

Created comprehensive test suite (`test_array_extraction.py`):
- ✅ JSONPath array extraction (3/3 tests pass)
- ✅ Generic parser request parsing (all fields captured)
- ✅ Quality validation (detects incomplete data)

#### Storage Impact

- Events now ~3-6x larger due to complete data capture
- Acceptable trade-off: prevents 97% data loss
- Disk is cheap, lost context is expensive

#### Backward Compatibility

✅ Fully backward compatible:
- Old events remain unchanged
- New fields are optional
- No breaking API changes
- Legacy parsers still work as fallback

#### Performance Impact

- Parsing overhead: +3ms (+60%), acceptable for correctness
- No network or query performance impact
- Async MongoDB writes remain non-blocking

See `VALIDATION_REPORT_v0.4.1.md` for detailed validation results.

## [0.4.0] - 2026-02-07

### Added - Dynamic Provider Configuration System

**Revolutionary change**: Add new LLM providers via JSON configuration without modifying code.

- **`tokentap/providers.json`**: Dynamic provider configuration file with JSONPath-based field extraction
- **`tokentap/provider_config.py`**: Configuration loader with Pydantic validation and user override support
- **`tokentap/generic_parser.py`**: Template-based request/response parser that works with any provider config
- **Fallback paths**: Support multiple field paths for inconsistent APIs (`input_tokens_path_alt`)
- **Hot reload**: `tokentap reload-config` command reloads configuration without service restart
- **Capture modes**:
  - `known_only` (default): Only capture configured providers
  - `capture_all`: Capture ALL HTTPS traffic with full request/response logging for debugging

**Benefits**:
- Add new providers in minutes, not hours
- Experiment with unknown providers using capture-all mode
- User overrides in `~/.tokentap/providers.json` without touching package files
- Backward compatible with hardcoded parsers as fallback

### Added - Robust Service Management

Auto-start on boot with health monitoring and automatic restart.

- **`scripts/service-manager.sh`**: Cross-platform service management script
  - macOS: launchd with KeepAlive (automatic restart on crash)
  - Linux: systemd with Restart=on-failure
  - Health monitoring with proxy health checks
  - Centralized logging at `~/.tokentap/logs/`
  - Throttle intervals to prevent restart loops (10s wait)

- **CLI service commands**:
  - `tokentap service enable` - Enable auto-start on boot
  - `tokentap service disable` - Disable auto-start
  - `tokentap service restart` - Restart service
  - `tokentap service status` - Detailed status with health checks

- **Service features**:
  - Auto-start on login (macOS) or boot (Linux)
  - Automatic restart on failure
  - Health monitoring via `/health` endpoint
  - Log rotation support
  - Docker dependency management

### Added - Context Metadata Tracking

Track which programs and projects are consuming LLM tokens.

- **Context fields in events**:
  ```json
  {
    "context": {
      "program_name": "my-script",
      "project_name": "my-project",
      "session_id": "abc123",
      "tags": ["automated"],
      "custom": {"experiment": "v2"}
    },
    "program": "my-script",  // Denormalized for queries
    "project": "my-project"
  }
  ```

- **`scripts/tokentap-wrapper.sh`**: Context injection wrapper
  - Automatically captures program name, project, session
  - Supports environment variables (`TOKENTAP_PROJECT`, `TOKENTAP_CONTEXT`)
  - JSON context via HTTP headers

- **Database enhancements**:
  - New indexes: `context.program_name`, `context.project_name`, `(program, timestamp)`, `(project, timestamp)`
  - New aggregations: `usage_by_program()`, `usage_by_project()`
  - Extended filters: Support `program`, `project`, `capture_mode` filters

- **Use cases**:
  - Track automated scripts and bots
  - A/B test different prompts
  - Analyze usage by team/project
  - Monitor CI/CD pipeline costs

### Added - Enhanced Proxy Features

- **Context extraction**: Automatic extraction from HTTP headers
  - `X-Tokentap-Program`, `X-Tokentap-Project`, `X-Tokentap-Session`
  - `X-Tokentap-Context` (full JSON context)
- **Full raw capture**: Store complete request/response for unknown providers
- **Cost estimation**: Calculate estimated costs based on provider metadata
- **Provider metadata**: Store tags and cost rates in events

### Added - Comprehensive Documentation

Reorganized and expanded documentation in `docs/` directory:

- **[01_QUICK_START.md](01_QUICK_START.md)**: 5-minute getting started guide
- **[02_INSTALLATION.md](02_INSTALLATION.md)**: Detailed installation for all platforms
- **[03_SERVICE_MANAGEMENT.md](03_SERVICE_MANAGEMENT.md)**: Service configuration and management
- **[04_PROVIDER_CONFIGURATION.md](04_PROVIDER_CONFIGURATION.md)**: JSON config reference with JSONPath
- **[05_CONTEXT_METADATA.md](05_CONTEXT_METADATA.md)**: Context tracking guide
- **[06_DEBUGGING_NEW_PROVIDERS.md](06_DEBUGGING_NEW_PROVIDERS.md)**: Step-by-step provider addition
- **[07_TROUBLESHOOTING.md](07_TROUBLESHOOTING.md)**: Common issues and solutions
- **[10_CLI_REFERENCE.md](10_CLI_REFERENCE.md)**: Complete CLI command reference
- **[11_ARCHITECTURE.md](11_ARCHITECTURE.md)**: Technical architecture documentation
- **[docs/README.md](README.md)**: Documentation index with reading order

### Changed

- **Provider detection**: Now uses dynamic configuration instead of hardcoded `DOMAIN_TO_PROVIDER`
- **Request/response parsing**: Generic parser with fallback to legacy parsers for backward compatibility
- **CLI `up` command**: Added `--no-detach` flag for systemd foreground mode
- **Event schema**: Added context fields, provider_tags, estimated_cost, capture_mode
- **README.md**: Added "What's New" section highlighting v0.4.0 features
- **CLAUDE.md**: Updated with new architecture and features

### Fixed

- Event loop blocking issue in proxy (async DB writes)
- Stream capture for SSE responses (proper `flow.response.stream` usage)
- Health check requires proxy protocol (`curl -x`)

### Dependencies

- **Added**: `jsonpath-ng>=1.6.0` (for JSONPath field extraction)
- **Already present**: `pydantic>=2.0.0` (for config validation)

## [0.3.0] - 2026-02-06

### Added - mitmproxy Migration

Complete rewrite from aiohttp relay proxy to mitmproxy MITM proxy.

- **Real HTTPS interception**: Decrypt and inspect HTTPS traffic via MITM
- **Universal proxy support**: Single `HTTPS_PROXY` environment variable works with all tools
- **Domain-based filtering**: Intercept only LLM API domains
- **Docker support**: Complete docker-compose.yml with proxy, web, and MongoDB
- **Web dashboard**: FastAPI + Alpine.js + Chart.js dashboard at `http://localhost:3000`
- **Amazon Q (Kiro) support**: Added support for Amazon Q CLI
- **EventStream detection**: Handle AWS EventStream format for Kiro

### Changed

- Proxy architecture: aiohttp relay → mitmproxy MITM
- Configuration: Per-provider `*_BASE_URL` → Single `HTTPS_PROXY`
- Certificate handling: mitmproxy CA certificate in `~/.mitmproxy/`
- Health check: Must use proxy protocol (`curl -x http://proxy http://localhost/health`)

### Added

- `tokentap up` - Start Docker services
- `tokentap down` - Stop Docker services
- `tokentap status` - Check service status
- `tokentap logs` - View container logs
- `tokentap open` - Open web dashboard
- `tokentap install` - Add shell integration
- `tokentap install-cert` - Trust mitmproxy CA certificate

## [0.2.0] - Earlier

### Added

- Anthropic (Claude) support
- OpenAI (Codex) support
- Google Gemini CLI support
- Rich terminal dashboard
- MongoDB event storage
- Token counting with tiktoken

### Features

- Real-time token tracking
- Request/response capture
- Prompt saving to markdown/JSON
- CLI wrappers for common tools

## [0.1.0] - Initial Release

### Added

- Basic proxy functionality
- Token usage tracking
- Simple storage

---

## Decision Log

### Why mitmproxy over aiohttp relay proxy? (v0.3.0)

**Decision**: Migrate to mitmproxy for MITM HTTPS interception

**Rationale**:
- **Universal compatibility**: `HTTPS_PROXY` env var works with all tools (no per-provider `*_BASE_URL` vars)
- **Real HTTPS interception**: Decrypt and inspect encrypted traffic
- **Domain filtering**: Only intercept LLM APIs, ignore other traffic
- **Mature platform**: Battle-tested, well-documented, active development
- **SSE streaming support**: Proper handling of Server-Sent Events

**Trade-offs**:
- Requires CA certificate trust (mitmproxy-ca-cert.pem)
- More complex setup than simple relay proxy
- Docker required for isolated environment

### Why JSONPath for provider configuration? (v0.4.0)

**Decision**: Use JSONPath expressions for field extraction in provider configs

**Rationale**:
- **Flexibility**: Handle varying API response structures
- **No code changes**: Configure field locations via JSON
- **Fallback support**: Try multiple paths with `*_path_alt` fields
- **Standard syntax**: Well-known, widely supported
- **Library available**: `jsonpath-ng` Python library

**Alternatives considered**:
- **JMESPath**: More powerful but less familiar
- **Regex**: Too brittle for nested JSON
- **Hard-coded**: No flexibility for new providers

### Why capture_all mode instead of always capturing? (v0.4.0)

**Decision**: Default to `known_only`, opt-in to `capture_all`

**Rationale**:
- **Privacy**: Don't capture non-LLM traffic by default
- **Performance**: Smaller database, faster queries
- **Debug mode**: Enable when needed for new providers
- **Storage**: Full request/response can be large

### Why context as separate field vs. top-level fields? (v0.4.0)

**Decision**: Store context in nested object + denormalized top-level fields

**Structure**:
```json
{
  "context": {
    "program_name": "...",
    "project_name": "...",
    ...
  },
  "program": "...",  // Denormalized
  "project": "..."   // Denormalized
}
```

**Rationale**:
- **Flexibility**: `context.custom` can store any user metadata
- **Query performance**: Top-level `program` and `project` fields are indexed and fast to query
- **Backward compatibility**: Old events without context still work
- **Clarity**: Clear separation of context vs. core event fields

### Why launchd + systemd instead of Docker restart policies? (v0.4.0)

**Decision**: Use OS-native service managers (launchd/systemd) instead of Docker's restart policy

**Rationale**:
- **Boot-time startup**: Docker may not be running at boot
- **Health monitoring**: OS service managers have better health checks
- **Log management**: Centralized logging via system tools
- **User control**: Familiar `systemctl` / `launchctl` commands
- **Fine-grained control**: Throttle intervals, restart conditions

**Trade-offs**:
- Platform-specific configuration (plist vs. service file)
- More complex than Docker's `restart: always`

---

## Upgrade Guide

### Upgrading to 0.4.0 from 0.3.x

**No breaking changes**. All existing functionality preserved.

**New features are opt-in**:

1. **Dynamic provider config** (optional):
   ```bash
   # Create user config
   mkdir -p ~/.tokentap
   cp tokentap/providers.json ~/.tokentap/providers.json
   # Edit and customize
   tokentap reload-config
   ```

2. **Service management** (optional):
   ```bash
   tokentap service enable
   ```

3. **Context tracking** (optional):
   ```bash
   export TOKENTAP_PROJECT="my-project"
   # Or use wrapper script
   ./scripts/tokentap-wrapper.sh "my-program" claude
   ```

**Existing events**:
- Old events without context fields will work fine
- New aggregations (`usage_by_program`) will group old events as "unknown"

### Upgrading to 0.3.0 from 0.2.x

**Breaking changes**:

1. **Proxy URL changed**:
   - Old: Provider-specific `*_BASE_URL` vars
   - New: Single `HTTPS_PROXY=http://127.0.0.1:8080`

2. **CA certificate required**:
   ```bash
   tokentap install-cert
   ```

3. **Docker required**:
   ```bash
   tokentap up
   ```

**Migration**:
```bash
# Uninstall old version
tokentap down  # If old version had docker
pip uninstall tokentap

# Install new version
pip install tokentap==0.3.0
tokentap up
tokentap install
tokentap install-cert
```

---

## See Also

- [Quick Start Guide](01_QUICK_START.md)
- [Documentation Index](README.md)
- [GitHub Repository](https://github.com/jmuncor/tokentap)
