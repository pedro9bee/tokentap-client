"""CLI interface for tokentap."""

import asyncio
import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from tokentap.config import (
    DEFAULT_PROXY_PORT,
    DEFAULT_TOKEN_LIMIT,
    MITMPROXY_CA_CERT,
    MITMPROXY_CA_DIR,
    NO_PROXY,
    PROVIDERS,
    PROMPTS_DIR,
    SHELL_INTEGRATION_END,
    SHELL_INTEGRATION_START,
    TOKENTAP_DIR,
    WEB_PORT,
)

console = Console()


def _find_compose_file() -> Path:
    """Find docker-compose.yml - check package dir, then cwd."""
    # Check alongside the package (installed from source / editable)
    pkg_dir = Path(__file__).parent.parent
    candidates = [
        pkg_dir / "docker-compose.yml",
        Path.cwd() / "docker-compose.yml",
    ]
    for p in candidates:
        if p.exists():
            return p

    # Fall back to package dir (will be created on install)
    return pkg_dir / "docker-compose.yml"


def _docker_compose_cmd() -> list[str]:
    """Return the docker compose base command with compose file."""
    compose_file = _find_compose_file()
    return ["docker", "compose", "-f", str(compose_file)]


def save_prompt_to_file(event: dict, prompts_dir: Path) -> None:
    """Save a prompt to markdown and raw JSON files."""
    prompts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.fromisoformat(event["timestamp"])
    base_filename = timestamp.strftime(f"%Y-%m-%d_%H-%M-%S_{event['provider']}")

    # Save markdown file (human-readable)
    md_filepath = prompts_dir / f"{base_filename}.md"
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

    md_filepath.write_text("\n".join(lines))

    # Save raw JSON file (original request body)
    raw_body = event.get("raw_body")
    if raw_body is not None:
        json_filepath = prompts_dir / f"{base_filename}.json"
        json_filepath.write_text(json.dumps(raw_body, indent=2))


def get_prompts_dir_interactive() -> Path:
    """Prompt user for prompts directory."""
    console.print(f"[cyan]Directory to save prompts (press Enter for default):[/cyan]")
    console.print(f"[dim]Default: {PROMPTS_DIR}[/dim]")

    try:
        user_input = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        user_input = ""

    if user_input:
        return Path(user_input).expanduser().resolve()
    return PROMPTS_DIR


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """tokentap - LLM token usage tracker.

    Quick start (Docker):

        tokentap up          # Start proxy + dashboard + MongoDB
        tokentap install     # Auto-configure shell
        tokentap open        # Open web dashboard

    Legacy mode (no Docker):

        tokentap start       # Start proxy + Rich dashboard
        tokentap claude      # Run Claude through proxy
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# =============================================================================
# Docker commands
# =============================================================================

@main.command()
@click.option("--build", "do_build", is_flag=True, default=True, help="Rebuild images")
def up(do_build):
    """Start tokentap services (proxy + web dashboard + MongoDB)."""
    cmd = _docker_compose_cmd() + ["up", "-d"]
    if do_build:
        cmd.append("--build")

    console.print("[cyan]Starting tokentap services...[/cyan]")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        # Copy mitmproxy CA cert from the proxy container to host
        MITMPROXY_CA_DIR.mkdir(parents=True, exist_ok=True)
        cp_cmd = _docker_compose_cmd() + [
            "cp", "proxy:/root/.mitmproxy/mitmproxy-ca-cert.pem",
            str(MITMPROXY_CA_CERT),
        ]
        cp_result = subprocess.run(cp_cmd, capture_output=True)
        if cp_result.returncode == 0:
            console.print(f"[green]CA certificate copied to {MITMPROXY_CA_CERT}[/green]")
        else:
            console.print("[yellow]Could not copy CA cert from container (proxy may still be starting).[/yellow]")
            console.print(f"[dim]Retry with: docker compose cp proxy:/root/.mitmproxy/mitmproxy-ca-cert.pem {MITMPROXY_CA_CERT}[/dim]")

        console.print()
        console.print("[green]Tokentap is running![/green]")
        console.print(f"  Proxy:     http://127.0.0.1:{DEFAULT_PROXY_PORT}")
        console.print(f"  Dashboard: http://127.0.0.1:{WEB_PORT}")
        console.print()
        console.print("[dim]Run 'tokentap install' to auto-configure your shell.[/dim]")
        console.print("[dim]Run 'tokentap install-cert' to trust the HTTPS CA certificate.[/dim]")
    else:
        console.print("[red]Failed to start services. Is Docker running?[/red]")
        sys.exit(result.returncode)


@main.command()
def down():
    """Stop tokentap services."""
    cmd = _docker_compose_cmd() + ["down"]
    console.print("[cyan]Stopping tokentap services...[/cyan]")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        console.print("[green]Services stopped.[/green]")
    else:
        sys.exit(result.returncode)


@main.command()
def status():
    """Show status of tokentap services."""
    cmd = _docker_compose_cmd() + ["ps", "--format", "table {{.Name}}\t{{.Status}}\t{{.Ports}}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            console.print(output)
        else:
            console.print("[yellow]No tokentap services running.[/yellow]")
    else:
        console.print("[yellow]No tokentap services running (or Docker is not available).[/yellow]")


@main.command()
@click.option("--follow", "-f", is_flag=True, default=True, help="Follow log output")
@click.argument("service", required=False)
def logs(follow, service):
    """Show logs from tokentap services."""
    cmd = _docker_compose_cmd() + ["logs"]
    if follow:
        cmd.append("-f")
    if service:
        cmd.append(service)
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


@main.command(name="open")
def open_dashboard():
    """Open the web dashboard in your browser."""
    url = f"http://127.0.0.1:{WEB_PORT}"
    console.print(f"[cyan]Opening {url}...[/cyan]")
    webbrowser.open(url)


# =============================================================================
# Shell integration
# =============================================================================

def _get_shell_rc() -> Path | None:
    """Detect the user's shell rc file."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    elif "bash" in shell:
        # Prefer .bashrc, fall back to .bash_profile on macOS
        bashrc = home / ".bashrc"
        if bashrc.exists():
            return bashrc
        return home / ".bash_profile"
    return None


