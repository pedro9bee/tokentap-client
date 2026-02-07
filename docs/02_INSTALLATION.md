# Installation Guide

Detailed installation instructions for all platforms.

## System Requirements

- **Python**: 3.10 or higher
- **Docker**: Docker Desktop (macOS) or Docker Engine (Linux)
- **Disk Space**: ~500MB for Docker images
- **RAM**: 2GB minimum

## Installation Methods

### Method 1: Automated Script (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/jmuncor/tokentap/main/scripts/install.sh | bash
```

**What it does:**
1. Checks Python 3.10+ and Docker
2. Creates `~/.tokentap/venv` virtual environment
3. Installs tokentap package
4. Starts Docker services
5. Configures shell integration
6. Offers to trust mitmproxy CA certificate

### Method 2: From PyPI

```bash
pip install tokentap
tokentap up
tokentap install
```

### Method 3: From Source

```bash
git clone https://github.com/jmuncor/tokentap.git
cd tokentap
pip install -e .
tokentap up
tokentap install
```

## Post-Installation

### 1. Verify Installation

```bash
tokentap status
tokentap open
```

### 2. Trust CA Certificate (Optional but Recommended)

Required for HTTPS interception:

```bash
tokentap install-cert
```

**macOS**: Adds to system keychain
**Linux**: Adds to `/usr/local/share/ca-certificates/`

### 3. Configure Auto-Start (Optional)

```bash
tokentap service enable
```

## Platform-Specific Notes

### macOS

**Requirements:**
- macOS 10.15+ (Catalina or later)
- Docker Desktop 4.0+

**Permissions:**
- `tokentap install-cert` requires sudo (adds to system keychain)

**Shell:**
- Supports zsh (default) and bash
- Shell integration added to `~/.zshrc` or `~/.bashrc`

### Linux (Ubuntu/Debian)

**Requirements:**
- Ubuntu 20.04+ or Debian 11+
- Docker Engine 20.10+

**Installation:**
```bash
# Install Docker if needed
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install tokentap
pip install tokentap
tokentap up
```

**Permissions:**
- `tokentap install-cert` requires sudo (updates CA certificates)

### Linux (Other Distributions)

Tokentap should work on any Linux with Docker. Install Docker for your distribution and follow standard installation.

## Verification

After installation, verify each component:

```bash
# 1. Check Python version
python3 --version  # Should be 3.10+

# 2. Check Docker
docker ps

# 3. Check tokentap command
tokentap --version

# 4. Check services
tokentap status

# 5. Check proxy health
curl -x http://127.0.0.1:8080 http://localhost/health

# 6. Check environment
echo $HTTPS_PROXY  # Should be: http://127.0.0.1:8080
```

## Configuration Files

Tokentap creates these directories and files:

```
~/.tokentap/
├── venv/                          # Python virtual environment
├── logs/                          # Service logs
│   ├── service.log
│   └── service.error.log
└── providers.json                 # User provider overrides (optional)

~/.mitmproxy/
└── mitmproxy-ca-cert.pem          # HTTPS CA certificate
```

## Upgrading

### From PyPI

```bash
pip install --upgrade tokentap
tokentap down
tokentap up --build
```

### From Source

```bash
git pull
pip install -e .
tokentap down
tokentap up --build
```

## Uninstallation

### Complete Removal

```bash
# 1. Stop services
tokentap down

# 2. Remove shell integration
tokentap uninstall

# 3. Disable service (if enabled)
tokentap service disable

# 4. Remove Docker volumes (optional, deletes all data)
docker volume rm tokentap-client_mongodb_data
docker volume rm tokentap-client_mitmproxy_data

# 5. Remove tokentap directory
rm -rf ~/.tokentap

# 6. Uninstall package
pip uninstall tokentap

# 7. Remove CA certificate (optional)
# macOS:
sudo security delete-certificate -c "mitmproxy"
# Linux:
sudo rm /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt
sudo update-ca-certificates
```

### Keep Data, Remove Software

```bash
# Stop services but keep data
tokentap down

# Uninstall package
pip uninstall tokentap
```

## Next Steps

- **[Quick Start Guide](01_QUICK_START.md)** - Get started quickly
- **[Service Management](03_SERVICE_MANAGEMENT.md)** - Configure auto-start
- **[Troubleshooting](07_TROUBLESHOOTING.md)** - Fix common issues
