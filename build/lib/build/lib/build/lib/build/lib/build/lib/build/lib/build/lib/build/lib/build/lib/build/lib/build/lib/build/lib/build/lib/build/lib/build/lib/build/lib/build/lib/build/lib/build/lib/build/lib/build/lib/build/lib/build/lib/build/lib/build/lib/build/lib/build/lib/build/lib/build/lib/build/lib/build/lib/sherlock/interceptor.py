"""mitmproxy addon for intercepting LLM API traffic."""

import json
import os
import sys
from datetime import datetime

from mitmproxy import http

# Add parent directory to path for imports when run as addon
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sherlock.config import INTERCEPTED_HOSTS
from sherlock.parser import count_tokens, extract_last_user_message, parse_request


class SherlockAddon:
    """mitmproxy addon that intercepts LLM API requests."""

    def __init__(self):
        self.ipc_file = os.environ.get("SHERLOCK_IPC_FILE")
        if not self.ipc_file:
            print("Warning: SHERLOCK_IPC_FILE not set", file=sys.stderr)

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept outgoing requests to LLM APIs."""
        host = flow.request.host

        # Check if this is a request to an intercepted host
        if not any(h in host for h in INTERCEPTED_HOSTS):
            return

        # Only intercept POST requests (API calls)
        if flow.request.method != "POST":
            return

        # Parse the request body
        body = flow.request.content
        if not body:
            return

        parsed = parse_request(host, body)
        if not parsed:
            return

        # Count tokens
        token_count = count_tokens(parsed["total_text"])

        # Get last user message for preview
        last_user_message = extract_last_user_message(parsed["messages"])

        # Build event data
        event = {
            "timestamp": datetime.now().isoformat(),
            "provider": parsed["provider"],
            "model": parsed["model"],
            "tokens": token_count,
            "last_user_message": last_user_message,
            "messages": parsed["messages"],
            "system": parsed["system"],
        }

        # Write to IPC file
        if self.ipc_file:
            try:
                with open(self.ipc_file, "a") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception as e:
                print(f"Error writing to IPC file: {e}", file=sys.stderr)


# mitmproxy addon entry point
addons = [SherlockAddon()]
