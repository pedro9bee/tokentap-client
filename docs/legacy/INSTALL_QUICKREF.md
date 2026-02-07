# Tokentap Installation Quick Reference

## One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/jmuncor/tokentap/main/scripts/install.sh | bash
```

After installation:
```bash
source ~/.zshrc  # or ~/.bashrc
tokentap open    # Opens http://127.0.0.1:3000
```

## From Source

```bash
git clone https://github.com/jmuncor/tokentap.git
cd tokentap

# Option 1: Automated (recommended)
../scripts/install.sh

# Option 2: Step by step
../scripts/setup.sh   # Install dependencies
../scripts/install.sh # Install tokentap
```

## Manual Install

```bash
# 1. Prerequisites
# - Python 3.10+
# - Docker & Docker Compose
# - curl

# 2. Install
pip install tokentap

# 3. Start services
tokentap up

# 4. Shell integration
tokentap install
source ~/.zshrc  # or ~/.bashrc

# 5. (Optional) Trust CA certificate
tokentap install-cert

# 6. Open dashboard
tokentap open
```

## Verify Installation

```bash
# Check services
tokentap status

# Check proxy is configured
echo $HTTPS_PROXY
# Should output: http://127.0.0.1:8080

# Test proxy health
curl -x http://127.0.0.1:8080 http://localhost/health

# Test web dashboard
curl http://127.0.0.1:3000
```

## Troubleshooting

### Docker not running
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### Permission denied (Docker)
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Services won't start
```bash
tokentap logs        # View all logs
tokentap logs proxy  # View proxy logs
tokentap logs web    # View web logs
```

### Proxy not working
```bash
# Reload shell
source ~/.zshrc  # or ~/.bashrc

# Verify environment
echo $HTTPS_PROXY
grep "tokentap shell-init" ~/.zshrc
```

### SSL certificate errors
```bash
tokentap install-cert  # Trust CA system-wide
```

## Uninstall

```bash
# Automated (recommended)
../scripts/uninstall.sh

# Manual
tokentap down                                # Stop services
docker volume rm tokentap-client_mongodb_data  # Delete data
docker volume rm tokentap-client_mitmproxy_certs
tokentap uninstall                           # Remove shell integration
pip uninstall tokentap                       # Uninstall package
rm -rf ~/.tokentap                           # Remove venv
```

## Commands

| Command | Description |
|---------|-------------|
| `tokentap up` | Start all services |
| `tokentap down` | Stop all services |
| `tokentap status` | Check service status |
| `tokentap logs` | View logs |
| `tokentap open` | Open web dashboard |
| `tokentap install` | Add shell integration |
| `tokentap uninstall` | Remove shell integration |
| `tokentap install-cert` | Trust CA certificate |

## Platform Notes

### macOS
- Requires Docker Desktop
- Install via: `brew install --cask docker`
- Start Docker Desktop before running `tokentap up`

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER  # Log out and back in
```

### Linux (RHEL/CentOS/Fedora)
```bash
sudo dnf install docker docker-compose
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER  # Log out and back in
```

## Help

- Documentation: [README.md](../README.md)
- Troubleshooting: [README.md#troubleshooting](../README.md#troubleshooting)
- Issues: https://github.com/jmuncor/tokentap/issues
- Script docs: [SCRIPTS.md](SCRIPTS.md)
