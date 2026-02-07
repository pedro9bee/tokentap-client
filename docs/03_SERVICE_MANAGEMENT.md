# Service Management Guide

This guide explains how to set up tokentap to run automatically when your machine boots, with health monitoring and automatic restart on failure.

## Quick Start

```bash
# Enable auto-start on boot
tokentap service enable

# Check status
tokentap service status

# View logs
./scripts/service-manager.sh logs -f
```

## Overview

Tokentap supports robust service management on both macOS and Linux:

- **Auto-start on boot**: Service starts when you log in (macOS) or machine boots (Linux)
- **Automatic restart**: Service restarts automatically if it crashes
- **Health monitoring**: Built-in health checks for the proxy
- **Log management**: Centralized logging to `~/.tokentap/logs/`

## macOS (launchd)

### Enable Auto-Start

```bash
tokentap service enable
```

This creates `~/Library/LaunchAgents/com.tokentap.service.plist` with:

- **RunAtLoad**: Starts on login
- **KeepAlive**: Automatically restarts on crash
- **ThrottleInterval**: Waits 10 seconds between restart attempts

### Manual Service Control

```bash
# Start service
./scripts/service-manager.sh start

# Stop service
./scripts/service-manager.sh stop

# Restart service
./scripts/service-manager.sh restart

# Check detailed status
./scripts/service-manager.sh status
```

### View Logs

```bash
# View service logs
./scripts/service-manager.sh logs

# Follow logs in real-time
./scripts/service-manager.sh logs -f

# Or directly access log files
tail -f ~/.tokentap/logs/service.log
tail -f ~/.tokentap/logs/service.error.log
```

### Disable Auto-Start

```bash
tokentap service disable
```

### Manual Service Configuration

If you prefer manual setup, create `~/Library/LaunchAgents/com.tokentap.service.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tokentap.service</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/sh</string>
        <string>-c</string>
        <string>cd ~/.tokentap && ./venv/bin/tokentap up</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>StandardOutPath</key>
    <string>~/.tokentap/logs/service.log</string>

    <key>StandardErrorPath</key>
    <string>~/.tokentap/logs/service.error.log</string>
</dict>
</plist>
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.tokentap.service.plist
```

## Linux (systemd)

### Enable Auto-Start

```bash
tokentap service enable
```

This creates `~/.config/systemd/user/tokentap.service` with:

- **Type=simple**: Foreground service with `--no-detach` flag
- **Restart=on-failure**: Automatically restarts on crash
- **RestartSec=10**: Waits 10 seconds between restart attempts
- **After/Requires docker.service**: Ensures Docker is running first

### Manual Service Control

```bash
# Start service
systemctl --user start tokentap.service

# Stop service
systemctl --user stop tokentap.service

# Restart service
systemctl --user restart tokentap.service

# Check status
systemctl --user status tokentap.service

# Enable/disable auto-start
systemctl --user enable tokentap.service
systemctl --user disable tokentap.service
```

### View Logs

```bash
# View all logs
journalctl --user -u tokentap.service

# Follow logs in real-time
journalctl --user -u tokentap.service -f

# Last 50 lines
journalctl --user -u tokentap.service -n 50

# Or use the service manager
./scripts/service-manager.sh logs -f
```

### Enable Lingering (Optional)

By default, user services stop when you log out. To keep tokentap running even when logged out:

```bash
loginctl enable-linger $USER
```

### Manual Service Configuration

If you prefer manual setup, create `~/.config/systemd/user/tokentap.service`:

```ini
[Unit]
Description=Tokentap LLM Token Tracking Service
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=%h/.tokentap
ExecStart=%h/.tokentap/venv/bin/tokentap up --no-detach
ExecStop=%h/.tokentap/venv/bin/tokentap down
Restart=on-failure
RestartSec=10
StandardOutput=append:%h/.tokentap/logs/service.log
StandardError=append:%h/.tokentap/logs/service.error.log

[Install]
WantedBy=default.target
```

Then enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable tokentap.service
systemctl --user start tokentap.service
```

## Health Monitoring

The service includes automatic health monitoring:

### Built-in Health Check

```bash
# Check if proxy is responding
curl -x http://127.0.0.1:8080 http://localhost/health

# Should return:
# {"status": "ok", "proxy": true}
```

### Status Command

```bash
./scripts/service-manager.sh status
```

This checks:
- Service status (launchd/systemd)
- Docker container status
- Proxy health check endpoint

### Manual Health Check

```bash
# Check Docker containers
tokentap status

# Check proxy health
curl -sf -x http://127.0.0.1:8080 http://localhost/health && echo "✓ Proxy OK" || echo "✗ Proxy failed"
```

## Troubleshooting

### Service Won't Start

1. **Check Docker is running**:
   ```bash
   docker ps
   ```

2. **Check logs**:
   ```bash
   ./scripts/service-manager.sh logs
   ```

3. **Manual start to see errors**:
   ```bash
   tokentap up
   ```

### Service Keeps Restarting

Check the error logs:

**macOS**:
```bash
tail -f ~/.tokentap/logs/service.error.log
```

**Linux**:
```bash
journalctl --user -u tokentap.service -n 100
```

Common causes:
- Port 8080 already in use
- MongoDB connection failed
- Docker daemon not running

### Proxy Health Check Fails

1. **Wait a moment**: Services may take 10-15 seconds to start

2. **Check container status**:
   ```bash
   tokentap status
   ```

3. **Check proxy logs**:
   ```bash
   tokentap logs proxy
   ```

4. **Test proxy directly**:
   ```bash
   curl -x http://127.0.0.1:8080 http://localhost/health
   ```

### Changes Not Taking Effect

After modifying service files, reload the configuration:

**macOS**:
```bash
launchctl unload ~/Library/LaunchAgents/com.tokentap.service.plist
launchctl load ~/Library/LaunchAgents/com.tokentap.service.plist
```

**Linux**:
```bash
systemctl --user daemon-reload
systemctl --user restart tokentap.service
```

## Log Rotation

Service logs are appended to `~/.tokentap/logs/`. To prevent logs from growing indefinitely:

### macOS

Use `newsyslog` or manually rotate:

```bash
# Rotate logs
mv ~/.tokentap/logs/service.log ~/.tokentap/logs/service.log.old
./scripts/service-manager.sh restart
```

### Linux

Use `logrotate`:

Create `/etc/logrotate.d/tokentap`:

```
/home/*/.tokentap/logs/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl --user reload tokentap.service
    endscript
}
```

## Advanced Configuration

### Custom Ports

To use a different port, edit the service file and change `DEFAULT_PROXY_PORT`:

```bash
# Edit service file (macOS)
vim ~/Library/LaunchAgents/com.tokentap.service.plist

# Edit service file (Linux)
vim ~/.config/systemd/user/tokentap.service
```

### Environment Variables

Add environment variables to the service:

**macOS** (launchd):
```xml
<key>EnvironmentVariables</key>
<dict>
    <key>TOKENTAP_MONGO_URI</key>
    <string>mongodb://custom-host:27017</string>
</dict>
```

**Linux** (systemd):
```ini
[Service]
Environment="TOKENTAP_MONGO_URI=mongodb://custom-host:27017"
```

## See Also

- [Provider Configuration Guide](PROVIDER_CONFIGURATION.md)
- [Context Metadata Guide](CONTEXT_METADATA.md)
- [Debugging New Providers](DEBUGGING_NEW_PROVIDERS.md)
