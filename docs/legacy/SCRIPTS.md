# Tokentap Installation Scripts

Automated installation scripts for tokentap that handle dependency checking, installation, and configuration.

## Scripts Overview

### `common.sh`
Shared utilities used by all other scripts:
- OS and package manager detection
- Colored logging functions
- Python version checking
- Docker daemon status checking
- Service health check polling
- Shell RC file detection

**Not meant to be run directly** - sourced by other scripts.

### `setup.sh`
Installs system dependencies (Python 3.10+, Docker, curl).

**Usage:**
```bash
./scripts/setup.sh
```

**What it does:**
1. Detects OS and package manager
2. Checks for required dependencies
3. Installs missing dependencies using platform-specific commands
4. Configures Docker (starts daemon, adds user to docker group on Linux)
5. Prints summary of what was installed

**Platform support:**
- macOS (Homebrew)
- Ubuntu/Debian (apt)
- RHEL/CentOS/Fedora (dnf/yum)

**Exit codes:**
- `0`: Success (all dependencies present or successfully installed)
- `1`: Failed to install one or more dependencies

### `install.sh`
Installs and configures tokentap application.

**Usage:**
```bash
./scripts/install.sh
```

**What it does:**
1. Pre-flight checks (Python 3.10+, Docker running, disk space)
2. Creates/activates virtual environment at `~/.tokentap/venv`
3. Installs tokentap package (from source if in repo, otherwise PyPI)
4. Starts Docker services (`tokentap up`)
5. Waits for health checks (proxy and web dashboard)
6. Installs shell integration (`tokentap install`)
7. Prompts for CA certificate installation (interactive)
8. Validates installation
9. Prints next steps

**Error handling:**
- Traps errors and runs cleanup on failure
- Rolls back changes (stops services, removes venv, removes shell integration)
- Prints helpful error messages and logs

**Exit codes:**
- `0`: Success (fully installed and validated)
- `1`: Failed (with rollback)

**Environment variables:**
- `CI`: Set to any value to skip interactive prompts

### `uninstall.sh`
Completely removes tokentap and optionally all data.

**Usage:**
```bash
./scripts/uninstall.sh
```

**What it does:**
1. Stops Docker services
2. Prompts to remove Docker volumes (deletes all data)
3. Removes shell integration
4. Uninstalls tokentap package
5. Prompts to remove virtual environment
6. Prompts to remove trusted CA certificate (requires sudo)

**Interactive prompts:**
- Remove Docker volumes? (data deletion)
- Remove virtual environment?
- Remove CA certificate? (requires sudo)

All prompts can be answered with `y` (yes) or `n` (no).

## Quick Start

### New Machine (Automated)

```bash
# One command - downloads and runs install.sh
curl -fsSL https://raw.githubusercontent.com/jmuncor/tokentap/main/scripts/install.sh | bash
```

### From Source (Full Control)

```bash
# Clone repository
git clone https://github.com/jmuncor/tokentap.git
cd tokentap

# Install dependencies (if needed)
./scripts/setup.sh

# Install tokentap
./scripts/install.sh
```

### Uninstall

```bash
# Complete removal
./scripts/uninstall.sh
```

## Platform-Specific Notes

### macOS

**Dependencies installed via Homebrew:**
- `python@3.10` (if Python 3.10+ not found)
- `docker` (Docker Desktop as cask)
- `curl` (usually pre-installed)

**Docker:**
- Docker Desktop is installed but not started automatically
- User must start Docker Desktop from Applications manually
- No docker group management needed (Desktop handles permissions)

**Certificate trust:**
- Adds to System Keychain via `security add-trusted-cert`
- Requires sudo privileges

### Linux (Ubuntu/Debian)

**Dependencies installed via apt:**
- `python3 python3-pip python3-venv`
- `docker.io docker-compose`
- `curl`

**Docker:**
- Daemon started automatically: `systemctl start docker`
- User added to docker group: `usermod -aG docker $USER`
- **User must log out and back in** for group membership to take effect

**Certificate trust:**
- Copies to `/usr/local/share/ca-certificates/`
- Runs `update-ca-certificates`
- Requires sudo privileges

### Linux (RHEL/CentOS/Fedora)

