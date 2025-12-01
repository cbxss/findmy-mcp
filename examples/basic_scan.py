"""Basic MCP Scanner example."""

import asyncio

from findmy_mcp import MCPScanner, ScannerConfig


async def main() -> None:
    """Run a basic MCP scan."""
    # Create configuration
    # Note: SHODAN_API_KEY should be set in environment or .env file
    config = ScannerConfig(
        max_results_per_filter=50,
        max_concurrent_verifications=15,
        verification_timeout=10.0,
    )

    # Create scanner
    scanner = MCPScanner(config)

    # Validate API key and check credits
    info = scanner.validate_api_key()
    print(f"Shodan credits: {info.get('query_credits', 0)}")

    # Load filters
    scanner.load_filters()

    # Run scan on core protocol filters only
    print("\nStarting scan with core_protocol filters...")
    result = await scanner.scan(category="core_protocol")

    # Display results
    print(f"\n{'='*80}")
    print(f"Scan Results - {result.scan_id}")
    print(f"{'='*80}")
    print(f"Discovered servers: {result.total_shodan_results}")
    print(f"Verified MCP servers: {len(result.verified_servers)}")

    if result.verified_servers:
        print(f"\n{'='*80}")
        print("Verified Servers:")
        print(f"{'='*80}")

        for server in result.verified_servers:
            print(f"\nURL: {server.url}")
            print(f"  Transport: {server.transport_type.value}")
            print(f"  Protocol: {server.protocol_version or 'Unknown'}")
            print(f"  Server: {server.server_info.get('name', 'Unknown')}")
            print(f"  Tools: {len(server.tools)}")

            if server.tools:
                print("  Available tools:")
                for tool in server.tools[:5]:  # Show first 5 tools
                    desc = tool.description or "No description"
                    print(f"    - {tool.name}: {desc[:60]}")

                if len(server.tools) > 5:
                    print(f"    ... and {len(server.tools) - 5} more tools")


if __name__ == "__main__":
    asyncio.run(main())
