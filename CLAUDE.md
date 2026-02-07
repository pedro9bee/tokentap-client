# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tokentap is a Python CLI tool for tracking LLM token usage in real-time. It runs a MITM proxy (mitmproxy) that intercepts HTTPS API traffic between LLM CLI tools (Claude Code, Gemini CLI, OpenAI Codex) and their upstream APIs, parsing both requests and responses to capture token usage. Clients use standard `HTTPS_PROXY` env var -- no provider-specific `*_BASE_URL` vars needed. Data is stored in MongoDB and visualized through a web dashboard.

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

# Legacy mode (no Docker, Rich terminal dashboard)
tokentap start                    # Start proxy + Rich dashboard
tokentap claude                   # Run Claude Code through proxy
tokentap codex                    # Run OpenAI Codex through proxy

# Run tests (pytest is the configured runner)
pytest
```

## Architecture

### Docker Mode (Primary)

Three Docker containers orchestrated via `docker-compose.yml`:

```
Claude Code / Codex / Gemini CLI / any tool
    | HTTPS_PROXY=http://127.0.0.1:8080
    v
mitmproxy (port 8080, regular mode)
    | MITM: decrypts HTTPS, filters by domain
    | TokentapAddon: parses tokens, writes to MongoDB
    v
API upstream (api.anthropic.com, api.openai.com, etc.)

MongoDB (mongo:7) <--- Web Dashboard (FastAPI :3000)
```

Shell integration (`tokentap install`) adds `eval "$(tokentap shell-init)"` to the user's shell rc, which exports `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY`, and CA cert env vars (`NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`) pointing to `~/.mitmproxy/mitmproxy-ca-cert.pem`.

### Module Responsibilities

- **`config.py`** -- Constants: `PROVIDERS` dict (host per provider), `DEFAULT_PROXY_PORT`, MongoDB settings, mitmproxy CA paths, shell integration markers.
- **`cli.py`** -- Click-based CLI. Docker commands (`up`, `down`, `status`, `logs`, `open`), shell integration (`install`, `uninstall`, `shell-init`), `install-cert`, legacy commands (`start`, `claude`, `gemini`, `codex`, `run`).
- **`proxy.py`** -- mitmproxy addon (`TokentapAddon`). Intercepts HTTPS via MITM by domain (`DOMAIN_TO_PROVIDER`). SSE streaming via `flow.response.stream` callable. Async DB writes. Health check at `/health`. Backward compat: localhost requests rewritten to upstream HTTPS.
- **`response_parser.py`** -- Extracts token usage from provider responses (JSON and SSE streams).
- **`parser.py`** -- Token counting (tiktoken `cl100k_base`) and Anthropic request parsing.
- **`db.py`** -- `MongoEventStore` (motor async driver). CRUD and aggregation pipelines.
- **`dashboard.py`** -- Legacy Rich terminal UI for `tokentap start`.
- **`web/app.py`** -- FastAPI REST API and static frontend.
- **`web/static/`** -- Alpine.js + Chart.js dashboard.
- **`proxy_service.py`** -- Docker entrypoint for proxy container.
- **`web_service.py`** -- Docker entrypoint for web container (uvicorn).

## Key Dependencies

| Package | Purpose |
|---------|---------|
| mitmproxy | MITM proxy for HTTPS interception |
| motor | Async MongoDB driver |
| fastapi + uvicorn | Web dashboard API + server |
| tiktoken | Token counting |
| click | CLI framework |
| rich | Legacy terminal dashboard |

## CI/CD

`.github/workflows/publish.yml` -- Publishes to PyPI on GitHub release using trusted publisher.
