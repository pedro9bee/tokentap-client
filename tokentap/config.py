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
