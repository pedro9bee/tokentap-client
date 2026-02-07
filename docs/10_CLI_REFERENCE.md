# CLI Reference

Complete command reference for tokentap CLI.

## Command Format

```bash
tokentap <command> [options]
```

## Docker Commands

### up

Start tokentap services (proxy + web dashboard + MongoDB).

```bash
tokentap up [--build] [--no-detach]

Options:
  --build       Rebuild Docker images (default: true)
  --no-detach   Run in foreground (for systemd)

Examples:
  tokentap up                    # Start services
  tokentap up --no-build         # Start without rebuild
  tokentap up --no-detach        # Foreground mode
```

### down

Stop tokentap services.

```bash
tokentap down

Examples:
  tokentap down
```

### status

Show status of tokentap services.

```bash
tokentap status

Examples:
  tokentap status
```

### logs

Show logs from tokentap services.

```bash
tokentap logs [-f] [service]

Options:
  -f, --follow  Follow log output
  service       Specific service (proxy, web, mongodb)

Examples:
  tokentap logs            # All logs
  tokentap logs -f         # Follow all logs
  tokentap logs proxy      # Proxy logs only
  tokentap logs -f web     # Follow web logs
```

### open

Open the web dashboard in your browser.

```bash
tokentap open

Examples:
  tokentap open
```

## Service Management Commands

### service enable

Enable auto-start on boot.

```bash
tokentap service enable

Examples:
  tokentap service enable
```

### service disable

Disable auto-start.

```bash
tokentap service disable

Examples:
  tokentap service disable
```

### service restart

Restart the service.

```bash
tokentap service restart

Examples:
  tokentap service restart
```

### service status

Show detailed service status.

```bash
tokentap service status

Examples:
  tokentap service status
```

## Configuration Commands

### install

Add tokentap shell integration to your shell RC file.

```bash
tokentap install

Examples:
  tokentap install
```

### uninstall

Remove tokentap shell integration.

```bash
tokentap uninstall

Examples:
  tokentap uninstall
```

### shell-init

Print shell environment exports for eval.

```bash
tokentap shell-init

Examples:
  eval "$(tokentap shell-init)"
```

### install-cert

Trust the mitmproxy CA certificate.

```bash
tokentap install-cert

Examples:
  tokentap install-cert
```

### reload-config

Reload provider configuration without restart.

```bash
tokentap reload-config

Examples:
  tokentap reload-config
```

### env

Generate .env file contents for project-level proxy config.

```bash
tokentap env [-o FILE]

Options:
  -o, --output FILE  Write to file instead of stdout

Examples:
  tokentap env              # Print to stdout
  tokentap env >> .env      # Append to .env
  tokentap env -o .env      # Write to .env
```

## Legacy Commands

### start

[Legacy] Start proxy and Rich terminal dashboard.

```bash
tokentap start [-p PORT] [-l LIMIT]

Options:
  -p, --port PORT    Proxy port (default: 8080)
  -l, --limit LIMIT  Token limit (default: 200000)

Examples:
  tokentap start
  tokentap start -p 8081
```

**Note**: Consider using `tokentap up` for Docker-based setup instead.

### claude / codex / gemini

[Legacy] Run LLM CLI through proxy.

```bash
tokentap claude [args...]
tokentap codex [args...]
tokentap gemini [args...]

Examples:
  tokentap claude "Write hello world"
  tokentap codex --help
```

**Note**: With shell integration, use CLI directly without wrapper.

### run

[Legacy] Run any command through proxy.

```bash
tokentap run --provider NAME <command> [args...]

Options:
  --provider NAME  Provider name (anthropic, openai, gemini)

Examples:
  tokentap run --provider anthropic claude "Write code"
```

## Environment Variables

Tokentap respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TOKENTAP_MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `TOKENTAP_MONGO_DB` | MongoDB database name | `tokentap` |
| `TOKENTAP_WEB_PORT` | Web dashboard port | `3000` |
| `TOKENTAP_PROJECT` | Project name for context | Current directory |
| `TOKENTAP_CONTEXT` | Full JSON context | `{}` |
| `HTTPS_PROXY` | Proxy URL (set by shell-init) | `http://127.0.0.1:8080` |
| `HTTP_PROXY` | HTTP proxy URL | `http://127.0.0.1:8080` |
| `NO_PROXY` | Bypass proxy for hosts | `localhost,127.0.0.1` |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Command not found |
| 130 | Interrupted (Ctrl+C) |

## Examples

### Complete Setup Flow

```bash
# Install and start
pip install tokentap
tokentap up
tokentap install
source ~/.zshrc

# Enable auto-start
tokentap service enable

# Use normally
claude "Write code"

# View dashboard
tokentap open
```

### Project-Specific Configuration

```bash
# In project directory
tokentap env -o .env

# Add to .env:
# HTTPS_PROXY=http://127.0.0.1:8080
# ...

# Now all API calls in this project go through proxy
```

### Add New Provider

```bash
# Enable capture mode
echo '{"capture_mode":"capture_all"}' > ~/.tokentap/providers.json
tokentap reload-config

# Make test request
your-new-cli "test"

# Inspect captured data
docker exec -it tokentap-client-mongodb-1 mongosh tokentap
db.events.find({provider:"unknown"}).limit(1).pretty()

# Create provider config in ~/.tokentap/providers.json
# Reload
tokentap reload-config
```

## See Also

- [Quick Start](01_QUICK_START.md)
- [Service Management](03_SERVICE_MANAGEMENT.md)
- [Provider Configuration](04_PROVIDER_CONFIGURATION.md)
