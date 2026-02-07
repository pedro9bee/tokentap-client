#!/bin/sh
# shellcheck shell=sh
# Tokentap service configuration
# Sets up auto-start on boot and creates convenient aliases

set -e

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/common.sh
. "$SCRIPT_DIR/common.sh"

# Configuration
TOKENTAP_HOME="$HOME/.tokentap"
TOKENTAP_VENV="$TOKENTAP_HOME/venv"

# Find tokentap CLI
find_tokentap() {
    if [ -f "$TOKENTAP_VENV/bin/tokentap" ]; then
        echo "$TOKENTAP_VENV/bin/tokentap"
    elif command -v tokentap >/dev/null 2>&1; then
        command -v tokentap
    else
        return 1
    fi
}

# macOS: Create launchd plist
setup_macos_service() {
    local tokentap_bin="$1"
    local plist_file="$HOME/Library/LaunchAgents/com.tokentap.service.plist"

    log_info "Setting up macOS launchd service..."

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$HOME/Library/LaunchAgents"

    # Create plist file
    cat > "$plist_file" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tokentap.service</string>

    <key>ProgramArguments</key>
    <array>
        <string>$tokentap_bin</string>
        <string>up</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>StandardOutPath</key>
    <string>$TOKENTAP_HOME/logs/service.log</string>

    <key>StandardErrorPath</key>
    <string>$TOKENTAP_HOME/logs/service.error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

    # Create logs directory
    mkdir -p "$TOKENTAP_HOME/logs"

    # Set proper permissions
    chmod 644 "$plist_file"

    log_success "launchd service created at $plist_file"

    # Load the service
    if launchctl load "$plist_file" 2>/dev/null; then
        log_success "Service loaded and will start on next login"
    else
        log_warn "Service created but not loaded (may already be loaded)"
    fi
}

# Linux: Create systemd service
setup_linux_service() {
    local tokentap_bin="$1"
    local service_file="$HOME/.config/systemd/user/tokentap.service"

    log_info "Setting up systemd user service..."

    # Create systemd user directory
    mkdir -p "$HOME/.config/systemd/user"

    # Create service file
    cat > "$service_file" <<EOF
[Unit]
Description=Tokentap LLM Token Tracking Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$tokentap_bin up
ExecStop=$tokentap_bin down
StandardOutput=append:$TOKENTAP_HOME/logs/service.log
StandardError=append:$TOKENTAP_HOME/logs/service.error.log

[Install]
WantedBy=default.target
EOF

    # Create logs directory
    mkdir -p "$TOKENTAP_HOME/logs"

    # Reload systemd daemon
    if systemctl --user daemon-reload 2>/dev/null; then
        log_success "systemd service created"

        # Enable service
        if systemctl --user enable tokentap.service 2>/dev/null; then
            log_success "Service enabled to start on boot"
        fi
    else
        log_warn "Could not reload systemd daemon (systemd may not be available)"
    fi
}

# Create shell aliases
setup_aliases() {
    local shell_rc
    shell_rc=$(get_shell_rc)

    log_info "Setting up tokentap aliases..."

    # Check if aliases already exist
    if grep -q "# Tokentap aliases" "$shell_rc" 2>/dev/null; then
        log_info "Aliases already configured"
        return 0
    fi

    # Backup shell RC
    cp "$shell_rc" "$shell_rc.backup.$(date +%Y%m%d_%H%M%S)"

    # Add aliases block
    cat >> "$shell_rc" <<'EOF'

# Tokentap aliases
alias tokentap-start='tokentap up && echo "✓ Tokentap proxy and services started"'
alias tokentap-stop='tokentap down && echo "✓ Tokentap services stopped"'
alias tokentap-web-start='docker start tokentap-client-web-1 2>/dev/null && echo "✓ Tokentap web dashboard started at http://127.0.0.1:3000" || echo "✗ Failed to start web dashboard"'
alias tokentap-web-stop='docker stop tokentap-client-web-1 2>/dev/null && echo "✓ Tokentap web dashboard stopped" || echo "✗ Web dashboard not running"'
alias tokentap-status='tokentap status'
alias tokentap-logs='tokentap logs'
alias tokentap-open='tokentap open'
EOF

    log_success "Aliases added to $shell_rc"
    log_info "Reload your shell: source $shell_rc"
}

