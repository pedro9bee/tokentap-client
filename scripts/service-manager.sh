#!/usr/bin/env bash
#
# Tokentap Service Manager
# Robust service management with health monitoring and auto-restart
#
# Usage:
#   ./service-manager.sh start      # Start service
#   ./service-manager.sh stop       # Stop service
#   ./service-manager.sh restart    # Restart service
#   ./service-manager.sh status     # Show detailed status
#   ./service-manager.sh enable     # Enable auto-start on boot
#   ./service-manager.sh disable    # Disable auto-start
#   ./service-manager.sh logs [-f]  # View logs

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Wait for proxy health check
wait_for_proxy() {
    local proxy_url="$1"
    local timeout="${2:-30}"
    local interval="${3:-2}"
    local elapsed=0

    log_info "Waiting for proxy to be ready..."

    while [ $elapsed -lt $timeout ]; do
        if curl -sf -x "$proxy_url" http://localhost/health >/dev/null 2>&1; then
            log_success "Proxy is ready"
            return 0
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
        echo -n "."
    done

    log_error "Proxy health check failed after ${timeout}s"
    return 1
}

# macOS (launchd) functions
macos_service_file() {
    echo "$HOME/Library/LaunchAgents/com.tokentap.service.plist"
}

macos_create_service() {
    local service_file
    service_file=$(macos_service_file)
    local tokentap_dir="$HOME/.tokentap"

    mkdir -p "$HOME/Library/LaunchAgents"
    mkdir -p "$tokentap_dir/logs"

    cat >"$service_file" <<EOF
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
        <string>cd $tokentap_dir && ./venv/bin/tokentap up</string>
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
    <string>$tokentap_dir/logs/service.log</string>

    <key>StandardErrorPath</key>
    <string>$tokentap_dir/logs/service.error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

    log_success "Created launchd service: $service_file"
}

macos_enable() {
    local service_file
    service_file=$(macos_service_file)

    if [ ! -f "$service_file" ]; then
        macos_create_service
    fi

    launchctl load "$service_file" 2>/dev/null || true
    log_success "Service enabled (will start on login)"
}

macos_disable() {
    local service_file
    service_file=$(macos_service_file)

    if [ -f "$service_file" ]; then
        launchctl unload "$service_file" 2>/dev/null || true
        log_success "Service disabled"
    else
        log_warn "Service file not found"
    fi
}

macos_start() {
    macos_enable
    wait_for_proxy "http://127.0.0.1:8080" 30 2
}

macos_stop() {
    # Stop containers first
    if command -v tokentap >/dev/null 2>&1; then
        tokentap down 2>/dev/null || true
    fi

    macos_disable
    log_success "Service stopped"
}

macos_status() {
    local service_file
    service_file=$(macos_service_file)

    if launchctl list | grep -q "com.tokentap.service"; then
        log_success "Service is loaded in launchd"
    else
        log_warn "Service is not loaded in launchd"
    fi

    # Check containers
    if command -v tokentap >/dev/null 2>&1; then
        echo ""
        log_info "Docker containers:"
        tokentap status || log_error "Containers not running"
    fi

    # Check proxy health
    echo ""
    if curl -sf -x http://127.0.0.1:8080 http://localhost/health >/dev/null 2>&1; then
        log_success "Proxy health check: OK"
    else
        log_error "Proxy health check: FAILED"
    fi
}

macos_logs() {
    local follow="${1:-}"
    local tokentap_dir="$HOME/.tokentap"

    if [ "$follow" = "-f" ]; then
        tail -f "$tokentap_dir/logs/service.log"
    else
        cat "$tokentap_dir/logs/service.log"
    fi
}

# Linux (systemd) functions
linux_service_file() {
    echo "$HOME/.config/systemd/user/tokentap.service"
}

linux_create_service() {
    local service_file
    service_file=$(linux_service_file)
    local tokentap_dir="$HOME/.tokentap"

    mkdir -p "$HOME/.config/systemd/user"
    mkdir -p "$tokentap_dir/logs"

    cat >"$service_file" <<EOF
[Unit]
Description=Tokentap LLM Token Tracking Service
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=$tokentap_dir
ExecStart=$tokentap_dir/venv/bin/tokentap up --no-detach
ExecStop=$tokentap_dir/venv/bin/tokentap down
Restart=on-failure
RestartSec=10
StandardOutput=append:$tokentap_dir/logs/service.log
StandardError=append:$tokentap_dir/logs/service.error.log

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    log_success "Created systemd service: $service_file"
}

