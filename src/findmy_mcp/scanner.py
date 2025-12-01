"""MCP server scanner using Shodan API."""

import asyncio
import json
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any
from uuid import uuid4

import shodan
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from findmy_mcp.config import ScannerConfig
from findmy_mcp.models import DiscoveredServer, ScanResult, ShodanResult
from findmy_mcp.verifier import MCPVerifier

console = Console()


class MCPScanner:
    """MCP server scanner."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize scanner.

        Args:
            config: Scanner configuration
        """
        self.config = config
        self.shodan_api = shodan.Shodan(config.shodan_api_key)
        self.verifier = MCPVerifier(config)
        self.filters: dict[str, list[str]] = {}

    def load_filters(self) -> None:
        """Load Shodan filters from JSON file."""
        try:
            with self.config.filters_file.open() as f:
                self.filters = json.load(f)
            console.print(
                f"[green]Loaded {sum(len(f) for f in self.filters.values())} "
                f"filters from {len(self.filters)} categories[/green]"
            )
        except Exception as e:
            console.print(f"[red]Error loading filters: {e!s}[/red]")
            raise

    def validate_api_key(self) -> dict[str, Any]:
        """Validate Shodan API key and get account info.

        Returns:
            Account information from Shodan

        Raises:
            shodan.APIError: If API key is invalid
        """
        try:
            info = self.shodan_api.info()
            console.print("[green]✓[/green] Shodan API key validated")
            console.print(f"  Credits: {info.get('query_credits', 0)}")
            console.print(f"  Scan credits: {info.get('scan_credits', 0)}")
            return info
        except shodan.APIError as e:
            console.print(f"[red]✗[/red] Invalid Shodan API key: {e!s}")
            raise

    async def search_shodan(
        self,
        filters: list[str] | None = None,
        category: str | None = None,
    ) -> list[DiscoveredServer]:
        """Search Shodan for MCP servers.

        Args:
            filters: Specific filters to use (overrides category)
            category: Filter category to use (e.g., "core_protocol")

        Returns:
            List of discovered servers
        """
        search_filters: list[str] = []

        if filters:
            search_filters = filters
        elif category and category in self.filters:
            search_filters = self.filters[category]
        else:
            # Use all filters
            search_filters = [
                f for category_filters in self.filters.values() for f in category_filters
            ]

        console.print(f"[cyan]Searching Shodan with {len(search_filters)} filters...[/cyan]")

        discovered: dict[str, DiscoveredServer] = {}

        # Limit concurrent Shodan API calls (Shodan rate limits apply)
        semaphore = asyncio.Semaphore(5)  # 5 concurrent searches

        async def search_single_filter(search_filter: str, task_id: Any) -> None:
            """Search Shodan with a single filter."""
            async with semaphore:
                try:
                    # Run Shodan search in thread pool (it's blocking)
                    loop = asyncio.get_event_loop()
                    search_func = partial(
                        self.shodan_api.search,
                        search_filter,
                        limit=self.config.max_results_per_filter,
                    )
                    results = await loop.run_in_executor(None, search_func)

                    # Process results
                    for result in results.get("matches", []):
                        try:
                            shodan_result = ShodanResult.model_validate(result)
                            server_id = f"{shodan_result.ip_str}:{shodan_result.port}"

                            if server_id not in discovered:
                                discovered[server_id] = DiscoveredServer(
                                    ip=shodan_result.ip_str,
                                    port=shodan_result.port,
                                    hostnames=shodan_result.hostnames,
                                    domains=shodan_result.domains,
                                    shodan_data=result,
                                    search_filter=search_filter,
                                )

                        except Exception as e:
                            console.print(f"[yellow]Error parsing result: {e!s}[/yellow]")

                except shodan.APIError as e:
                    if "Invalid query" in str(e):
                        console.print(f"[yellow]Invalid filter: {search_filter}[/yellow]")
                    else:
                        console.print(f"[red]Shodan API error: {e!s}[/red]")
                except Exception as e:
                    console.print(f"[red]Error searching: {e!s}[/red]")
                finally:
                    prog.update(task_id, advance=1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as prog:
            task = prog.add_task(
                "[cyan]Searching...",
                total=len(search_filters),
            )

            # Run all searches concurrently
            await asyncio.gather(
                *[search_single_filter(f, task) for f in search_filters],
                return_exceptions=True,
            )

        console.print(
            f"[green]Found {len(discovered)} unique servers "
            f"from {len(search_filters)} filters[/green]"
        )
        return list(discovered.values())

    async def scan(
        self,
        filters: list[str] | None = None,
        category: str | None = None,
        discover_only: bool = False,
    ) -> ScanResult:
        """Perform complete scan: discover and verify servers.

        Args:
            filters: Specific filters to use
            category: Filter category to use
            discover_only: If True, only discover servers without verification

        Returns:
            Complete scan results
        """
        scan_id = uuid4().hex[:8]
        started_at = datetime.now(UTC)

        console.print(f"\n[bold cyan]Starting MCP scan {scan_id}[/bold cyan]\n")

        # Create output directory
        output_dir = (
            self.config.output_dir / f"scan_{scan_id}_{started_at.strftime('%Y%m%d_%H%M%S')}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        result = ScanResult(
            scan_id=scan_id,
            started_at=started_at,
        )

        try:
            # Load filters
            if not self.filters:
                self.load_filters()

            # Determine which filters to use
            if filters:
                result.filters_used = filters
            elif category and category in self.filters:
                result.filters_used = self.filters[category]
            else:
                result.filters_used = [
                    f for cat_filters in self.filters.values() for f in cat_filters
                ]

            # Search Shodan
            discovered = await self.search_shodan(filters=filters, category=category)
            result.discovered_servers = discovered
            result.total_shodan_results = len(discovered)

            if not discovered:
                console.print("[yellow]No servers discovered[/yellow]")
                return result

            # Save discovered servers immediately (checkpoint)
            await self._save_discovered_servers(discovered, output_dir)
            console.print(
                f"[green]✓ Saved {len(discovered)} discovered servers to "
                f"{output_dir / 'discovered_servers.json'}[/green]\n"
            )

            # Skip verification if discover_only mode
            if discover_only:
                console.print("[cyan]Discovery-only mode: skipping verification[/cyan]")
                return result

            # Verify servers
            console.print(f"\n[cyan]Verifying {len(discovered)} servers...[/cyan]\n")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
            ) as prog:
                task = prog.add_task(
                    "[cyan]Verifying...",
                    total=len(discovered),
                )

                # Create progress callback
                def update_progress() -> None:
                    prog.update(task, advance=1)

                verified = await self.verifier.verify_servers_batch(
                    discovered, progress_callback=update_progress
                )
                result.verified_servers = verified

            console.print(
                f"\n[green]✓ Verified {len(verified)} MCP servers "
                f"out of {len(discovered)} candidates[/green]\n"
            )

            # Save results
            await self._save_results(result, output_dir)

        except Exception as e:
            console.print(f"[red]Scan error: {e!s}[/red]")
            result.errors.append(str(e))
        finally:
            result.completed_at = datetime.now(UTC)
            await self.verifier.close()

        return result

    async def verify_from_file(self, discovery_file: Path) -> ScanResult:
        """Verify servers from a saved discovery file.

        Args:
            discovery_file: Path to discovered_servers.json file

        Returns:
            Scan results with verified servers
        """
        scan_id = uuid4().hex[:8]
        started_at = datetime.now(UTC)

        console.print(f"\n[bold cyan]Starting verification from {discovery_file}[/bold cyan]\n")

        # Load discovered servers
        with discovery_file.open() as f:
            data = json.load(f)
            discovered = [DiscoveredServer.model_validate(s) for s in data]

        console.print(f"[cyan]Loaded {len(discovered)} discovered servers[/cyan]\n")

        # Create output directory
        output_dir = (
            self.config.output_dir / f"verify_{scan_id}_{started_at.strftime('%Y%m%d_%H%M%S')}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        result = ScanResult(
            scan_id=scan_id,
            started_at=started_at,
            discovered_servers=discovered,
            total_shodan_results=len(discovered),
        )

        try:
            # Verify servers
            console.print(f"[cyan]Verifying {len(discovered)} servers...[/cyan]\n")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
            ) as prog:
                task = prog.add_task(
                    "[cyan]Verifying...",
                    total=len(discovered),
                )

                # Create progress callback
                def update_progress() -> None:
                    prog.update(task, advance=1)

                verified = await self.verifier.verify_servers_batch(
                    discovered, progress_callback=update_progress
                )
                result.verified_servers = verified

            console.print(
                f"\n[green]✓ Verified {len(verified)} MCP servers "
                f"out of {len(discovered)} candidates[/green]\n"
            )

            # Save results
            await self._save_results(result, output_dir)

        except Exception as e:
            console.print(f"[red]Verification error: {e!s}[/red]")
            result.errors.append(str(e))
        finally:
            result.completed_at = datetime.now(UTC)
            await self.verifier.close()

        return result

    async def _save_discovered_servers(
        self, servers: list[DiscoveredServer], output_dir: Path
    ) -> None:
        """Save discovered servers to JSON file.

        Args:
            servers: List of discovered servers
            output_dir: Output directory
        """
        discovered_file = output_dir / "discovered_servers.json"
        with discovered_file.open("w") as f:
            json.dump(
                [s.model_dump(mode="json") for s in servers],
                f,
                indent=2,
                default=str,
            )

    async def _save_results(self, result: ScanResult, output_dir: Path) -> None:
        """Save scan results to files.

        Args:
            result: Scan results
            output_dir: Output directory
        """
        # Save complete results as JSON
        results_file = output_dir / "results.json"
        with results_file.open("w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

        console.print(f"[green]Saved complete results to {results_file}[/green]")

        # Save verified servers as JSON
        if result.verified_servers:
            verified_file = output_dir / "verified_servers.json"
            with verified_file.open("w") as f:
                json.dump(
                    [s.model_dump(mode="json") for s in result.verified_servers],
                    f,
                    indent=2,
                    default=str,
                )

            # Save as CSV
            csv_file = output_dir / "verified_servers.csv"
            with csv_file.open("w") as f:
                f.write(
                    "URL,IP,Port,Transport,Protocol Version,Server Name,"
                    "Tools Count,Response Time (ms),SSL Enabled\n"
                )
                for server in result.verified_servers:
                    server_name = server.server_info.get("name", "Unknown")
                    f.write(
                        f"{server.url},{server.ip},{server.port},"
                        f"{server.transport_type.value},"
                        f"{server.protocol_version or 'N/A'},"
                        f"{server_name},{len(server.tools)},"
                        f"{server.response_time_ms or 0:.2f},"
                        f"{server.ssl_enabled}\n"
                    )

            console.print(f"[green]Saved verified servers to {verified_file}[/green]")
            console.print(f"[green]Saved CSV to {csv_file}[/green]")

        # Save summary
        summary_file = output_dir / "summary.txt"
        with summary_file.open("w") as f:
            f.write(f"MCP Scan Summary - {result.scan_id}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Started: {result.started_at}\n")
            f.write(f"Completed: {result.completed_at}\n")
            f.write(f"Duration: {result.completed_at - result.started_at}\n\n")
            f.write(f"Filters used: {len(result.filters_used)}\n")
            f.write(f"Servers discovered: {result.total_shodan_results}\n")
            f.write(f"Servers verified: {len(result.verified_servers)}\n\n")

            if result.verified_servers:
                f.write("Verified Servers:\n")
                f.write("-" * 80 + "\n")
                for server in result.verified_servers:
                    f.write(f"\nURL: {server.url}\n")
                    f.write(f"  IP: {server.ip}:{server.port}\n")
                    f.write(f"  Transport: {server.transport_type.value}\n")
                    f.write(f"  Protocol: {server.protocol_version or 'N/A'}\n")
                    f.write(f"  Server: {server.server_info.get('name', 'Unknown')}\n")
                    f.write(f"  Tools: {len(server.tools)}\n")
                    if server.tools:
                        for tool in server.tools:
                            f.write(f"    - {tool.name}: {tool.description or 'No description'}\n")

        console.print(f"[green]Saved summary to {summary_file}[/green]")
