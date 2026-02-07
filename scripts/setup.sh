#!/bin/sh
# shellcheck shell=sh
# Tokentap dependency installer
# Installs Python 3.10+, Docker, Docker Compose, and curl

set -e

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/common.sh
. "$SCRIPT_DIR/common.sh"

# Track if any dependencies were missing
INSTALLED_SOMETHING=0

# Install Python 3.10+
install_python() {
    local os="$1"
    local pkg_mgr="$2"

    log_info "Installing Python 3.10+..."

    case "$pkg_mgr" in
        brew)
            if brew install python@3.10; then
                log_success "Python 3.10 installed via Homebrew"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        apt)
            if sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv; then
                log_success "Python 3 installed via apt"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        dnf)
            if sudo dnf install -y python3 python3-pip; then
                log_success "Python 3 installed via dnf"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        yum)
            if sudo yum install -y python3 python3-pip; then
                log_success "Python 3 installed via yum"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        *)
            log_error "No supported package manager found for Python installation"
            ;;
    esac

    # If automated install failed, print manual instructions
    log_error "Automated Python installation failed. Please install manually:"
    case "$os" in
        macos)
            echo "  brew install python@3.10"
            echo "  or download from https://www.python.org/downloads/"
            ;;
        ubuntu|debian)
            echo "  sudo apt-get update"
            echo "  sudo apt-get install python3 python3-pip python3-venv"
            ;;
        centos|rhel|fedora)
            echo "  sudo dnf install python3 python3-pip"
            ;;
        *)
            echo "  Visit https://www.python.org/downloads/"
            ;;
    esac
    return 1
}

# Install Docker
install_docker() {
    local os="$1"
    local pkg_mgr="$2"

    log_info "Installing Docker..."

    case "$pkg_mgr" in
        brew)
            log_info "Installing Docker Desktop via Homebrew..."
            if brew install --cask docker; then
                log_success "Docker Desktop installed via Homebrew"
                log_warn "Please start Docker Desktop from Applications before using tokentap"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        apt)
            if sudo apt-get update && sudo apt-get install -y docker.io docker-compose; then
                log_success "Docker installed via apt"
                # Start Docker daemon
                if sudo systemctl start docker 2>/dev/null; then
                    log_success "Docker daemon started"
                fi
                # Add user to docker group
                if sudo usermod -aG docker "$USER" 2>/dev/null; then
                    log_warn "Added $USER to docker group. Please log out and back in for this to take effect."
                fi
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        dnf)
            if sudo dnf install -y docker docker-compose; then
                log_success "Docker installed via dnf"
                # Start and enable Docker daemon
                if sudo systemctl start docker && sudo systemctl enable docker 2>/dev/null; then
                    log_success "Docker daemon started"
                fi
                # Add user to docker group
                if sudo usermod -aG docker "$USER" 2>/dev/null; then
                    log_warn "Added $USER to docker group. Please log out and back in for this to take effect."
                fi
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        yum)
            if sudo yum install -y docker docker-compose; then
                log_success "Docker installed via yum"
                # Start and enable Docker daemon
                if sudo systemctl start docker && sudo systemctl enable docker 2>/dev/null; then
                    log_success "Docker daemon started"
                fi
                # Add user to docker group
                if sudo usermod -aG docker "$USER" 2>/dev/null; then
                    log_warn "Added $USER to docker group. Please log out and back in for this to take effect."
                fi
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        *)
            log_error "No supported package manager found for Docker installation"
            ;;
    esac

    # If automated install failed, print manual instructions
    log_error "Automated Docker installation failed. Please install manually:"
    case "$os" in
        macos)
            echo "  Download Docker Desktop from https://www.docker.com/products/docker-desktop/"
            echo "  or run: brew install --cask docker"
            ;;
        ubuntu|debian)
            echo "  sudo apt-get update"
            echo "  sudo apt-get install docker.io docker-compose"
            echo "  sudo systemctl start docker"
            echo "  sudo usermod -aG docker \$USER"
            ;;
        centos|rhel|fedora)
            echo "  sudo dnf install docker docker-compose"
            echo "  sudo systemctl start docker"
            echo "  sudo systemctl enable docker"
            echo "  sudo usermod -aG docker \$USER"
            ;;
        *)
            echo "  Visit https://docs.docker.com/engine/install/"
            ;;
    esac
    return 1
}

