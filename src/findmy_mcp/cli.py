"""CLI interface for FindMyMCP."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from findmy_mcp.config import ScannerConfig
from findmy_mcp.scanner import MCPScanner

app = typer.Typer(
    name="mcp-scan",
    help="Fast, concurrent MCP server discovery and analysis tool for security research",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print("FindMyMCP v1.0.0")
        raise typer.Exit()


@app.command()
def scan(
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar="MCP_SCANNER_SHODAN_API_KEY",
            help="Shodan API key",
        ),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Filter category (e.g., core_protocol, transport_sse)",
        ),
    ] = None,
    filters: Annotated[
        list[str] | None,
        typer.Option(
            "--filter",
            "-f",
            help="Specific Shodan filters to use (can specify multiple)",
        ),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option(
            "--max-results",
            "-m",
            help="Maximum results per filter",
        ),
    ] = 100,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            help="Maximum concurrent verifications",
        ),
    ] = 50,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            "-t",
            help="Verification timeout in seconds",
        ),
    ] = 3.0,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for results",
        ),
    ] = Path("scan_results"),
    no_ssl_verify: Annotated[
        bool,
        typer.Option(
            "--no-ssl-verify",
            help="Disable SSL certificate verification",
        ),
    ] = False,
    discover_only: Annotated[
        bool,
        typer.Option(
            "--discover-only",
            help="Only discover servers, skip verification (saves to checkpoint file)",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    """Scan for MCP servers using Shodan.

    This tool discovers publicly exposed MCP servers and verifies their
    protocol compliance. Use responsibly for authorized security research only.

    Example usage:

        # Scan with API key from environment
        mcp-scan scan

        # Scan specific category
        mcp-scan scan --category core_protocol

        # Discover only (fast, saves checkpoint)
        mcp-scan scan --discover-only

        # Verify later from checkpoint
        mcp-scan verify scan_results/scan_xxx/discovered_servers.json

        # Scan with custom filters
        mcp-scan scan --filter '"Model Context Protocol"' --filter 'mcp server'

        # Scan with custom settings
        mcp-scan scan --max-results 50 --concurrency 20 --timeout 15
    """
    if not api_key:
        console.print(
            "[red]Error: Shodan API key required. "
            "Set MCP_SCANNER_SHODAN_API_KEY or use --api-key[/red]"
        )
        raise typer.Exit(1)

    # Display banner
    console.print(
        Panel.fit(
            "[bold cyan]FindMyMCP v1.0[/bold cyan]\n"
            "[dim]Fast, Concurrent MCP Server Discovery[/dim]\n\n"
            "[yellow]⚠ Use only for authorized security research[/yellow]",
            border_style="cyan",
        )
    )

    # Create configuration
    config = ScannerConfig(
        shodan_api_key=api_key,
        max_results_per_filter=max_results,
        max_concurrent_verifications=concurrency,
        verification_timeout=timeout,
        output_dir=output_dir,
        verify_ssl=not no_ssl_verify,
    )

    # Create scanner
    scanner = MCPScanner(config)

    try:
        # Validate API key
        info = scanner.validate_api_key()

        # Check credits
        if info.get("query_credits", 0) < 1:
            console.print(
                "[red]Error: Insufficient Shodan query credits. "
                "Please upgrade your account.[/red]"
            )
            raise typer.Exit(1)

        # Run scan
        result = asyncio.run(
            scanner.scan(filters=filters, category=category, discover_only=discover_only)
        )

        # Display results summary
        _display_results(result)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)


@app.command()
def verify(
    discovery_file: Annotated[
        Path,
        typer.Argument(
            help="Path to discovered_servers.json file from a previous scan",
        ),
    ],
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            help="Maximum concurrent verifications",
        ),
    ] = 50,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            "-t",
            help="Verification timeout in seconds",
        ),
    ] = 3.0,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for results",
        ),
    ] = Path("scan_results"),
    no_ssl_verify: Annotated[
        bool,
        typer.Option(
            "--no-ssl-verify",
            help="Disable SSL certificate verification",
        ),
    ] = False,
) -> None:
    """Verify MCP servers from a saved discovery file.

    This command allows you to verify servers that were previously discovered
    using the --discover-only flag. This is useful for separating the slow
    discovery phase from the verification phase.

    Example usage:

        # First, discover servers (fast)
        mcp-scan scan --discover-only

        # Later, verify them (can be done multiple times)
        mcp-scan verify scan_results/scan_xxx/discovered_servers.json

        # Verify with custom settings
        mcp-scan verify discovered_servers.json --concurrency 20 --timeout 15
    """
    if not discovery_file.exists():
        console.print(f"[red]Error: Discovery file not found: {discovery_file}[/red]")
        raise typer.Exit(1)

    # Display banner
    console.print(
        Panel.fit(
            "[bold cyan]FindMyMCP v1.0[/bold cyan]\n"
            "[dim]Verification Mode[/dim]\n\n"
            "[yellow]⚠ Use only for authorized security research[/yellow]",
            border_style="cyan",
        )
    )

    # Create configuration (no API key needed for verification)
    config = ScannerConfig(
        shodan_api_key="dummy",  # Not needed for verification
        max_concurrent_verifications=concurrency,
        verification_timeout=timeout,
        output_dir=output_dir,
        verify_ssl=not no_ssl_verify,
    )

    # Create scanner
    scanner = MCPScanner(config)

    try:
        # Run verification
        result = asyncio.run(scanner.verify_from_file(discovery_file))

        # Display results summary
        _display_results(result)

    except KeyboardInterrupt:
        console.print("\n[yellow]Verification interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)


@app.command()
def list_filters(
    filters_file: Annotated[
        Path,
        typer.Option(
            "--file",
            "-f",
            help="Path to filters JSON file",
        ),
    ] = Path("src/findmy_mcp/filters.json"),
) -> None:
    """List available Shodan filter categories."""
    import json

    try:
        with filters_file.open() as f:
            filters = json.load(f)

        table = Table(title="Available Filter Categories", show_header=True)
        table.add_column("Category", style="cyan")
        table.add_column("Filters", justify="right", style="green")
        table.add_column("Example", style="dim")

        for category, filter_list in filters.items():
            example = filter_list[0] if filter_list else "N/A"
            if len(example) > 50:
                example = example[:47] + "..."
            table.add_row(category, str(len(filter_list)), example)

        console.print(table)
        console.print(
            f"\n[dim]Total: {len(filters)} categories, "
            f"{sum(len(f) for f in filters.values())} filters[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error loading filters: {e!s}[/red]")
        raise typer.Exit(1)


def _display_results(result: "ScanResult") -> None:  # noqa: F821
    """Display scan results summary.

    Args:
        result: Scan results
    """

    # Summary table
    table = Table(title="Scan Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    duration = result.completed_at - result.started_at if result.completed_at else None

    table.add_row("Scan ID", result.scan_id)
    table.add_row("Duration", str(duration) if duration else "N/A")
    table.add_row("Filters Used", str(len(result.filters_used)))
    table.add_row("Servers Discovered", str(result.total_shodan_results))
    table.add_row("Servers Verified", str(len(result.verified_servers)))

    if result.verified_servers:
        success_rate = (
            len(result.verified_servers) / result.total_shodan_results * 100
            if result.total_shodan_results > 0
            else 0
        )
        table.add_row("Success Rate", f"{success_rate:.1f}%")

    console.print("\n")
    console.print(table)

    # Verified servers table
    if result.verified_servers:
        servers_table = Table(
            title="\nVerified MCP Servers",
            show_header=True,
            header_style="bold green",
        )
        servers_table.add_column("URL", style="cyan")
        servers_table.add_column("Transport", style="yellow")
        servers_table.add_column("Protocol", style="magenta")
        servers_table.add_column("Tools", justify="right", style="green")
        servers_table.add_column("Response (ms)", justify="right", style="blue")

        for server in result.verified_servers[:20]:  # Show first 20
            servers_table.add_row(
                server.url,
                server.transport_type.value.upper(),
                server.protocol_version or "N/A",
                str(len(server.tools)),
                f"{server.response_time_ms:.2f}" if server.response_time_ms else "N/A",
            )

        console.print("\n")
        console.print(servers_table)

        if len(result.verified_servers) > 20:
            console.print(
                f"\n[dim]... and {len(result.verified_servers) - 20} more servers[/dim]"
            )


if __name__ == "__main__":
    app()