# Remove service (for uninstall)
remove_service() {
    local os
    os=$(detect_os)

    log_info "Removing tokentap service..."

    case "$os" in
        macos)
            local plist_file="$HOME/Library/LaunchAgents/com.tokentap.service.plist"
            if [ -f "$plist_file" ]; then
                launchctl unload "$plist_file" 2>/dev/null || true
                rm "$plist_file"
                log_success "launchd service removed"
            else
                log_info "No launchd service found"
            fi
            ;;
        *)
            local service_file="$HOME/.config/systemd/user/tokentap.service"
            if [ -f "$service_file" ]; then
                systemctl --user stop tokentap.service 2>/dev/null || true
                systemctl --user disable tokentap.service 2>/dev/null || true
                rm "$service_file"
                systemctl --user daemon-reload 2>/dev/null || true
                log_success "systemd service removed"
            else
                log_info "No systemd service found"
            fi
            ;;
    esac
}

# Remove aliases
remove_aliases() {
    local shell_rc
    shell_rc=$(get_shell_rc)

    log_info "Removing tokentap aliases..."

    if grep -q "# Tokentap aliases" "$shell_rc" 2>/dev/null; then
        # Backup
        cp "$shell_rc" "$shell_rc.backup.$(date +%Y%m%d_%H%M%S)"

        # Remove aliases block
        sed -i.tmp '/# Tokentap aliases/,/^$/d' "$shell_rc"
        rm -f "$shell_rc.tmp"

        log_success "Aliases removed from $shell_rc"
    else
        log_info "No aliases found"
    fi
}

# Main setup workflow
setup() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Service Configuration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Find tokentap
    if ! TOKENTAP_BIN=$(find_tokentap); then
        log_error "tokentap not found. Please run ./scripts/install.sh first"
        exit 1
    fi

    log_info "Found tokentap at: $TOKENTAP_BIN"
    echo ""

    # Detect OS
    OS=$(detect_os)
    log_info "Detected OS: $OS"
    echo ""

    # Setup service
    case "$OS" in
        macos)
            setup_macos_service "$TOKENTAP_BIN"
            ;;
        ubuntu|debian|centos|rhel|fedora)
            setup_linux_service "$TOKENTAP_BIN"
            ;;
        *)
            log_warn "Automatic service setup not supported on this OS"
            log_info "You can manually configure service to run: $TOKENTAP_BIN up"
            ;;
    esac

    echo ""

    # Setup aliases
    setup_aliases

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Service Configuration Complete"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    log_success "Tokentap is configured to start automatically on boot"
    echo ""

    echo "Available aliases (after reloading shell):"
    echo "  tokentap-start        - Start proxy and all services"
    echo "  tokentap-stop         - Stop all services"
    echo "  tokentap-web-start    - Start only web dashboard"
    echo "  tokentap-web-stop     - Stop only web dashboard"
    echo "  tokentap-status       - Check service status"
    echo "  tokentap-logs         - View logs"
    echo "  tokentap-open         - Open dashboard in browser"
    echo ""

    SHELL_RC=$(get_shell_rc)
    log_info "Next steps:"
    echo "  1. Reload your shell: source $SHELL_RC"
    echo "  2. Test aliases: tokentap-status"
    if [ "$OS" = "macos" ]; then
        echo "  3. Service will start automatically on next login"
    else
        echo "  3. Start service now: systemctl --user start tokentap.service"
    fi
    echo ""
}

# Show usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - Configure auto-start service and aliases (default)"
    echo "  remove    - Remove service and aliases"
    echo "  status    - Show current service status"
    echo ""
}

# Check service status
check_status() {
    OS=$(detect_os)

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Service Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    case "$OS" in
        macos)
            local plist_file="$HOME/Library/LaunchAgents/com.tokentap.service.plist"
            if [ -f "$plist_file" ]; then
                log_success "launchd service installed"
                if launchctl list | grep -q "com.tokentap.service"; then
                    log_success "Service is loaded"
                else
                    log_warn "Service is not loaded"
                fi
            else
                log_error "launchd service not found"
            fi
            ;;
        *)
            if systemctl --user is-enabled tokentap.service >/dev/null 2>&1; then
                log_success "systemd service enabled"
                if systemctl --user is-active tokentap.service >/dev/null 2>&1; then
                    log_success "Service is active"
                else
                    log_warn "Service is not active"
                fi
            else
                log_error "systemd service not found or not enabled"
            fi
            ;;
    esac

    # Check aliases
    SHELL_RC=$(get_shell_rc)
    if grep -q "# Tokentap aliases" "$SHELL_RC" 2>/dev/null; then
        log_success "Aliases configured in $SHELL_RC"
    else
        log_warn "Aliases not configured"
    fi

    echo ""
}

# Main entry point
main() {
    case "${1:-setup}" in
        setup)
            setup
            ;;
        remove)
            remove_service
            remove_aliases
            log_success "Service and aliases removed"
            ;;
        status)
            check_status
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