**Dependencies installed via dnf/yum:**
- `python3 python3-pip`
- `docker docker-compose`
- `curl`

**Docker:**
- Daemon started and enabled: `systemctl start docker && systemctl enable docker`
- User added to docker group: `usermod -aG docker $USER`
- **User must log out and back in** for group membership to take effect

**Certificate trust:**
- Copies to `/etc/pki/ca-trust/source/anchors/`
- Runs `update-ca-trust`
- Requires sudo privileges

## Design Principles

### POSIX Compliance
- Uses `/bin/sh` (not bash-specific features)
- Compatible with sh, bash, zsh, dash
- Portable across different Unix-like systems

### Idempotency
- Safe to run multiple times
- Checks before acting (command exists, file exists, service running)
- Doesn't re-install if already present

### Error Handling
- Uses `set -e` to exit on error
- Traps ERR signal for cleanup
- Prints helpful error messages
- Continues with other dependencies if one fails (in setup.sh)

### User Experience
- Colored output with fallback for non-terminals
- Progress indicators for long operations
- Clear section headers and summaries
- Interactive prompts where appropriate (can be skipped in CI)

## Testing

### Syntax Check
```bash
# Verify shell syntax
for script in scripts/*.sh; do
  sh -n "$script"
done
```

### Unit Test Utilities
```bash
# Test common.sh functions
sh -c '. ./scripts/common.sh && detect_os'
sh -c '. ./scripts/common.sh && find_python'
sh -c '. ./scripts/common.sh && is_docker_running'
```

### Integration Test
```bash
# Full install on clean system (recommended: use Docker container)
./scripts/setup.sh
./scripts/install.sh

# Verify
tokentap status
echo $HTTPS_PROXY  # Should be http://127.0.0.1:8080

# Uninstall
./scripts/uninstall.sh
```

### Test Environments

**macOS:**
- Fresh macOS with Homebrew (Intel)
- Fresh macOS with Homebrew (ARM/Apple Silicon)
- macOS with Docker Desktop already installed

**Linux:**
```bash
# Ubuntu 22.04
docker run -it --privileged ubuntu:22.04 bash
apt-get update && apt-get install -y git curl sudo
# Run install scripts

# CentOS Stream 9
docker run -it --privileged quay.io/centos/centos:stream9 bash
dnf install -y git curl sudo
# Run install scripts
```

**Edge cases:**
- Install when services already running (idempotency)
- Install after partial failure (resume)
- Install without sudo access (graceful failure on cert install)
- Python 3.9 installed (fail with helpful message)

## Troubleshooting

### "Pre-flight checks failed"
Run `./scripts/setup.sh` to install missing dependencies.

### "Docker daemon is not running"
- **macOS**: Start Docker Desktop from Applications
- **Linux**: `sudo systemctl start docker`

### "Permission denied" when accessing Docker
Add your user to docker group and re-login:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Installation hangs during health checks
Check service logs:
```bash
tokentap logs proxy
tokentap logs web
```

Common issues:
- Port 8080 or 3000 already in use
- Docker out of memory
- Firewall blocking localhost connections

### Shell integration not working
Manually reload shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

Verify environment variable:
```bash
echo $HTTPS_PROXY  # Should be http://127.0.0.1:8080
```

## CI/CD Integration

Scripts detect CI environments and skip interactive prompts:
- GitHub Actions: `$GITHUB_ACTIONS`
- Travis CI: `$TRAVIS`
- CircleCI: `$CIRCLECI`
- Generic: `$CI`

Example GitHub Actions workflow:
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: ./scripts/setup.sh
      - name: Install tokentap
        run: ./scripts/install.sh
        env:
          CI: true
      - name: Test
        run: |
          source ~/.bashrc
          tokentap status
```

## Contributing

When modifying scripts:

1. **Maintain POSIX compliance** - test with `/bin/sh` not `/bin/bash`
2. **Run shellcheck** - `shellcheck scripts/*.sh`
3. **Test on multiple platforms** - macOS and Linux (Ubuntu + CentOS)
4. **Update this README** - document new functionality
5. **Test edge cases** - partial install, re-run, missing sudo

## License

MIT - See [LICENSE](../LICENSE)
