"""Configuration constants for tokentap."""

import os
from pathlib import Path

# Provider domains (used by proxy.py for backward compat host rewrite)
PROVIDERS = {
    "anthropic": {
        "host": "api.anthropic.com",
    },
    "openai": {
        "host": "api.openai.com",
    },
    "gemini": {
        "host": "generativelanguage.googleapis.com",
    },
    "kiro": {
        "host": "q.us-east-1.amazonaws.com",
    },
}

# Default token limits
DEFAULT_TOKEN_LIMIT = 200_000

# Default proxy port
DEFAULT_PROXY_PORT = 8080

# Data directories
TOKENTAP_DIR = Path.home() / ".tokentap"
PROMPTS_DIR = TOKENTAP_DIR / "prompts"

# Dashboard settings (used by legacy Rich dashboard)
PROMPT_PREVIEW_LENGTH = 200
MAX_LOG_ENTRIES = 100

# MongoDB settings
MONGO_URI = os.environ.get("TOKENTAP_MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("TOKENTAP_MONGO_DB", "tokentap")

# Web dashboard settings
WEB_PORT = int(os.environ.get("TOKENTAP_WEB_PORT", "3000"))

# mitmproxy CA certificate
MITMPROXY_CA_DIR = Path.home() / ".mitmproxy"
MITMPROXY_CA_CERT = MITMPROXY_CA_DIR / "mitmproxy-ca-cert.pem"
NO_PROXY = "localhost,127.0.0.1"

# Provider configuration
DEFAULT_PROVIDERS_PATH = Path(__file__).parent / "providers.json"

# Shell integration marker
SHELL_INTEGRATION_START = "# >>> tokentap shell integration >>>"
SHELL_INTEGRATION_END = "# <<< tokentap shell integration <<<"

# Network and security settings (v0.6.0)
NETWORK_MODE = os.environ.get("TOKENTAP_NETWORK_MODE", "local")  # local or network
DEBUG_MODE = os.environ.get("TOKENTAP_DEBUG", "false").lower() == "true"
ADMIN_TOKEN_FILE = TOKENTAP_DIR / "admin.token"


def get_or_create_admin_token() -> str:
    """Get existing admin token or create a new one."""
    import secrets

    TOKENTAP_DIR.mkdir(parents=True, exist_ok=True)

    if ADMIN_TOKEN_FILE.exists():
        return ADMIN_TOKEN_FILE.read_text().strip()

    # Generate new token
    token = secrets.token_urlsafe(32)
    ADMIN_TOKEN_FILE.write_text(token + "\n")
    ADMIN_TOKEN_FILE.chmod(0o600)  # Read/write for owner only

    return token
