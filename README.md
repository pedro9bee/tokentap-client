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

## ✨ What's New in v0.4.0

### 🔧 Dynamic Provider Configuration
Add new LLM providers via JSON config—**no code changes required**! Use JSONPath expressions to define field mappings, enable "capture all" mode for debugging, and hot-reload configs without restart.

### 🚀 Robust Service Management
Auto-start on boot with systemd/launchd, automatic restart on failure, health monitoring, and centralized logging. Enable with `tokentap service enable`.

### 📊 Context Tracking
Track which programs and projects use LLM tokens. Perfect for monitoring automation scripts, CI/CD pipelines, and A/B testing experiments.

**See [Service Management](docs/SERVICE_MANAGEMENT.md), [Provider Configuration](docs/PROVIDER_CONFIGURATION.md), and [Context Tracking](docs/CONTEXT_METADATA.md) guides.**

---

## Installation

### Quick Start (Automated)

The fastest way to get tokentap running on a fresh machine:

```bash
# One-command install (downloads and runs install.sh)
curl -fsSL https://raw.githubusercontent.com/jmuncor/tokentap/main/scripts/install.sh | bash
```

Or for more control:

```bash
# Clone and install
git clone https://github.com/jmuncor/tokentap.git
cd tokentap

# Install system dependencies (if needed)
./scripts/setup.sh

# Install tokentap
./scripts/install.sh
```

The automated installer will:
1. Check for Python 3.10+, Docker, and curl
2. Create a virtual environment at `~/.tokentap/venv`
3. Install tokentap package
4. Start Docker services (proxy, web dashboard, MongoDB)
5. Install shell integration (adds `eval "$(tokentap shell-init)"` to your shell RC)
6. Optionally install the mitmproxy CA certificate system-wide

After installation, reload your shell and use your LLM tools normally. View the dashboard at `http://127.0.0.1:3000`.

### Service Configuration (Optional)

Configure tokentap to start automatically on boot and add convenient shell aliases:

```bash
./scripts/configure-service.sh setup
```

This will:
- Set up auto-start service (macOS: launchd, Linux: systemd)
- Add helpful shell aliases: `tokentap-start`, `tokentap-stop`, `tokentap-web-start`, `tokentap-web-stop`
- Configure logging at `~/.tokentap/logs/`

**Available aliases after configuration:**
```bash
tokentap-start        # Start proxy and all services
tokentap-stop         # Stop all services
tokentap-web-start    # Start only web dashboard
tokentap-web-stop     # Stop only web dashboard
tokentap-status       # Check service status
tokentap-logs         # View logs
tokentap-open         # Open dashboard in browser
```

