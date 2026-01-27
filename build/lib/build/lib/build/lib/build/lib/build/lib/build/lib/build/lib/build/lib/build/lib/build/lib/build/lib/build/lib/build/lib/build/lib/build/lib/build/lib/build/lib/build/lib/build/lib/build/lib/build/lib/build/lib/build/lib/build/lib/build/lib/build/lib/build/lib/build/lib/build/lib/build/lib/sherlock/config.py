"""Configuration constants for Sherlock."""

from pathlib import Path

# API endpoints to intercept
ANTHROPIC_HOST = "api.anthropic.com"
GEMINI_HOST = "generativelanguage.googleapis.com"

INTERCEPTED_HOSTS = [ANTHROPIC_HOST, GEMINI_HOST]

# Default token limits
DEFAULT_TOKEN_LIMIT = 200_000

# Default proxy port
DEFAULT_PROXY_PORT = 8080

# Data directories
SHERLOCK_DIR = Path.home() / ".sherlock"
HISTORY_FILE = SHERLOCK_DIR / "history.json"
PROMPTS_DIR = SHERLOCK_DIR / "prompts"

# IPC file for communication between interceptor and dashboard
IPC_FILENAME = "sherlock_ipc.jsonl"

# Dashboard settings
PROMPT_PREVIEW_LENGTH = 200
MAX_LOG_ENTRIES = 100
