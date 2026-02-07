#!/bin/sh
# shellcheck shell=sh
# Tokentap uninstaller
# Complete removal of tokentap and all associated data

set -e

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/common.sh
. "$SCRIPT_DIR/common.sh"

# Tokentap installation directory
TOKENTAP_HOME="$HOME/.tokentap"
TOKENTAP_VENV="$TOKENTAP_HOME/venv"

# Prompt user for confirmation
prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    if is_ci; then
        # In CI, use default without prompting
        echo "$default"
        return 0
    fi

    printf "%s [y/N] " "$prompt"
    read -r response

    case "$response" in
        [yY]|[yY][eE][sS])
            echo "y"
            ;;
        *)
            echo "n"
            ;;
    esac
}

# Stop Docker services
stop_services() {
    log_info "Stopping Docker services..."

    # Try to find tokentap command
    if command -v tokentap >/dev/null 2>&1; then
        if tokentap down 2>/dev/null; then
            log_success "Docker services stopped"
        else
            log_warn "Failed to stop services (they may not be running)"
        fi
    else
        log_warn "tokentap command not found, skipping service stop"
    fi
}

# Remove Docker volumes
remove_volumes() {
    response=$(prompt_yes_no "Remove Docker volumes? This will delete all stored data.")

    if [ "$response" = "y" ]; then
        log_info "Removing Docker volumes..."

        # Remove volumes
        if docker volume rm tokentap-client_mongodb_data 2>/dev/null; then
            log_success "MongoDB data volume removed"
        else
            log_warn "MongoDB data volume not found or failed to remove"
        fi

        if docker volume rm tokentap-client_mitmproxy_certs 2>/dev/null; then
            log_success "mitmproxy certs volume removed"
        else
            log_warn "mitmproxy certs volume not found or failed to remove"
        fi
    else
        log_info "Kept Docker volumes"
    fi
}

# Remove shell integration
remove_shell_integration() {
    log_info "Removing shell integration..."

    # Try to use tokentap uninstall command
    if command -v tokentap >/dev/null 2>&1; then
        if tokentap uninstall 2>/dev/null; then
            log_success "Shell integration removed via tokentap"
            return 0
        fi
    fi

    # Manual removal as fallback
    SHELL_RC=$(get_shell_rc)
    if [ -f "$SHELL_RC" ]; then
        # Remove lines between markers
        if grep -q "# Added by tokentap" "$SHELL_RC" 2>/dev/null; then
            # Create temp file without tokentap lines
            grep -v "# Added by tokentap" "$SHELL_RC" | grep -v "tokentap shell-init" > "$SHELL_RC.tmp"
            mv "$SHELL_RC.tmp" "$SHELL_RC"
            log_success "Shell integration removed from $SHELL_RC"
        else
            log_info "No shell integration found in $SHELL_RC"
        fi
    fi
}

# Uninstall tokentap package
uninstall_package() {
    log_info "Uninstalling tokentap package..."

    # Check if installed in a venv
    if [ -f "$TOKENTAP_VENV/bin/pip" ]; then
        if "$TOKENTAP_VENV/bin/pip" uninstall -y tokentap 2>/dev/null; then
            log_success "Tokentap uninstalled from venv"
        else
            log_warn "Failed to uninstall from venv"
        fi
    elif command -v pip >/dev/null 2>&1; then
        if pip uninstall -y tokentap 2>/dev/null; then
            log_success "Tokentap uninstalled"
        else
            log_warn "Failed to uninstall tokentap"
        fi
    else
        log_warn "pip not found, skipping package uninstall"
    fi
}

# Remove virtual environment
remove_venv() {
    if [ ! -d "$TOKENTAP_VENV" ]; then
        log_info "No virtual environment found"
        return 0
    fi

    response=$(prompt_yes_no "Remove virtual environment at $TOKENTAP_VENV?")

    if [ "$response" = "y" ]; then
        log_info "Removing virtual environment..."
        rm -rf "$TOKENTAP_VENV"
        log_success "Virtual environment removed"

        # Remove parent directory if empty
        if [ -d "$TOKENTAP_HOME" ] && [ -z "$(ls -A "$TOKENTAP_HOME")" ]; then
            rmdir "$TOKENTAP_HOME"
            log_success "Removed empty directory: $TOKENTAP_HOME"
        fi
    else
        log_info "Kept virtual environment"
    fi
}