@main.command(name="shell-init")
def shell_init():
    """Print shell environment exports for eval. Usage: eval \"$(tokentap shell-init)\""""
    proxy_url = f"http://127.0.0.1:{DEFAULT_PROXY_PORT}"
    ca_cert = str(MITMPROXY_CA_CERT)
    lines = [
        f'export HTTPS_PROXY="{proxy_url}"',
        f'export HTTP_PROXY="{proxy_url}"',
        f'export NO_PROXY="{NO_PROXY}"',
        f'export NODE_EXTRA_CA_CERTS="{ca_cert}"',
        f'export SSL_CERT_FILE="{ca_cert}"',
        f'export REQUESTS_CA_BUNDLE="{ca_cert}"',
    ]
    click.echo("\n".join(lines))


@main.command()
@click.option("--output", "-o", default=None, help="Write to file instead of stdout (e.g. -o .env)")
def env(output):
    """Generate .env file contents for project-level proxy config.

    Use this to route a specific project's SDK calls through tokentap:

        tokentap env >> .env
        tokentap env -o .env
    """
    proxy_url = f"http://127.0.0.1:{DEFAULT_PROXY_PORT}"
    ca_cert = str(MITMPROXY_CA_CERT)
    lines = [
        "# tokentap proxy — routes LLM API calls through HTTPS_PROXY",
        f"HTTPS_PROXY={proxy_url}",
        f"HTTP_PROXY={proxy_url}",
        f"NO_PROXY={NO_PROXY}",
        f"NODE_EXTRA_CA_CERTS={ca_cert}",
        f"SSL_CERT_FILE={ca_cert}",
        f"REQUESTS_CA_BUNDLE={ca_cert}",
    ]
    content = "\n".join(lines) + "\n"

    if output:
        out_path = Path(output)
        if out_path.exists():
            # Append to existing .env
            existing = out_path.read_text()
            if "tokentap proxy" in existing:
                console.print(f"[yellow]Tokentap vars already in {out_path}[/yellow]")
                return
            with open(out_path, "a") as f:
                f.write("\n" + content)
            console.print(f"[green]Appended tokentap vars to {out_path}[/green]")
        else:
            out_path.write_text(content)
            console.print(f"[green]Created {out_path} with tokentap vars[/green]")
    else:
        click.echo(content, nl=False)


