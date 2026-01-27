"""CLI interface for Sherlock."""

import os
import subprocess
import sys

import click

from sherlock.config import DEFAULT_PROXY_PORT, DEFAULT_TOKEN_LIMIT


def get_combined_ca_bundle() -> str | None:
    """Get or create a combined CA bundle with mitmproxy cert.

    Returns path to the combined bundle, or None if not available.
    """
    from pathlib import Path
    import tempfile

    mitmproxy_ca = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    if not mitmproxy_ca.exists():
        return None

    # Try to find the system/certifi CA bundle
    ca_bundle = None
    try:
        import certifi
        ca_bundle = certifi.where()
    except ImportError:
        # Try common system locations
        for path in [
            "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
            "/etc/pki/tls/certs/ca-bundle.crt",    # RHEL/CentOS
            "/etc/ssl/cert.pem",                    # macOS
        ]:
            if Path(path).exists():
                ca_bundle = path
                break

    if not ca_bundle:
        return None

    # Create combined bundle in sherlock config dir
    sherlock_dir = Path.home() / ".sherlock"
    sherlock_dir.mkdir(exist_ok=True)
    combined_path = sherlock_dir / "ca-bundle.pem"

    # Regenerate if mitmproxy cert is newer than combined bundle
    if not combined_path.exists() or mitmproxy_ca.stat().st_mtime > combined_path.stat().st_mtime:
        with open(combined_path, "w") as out:
            with open(ca_bundle) as f:
                out.write(f.read())
            out.write("\n# mitmproxy CA\n")
            with open(mitmproxy_ca) as f:
                out.write(f.read())

    return str(combined_path)


def get_node_global_path() -> str | None:
    """Get the global node_modules path."""
    try:
        result = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_node_proxy_deps() -> tuple[bool, str | None]:
    """Check if required Node.js proxy dependencies are installed.

    Checks for 'undici' (preferred) or 'global-agent'.
    Returns:
        Tuple of (is_installed, node_path)
    """
    node_path = get_node_global_path()
    if not node_path:
        return False, None

    env = os.environ.copy()
    env["NODE_PATH"] = node_path

    # Check for undici first (preferred)
    try:
        result = subprocess.run(
            ["node", "-e", "require('undici')"],
            capture_output=True,
            timeout=5,
            env=env,
        )
        if result.returncode == 0:
            return True, node_path
    except Exception:
        pass

    # Check for global-agent (fallback)
    try:
        result = subprocess.run(
            ["node", "-e", "require('global-agent')"],
            capture_output=True,
            timeout=5,
            env=env,
        )
        if result.returncode == 0:
            return True, node_path
    except Exception:
        pass

    return False, node_path


