# Tokentap Documentation

Complete documentation for Tokentap - LLM token usage tracker with MITM proxy, dynamic provider configuration, and service management.

**Current Version**: 0.4.0

## 📚 Documentation Index

Read the documentation in this suggested order:

### Getting Started

1. **[Quick Start Guide](01_QUICK_START.md)** - Get up and running in 5 minutes
2. **[Installation Guide](02_INSTALLATION.md)** - Detailed installation instructions for all platforms

### Core Features

3. **[Service Management](03_SERVICE_MANAGEMENT.md)** - Auto-start on boot, health monitoring, restart policies
4. **[Provider Configuration](04_PROVIDER_CONFIGURATION.md)** - Add new LLM providers via JSON config
5. **[Context Tracking](05_CONTEXT_METADATA.md)** - Track usage by program and project
6. **[Debugging New Providers](06_DEBUGGING_NEW_PROVIDERS.md)** - Step-by-step guide to add providers

### Reference & Advanced

7. **[Troubleshooting](07_TROUBLESHOOTING.md)** - Common issues and solutions
8. **[CLI Reference](10_CLI_REFERENCE.md)** - Complete command reference
9. **[Architecture](11_ARCHITECTURE.md)** - How Tokentap works internally

### Project Information

- **[CHANGES.md](CHANGES.md)** - Version history and changelog with decision log
- **[Legacy Docs](legacy/)** - Previous documentation (service configuration, scripts reference)

## Quick Links

### Most Common Tasks

| Task | Documentation |
|------|---------------|
| **Get started quickly** | [Quick Start](01_QUICK_START.md) |
| **Install on my machine** | [Installation](02_INSTALLATION.md) |
| **Enable auto-start on boot** | [Service Management → Enable](03_SERVICE_MANAGEMENT.md#enable-auto-start) |
| **Add a new LLM provider** | [Debugging New Providers](06_DEBUGGING_NEW_PROVIDERS.md) |
| **Track usage by project** | [Context Tracking](05_CONTEXT_METADATA.md) |
| **Fix an issue** | [Troubleshooting](07_TROUBLESHOOTING.md) |
| **See all commands** | [CLI Reference](10_CLI_REFERENCE.md) |

## What's New in v0.4.0

### 🔧 Dynamic Provider Configuration
- Add new LLM providers via JSON config (no code changes)
- JSONPath expressions for field extraction
- "Capture all" mode for debugging unknown providers
- Hot-reload with `tokentap reload-config`

### 🚀 Robust Service Management
- Auto-start on boot (macOS launchd / Linux systemd)
- Automatic restart on failure
- Health monitoring with built-in checks
- Centralized logging

### 📊 Context Tracking
- Track usage by program and project
- Custom tags and metadata
- Perfect for monitoring automation scripts and CI/CD

**See [CHANGES.md](CHANGES.md) for complete details.**

## Documentation Structure

```
docs/
├── README.md                          # This file - documentation index
├── 01_QUICK_START.md                  # 5-minute getting started
├── 02_INSTALLATION.md                 # Detailed installation
├── 03_SERVICE_MANAGEMENT.md           # Auto-start and service control
├── 04_PROVIDER_CONFIGURATION.md       # Dynamic provider config
├── 05_CONTEXT_METADATA.md             # Context tracking
├── 06_DEBUGGING_NEW_PROVIDERS.md      # Adding new providers
├── 07_TROUBLESHOOTING.md              # Common issues
├── 10_CLI_REFERENCE.md                # CLI command reference
├── 11_ARCHITECTURE.md                 # Technical architecture
├── CHANGES.md                         # Version history with decision log
└── legacy/                            # Previous documentation
    ├── BEFORE_AFTER.md
    ├── INSTALL_QUICKREF.md
    ├── INSTALLATION_SCRIPTS.md
    └── SCRIPTS.md
```

## For Different Audiences

### New Users

Start here:
1. [Quick Start](01_QUICK_START.md) - Get running in 5 minutes
2. [Installation](02_INSTALLATION.md) - Detailed setup guide
3. [Service Management](03_SERVICE_MANAGEMENT.md) - Enable auto-start

### Developers Adding Providers

1. [Provider Configuration](04_PROVIDER_CONFIGURATION.md) - JSON config reference
2. [Debugging New Providers](06_DEBUGGING_NEW_PROVIDERS.md) - Step-by-step guide
3. [Architecture](11_ARCHITECTURE.md) - How parsing works

### DevOps / CI/CD

1. [Context Tracking](05_CONTEXT_METADATA.md) - Monitor automated scripts
2. [Service Management](03_SERVICE_MANAGEMENT.md) - Production deployment
3. [CLI Reference](10_CLI_REFERENCE.md) - Automation commands

### Troubleshooting

1. [Troubleshooting](07_TROUBLESHOOTING.md) - Common issues
2. [Service Management → Troubleshooting](03_SERVICE_MANAGEMENT.md#troubleshooting) - Service-specific issues
3. [GitHub Issues](https://github.com/jmuncor/tokentap/issues) - Report bugs

## Support

- **Documentation**: You're reading it!
- **Issues**: [GitHub Issues](https://github.com/jmuncor/tokentap/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jmuncor/tokentap/discussions)
- **Email**: support@tokentap.ai

## Contributing to Documentation

See main [README.md](../README.md) for contribution guidelines.

**Documentation standards**:
- GitHub-flavored Markdown
- Code blocks with language specifiers
- Working examples with expected output
- Cross-references to related docs
- Clear headings and sections

## License

All documentation is released under the MIT License - see [LICENSE](../LICENSE).
