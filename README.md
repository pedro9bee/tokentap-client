<p align="center">
  <h1 align="center">Tokentap</h1>
  <p align="center">
    <strong>Track LLM token usage across Claude Code, Codex, Gemini CLI, and more</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
    <img src="https://img.shields.io/badge/Claude_Code-supported-blueviolet.svg" alt="Claude Code">
    <img src="https://img.shields.io/badge/Codex-supported-green.svg" alt="Codex">
    <img src="https://img.shields.io/badge/Gemini_CLI-supported-blue.svg" alt="Gemini">
  </p>
</p>

---

Tokentap runs a MITM proxy that transparently intercepts HTTPS traffic to LLM APIs, captures token usage from every request/response, and shows it all on a web dashboard. Works with **any** CLI tool that respects `HTTPS_PROXY` -- no per-tool configuration needed.

## Quick Start (step by step)

### Prerequisites

- Python 3.10+
- Docker

### 1. Install tokentap

```bash
pip install tokentap
```

Or from source:

```bash
git clone https://github.com/jmuncor/tokentap.git
cd tokentap
pip install -e .
```

### 2. Start the services

```bash
tokentap up
```

This starts three Docker containers: the mitmproxy proxy (port 8080), MongoDB, and the web dashboard (port 3000). It also copies the mitmproxy CA certificate to `~/.mitmproxy/`.

### 3. Configure your shell

```bash
tokentap install
```

This adds `eval "$(tokentap shell-init)"` to your `~/.zshrc` (or `~/.bashrc`), which exports:

| Variable | Value |
|----------|-------|
| `HTTPS_PROXY` | `http://127.0.0.1:8080` |
| `HTTP_PROXY` | `http://127.0.0.1:8080` |
| `NO_PROXY` | `localhost,127.0.0.1` |
| `NODE_EXTRA_CA_CERTS` | `~/.mitmproxy/mitmproxy-ca-cert.pem` |
| `SSL_CERT_FILE` | `~/.mitmproxy/mitmproxy-ca-cert.pem` |
| `REQUESTS_CA_BUNDLE` | `~/.mitmproxy/mitmproxy-ca-cert.pem` |

Reload your shell:

```bash
source ~/.zshrc   # or ~/.bashrc
```

### 4. (Optional) Trust the CA system-wide

If your tools don't respect `SSL_CERT_FILE` / `NODE_EXTRA_CA_CERTS`:

```bash
tokentap install-cert
```

This adds the mitmproxy CA to the macOS system keychain (or Linux ca-certificates).

### 5. Use your LLM tools normally

```bash
claude          # Claude Code
codex           # OpenAI Codex
gemini          # Gemini CLI
```

All HTTPS traffic to `api.anthropic.com`, `api.openai.com`, and `generativelanguage.googleapis.com` is automatically intercepted, parsed for token usage, and stored in MongoDB.

### 6. View the dashboard

```bash
tokentap open
```

Opens `http://127.0.0.1:3000` in your browser -- live stats, per-model breakdowns, and full event log.

## How It Works

```
Claude Code / Codex / Gemini CLI / any tool
    | HTTPS_PROXY=http://127.0.0.1:8080
    v
mitmproxy (port 8080)
    | Decrypts HTTPS, detects provider by domain
    | TokentapAddon parses tokens, writes to MongoDB
    v
Upstream API (api.anthropic.com, api.openai.com, etc.)

MongoDB <--- Web Dashboard (port 3000)
```

Tokentap uses **mitmproxy** in regular HTTP proxy mode. When a CLI tool connects through `HTTPS_PROXY`, mitmproxy performs a man-in-the-middle on the TLS connection using its own CA certificate, allowing it to read the request and response in plaintext. Token usage is extracted from:

- **Anthropic**: `message_start` / `message_delta` SSE events, or `usage` in JSON response
- **OpenAI**: `usage` field in response or streaming chunks
- **Gemini**: `usageMetadata` field

Non-LLM traffic (any domain not in the intercept list) passes through the proxy untouched.

## Commands

| Command | Description |
|---------|-------------|
| `tokentap up` | Start proxy + web dashboard + MongoDB (Docker) |
| `tokentap down` | Stop all services |
| `tokentap status` | Show service status |
| `tokentap logs` | View service logs |
| `tokentap open` | Open web dashboard in browser |
| `tokentap install` | Add shell integration to ~/.zshrc or ~/.bashrc |
| `tokentap uninstall` | Remove shell integration |
| `tokentap shell-init` | Print env exports (for `eval "$(tokentap shell-init)"`) |
| `tokentap env` | Generate `.env` file for project-level config |
| `tokentap install-cert` | Trust the mitmproxy CA in system keychain |

### Legacy commands (no Docker)

| Command | Description |
|---------|-------------|
| `tokentap start` | Start proxy + Rich terminal dashboard |
| `tokentap claude` | Run Claude Code through proxy |
| `tokentap codex` | Run OpenAI Codex through proxy |
| `tokentap gemini` | Run Gemini CLI through proxy |
| `tokentap run --provider <name> <cmd>` | Run any command through proxy |

## Supported Providers

| Provider | Domain | Status |
|----------|--------|--------|
| Anthropic (Claude Code) | `api.anthropic.com` | Supported |
| OpenAI (Codex) | `api.openai.com` | Supported |
| Google (Gemini CLI) | `generativelanguage.googleapis.com` | Supported |

## Development

```bash
git clone https://github.com/jmuncor/tokentap.git
cd tokentap
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT -- see [LICENSE](LICENSE).

---

<p align="center">
  <em>See what's really being sent to the LLM. Track. Learn. Optimize.</em>
</p>
<p align="center">
  <a href="https://tokentap.ai">tokentap.ai</a>
</p>
