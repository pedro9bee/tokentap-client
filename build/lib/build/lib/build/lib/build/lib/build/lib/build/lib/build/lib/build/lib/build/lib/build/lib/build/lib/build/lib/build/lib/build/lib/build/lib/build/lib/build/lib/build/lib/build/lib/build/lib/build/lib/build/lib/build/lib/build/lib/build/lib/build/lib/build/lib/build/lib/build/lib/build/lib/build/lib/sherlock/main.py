"""Main entry point for Sherlock proxy and dashboard."""

import atexit
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console

from sherlock.certs import ensure_certs_ready
from sherlock.config import (
    DEFAULT_PROXY_PORT,
    DEFAULT_TOKEN_LIMIT,
    HISTORY_FILE,
    IPC_FILENAME,
    PROMPTS_DIR,
    SHERLOCK_DIR,
)
from sherlock.dashboard import SherlockDashboard

console = Console()


def check_dependencies() -> bool:
    """Check that all required dependencies are installed.

    Returns:
        True if all dependencies are available, False otherwise.
    """
    missing = []

    # Check for mitmproxy
    if importlib.util.find_spec("mitmproxy") is None:
        missing.append("mitmproxy")

    if missing:
        console.print("[red bold]Missing required dependencies:[/red bold]")
        for dep in missing:
            console.print(f"  [red]• {dep}[/red]")
        console.print()
        console.print("[yellow]Install with:[/yellow]")
        console.print(f"  pip install {' '.join(missing)}")
        console.print()
        return False

    return True


def save_prompt_to_file(event: dict) -> None:
    """Save a prompt to a markdown file."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.fromisoformat(event["timestamp"])
    filename = timestamp.strftime(f"%Y-%m-%d_%H-%M-%S_{event['provider']}.md")
    filepath = PROMPTS_DIR / filename

    lines = [
        f"# Prompt - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Provider:** {event['provider'].capitalize()}",
        f"**Model:** {event['model']}",
        f"**Tokens:** {event['tokens']:,}",
        "",
        "## Messages",
    ]

    for msg in event.get("messages", []):
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        lines.append(f"### {role}")
        lines.append(content)
        lines.append("")

    filepath.write_text("\n".join(lines))


def load_history() -> list[dict]:
    """Load token history from file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return []


def save_history(events: list[dict]) -> None:
    """Save token history to file."""
    SHERLOCK_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(events, indent=2))


def start_sherlock(
    port: int = DEFAULT_PROXY_PORT,
    token_limit: int = DEFAULT_TOKEN_LIMIT,
    persist: bool = False,
    save_prompts: bool = False,
    skip_cert_check: bool = False,
) -> None:
    """Start the Sherlock proxy and dashboard.

    Args:
        port: Proxy port number
        token_limit: Maximum token limit for fuel gauge
        persist: Whether to persist token history
        save_prompts: Whether to save prompts to files
        skip_cert_check: Whether to skip certificate verification
    """
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)

    # Ensure certificates are ready before starting
    if not ensure_certs_ready(skip_check=skip_cert_check):
        console.print("[red]Certificate setup failed. Cannot start proxy.[/red]")
        sys.exit(1)

    # Create temp file for IPC
    ipc_dir = tempfile.mkdtemp(prefix="sherlock_")
    ipc_file = Path(ipc_dir) / IPC_FILENAME

    # Track all events for history
    all_events: list[dict] = []

    # Cleanup function
    def cleanup():
        if mitm_process and mitm_process.poll() is None:
            mitm_process.terminate()
            try:
                mitm_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mitm_process.kill()
        if ipc_file.exists():
            ipc_file.unlink()
        if Path(ipc_dir).exists():
            Path(ipc_dir).rmdir()
        if persist and all_events:
            save_history(all_events)

    atexit.register(cleanup)

    # Get path to interceptor module
    interceptor_path = Path(__file__).parent / "interceptor.py"

    # Find mitmdump binary (should be in same directory as Python executable)
    mitmdump_path = Path(sys.executable).parent / "mitmdump"
    if not mitmdump_path.exists():
        # Fallback: try to find it in PATH
        mitmdump_path = shutil.which("mitmdump")
        if not mitmdump_path:
            console.print("[red]Error: mitmdump not found. Install with: pip install mitmproxy[/red]")
            sys.exit(1)

    # Set up environment for mitmproxy subprocess
    env = os.environ.copy()
    env["SHERLOCK_IPC_FILE"] = str(ipc_file)

    # Start mitmproxy subprocess
    mitm_cmd = [
        str(mitmdump_path),
        "--listen-port", str(port),
        "--set", "ssl_insecure=true",
        "--scripts", str(interceptor_path),
        "--quiet",
    ]

    console.print(f"[cyan]Starting proxy on port {port}...[/cyan]")

    try:
        mitm_process = subprocess.Popen(
            mitm_cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        console.print("[red]Error: mitmproxy not found. Install with: pip install mitmproxy[/red]")
        sys.exit(1)

    # Give mitmproxy time to start
    time.sleep(1)

    # Check if process started successfully
    if mitm_process.poll() is not None:
        stderr = mitm_process.stderr.read().decode() if mitm_process.stderr else ""
        console.print(f"[red]Failed to start mitmproxy:[/red] {stderr}")
        sys.exit(1)

    console.print(f"[green]Proxy running on http://127.0.0.1:{port}[/green]")
    console.print()
    console.print("[yellow]To intercept traffic, in another terminal run:[/yellow]")
    console.print("  [cyan]sherlock claude[/cyan]      # for Claude Code")
    console.print("  [cyan]sherlock gemini[/cyan]      # for Gemini CLI")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    # Create dashboard
    dashboard = SherlockDashboard(token_limit=token_limit)

    # Load history if persisting
    if persist:
        history = load_history()
        all_events.extend(history)
        dashboard.load_history(history)

    # Track file position for reading new events
    file_pos = 0

    def poll_ipc() -> list[dict]:
        """Poll the IPC file for new events."""
        nonlocal file_pos
        events = []

        if not ipc_file.exists():
            return events

        try:
            with open(ipc_file, "r") as f:
                f.seek(file_pos)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            events.append(event)
                            all_events.append(event)

                            # Save prompt if enabled
                            if save_prompts:
                                save_prompt_to_file(event)
                        except json.JSONDecodeError:
                            pass
                file_pos = f.tell()
        except IOError:
            pass

        return events

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        console.print("\n[yellow]Shutting down...[/yellow]")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run dashboard
    try:
        dashboard.run(poll_ipc)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