@main.command()
def install():
    """Add tokentap shell integration to your shell rc file."""
    rc_file = _get_shell_rc()
    if not rc_file:
        console.print("[red]Could not detect shell. Manually add to your shell rc:[/red]")
        console.print('  eval "$(tokentap shell-init)"')
        return

    # Check if already installed
    if rc_file.exists():
        content = rc_file.read_text()
        if SHELL_INTEGRATION_START in content:
            console.print(f"[yellow]Shell integration already installed in {rc_file}[/yellow]")
            return
    else:
        content = ""

    # Append integration
    block = f"""
{SHELL_INTEGRATION_START}
eval "$(tokentap shell-init)"
{SHELL_INTEGRATION_END}
"""
    with open(rc_file, "a") as f:
        f.write(block)

    console.print(f"[green]Shell integration added to {rc_file}[/green]")
    console.print(f"[dim]Run 'source {rc_file}' or open a new terminal to activate.[/dim]")


@main.command()
def uninstall():
    """Remove tokentap shell integration from your shell rc file."""
    rc_file = _get_shell_rc()
    if not rc_file or not rc_file.exists():
        console.print("[yellow]No shell rc file found.[/yellow]")
        return

    content = rc_file.read_text()
    if SHELL_INTEGRATION_START not in content:
        console.print("[yellow]Shell integration not found in {rc_file}[/yellow]")
        return

    # Remove the block
    lines = content.split("\n")
    new_lines = []
    inside_block = False
    for line in lines:
        if SHELL_INTEGRATION_START in line:
            inside_block = True
            continue
        if SHELL_INTEGRATION_END in line:
            inside_block = False
            continue
        if not inside_block:
            new_lines.append(line)

    # Remove trailing blank lines from the block removal
    while new_lines and new_lines[-1] == "":
        new_lines.pop()
    new_lines.append("")  # Ensure file ends with newline

    rc_file.write_text("\n".join(new_lines))
    console.print(f"[green]Shell integration removed from {rc_file}[/green]")


@main.command(name="install-cert")
def install_cert():
    """Trust the mitmproxy CA certificate (needed for HTTPS interception).

    On macOS, adds the cert to the system keychain.
    On Linux, copies to /usr/local/share/ca-certificates and runs update-ca-certificates.
    """
    cert_path = MITMPROXY_CA_CERT
    if not cert_path.exists():
        console.print(f"[red]CA certificate not found at {cert_path}[/red]")
        console.print("[dim]Start the proxy first (tokentap up) to generate the certificate.[/dim]")
        sys.exit(1)

    import platform
    system = platform.system()

    if system == "Darwin":
        console.print(f"[cyan]Adding {cert_path} to macOS system keychain...[/cyan]")
        result = subprocess.run([
            "sudo", "security", "add-trusted-cert",
            "-d", "-r", "trustRoot",
            "-k", "/Library/Keychains/System.keychain",
            str(cert_path),
        ])
        if result.returncode == 0:
            console.print("[green]Certificate trusted successfully.[/green]")
        else:
            console.print("[red]Failed to trust certificate. Try running with sudo.[/red]")
            sys.exit(result.returncode)
    elif system == "Linux":
        dest = Path("/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt")
        console.print(f"[cyan]Copying {cert_path} to {dest}...[/cyan]")
        result = subprocess.run(["sudo", "cp", str(cert_path), str(dest)])
        if result.returncode != 0:
            console.print("[red]Failed to copy certificate.[/red]")
            sys.exit(result.returncode)
        result = subprocess.run(["sudo", "update-ca-certificates"])
        if result.returncode == 0:
            console.print("[green]Certificate trusted successfully.[/green]")
        else:
            console.print("[red]Failed to update CA certificates.[/red]")
            sys.exit(result.returncode)
    else:
        console.print(f"[yellow]Unsupported platform: {system}[/yellow]")
        console.print(f"[dim]Manually trust the certificate at: {cert_path}[/dim]")