linux_enable() {
    local service_file
    service_file=$(linux_service_file)

    if [ ! -f "$service_file" ]; then
        linux_create_service
    fi

    systemctl --user enable tokentap.service
    log_success "Service enabled (will start on boot)"
}

linux_disable() {
    systemctl --user disable tokentap.service 2>/dev/null || true
    log_success "Service disabled"
}

linux_start() {
    linux_enable
    systemctl --user start tokentap.service
    wait_for_proxy "http://127.0.0.1:8080" 30 2
}

linux_stop() {
    systemctl --user stop tokentap.service 2>/dev/null || true
    log_success "Service stopped"
}

linux_status() {
    echo ""
    systemctl --user status tokentap.service || true

    echo ""
    # Check proxy health
    if curl -sf -x http://127.0.0.1:8080 http://localhost/health >/dev/null 2>&1; then
        log_success "Proxy health check: OK"
    else
        log_error "Proxy health check: FAILED"
    fi
}

linux_logs() {
    local follow="${1:-}"

    if [ "$follow" = "-f" ]; then
        journalctl --user -u tokentap.service -f
    else
        journalctl --user -u tokentap.service --no-pager
    fi
}

# Main commands
cmd_start() {
    local os
    os=$(detect_os)

    log_info "Starting tokentap service..."

    case "$os" in
    macos)
        macos_start
        ;;
    linux)
        linux_start
        ;;
    *)
        log_error "Unsupported OS: $os"
        exit 1
        ;;
    esac

    log_success "Service started successfully"
}

cmd_stop() {
    local os
    os=$(detect_os)

    log_info "Stopping tokentap service..."

    case "$os" in
    macos)
        macos_stop
        ;;
    linux)
        linux_stop
        ;;
    *)
        log_error "Unsupported OS: $os"
        exit 1
        ;;
    esac
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    local os
    os=$(detect_os)

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Service Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    case "$os" in
    macos)
        macos_status
        ;;
    linux)
        linux_status
        ;;
    *)
        log_error "Unsupported OS: $os"
        exit 1
        ;;
    esac
}

cmd_enable() {
    local os
    os=$(detect_os)

    log_info "Enabling tokentap service (auto-start on boot)..."

    case "$os" in
    macos)
        macos_enable
        ;;
    linux)
        linux_enable
        # Enable lingering for user services to start without login
        loginctl enable-linger "$USER" 2>/dev/null || true
        ;;
    *)
        log_error "Unsupported OS: $os"
        exit 1
        ;;
    esac
}

cmd_disable() {
    local os
    os=$(detect_os)

    log_info "Disabling tokentap service..."

    case "$os" in
    macos)
        macos_disable
        ;;
    linux)
        linux_disable
        ;;
    *)
        log_error "Unsupported OS: $os"
        exit 1
        ;;
    esac
}

cmd_logs() {
    local os
    os=$(detect_os)
    local follow="${1:-}"

    case "$os" in
    macos)
        macos_logs "$follow"
        ;;
    linux)
        linux_logs "$follow"
        ;;
    *)
        log_error "Unsupported OS: $os"
        exit 1
        ;;
    esac
}

# Usage
usage() {
    cat <<EOF
Tokentap Service Manager

Usage:
  $0 start      Start the service
  $0 stop       Stop the service
  $0 restart    Restart the service
  $0 status     Show detailed status
  $0 enable     Enable auto-start on boot
  $0 disable    Disable auto-start
  $0 logs [-f]  View service logs (-f to follow)

Examples:
  $0 enable     # Enable auto-start
  $0 start      # Start now
  $0 status     # Check status
  $0 logs -f    # Follow logs
EOF
}

# Main
main() {
    local command="${1:-}"

    case "$command" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    enable)
        cmd_enable
        ;;
    disable)
        cmd_disable
        ;;
    logs)
        cmd_logs "${2:-}"
        ;;
    *)
        usage
        exit 1
        ;;
    esac
}

main "$@"