For more details, see [Service Configuration Documentation](docs/README.md#service-configuration).

### Manual Installation (step by step)

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

## Platform-Specific Notes

### macOS (Intel & Apple Silicon)
- **Docker Desktop** is required. The automated installer can install it via Homebrew.
- **Homebrew** is recommended for dependency installation. If not installed, get it at [brew.sh](https://brew.sh).
- Certificate trust (`tokentap install-cert`) adds the CA to the System Keychain and requires sudo.

### Linux (Ubuntu/Debian)
- Docker installation: `sudo apt-get install docker.io docker-compose`
- After installing Docker, add your user to the docker group: `sudo usermod -aG docker $USER`
- **Important**: You must log out and back in after being added to the docker group
- Certificate trust copies the CA to `/usr/local/share/ca-certificates/` and requires sudo

### Linux (RHEL/CentOS/Fedora)
- Docker installation: `sudo dnf install docker docker-compose`
- Start Docker daemon: `sudo systemctl start docker && sudo systemctl enable docker`
- Add your user to the docker group: `sudo usermod -aG docker $USER`
- **Important**: You must log out and back in after being added to the docker group
- Certificate trust copies the CA to `/etc/pki/ca-trust/source/anchors/` and requires sudo

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
| Anthropic (Claude Code) | `api.anthropic.com` | ✅ Supported |
| OpenAI (Codex) | `api.openai.com` | ✅ Supported |
| Google (Gemini CLI) | `generativelanguage.googleapis.com` | ✅ Supported |
| Amazon Q (Kiro CLI) | `q.*.amazonaws.com` | ✅ Supported |

### Adding New Providers

**Tokentap now supports dynamic provider configuration!** You can add new LLM providers without modifying code:

1. Enable capture mode in `~/.tokentap/providers.json`:
   ```json
   {"capture_mode": "capture_all"}
   ```

2. Make test requests to the new provider

3. Inspect captured data in MongoDB to find field locations

4. Create provider configuration with JSONPath expressions

5. Reload: `tokentap reload-config`

See the **[Adding New Providers Guide](docs/DEBUGGING_NEW_PROVIDERS.md)** for step-by-step instructions.

## Service Management

Tokentap can run automatically when your machine boots with robust health monitoring:

```bash
# Enable auto-start on boot
tokentap service enable

# Check detailed status
tokentap service status

# Restart service
tokentap service restart
```

**Features:**
- ✅ Auto-start on boot (macOS launchd / Linux systemd)
- ✅ Automatic restart on failure
- ✅ Health monitoring with built-in checks
- ✅ Centralized logging at `~/.tokentap/logs/`

See **[Service Management Guide](docs/SERVICE_MANAGEMENT.md)** for full documentation.

## Context Tracking

Track which programs and projects are using LLM tokens:

```bash
# Method 1: Environment variables
export TOKENTAP_PROJECT="my-project"
export TOKENTAP_CONTEXT='{"experiment":"v2"}'
claude "Write code"

# Method 2: Wrapper script
./scripts/tokentap-wrapper.sh "my-automation" python bot.py

# Query usage by program
curl 'http://localhost:3000/api/stats/by-program'

# Query usage by project
curl 'http://localhost:3000/api/stats/by-project'
```

**Use cases:**
- Track automated scripts and bots
- A/B test different prompts
- Analyze usage by project/team
- Monitor CI/CD pipelines

See **[Context Metadata Guide](docs/CONTEXT_METADATA.md)** for details.

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

### Core Guides

- **[Service Management](docs/SERVICE_MANAGEMENT.md)** - Auto-start, health monitoring, restart policies
- **[Provider Configuration](docs/PROVIDER_CONFIGURATION.md)** - Add new providers via JSON config
- **[Context Tracking](docs/CONTEXT_METADATA.md)** - Track usage by program and project
- **[Debugging New Providers](docs/DEBUGGING_NEW_PROVIDERS.md)** - Step-by-step guide

### Installation & Setup

- **[Quick Reference](docs/INSTALL_QUICKREF.md)** - Fast installation and common commands
- **[Installation Scripts](docs/SCRIPTS.md)** - Detailed script documentation
- **[Before/After Comparison](docs/BEFORE_AFTER.md)** - User experience improvements

The `docs/` directory contains all supplementary documentation including:
- Service configuration and auto-start setup
- Dynamic provider configuration with JSONPath
- Context metadata for tracking programs and projects
- Installation guides and troubleshooting
- Script reference and platform-specific notes

For detailed information, see the [Documentation README](docs/README.md).

## Development

```bash
git clone https://github.com/jmuncor/tokentap.git
cd tokentap
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Troubleshooting

### Docker daemon is not running

**macOS:**
```bash
# Start Docker Desktop from Applications
open -a Docker

# Or install if not present
brew install --cask docker
```

**Linux (systemd):**
```bash
# Start Docker daemon
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Check status
sudo systemctl status docker
```

### Permission denied when accessing Docker

This usually means your user is not in the `docker` group:

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# IMPORTANT: Log out and back in for this to take effect
# Or run: newgrp docker (temporary for current shell)

# Verify group membership
groups
```

### Services won't start / Health checks fail

**Check logs:**
```bash
tokentap logs          # All services
tokentap logs proxy    # Just proxy
tokentap logs web      # Just web dashboard
```

**Common issues:**

1. **Port conflicts**: Another service is using port 8080 or 3000
   ```bash
   # Find what's using the port
   lsof -i :8080
   lsof -i :3000

   # Stop the conflicting service or change tokentap ports in docker-compose.yml
   ```

2. **Docker out of memory**: Increase Docker memory allocation in Docker Desktop preferences (macOS) or `/etc/docker/daemon.json` (Linux)

3. **Stale containers**: Remove old containers and volumes
   ```bash
   tokentap down
   docker system prune -a --volumes
   tokentap up
   ```

### Shell integration not working

**Verify environment variables:**
```bash
# Should output: http://127.0.0.1:8080
echo $HTTPS_PROXY

# If empty, reload your shell
source ~/.zshrc  # or ~/.bashrc
```

**Check shell RC file:**
```bash
# Should contain: eval "$(tokentap shell-init)"
grep "tokentap shell-init" ~/.zshrc  # or ~/.bashrc
```

**Manual fix:**
```bash
# Re-run shell integration
tokentap install

# Reload shell
source ~/.zshrc  # or ~/.bashrc
```

### SSL certificate verify failed

Some tools don't respect `SSL_CERT_FILE` and need system-wide certificate trust:

```bash
# Install certificate system-wide (requires sudo)
tokentap install-cert
```

If you've installed the certificate but still see errors:

**macOS:**
```bash
# Verify certificate is in keychain
security find-certificate -c "mitmproxy" /Library/Keychains/System.keychain
```

**Linux:**
```bash
# Verify certificate is trusted
ls /usr/local/share/ca-certificates/  # Ubuntu/Debian
ls /etc/pki/ca-trust/source/anchors/  # RHEL/CentOS
```

### Tools not respecting HTTPS_PROXY

Some tools need additional configuration:

**Node.js / npm:**
```bash
# Already handled by NODE_EXTRA_CA_CERTS from shell-init
# But if needed manually:
export NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
```

**Python / pip:**
```bash
# Already handled by REQUESTS_CA_BUNDLE and SSL_CERT_FILE
# But if needed manually:
export SSL_CERT_FILE=~/.mitmproxy/mitmproxy-ca-cert.pem
```

**Git:**
```bash
# Configure git to use system CA bundle
git config --global http.sslCAInfo ~/.mitmproxy/mitmproxy-ca-cert.pem
```

### Uninstall tokentap

Complete removal of tokentap and all data:

```bash
# Automated uninstall (interactive prompts)
./scripts/uninstall.sh
```

Or manually:

```bash
# Stop services
tokentap down

# Remove Docker volumes (deletes all data)
docker volume rm tokentap-client_mongodb_data
docker volume rm tokentap-client_mitmproxy_certs

# Remove shell integration
tokentap uninstall

# Uninstall package
pip uninstall tokentap

# Remove virtual environment
rm -rf ~/.tokentap/venv

# Remove CA certificate (macOS)
sudo security delete-certificate -Z $(openssl x509 -noout -fingerprint -sha1 -in ~/.mitmproxy/mitmproxy-ca-cert.pem | cut -d= -f2 | tr -d ':') /Library/Keychains/System.keychain

# Remove CA certificate (Ubuntu/Debian)
sudo rm /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt
sudo update-ca-certificates

# Remove CA certificate (RHEL/CentOS)
sudo rm /etc/pki/ca-trust/source/anchors/mitmproxy-ca-cert.pem
sudo update-ca-trust
```

### Getting Help

If you're still having issues:

1. Check the [GitHub issues](https://github.com/jmuncor/tokentap/issues) for similar problems
2. Enable verbose logging: `TOKENTAP_DEBUG=1 tokentap up`
3. Create a new issue with:
   - Your OS and version (`uname -a`)
   - Python version (`python --version`)
   - Docker version (`docker --version`)
   - Full error message and logs (`tokentap logs`)

## License

MIT -- see [LICENSE](LICENSE).

---

<p align="center">
  <em>See what's really being sent to the LLM. Track. Learn. Optimize.</em>
</p>
<p align="center">
  <a href="https://tokentap.ai">tokentap.ai</a>
</p>