# =============================================================================
# Legacy commands (still functional)
# =============================================================================

@main.command()
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.option("--limit", "-l", default=DEFAULT_TOKEN_LIMIT, help="Token limit for fuel gauge")
def start(port: int, limit: int):
    """[Legacy] Start the proxy and Rich terminal dashboard.

    Run this in one terminal, then use 'tokentap claude' (or gemini/codex)
    in another terminal.

    Consider using 'tokentap up' for the Docker-based setup instead.
    """
    from tokentap.dashboard import TokenTapDashboard

    console.print("[dim]Tip: Use 'tokentap up' for the Docker-based setup with web dashboard.[/dim]")
    console.print()

    # Ask for prompts directory
    prompts_dir = get_prompts_dir_interactive()
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Create dashboard
    dashboard = TokenTapDashboard(token_limit=limit)

    # Event queue for thread-safe communication
    event_queue = []
    event_lock = threading.Lock()

    def on_request(event: dict) -> None:
        save_prompt_to_file(event, prompts_dir)
        with event_lock:
            event_queue.append(event)

    def poll_events() -> list[dict]:
        with event_lock:
            events = event_queue.copy()
            event_queue.clear()
        return events

    # Create and start proxy via mitmproxy
    from tokentap.proxy import start_mitmproxy

    loop = asyncio.new_event_loop()

    def run_proxy():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_mitmproxy(port=port, on_request=on_request))

    proxy_thread = threading.Thread(target=run_proxy, daemon=True)
    proxy_thread.start()

    import time
    time.sleep(0.5)

    console.print(f"[green]Proxy running on http://127.0.0.1:{port}[/green]")
    console.print(f"[green]Saving prompts to {prompts_dir}[/green]")
    console.print()
    console.print("[yellow]In another terminal, run:[/yellow]")
    console.print(f"  [cyan]tokentap claude[/cyan]")
    console.print(f"  [cyan]tokentap gemini[/cyan]")
    console.print(f"  [cyan]tokentap codex[/cyan]")
    console.print()
    console.print("[dim]Starting dashboard...[/dim]")

    time.sleep(1)

    try:
        dashboard.run(poll_events)
    except KeyboardInterrupt:
        pass
    finally:
        loop.call_soon_threadsafe(loop.stop)
        console.print()
        console.print(f"[cyan]Session complete. Total: {dashboard.total_tokens:,} tokens across {len(dashboard.requests)} requests.[/cyan]")


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def claude(port: int, args: tuple):
    """[Legacy] Run Claude Code with proxy configured.

    Consider using 'tokentap up && tokentap install' instead.
    """
    _run_tool("anthropic", "claude", port, args)


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def gemini(port: int, args: tuple):
    """[Legacy] Run Gemini CLI with proxy configured."""
    _run_tool("gemini", "gemini", port, args)


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def codex(port: int, args: tuple):
    """[Legacy] Run OpenAI Codex CLI with proxy configured."""
    _run_tool("openai", "codex", port, args)


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.option("--provider", "-P", required=True, type=click.Choice(list(PROVIDERS.keys())), help="LLM provider")
@click.argument("command")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def run(port: int, provider: str, command: str, args: tuple):
    """[Legacy] Run any command with proxy configured."""
    _run_tool(provider, command, port, args)


def _run_tool(provider: str, command: str, port: int, args: tuple) -> None:
    """Run a tool with the proxy environment variable set."""
    provider_config = PROVIDERS.get(provider)
    if not provider_config:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        sys.exit(1)

    env = os.environ.copy()
    proxy_url = f"http://127.0.0.1:{port}"
    ca_cert = str(MITMPROXY_CA_CERT)

    env["HTTPS_PROXY"] = proxy_url
    env["HTTP_PROXY"] = proxy_url
    env["NO_PROXY"] = NO_PROXY
    env["NODE_EXTRA_CA_CERTS"] = ca_cert
    env["SSL_CERT_FILE"] = ca_cert
    env["REQUESTS_CA_BUNDLE"] = ca_cert

    cmd = [command] + list(args)
    try:
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except FileNotFoundError:
        console.print(f"[red]Error: '{command}' not found. Make sure it's installed and in your PATH.[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