def run_with_proxy(command: str, port: int, args: tuple, is_node_app: bool = False) -> None:
    """Run a command with proxy environment variables set."""
    from pathlib import Path

    env = os.environ.copy()
    proxy_url = f"http://127.0.0.1:{port}"
    env["HTTP_PROXY"] = proxy_url
    env["HTTPS_PROXY"] = proxy_url

    # Set certificate paths for various SSL libraries
    combined_ca = get_combined_ca_bundle()
    if combined_ca:
        # For Python requests/urllib3
        env["REQUESTS_CA_BUNDLE"] = combined_ca
        env["SSL_CERT_FILE"] = combined_ca

    # For Node.js, we can just add the mitmproxy cert
    mitmproxy_ca = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    if mitmproxy_ca.exists():
        env["NODE_EXTRA_CA_CERTS"] = str(mitmproxy_ca)

    # For Node.js apps, we need to inject proxy setup via a preload script
    if is_node_app:
        # Check if we have the necessary dependencies
        has_deps, node_path = check_node_proxy_deps()
        if not has_deps:
            click.echo(
                "[Warning] Node.js proxy dependencies not found.\n"
                "To proxy Node.js apps, please run:\n"
                "  npm install -g undici\n",
                err=True,
            )

        # Find the bootstrap script (installed with sherlock package)
        bootstrap_script = Path(__file__).parent / "node_proxy_bootstrap.js"

        if bootstrap_script.exists():
            # Set NODE_PATH so global modules can be found
            if node_path:
                existing_node_path = env.get("NODE_PATH", "")
                env["NODE_PATH"] = f"{node_path}:{existing_node_path}".rstrip(":")

            # Set proxy URL for the bootstrap script
            env["SHERLOCK_PROXY_URL"] = proxy_url

            # Also set these for global-agent fallback
            env["GLOBAL_AGENT_HTTP_PROXY"] = proxy_url
            env["GLOBAL_AGENT_HTTPS_PROXY"] = proxy_url
            env["GLOBAL_AGENT_NO_PROXY"] = ""

            # Load our bootstrap script before the app runs
            existing_node_options = env.get("NODE_OPTIONS", "")
            env["NODE_OPTIONS"] = f"--require {bootstrap_script} {existing_node_options}".strip()
        else:
            click.echo(
                "[Warning] Could not find Node.js proxy bootstrap script.\n",
                err=True,
            )

    cmd = [command] + list(args)
    try:
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except FileNotFoundError:
        click.echo(f"Error: '{command}' not found. Make sure it's installed and in your PATH.", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Sherlock - LLM API traffic interceptor and token usage dashboard."""
    if ctx.invoked_subcommand is None:
        # Default to 'start' command
        ctx.invoke(start)


@main.command()
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.option("--limit", "-l", default=DEFAULT_TOKEN_LIMIT, help="Token limit for fuel gauge")
@click.option("--persist", is_flag=True, help="Save token history to ~/.sherlock/history.json")
@click.option("--save-prompts", is_flag=True, help="Save prompts to ~/.sherlock/prompts/")
@click.option("--skip-cert-check", is_flag=True, help="Skip certificate verification")
def start(port: int, limit: int, persist: bool, save_prompts: bool, skip_cert_check: bool):
    """Start the proxy and dashboard."""
    from sherlock.main import start_sherlock
    start_sherlock(port=port, token_limit=limit, persist=persist, save_prompts=save_prompts, skip_cert_check=skip_cert_check)


@main.command("check-certs")
def check_certs():
    """Check if mitmproxy CA certificate is installed."""
    from sherlock.certs import check_certs as do_check
    do_check()


@main.command("install-certs")
def install_certs():
    """Print instructions for installing the CA certificate."""
    from sherlock.certs import print_install_instructions
    print_install_instructions()


@main.command()
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
def env(port: int):
    """Print environment variables for proxy configuration."""
    from sherlock.certs import output_env_vars
    output_env_vars(port=port)


@main.command()
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.option("--node", is_flag=True, help="Inject Node.js proxy configuration")
@click.argument("command")
@click.argument("args", nargs=-1)
def run(port: int, node: bool, command: str, args: tuple):
    """Run any command with proxy configured.

    Example: sherlock run curl https://api.anthropic.com/v1/messages ...
    Example: sherlock run --node my-node-script.js
    """
    run_with_proxy(command, port, args, is_node_app=node)


@main.command()
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.argument("args", nargs=-1)
def claude(port: int, args: tuple):
    """Run Claude Code with proxy configured.

    Start sherlock in another terminal first, then use this command.
    Any additional arguments are passed to claude.

    Example: sherlock claude --help
    """
    run_with_proxy("claude", port, args, is_node_app=True)


@main.command()
@click.option("--port", "-p", default=DEFAULT_PROXY_PORT, help="Proxy port number")
@click.argument("args", nargs=-1)
def gemini(port: int, args: tuple):
    """Run Gemini CLI with proxy configured.

    Start sherlock in another terminal first, then use this command.
    Any additional arguments are passed to gemini.

    Example: sherlock gemini --help
    """
    run_with_proxy("gemini", port, args, is_node_app=True)


if __name__ == "__main__":
    main()
