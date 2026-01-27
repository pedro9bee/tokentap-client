"""Certificate checking and installation utilities."""

import platform
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()


def get_mitmproxy_cert_path() -> Path:
    """Get the path to the mitmproxy CA certificate."""
    return Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"


def cert_file_exists() -> bool:
    """Check if the mitmproxy CA certificate file exists."""
    return get_mitmproxy_cert_path().exists()


def check_cert_in_system_store() -> bool:
    """Check if mitmproxy CA is installed in the system trust store."""
    system = platform.system()

    if system == "Darwin":
        # macOS: Check keychain
        try:
            result = subprocess.run(
                ["security", "find-certificate", "-c", "mitmproxy", "/Library/Keychains/System.keychain"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    elif system == "Linux":
        # Linux: Check common certificate locations
        cert_locations = [
            Path("/etc/ssl/certs/mitmproxy-ca-cert.pem"),
            Path("/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt"),
            Path("/etc/pki/ca-trust/source/anchors/mitmproxy-ca-cert.pem"),
        ]
        return any(loc.exists() for loc in cert_locations)

    return False


def check_certs() -> bool:
    """Check certificate status and print results.

    Returns True if certs are properly installed.
    """
    cert_path = get_mitmproxy_cert_path()

    console.print()
    console.print("[bold]Certificate Status Check[/bold]")
    console.print()

    # Check if cert file exists
    if not cert_file_exists():
        console.print("[red]✗[/red] mitmproxy CA certificate not found")
        console.print(f"  Expected at: {cert_path}")
        console.print()
        console.print("[yellow]Run mitmproxy once to generate certificates:[/yellow]")
        console.print("  mitmdump --showhost")
        console.print("  (then press Ctrl+C to stop)")
        return False

    console.print(f"[green]✓[/green] CA certificate exists: {cert_path}")

    # Check system trust store
    if check_cert_in_system_store():
        console.print("[green]✓[/green] CA certificate is installed in system trust store")
        console.print()
        console.print("[green]Certificates are properly configured![/green]")
        return True
    else:
        console.print("[yellow]![/yellow] CA certificate may not be in system trust store")
        console.print()
        console.print("Run [cyan]sherlock install-certs[/cyan] for installation instructions")
        return False


def print_install_instructions() -> None:
    """Print OS-specific instructions for installing the CA certificate."""
    cert_path = get_mitmproxy_cert_path()
    system = platform.system()

    console.print()

    if not cert_file_exists():
        console.print(Panel(
            "[red]Certificate file not found![/red]\n\n"
            "First, generate the mitmproxy CA certificate by running:\n\n"
            "  [cyan]mitmdump --showhost[/cyan]\n\n"
            "Press Ctrl+C to stop, then run this command again.",
            title="Step 0: Generate Certificate",
            border_style="red",
        ))
        return

    console.print(f"[bold]CA Certificate Location:[/bold] {cert_path}")
    console.print()

    if system == "Darwin":
        console.print(Panel(
            "[bold]Option 1: Using Keychain Access (GUI)[/bold]\n\n"
            f"1. Open the certificate file:\n"
            f"   [cyan]open {cert_path}[/cyan]\n\n"
            "2. Keychain Access will open. Add to 'System' keychain.\n\n"
            "3. Find 'mitmproxy' in the list, double-click it.\n\n"
            "4. Expand 'Trust' section.\n\n"
            "5. Set 'When using this certificate' to 'Always Trust'.\n\n"
            "6. Close and enter your password to confirm.\n\n"
            "[bold]Option 2: Command Line[/bold]\n\n"
            f"[cyan]sudo security add-trusted-cert -d -r trustRoot \\\n"
            f"  -k /Library/Keychains/System.keychain {cert_path}[/cyan]",
            title="macOS Installation Instructions",
            border_style="cyan",
        ))

    elif system == "Linux":
        console.print(Panel(
            "[bold]For Debian/Ubuntu:[/bold]\n\n"
            f"[cyan]sudo cp {cert_path} /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt\n"
            "sudo update-ca-certificates[/cyan]\n\n"
            "[bold]For RHEL/CentOS/Fedora:[/bold]\n\n"
            f"[cyan]sudo cp {cert_path} /etc/pki/ca-trust/source/anchors/\n"
            "sudo update-ca-trust[/cyan]\n\n"
            "[bold]For Arch Linux:[/bold]\n\n"
            f"[cyan]sudo trust anchor --store {cert_path}[/cyan]",
            title="Linux Installation Instructions",
            border_style="cyan",
        ))

    else:
        console.print(Panel(
            f"Certificate location: {cert_path}\n\n"
            "Please consult your operating system's documentation\n"
            "for installing CA certificates in the system trust store.",
            title="Installation Instructions",
            border_style="yellow",
        ))

    console.print()
    console.print("After installation, run [cyan]sherlock check-certs[/cyan] to verify.")


def print_env_vars(port: int = 8080) -> None:
    """Print environment variables for proxy configuration."""
    proxy_url = f"http://127.0.0.1:{port}"

    shell = Path(environ.get("SHELL", "/bin/bash")).name if (environ := __import__("os").environ) else "bash"

    console.print()
    console.print("[bold]Set these environment variables to route traffic through Sherlock:[/bold]")
    console.print()

    if shell in ("bash", "zsh", "sh"):
        console.print(f'export HTTP_PROXY="{proxy_url}"')
        console.print(f'export HTTPS_PROXY="{proxy_url}"')
        console.print(f'export http_proxy="{proxy_url}"')
        console.print(f'export https_proxy="{proxy_url}"')
    elif shell == "fish":
        console.print(f'set -x HTTP_PROXY "{proxy_url}"')
        console.print(f'set -x HTTPS_PROXY "{proxy_url}"')
        console.print(f'set -x http_proxy "{proxy_url}"')
        console.print(f'set -x https_proxy "{proxy_url}"')
    else:
        console.print(f'HTTP_PROXY="{proxy_url}"')
        console.print(f'HTTPS_PROXY="{proxy_url}"')

    console.print()
    console.print("[dim]Or use: eval $(sherlock env)[/dim]")


def output_env_vars(port: int = 8080) -> None:
    """Output shell commands for setting proxy environment variables."""
    import os
    proxy_url = f"http://127.0.0.1:{port}"
    shell = Path(os.environ.get("SHELL", "/bin/bash")).name

    if shell == "fish":
        print(f'set -x HTTP_PROXY "{proxy_url}";')
        print(f'set -x HTTPS_PROXY "{proxy_url}";')
        print(f'set -x http_proxy "{proxy_url}";')
        print(f'set -x https_proxy "{proxy_url}";')
    else:
        # bash/zsh/sh compatible
        print(f'export HTTP_PROXY="{proxy_url}";')
        print(f'export HTTPS_PROXY="{proxy_url}";')
        print(f'export http_proxy="{proxy_url}";')
        print(f'export https_proxy="{proxy_url}";')


def generate_cert() -> bool:
    """Generate the mitmproxy CA certificate by running mitmproxy briefly.

    Returns True if certificate was generated successfully.
    """
    console.print("[cyan]Generating mitmproxy CA certificate...[/cyan]")

    # Find mitmdump executable in the same directory as the Python interpreter
    python_bin_dir = Path(sys.executable).parent
    mitmdump_path = python_bin_dir / "mitmdump"

    if not mitmdump_path.exists():
        # Fall back to system PATH
        import shutil
        mitmdump_path = shutil.which("mitmdump")
        if not mitmdump_path:
            console.print("[red]mitmdump not found. Install mitmproxy: pip install mitmproxy[/red]")
            return False

    try:
        # Run mitmdump briefly to generate certs
        process = subprocess.Popen(
            [str(mitmdump_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give it time to generate certs
        time.sleep(2)
        process.terminate()
        process.wait(timeout=5)
    except Exception as e:
        console.print(f"[red]Failed to generate certificate: {e}[/red]")
        return False

    if cert_file_exists():
        console.print("[green]✓[/green] Certificate generated successfully")
        return True
    else:
        console.print("[red]✗[/red] Failed to generate certificate")
        return False


def install_cert() -> bool:
    """Install the mitmproxy CA certificate in the system trust store.

    Returns True if installation was successful.
    """
    system = platform.system()
    cert_path = get_mitmproxy_cert_path()

    if not cert_file_exists():
        console.print("[red]Certificate file not found. Cannot install.[/red]")
        return False

    if system == "Darwin":
        # macOS: Install to system keychain
        console.print("[cyan]Installing certificate to system keychain (requires password)...[/cyan]")
        try:
            result = subprocess.run(
                [
                    "sudo", "security", "add-trusted-cert",
                    "-d", "-r", "trustRoot",
                    "-k", "/Library/Keychains/System.keychain",
                    str(cert_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print("[green]✓[/green] Certificate installed successfully")
                return True
            else:
                console.print(f"[red]✗[/red] Installation failed: {result.stderr}")
                return False
        except Exception as e:
            console.print(f"[red]✗[/red] Installation failed: {e}")
            return False

    elif system == "Linux":
        # Try to detect the Linux distribution
        console.print("[cyan]Installing certificate (requires password)...[/cyan]")

        # Try Debian/Ubuntu first
        debian_path = Path("/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt")
        try:
            result = subprocess.run(
                ["sudo", "cp", str(cert_path), str(debian_path)],
                capture_output=True,
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["sudo", "update-ca-certificates"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    console.print("[green]✓[/green] Certificate installed successfully")
                    return True
        except Exception:
            pass

        # Try RHEL/CentOS/Fedora
        rhel_path = Path("/etc/pki/ca-trust/source/anchors/mitmproxy-ca-cert.pem")
        try:
            result = subprocess.run(
                ["sudo", "cp", str(cert_path), str(rhel_path)],
                capture_output=True,
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["sudo", "update-ca-trust"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    console.print("[green]✓[/green] Certificate installed successfully")
                    return True
        except Exception:
            pass

        console.print("[red]✗[/red] Could not install certificate automatically")
        console.print("Run [cyan]sherlock install-certs[/cyan] for manual instructions")
        return False

    else:
        console.print(f"[yellow]Automatic installation not supported on {system}[/yellow]")
        console.print("Run [cyan]sherlock install-certs[/cyan] for manual instructions")
        return False


def ensure_certs_ready(skip_check: bool = False) -> bool:
    """Ensure certificates are generated and installed.

    This function:
    1. Checks if cert file exists, generates if not
    2. Checks if cert is in system trust store, prompts to install if not

    Args:
        skip_check: If True, skip the certificate check entirely

    Returns:
        True if certs are ready (or user chose to skip), False if setup failed
    """
    if skip_check:
        return True

    # Step 1: Check/generate certificate file
    if not cert_file_exists():
        console.print()
        console.print("[yellow]mitmproxy CA certificate not found.[/yellow]")
        if not generate_cert():
            return False
        console.print()

    # Step 2: Check/install in system trust store
    if not check_cert_in_system_store():
        console.print()
        console.print("[yellow]CA certificate is not installed in system trust store.[/yellow]")
        console.print("This is required for HTTPS interception to work.")
        console.print()

        if Confirm.ask("Install certificate now? (requires password)", default=True):
            if not install_cert():
                console.print()
                console.print("[yellow]You can try manual installation:[/yellow]")
                console.print("  sherlock install-certs")
                console.print()
                return False
        else:
            console.print()
            console.print("[yellow]Skipping certificate installation.[/yellow]")
            console.print("HTTPS interception may not work until you run:")
            console.print("  sherlock install-certs")
            console.print()
            # Continue anyway - user explicitly chose to skip
            return True

    return True