# Install curl
install_curl() {
    local os="$1"
    local pkg_mgr="$2"

    log_info "Installing curl..."

    case "$pkg_mgr" in
        brew)
            if brew install curl; then
                log_success "curl installed via Homebrew"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        apt)
            if sudo apt-get update && sudo apt-get install -y curl; then
                log_success "curl installed via apt"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
        dnf|yum)
            if sudo "$pkg_mgr" install -y curl; then
                log_success "curl installed via $pkg_mgr"
                INSTALLED_SOMETHING=1
                return 0
            fi
            ;;
    esac

    log_error "Failed to install curl"
    return 1
}

# Main setup workflow
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Tokentap Dependency Setup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Detect OS and package manager
    OS=$(detect_os)
    PKG_MGR=$(detect_package_manager)

    log_info "Detected OS: $OS"
    log_info "Package manager: $PKG_MGR"
    echo ""

    # Track failures
    FAILED_DEPS=""

    # Check Python version
    log_info "Checking Python version..."
    if PYTHON_CMD=$(find_python); then
        PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
        log_success "Python $PYTHON_VERSION found at $(command -v "$PYTHON_CMD")"
    else
        log_warn "Python 3.10+ not found"
        if [ "$PKG_MGR" = "none" ]; then
            log_error "Cannot install Python automatically (no package manager found)"
            FAILED_DEPS="$FAILED_DEPS python"
        else
            if ! install_python "$OS" "$PKG_MGR"; then
                FAILED_DEPS="$FAILED_DEPS python"
            fi
        fi
    fi
    echo ""

    # Check Docker
    log_info "Checking Docker..."
    if command -v docker >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
        log_success "Docker $DOCKER_VERSION found"

        # Check if Docker daemon is running
        if is_docker_running; then
            log_success "Docker daemon is running"
        else
            log_warn "Docker is installed but daemon is not running"
            if [ "$OS" = "macos" ]; then
                log_info "Start Docker Desktop from Applications"
            else
                log_info "Try: sudo systemctl start docker"
            fi
        fi
    else
        log_warn "Docker not found"
        if [ "$PKG_MGR" = "none" ]; then
            log_error "Cannot install Docker automatically (no package manager found)"
            FAILED_DEPS="$FAILED_DEPS docker"
        else
            if ! install_docker "$OS" "$PKG_MGR"; then
                FAILED_DEPS="$FAILED_DEPS docker"
            fi
        fi
    fi
    echo ""

    # Check Docker Compose (may be built into Docker on newer versions)
    log_info "Checking Docker Compose..."
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "built-in")
        log_success "Docker Compose $COMPOSE_VERSION found"
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | tr -d ',')
        log_success "docker-compose $COMPOSE_VERSION found"
    else
        log_warn "Docker Compose not found (may be included with Docker installation)"
    fi
    echo ""

    # Check curl
    log_info "Checking curl..."
    if command -v curl >/dev/null 2>&1; then
        CURL_VERSION=$(curl --version | head -1 | awk '{print $2}')
        log_success "curl $CURL_VERSION found"
    else
        log_warn "curl not found"
        if [ "$PKG_MGR" = "none" ]; then
            log_error "Cannot install curl automatically (no package manager found)"
            FAILED_DEPS="$FAILED_DEPS curl"
        else
            if ! install_curl "$OS" "$PKG_MGR"; then
                FAILED_DEPS="$FAILED_DEPS curl"
            fi
        fi
    fi
    echo ""

    # Print summary
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Setup Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [ -z "$FAILED_DEPS" ]; then
        log_success "All dependencies are installed!"

        if [ $INSTALLED_SOMETHING -eq 1 ]; then
            echo ""
            log_info "Next steps:"
            echo "  1. If Docker was just installed on Linux, log out and back in"
            echo "  2. Run: ./scripts/install.sh"
        else
            echo ""
            log_info "System is ready for tokentap installation"
            echo "  Run: ./scripts/install.sh"
        fi

        exit 0
    else
        log_error "Failed to install:$FAILED_DEPS"
        echo ""
        log_info "Please install missing dependencies manually and run this script again"
        exit 1
    fi
}

main "$@"
