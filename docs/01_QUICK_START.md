# Quick Start Guide

Get Tokentap running in 5 minutes.

## What is Tokentap?

Tokentap is a transparent MITM proxy that tracks LLM token usage from any CLI tool (Claude Code, Codex, Gemini CLI, etc.) without modifying the tools themselves.

**Key Features:**
- 🔍 Real-time token tracking with web dashboard
- 🚀 Auto-start on boot with service management
- 🔧 Add new providers via JSON config (no code changes)
- 📊 Track usage by program and project
- 🐳 Docker-based setup (MongoDB + Web + Proxy)

## Prerequisites

- **Python 3.10+**
- **Docker** (Docker Desktop on macOS, Docker Engine on Linux)

Check versions:
```bash
python3 --version  # Should be 3.10 or higher
docker --version
```

## Installation

### Option 1: Automated Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/jmuncor/tokentap/main/scripts/install.sh | bash
```

This will:
1. Create virtual environment at `~/.tokentap/venv`
2. Install tokentap package
3. Start Docker services (proxy, web, MongoDB)
4. Configure shell integration
5. Optionally trust the mitmproxy CA certificate

### Option 2: Manual Install

```bash
# Install package
pip install tokentap

# Start services
tokentap up

# Configure shell (adds HTTPS_PROXY env vars)
tokentap install

# Reload shell
source ~/.zshrc  # or ~/.bashrc
```

## Verify Installation

```bash
# Check services are running
tokentap status

# Check proxy health
curl -x http://127.0.0.1:8080 http://localhost/health

# Open web dashboard
tokentap open
```

You should see:
- Web dashboard at `http://localhost:3000`
- Three Docker containers running (proxy, web, mongodb)

## First Usage

### Test with Claude Code

```bash
# Make sure shell integration is active (HTTPS_PROXY should be set)
echo $HTTPS_PROXY  # Should show: http://127.0.0.1:8080

# Use Claude Code normally
claude "Write hello world in Python"
```

### View Results

Open the web dashboard:
```bash
tokentap open
```

Or query MongoDB directly:
```bash
# View recent events
docker exec -it tokentap-client-mongodb-1 mongosh tokentap
db.events.find().sort({timestamp: -1}).limit(5).pretty()
```

## Enable Auto-Start (Optional)

Configure tokentap to start automatically when your machine boots:

```bash
tokentap service enable
```

Check status:
```bash
tokentap service status
```

## Common Commands

```bash
# Service control
tokentap up                    # Start all services
tokentap down                  # Stop all services
tokentap status                # Check status
tokentap logs -f               # Follow logs

# Service management (auto-start)
tokentap service enable        # Enable auto-start on boot
tokentap service disable       # Disable auto-start
tokentap service restart       # Restart service
tokentap service status        # Detailed status

# Configuration
tokentap install               # Add shell integration
tokentap install-cert          # Trust HTTPS CA certificate
tokentap reload-config         # Reload provider configuration
tokentap open                  # Open web dashboard
```

## Next Steps

Now that tokentap is running:

1. **[Service Management](03_SERVICE_MANAGEMENT.md)** - Configure auto-start and health monitoring
2. **[Provider Configuration](04_PROVIDER_CONFIGURATION.md)** - Add new LLM providers
3. **[Context Tracking](05_CONTEXT_METADATA.md)** - Track usage by program/project

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check logs
tokentap logs

# Restart services
tokentap down && tokentap up
```

### Proxy not intercepting traffic

```bash
# Verify HTTPS_PROXY is set
echo $HTTPS_PROXY

# Re-run shell integration
tokentap install
source ~/.zshrc  # or ~/.bashrc

# Verify proxy health
curl -x http://127.0.0.1:8080 http://localhost/health
```

### Dashboard not accessible

```bash
# Check if web container is running
tokentap status

# Check if port 3000 is in use
lsof -i :3000

# Restart services
tokentap down && tokentap up
```

For more issues, see [Troubleshooting Guide](07_TROUBLESHOOTING.md).

## Uninstall

```bash
# Stop services
tokentap down

# Remove shell integration
tokentap uninstall

# Remove service (if enabled)
tokentap service disable

# Remove Docker volumes (optional, removes all data)
docker compose -f path/to/docker-compose.yml down -v

# Uninstall package
pip uninstall tokentap
```

## Support

- **Documentation**: [docs/README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/jmuncor/tokentap/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jmuncor/tokentap/discussions)