# Remove trusted CA certificate
remove_certificate() {
    response=$(prompt_yes_no "Remove trusted mitmproxy CA certificate? (requires sudo)")

    if [ "$response" != "y" ]; then
        log_info "Kept CA certificate"
        return 0
    fi

    log_info "Removing CA certificate..."

    OS=$(detect_os)
    CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

    case "$OS" in
        macos)
            # Remove from macOS Keychain
            if [ -f "$CERT_PATH" ]; then
                CERT_HASH=$(openssl x509 -noout -fingerprint -sha1 -in "$CERT_PATH" 2>/dev/null | cut -d= -f2 | tr -d ':')
                if [ -n "$CERT_HASH" ]; then
                    if sudo security delete-certificate -Z "$CERT_HASH" /Library/Keychains/System.keychain 2>/dev/null; then
                        log_success "Certificate removed from System Keychain"
                    else
                        log_warn "Failed to remove certificate from System Keychain (may not be installed)"
                    fi
                fi
            fi
            ;;
        ubuntu|debian)
            # Remove from ca-certificates
            CERT_NAME="mitmproxy-ca-cert.crt"
            if [ -f "/usr/local/share/ca-certificates/$CERT_NAME" ]; then
                if sudo rm "/usr/local/share/ca-certificates/$CERT_NAME" && sudo update-ca-certificates 2>/dev/null; then
                    log_success "Certificate removed from system trust"
                else
                    log_warn "Failed to remove certificate"
                fi
            else
                log_info "Certificate not found in system trust"
            fi
            ;;
        centos|rhel|fedora)
            # Remove from ca-trust
            CERT_NAME="mitmproxy-ca-cert.pem"
            if [ -f "/etc/pki/ca-trust/source/anchors/$CERT_NAME" ]; then
                if sudo rm "/etc/pki/ca-trust/source/anchors/$CERT_NAME" && sudo update-ca-trust 2>/dev/null; then
                    log_success "Certificate removed from system trust"
                else
                    log_warn "Failed to remove certificate"
                fi
            else
                log_info "Certificate not found in system trust"
            fi
            ;;
        *)
            log_warn "Unknown OS, skipping certificate removal"
            ;;
    esac

    # Remove mitmproxy directory if user wants
    if [ -d "$HOME/.mitmproxy" ]; then
        response=$(prompt_yes_no "Remove ~/.mitmproxy directory?")
        if [ "$response" = "y" ]; then
            rm -rf "$HOME/.mitmproxy"
            log_success "Removed ~/.mitmproxy directory"
        fi
    fi
}

# Main uninstall workflow
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Uninstaller"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    log_warn "This will remove tokentap and optionally all associated data"
    echo ""

    # Confirm uninstall
    response=$(prompt_yes_no "Continue with uninstall?")
    if [ "$response" != "y" ]; then
        log_info "Uninstall cancelled"
        exit 0
    fi

    echo ""

    # Step 1: Stop services
    stop_services
    echo ""

    # Step 2: Remove volumes (optional)
    remove_volumes
    echo ""

    # Step 3: Remove shell integration
    remove_shell_integration
    echo ""

    # Step 4: Uninstall package
    uninstall_package
    echo ""

    # Step 5: Remove venv (optional)
    remove_venv
    echo ""

    # Step 6: Remove certificate (optional)
    remove_certificate
    echo ""

    # Print summary
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Uninstall Complete"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_success "Tokentap has been uninstalled"
    echo ""
    log_info "To reinstall, run: curl -fsSL https://raw.githubusercontent.com/jmuncor/tokentap/main/scripts/install.sh | bash"
    echo ""
}

main "$@"
