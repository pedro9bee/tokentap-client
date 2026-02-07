#!/bin/sh
# Tokentap Proxy Activator
# Usage: source ./scripts/activate-proxy.sh
# or: eval "$(./scripts/activate-proxy.sh)"

# This script exports the necessary environment variables for tokentap proxy

# Check if tokentap command exists
if ! command -v tokentap >/dev/null 2>&1; then
    echo "❌ tokentap command not found" >&2
    echo "   Make sure tokentap is installed and in PATH" >&2
    return 1 2>/dev/null || exit 1
fi

# Export the proxy configuration
eval "$(tokentap shell-init)"

# Verify exports
if [ -n "${HTTPS_PROXY:-}" ]; then
    echo "✅ Tokentap proxy activated!"
    echo ""
    echo "   HTTPS_PROXY: $HTTPS_PROXY"
    echo "   HTTP_PROXY: $HTTP_PROXY"
    echo "   SSL_CERT_FILE: $SSL_CERT_FILE"
    echo ""
    echo "   You can now use LLM CLI tools and they will be tracked."
    echo "   View dashboard: tokentap open"
else
    echo "❌ Failed to activate proxy" >&2
    echo "   Try running: tokentap status" >&2
    return 1 2>/dev/null || exit 1
fi
