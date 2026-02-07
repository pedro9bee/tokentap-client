#!/bin/sh
# shellcheck shell=sh
# Tokentap diagnostic tool

set -e

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/common.sh
. "$SCRIPT_DIR/common.sh"

# Color codes
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ${BOLD}Tokentap Diagnostics${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check 1: Docker containers
echo "${BOLD}1. Docker Containers${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "tokentap" >/dev/null 2>&1; then
    log_success "Tokentap containers running:"
    docker ps --format "  {{.Names}}\t{{.Status}}" | grep tokentap
else
    log_error "No tokentap containers running"
    echo ""
    log_info "Start services with: tokentap up"
    exit 1
fi
echo ""

# Check 2: Environment variables
echo "${BOLD}2. Environment Variables${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ENV_OK=1

if [ -n "${HTTPS_PROXY:-}" ]; then
    log_success "HTTPS_PROXY: $HTTPS_PROXY"
else
    log_error "HTTPS_PROXY: not set"
    ENV_OK=0
fi

if [ -n "${HTTP_PROXY:-}" ]; then
    log_success "HTTP_PROXY: $HTTP_PROXY"
else
    log_warn "HTTP_PROXY: not set"
fi

if [ -n "${SSL_CERT_FILE:-}" ]; then
    log_success "SSL_CERT_FILE: $SSL_CERT_FILE"
else
    log_error "SSL_CERT_FILE: not set"
    ENV_OK=0
fi

if [ -n "${REQUESTS_CA_BUNDLE:-}" ]; then
    log_success "REQUESTS_CA_BUNDLE: $REQUESTS_CA_BUNDLE"
else
    log_warn "REQUESTS_CA_BUNDLE: not set"
fi

if [ -n "${NODE_EXTRA_CA_CERTS:-}" ]; then
    log_success "NODE_EXTRA_CA_CERTS: $NODE_EXTRA_CA_CERTS"
else
    log_warn "NODE_EXTRA_CA_CERTS: not set"
fi

if [ $ENV_OK -eq 0 ]; then
    echo ""
    log_error "Environment not configured properly!"
    echo ""
    echo "  ${BOLD}Quick fix:${NC}"
    echo "    eval \"\$(tokentap shell-init)\""
    echo ""
    echo "  ${BOLD}Permanent fix:${NC}"
    echo "    Open a new terminal (variables load automatically)"
    echo "    or run: source ~/.zshrc"
    echo ""
fi
echo ""

# Check 3: Proxy connectivity
echo "${BOLD}3. Proxy Connectivity${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if curl -sf -x http://127.0.0.1:8080 http://localhost/health >/dev/null 2>&1; then
    log_success "Proxy health check: OK"
else
    log_error "Proxy health check: FAILED"
    echo ""
    log_info "Check logs with: tokentap logs proxy"
fi

if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1; then
    log_success "Web dashboard: OK (http://127.0.0.1:3000)"
else
    log_error "Web dashboard: FAILED"
    echo ""
    log_info "Check logs with: tokentap logs web"
fi

echo ""

# Check 4: Shell integration
echo "${BOLD}4. Shell Integration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SHELL_RC=$(get_shell_rc)

if grep -q "tokentap shell-init" "$SHELL_RC" 2>/dev/null; then
    log_success "Shell integration present in $SHELL_RC"
else
    log_error "Shell integration NOT found in $SHELL_RC"
    echo ""
    log_info "Add integration with: tokentap install"
fi

# Check for aliases
if grep -q "tokentap-start" "$SHELL_RC" 2>/dev/null; then
    log_success "Convenience aliases present"
else
    log_warn "Convenience aliases not found"
    echo ""
    log_info "Add aliases with: ./scripts/configure-service.sh setup"
fi

echo ""

# Check 5: Certificate
echo "${BOLD}5. SSL Certificate${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

if [ -f "$CERT_PATH" ]; then
    log_success "mitmproxy CA certificate exists"

    # Check if certificate is valid
    if openssl x509 -noout -in "$CERT_PATH" 2>/dev/null; then
        log_success "Certificate is valid"
    else
        log_error "Certificate appears to be invalid"
    fi
else
    log_error "mitmproxy CA certificate not found"
    echo ""
    log_info "Certificate should be created when running: tokentap up"
fi

echo ""

# Check 6: MongoDB connection
echo "${BOLD}6. MongoDB Connection${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec tokentap-client-mongodb-1 mongosh --quiet --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
    log_success "MongoDB connection: OK"

    # Count events
    EVENT_COUNT=$(docker exec tokentap-client-mongodb-1 mongosh --quiet tokentap --eval "db.events.countDocuments()" 2>/dev/null || echo "0")
    log_info "Events in database: $EVENT_COUNT"
else
    log_error "MongoDB connection: FAILED"
fi

echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ${BOLD}Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $ENV_OK -eq 1 ]; then
    log_success "All checks passed! Tokentap is ready to use."
    echo ""
    echo "  Test with any LLM CLI tool (claude, codex, gemini)"
    echo "  View dashboard: tokentap open"
else
    log_warn "Some issues found. See above for details."
    echo ""
    echo "  ${BOLD}Most common issue:${NC} Environment not configured"
    echo "  ${BOLD}Quick fix:${NC} eval \"\$(tokentap shell-init)\""
    echo "  ${BOLD}Or:${NC} Open a new terminal"
fi

echo ""
