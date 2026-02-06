# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tokentap is a Python CLI tool that provides a live terminal dashboard for tracking LLM token usage in real-time. It works by running an HTTP relay proxy that intercepts API traffic between LLM CLI tools (Claude Code, Gemini CLI, OpenAI Codex) and their upstream APIs, parsing requests to count tokens and displaying usage in a Rich-powered dashboard.

## Setup & Development Commands

Requires Python 3.10+. Always use a virtual environment.

```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Build distribution package
python -m build

# Run the tool
tokentap start                    # Start proxy + dashboard
tokentap claude                   # Run Claude Code through proxy
tokentap codex                    # Run OpenAI Codex through proxy
tokentap run --provider <name> <cmd>  # Generic provider command

# Run tests (no tests exist yet — pytest is the configured runner)
pytest
```

## Architecture

**Two-terminal model:** Terminal 1 runs the proxy server + dashboard. Terminal 2 runs the LLM tool with injected environment variables pointing it at the local proxy.

**Threading model:** The proxy (`ProxyServer`, aiohttp async) runs in a daemon thread. The dashboard (`TokenTapDashboard`, Rich Live) runs in the main thread. A thread-safe event queue with `threading.Lock` passes parsed request data from proxy to dashboard.

### Module Responsibilities

- **`config.py`** — All constants and provider configuration. The `PROVIDERS` dict maps provider names to their upstream host, base URL, and environment variables to inject. Data paths live under `~/.tokentap/`.
- **`cli.py`** — Click-based CLI. `start()` orchestrates the proxy thread + dashboard main loop. `claude()`/`gemini()`/`codex()`/`run()` inject env vars and spawn the tool as a subprocess.
- **`proxy.py`** — aiohttp HTTP server on `127.0.0.1:8080`. Detects provider from request path (`/v1/messages` → Anthropic, `/v1/chat/completions` → OpenAI, `generateContent` → Gemini). Forwards requests to upstream HTTPS APIs, fires `on_request` callback with parsed data.
- **`parser.py`** — Extracts text from provider-specific request formats and counts tokens using tiktoken (`cl100k_base` encoding). Handles multimodal content structures.
- **`dashboard.py`** — Rich terminal UI with fuel gauge (color-coded by usage %), request log table, and prompt preview. Refreshes 4 times/second.

### Request Flow

```
LLM Tool → localhost:8080 (proxy) → parse & count tokens → forward to upstream API
                                   → fire callback → event queue → dashboard renders
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| aiohttp | Async HTTP proxy server |
| certifi | CA certificates for SSL (needed on macOS) |
| rich | Terminal dashboard UI |
| tiktoken | Token counting |
| click | CLI framework |

## CI/CD

`.github/workflows/publish.yml` — Publishes to PyPI on GitHub release using trusted publisher (no API keys). Builds with `python -m build`, publishes with `pypa/gh-action-pypi-publish`.
