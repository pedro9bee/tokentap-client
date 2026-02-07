#!/bin/sh
# shellcheck shell=sh
# Tokentap application installer
# Orchestrates full setup: venv, package install, Docker services, shell integration

set -e

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/common.sh
. "$SCRIPT_DIR/common.sh"

# Tokentap installation directory
TOKENTAP_HOME="$HOME/.tokentap"
TOKENTAP_VENV="$TOKENTAP_HOME/venv"

# Track if we created venv (for rollback)
CREATED_VENV=0
STARTED_SERVICES=0
INSTALLED_SHELL_INTEGRATION=0

# Cleanup on error
cleanup_on_error() {
    log_error "Installation failed, cleaning up..."

    # Stop Docker services if we started them
    if [ $STARTED_SERVICES -eq 1 ]; then
        log_info "Stopping Docker services..."
        if [ -n "$TOKENTAP_CLI" ]; then
            "$TOKENTAP_CLI" down 2>/dev/null || true
        fi
    fi

    # Remove shell integration if we installed it
    if [ $INSTALLED_SHELL_INTEGRATION -eq 1 ]; then
        log_info "Removing shell integration..."
        if [ -n "$TOKENTAP_CLI" ]; then
            "$TOKENTAP_CLI" uninstall 2>/dev/null || true
        fi
    fi

    # Remove venv if we created it
    if [ $CREATED_VENV -eq 1 ] && [ -d "$TOKENTAP_VENV" ]; then
        log_info "Removing virtual environment..."
        rm -rf "$TOKENTAP_VENV"
    fi

    echo ""
    log_error "Installation failed. Please check the errors above."
    log_info "For help, visit: https://github.com/jmuncor/tokentap/issues"
    exit 1
}

# Set up error trap
trap cleanup_on_error ERR

# Pre-flight checks
preflight_checks() {
    log_info "Running pre-flight checks..."

    local failed=0

    # Check Python version
    if ! PYTHON_CMD=$(find_python); then
        log_error "Python 3.10+ not found"
        log_info "Run: ./scripts/setup.sh"
        failed=1
    else
        PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
        log_success "Python $PYTHON_VERSION found"
    fi

    # Check Docker exists
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found"
        log_info "Run: ./scripts/setup.sh"
        failed=1
    else
        log_success "Docker found"
    fi

    # Check Docker daemon running
    if ! is_docker_running; then
        log_error "Docker daemon is not running"
        if [ "$(detect_os)" = "macos" ]; then
            log_info "Start Docker Desktop from Applications"
        else
            log_info "Try: sudo systemctl start docker"
        fi
        failed=1
    else
        log_success "Docker daemon is running"
    fi

    # Check curl exists
    if ! command -v curl >/dev/null 2>&1; then
        log_error "curl not found"
        log_info "Run: ./scripts/setup.sh"
        failed=1
    else
        log_success "curl found"
    fi

    # Check disk space (require 500MB)
    if ! check_disk_space 500 "$HOME"; then
        failed=1
    else
        log_success "Sufficient disk space available"
    fi

    if [ $failed -eq 1 ]; then
        echo ""
        log_error "Pre-flight checks failed"
        log_info "Run: ./scripts/setup.sh to install missing dependencies"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}

# Create and activate virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."

    # Check if already in a venv
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        log_info "Already in virtual environment: $VIRTUAL_ENV"
        return 0
    fi

    # Create tokentap home directory
    mkdir -p "$TOKENTAP_HOME"

    # Create venv if it doesn't exist
    if [ ! -d "$TOKENTAP_VENV" ]; then
        log_info "Creating virtual environment at $TOKENTAP_VENV..."
        "$PYTHON_CMD" -m venv "$TOKENTAP_VENV"
        CREATED_VENV=1
        log_success "Virtual environment created"
    else
        log_info "Using existing virtual environment"
    fi

    # Activate venv
    # shellcheck source=/dev/null
    . "$TOKENTAP_VENV/bin/activate"
    log_success "Virtual environment activated"
}

# Install tokentap package
install_package() {
    log_info "Installing tokentap package..."

    # Determine if we're in the source directory
    if [ -f "$SCRIPT_DIR/../pyproject.toml" ] && grep -q "name = \"tokentap\"" "$SCRIPT_DIR/../pyproject.toml" 2>/dev/null; then
        log_info "Installing from source in editable mode..."
        pip install -e "$SCRIPT_DIR/.." >/dev/null 2>&1
        log_success "Tokentap installed from source"
    else
        log_info "Installing from PyPI..."
        pip install tokentap >/dev/null 2>&1
        log_success "Tokentap installed from PyPI"
    fi

    # Verify installation
    if ! command -v tokentap >/dev/null 2>&1; then
        log_error "tokentap command not found after installation"
        return 1
    fi

    TOKENTAP_VERSION=$(tokentap --version 2>/dev/null | awk '{print $2}' || echo "unknown")
    log_success "Tokentap $TOKENTAP_VERSION installed"
}

