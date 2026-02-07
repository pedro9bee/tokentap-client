# Migration Guide: v0.5.0 → v0.6.0

## Overview

Version 0.6.0 addresses critical security vulnerabilities and quality issues identified in comprehensive code reviews. This release includes **breaking changes** for security, but maintains backward compatibility where possible.

## Breaking Changes

### 1. Network Binding (SECURITY)

**Change**: Services now bind to `127.0.0.1` (localhost) by default instead of `0.0.0.0` (all interfaces).

**Impact**: Services are no longer accessible from other machines on your network.

**Why**: Prevent unauthorized access to proxy, dashboard, and MongoDB from network devices.

**Migration**:
```bash
# If you need network access (e.g., testing from mobile device):
tokentap network-mode network

# Restart services
tokentap down && tokentap up
```

**Recommendation**: Only enable network mode in trusted environments.

---

### 2. Raw Payload Capture (SECURITY)

**Change**: Raw request/response payloads are NO LONGER captured by default.

**Impact**:
- `raw_request` and `raw_response` fields will be empty in MongoDB events
- Full API payloads only captured when debug mode is enabled

**Why**: Prevent accidental capture of:
- API keys and authentication tokens
- User credentials
- Personal identifiable information (PII)
- Proprietary prompts and data

**What You Still Get** (always captured for categorization):
- ✅ Token counts (input/output/cache)
- ✅ Model names
- ✅ API paths
- ✅ Client types (claude-code, kiro-cli, etc.)
- ✅ Message structure with roles (content redacted as `[REDACTED]`)
- ✅ Device tracking
- ✅ Smart token detection (`is_token_consuming`, `has_budget_tokens`)
- ✅ Cost estimates

**Migration**:
```bash
# Enable debug mode ONLY when needed (e.g., debugging new providers):
tokentap debug on
tokentap down && tokentap up

# Check current mode:
tokentap debug

# Disable after troubleshooting:
tokentap debug off
tokentap down && tokentap up
```

**Recommendation**: Keep debug mode OFF in production environments.

---

### 3. DELETE Endpoint Protection (SECURITY)

**Change**: Destructive API endpoints now require admin token authentication.

**Impact**:
- `DELETE /api/events/all` requires `X-Admin-Token` header
- `DELETE /api/devices/{id}` requires `X-Admin-Token` header
- Web UI will prompt for token before deletion

**Why**: Prevent accidental or unauthorized data deletion.

**Migration**:
```bash
# Get your admin token:
tokentap admin-token

# Use with curl:
curl -X DELETE \
  -H "X-Admin-Token: YOUR_TOKEN_HERE" \
  http://localhost:3000/api/events/all

# Token is auto-generated and stored in ~/.tokentap/admin.token
```

**Recommendation**: Keep admin token secure; treat it like a password.

---

## Non-Breaking Changes

### 1. Bug Fix: Provider Detection After Rewrite

**Fixed**: Provider detection now works correctly after backward compatibility host rewrite.

**Impact**: Events are now correctly classified when using legacy `*_BASE_URL` environment variables.

---

### 2. New API Endpoints

**Added**:
- `GET /api/stats/by-program` - Usage aggregated by program
- `GET /api/stats/by-project` - Usage aggregated by project

These endpoints were documented in v0.4.0 but not implemented.

---

### 3. Improved Packaging

**Fixed**: Docker files and scripts now included in PyPI package.

**Impact**: `tokentap up` now works after installing from PyPI (`pip install tokentap`).

---

## New Features

### 1. Network Mode Management

```bash
# View current mode
tokentap network-mode

# Switch to network mode (with warning)
tokentap network-mode network

# Switch to local mode (secure default)
tokentap network-mode local
```

### 2. Debug Mode Management

```bash
# View current mode
tokentap debug

# Enable debug mode (with warning)
tokentap debug on

# Disable debug mode
tokentap debug off
```

### 3. Admin Token Management

```bash
# Display admin token
tokentap admin-token
```

---

## Configuration Files

v0.6.0 introduces new configuration files in `~/.tokentap/`:

- `.network-mode` - Stores network binding preference (`local` or `network`)
- `.debug-mode` - Stores debug mode state (`true` or `false`)
- `admin.token` - Stores admin token (auto-generated, keep secure)

These files are automatically managed by the CLI commands.

---

## Security Checklist

After upgrading to v0.6.0:

- [ ] Verify services bind to localhost: `tokentap status`
- [ ] Confirm debug mode is OFF: `tokentap debug`
- [ ] Check network mode: `tokentap network-mode`
- [ ] Save admin token securely: `tokentap admin-token`
- [ ] Review existing MongoDB data for sensitive information
- [ ] Update any automation scripts that use DELETE endpoints to include admin token

---

## Rollback Plan

If you need to rollback to v0.5.0:

```bash
# Stop services
tokentap down

# Uninstall v0.6.0
pip uninstall tokentap

# Install v0.5.0
pip install tokentap==0.5.0

# Restart services
tokentap up
```

**Note**: Configuration files from v0.6.0 will be ignored by v0.5.0 but will not cause issues.

---

## Questions?

- **Q: Will my existing events be affected?**
  - A: No, existing events in MongoDB are unchanged. Only new events follow the new behavior.

- **Q: Can I re-enable raw payload capture for all events?**
  - A: Yes, use `tokentap debug on`, but be aware of security implications.

- **Q: Why can't I access the dashboard from my phone anymore?**
  - A: Default changed to localhost-only for security. Use `tokentap network-mode network` if needed.

- **Q: Do I need to regenerate my admin token?**
  - A: No, it's auto-generated on first use and persists across restarts.

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/jmuncor/tokentap/issues
- Run diagnostics: `tokentap status` and `docker logs tokentap-client-proxy-1`
