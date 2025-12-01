"""Example of using custom Shodan filters."""

import asyncio

from findmy_mcp import MCPScanner, ScannerConfig


async def main() -> None:
    """Run scan with custom filters."""
    # Create configuration
    config = ScannerConfig(
        max_results_per_filter=100,
        max_concurrent_verifications=20,
    )

    # Create scanner
    scanner = MCPScanner(config)

    # Validate API key
    scanner.validate_api_key()

    # Define custom filters focused on specific ports and protocols
    custom_filters = [
        '"Model Context Protocol"',
        '"jsonrpc": "2.0" mcp',
        "port:3000 jsonrpc",
        "port:8000 text/event-stream",
        '"FastMCP"',
        '"@modelcontextprotocol"',
    ]

    print(f"Using {len(custom_filters)} custom filters")

    # Run scan with custom filters
    result = await scanner.scan(filters=custom_filters)

    # Display summary
    print("\nScan completed!")
    print(f"  Discovered: {result.total_shodan_results} servers")
    print(f"  Verified: {len(result.verified_servers)} MCP servers")

    # Group by transport type
    if result.verified_servers:
        http_servers = [s for s in result.verified_servers if s.transport_type.value == "http"]
        sse_servers = [s for s in result.verified_servers if s.transport_type.value == "sse"]

        print("\nTransport breakdown:")
        print(f"  HTTP: {len(http_servers)}")
        print(f"  SSE: {len(sse_servers)}")

        # Show servers with most tools
        servers_with_tools = sorted(
            result.verified_servers,
            key=lambda s: len(s.tools),
            reverse=True,
        )[:5]

        if servers_with_tools:
            print("\nTop 5 servers by tool count:")
            for i, server in enumerate(servers_with_tools, 1):
                print(f"  {i}. {server.url} - {len(server.tools)} tools")


if __name__ == "__main__":
    asyncio.run(main())