# Start Docker services
start_services() {
    log_info "Starting Docker services..."

    # Find tokentap CLI (may be in venv)
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        TOKENTAP_CLI="$VIRTUAL_ENV/bin/tokentap"
    else
        TOKENTAP_CLI=$(command -v tokentap)
    fi

    # Start services
    if "$TOKENTAP_CLI" up; then
        STARTED_SERVICES=1
        log_success "Docker services started"
    else
        log_error "Failed to start Docker services"
        return 1
    fi
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be ready..."
    echo ""

    # Wait for proxy (must use proxy protocol)
    if ! wait_for_proxy "http://127.0.0.1:8080" 60 2; then
        log_error "Proxy health check failed"
        log_info "Check logs with: tokentap logs proxy"
        return 1
    fi

    # Wait for web dashboard
    if ! wait_for_service "http://127.0.0.1:3000" 30 2 "web dashboard"; then
        log_error "Web dashboard health check failed"
        log_info "Check logs with: tokentap logs web"
        return 1
    fi

    echo ""
    log_success "All services are healthy"
}

# Install shell integration
install_shell_integration() {
    log_info "Installing shell integration..."

    if "$TOKENTAP_CLI" install; then
        INSTALLED_SHELL_INTEGRATION=1
        log_success "Shell integration installed"

        # Show which shell RC was modified
        SHELL_RC=$(get_shell_rc)
        log_info "Modified: $SHELL_RC"
    else
        log_error "Failed to install shell integration"
        return 1
    fi
}

# Prompt for certificate installation
prompt_cert_install() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Certificate Installation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "The mitmproxy CA certificate allows tokentap to intercept HTTPS traffic."
    echo "Most tools respect SSL_CERT_FILE, but some require system-wide trust."
    echo ""
    echo "This step requires sudo privileges to:"

    OS=$(detect_os)
    if [ "$OS" = "macos" ]; then
        echo "  [macOS] Add certificate to System Keychain"
    else
        echo "  [Linux] Copy certificate to /usr/local/share/ca-certificates/"
    fi

    echo ""

    # Skip prompt in CI environments
    if is_ci; then
        log_info "CI environment detected, skipping certificate installation"
        return 0
    fi

    # Interactive prompt
    printf "Trust the mitmproxy CA certificate? [y/N] "
    read -r response

    case "$response" in
        [yY]|[yY][eE][sS])
            log_info "Installing certificate..."
            if "$TOKENTAP_CLI" install-cert; then
                log_success "Certificate installed"
            else
                log_warn "Certificate installation failed (you can try again later with: tokentap install-cert)"
            fi
            ;;
        *)
            log_info "Skipped certificate installation"
            log_info "You can install it later with: tokentap install-cert"
            ;;
    esac
}

# Validate full stack
validate_installation() {
    log_info "Validating installation..."

    # Check services are running
    if ! "$TOKENTAP_CLI" status >/dev/null 2>&1; then
        log_error "Services are not running"
        return 1
    fi
    log_success "Services are running"

    # Check shell integration
    SHELL_RC=$(get_shell_rc)
    if ! grep -q "tokentap shell-init" "$SHELL_RC" 2>/dev/null; then
        log_error "Shell integration not found in $SHELL_RC"
        return 1
    fi
    log_success "Shell integration present"

    # Check proxy env var (in a new shell)
    if sh -c ". $SHELL_RC && [ \"\$HTTPS_PROXY\" = \"http://127.0.0.1:8080\" ]" 2>/dev/null; then
        log_success "HTTPS_PROXY configured correctly"
    else
        log_warn "HTTPS_PROXY not set (will be set after shell reload)"
    fi

    log_success "Installation validated"
}

# Print next steps
print_next_steps() {
    SHELL_RC=$(get_shell_rc)

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap installation complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Next steps:"
    echo "  1. Reload your shell:"
    echo "     source $SHELL_RC"
    echo ""
    echo "  2. Verify proxy is configured:"
    echo "     echo \$HTTPS_PROXY"
    echo "     # Should output: http://127.0.0.1:8080"
    echo ""
    echo "  3. Use your LLM tools normally:"
    echo "     claude"
    echo "     codex"
    echo "     gemini"
    echo ""
    echo "  4. View the dashboard:"
    echo "     tokentap open"
    echo "     # Opens http://127.0.0.1:3000"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Useful commands:"
    echo "  tokentap status      # Check service status"
    echo "  tokentap logs        # View logs"
    echo "  tokentap down        # Stop services"
    echo "  tokentap up          # Restart services"
    echo ""
}

# Main installation workflow
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Installation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Step 1: Pre-flight checks
    preflight_checks
    echo ""

    # Step 2: Set up virtual environment
    setup_venv
    echo ""

    # Step 3: Install package
    install_package
    echo ""

    # Step 4: Start Docker services
    start_services
    echo ""

    # Step 5: Wait for health checks
    wait_for_services
    echo ""

    # Step 6: Install shell integration
    install_shell_integration
    echo ""

    # Step 7: Prompt for certificate installation
    prompt_cert_install
    echo ""

    # Step 8: Validate installation
    validate_installation
    echo ""

    # Step 9: Print next steps
    print_next_steps

    # Disable error trap (we succeeded)
    trap - ERR

    exit 0
}

main "$@"
