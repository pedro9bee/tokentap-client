#!/bin/sh
# shellcheck shell=sh
# Common utilities for tokentap installation scripts

set -e

# Color codes (with fallback for non-terminals)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    CYAN=''
    NC=''
fi

# Logging functions
log_info() {
    printf "${CYAN}[INFO]${NC} %s\n" "$1"
}

log_success() {
    printf "${GREEN}[SUCCESS]${NC} %s\n" "$1"
}

log_warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1" >&2
}

# OS Detection
detect_os() {
    local os_type
    os_type=$(uname -s)

    case "$os_type" in
        Darwin*)
            echo "macos"
            return 0
            ;;
        Linux*)
            if [ -f /etc/os-release ]; then
                # Parse ID field from os-release
                . /etc/os-release
                case "$ID" in
                    ubuntu) echo "ubuntu" ;;
                    debian) echo "debian" ;;
                    centos) echo "centos" ;;
                    rhel) echo "rhel" ;;
                    fedora) echo "fedora" ;;
                    arch) echo "arch" ;;
                    *) echo "unknown" ;;
                esac
            else
                echo "unknown"
            fi
            return 0
            ;;
        *)
            echo "unknown"
            return 1
            ;;
    esac
}

# Package Manager Detection
detect_package_manager() {
    if command -v brew >/dev/null 2>&1; then
        echo "brew"
    elif command -v apt-get >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v yum >/dev/null 2>&1; then
        echo "yum"
    elif command -v pacman >/dev/null 2>&1; then
        echo "pacman"
    else
        echo "none"
    fi
}

# Check if command exists
require_command() {
    local cmd="$1"
    local install_hint="$2"

    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Required command '$cmd' not found"
        if [ -n "$install_hint" ]; then
            log_info "$install_hint"
        fi
        return 1
    fi
    return 0
}

# Check Python version (requires >= 3.10)
check_python_version() {
    local python_cmd="$1"
    local min_major=3
    local min_minor=10

    if ! command -v "$python_cmd" >/dev/null 2>&1; then
        return 1
    fi

    # Get version string like "3.10.5"
    local version
    version=$("$python_cmd" --version 2>&1 | awk '{print $2}')

    # Extract major and minor versions
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    # Compare versions
    if [ "$major" -gt "$min_major" ]; then
        return 0
    elif [ "$major" -eq "$min_major" ] && [ "$minor" -ge "$min_minor" ]; then
        return 0
    else
        return 1
    fi
}

# Find suitable Python 3.10+ command
find_python() {
    # Try common Python command names
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if check_python_version "$cmd" 2>/dev/null; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

# Check disk space (in MB)
check_disk_space() {
    local required_mb="$1"
    local target_path="${2:-.}"

    # Get available space in MB (works on both Linux and macOS)
    local available_mb
    if [ "$(uname -s)" = "Darwin" ]; then
        available_mb=$(df -m "$target_path" | tail -1 | awk '{print $4}')
    else
        available_mb=$(df -BM "$target_path" | tail -1 | awk '{print $4}' | sed 's/M//')
    fi

    if [ "$available_mb" -lt "$required_mb" ]; then
        log_error "Insufficient disk space: ${available_mb}MB available, ${required_mb}MB required"
        return 1
    fi
    return 0
}

# Check if Docker daemon is running
is_docker_running() {
    if ! command -v docker >/dev/null 2>&1; then
        return 1
    fi

    # Try to ping Docker daemon
    if docker info >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Wait for service to become healthy
wait_for_service() {
    local url="$1"
    local timeout="${2:-60}"
    local interval="${3:-2}"
    local description="${4:-service}"

    log_info "Waiting for $description to be ready..."

    local elapsed=0
    while [ "$elapsed" -lt "$timeout" ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            log_success "$description is ready"
            return 0
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
        printf "."
    done

    printf "\n"
    log_error "$description failed to start within ${timeout}s"
    return 1
}

# Wait for proxy service specifically (requires proxy protocol)
wait_for_proxy() {
    local proxy_url="$1"
    local timeout="${2:-60}"
    local interval="${3:-2}"

    log_info "Waiting for proxy to be ready..."

    local elapsed=0
    while [ "$elapsed" -lt "$timeout" ]; do
        # Health check must use proxy protocol
        if curl -sf -x "$proxy_url" http://localhost/health >/dev/null 2>&1; then
            log_success "Proxy is ready"
            return 0
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
        printf "."
    done

    printf "\n"
    log_error "Proxy failed to start within ${timeout}s"
    return 1
}

# Get shell RC file path
get_shell_rc() {
    local shell_name
    shell_name=$(basename "$SHELL")

    case "$shell_name" in
        zsh)
            echo "$HOME/.zshrc"
            ;;
        bash)
            # Prefer .bashrc, fall back to .bash_profile
            if [ -f "$HOME/.bashrc" ]; then
                echo "$HOME/.bashrc"
            else
                echo "$HOME/.bash_profile"
            fi
            ;;
        *)
            # Default to .profile for unknown shells
            echo "$HOME/.profile"
            ;;
    esac
}

# Check if running in CI environment
is_ci() {
    [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${TRAVIS:-}" ] || [ -n "${CIRCLECI:-}" ]
}
