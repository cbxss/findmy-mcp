# FindMyMCP

> Fast, concurrent MCP server discovery and analysis tool for security research

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Built with uv](https://img.shields.io/badge/built%20with-uv-green.svg)](https://github.com/astral-sh/uv)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://github.com/astral-sh/ruff)

## Overview

FindMyMCP is a sophisticated security research tool that discovers and analyzes publicly exposed Model Context Protocol (MCP) servers using the Shodan API. Built with modern Python practices, it features concurrent scanning, checkpoint-based workflows, and comprehensive server verification.

## Features

- **⚡ Fast Concurrent Discovery**: Runs Shodan searches in parallel (5x faster than sequential)
- **💾 Checkpoint System**: Save discovered servers immediately, verify later
- **🔀 Two-Step Workflow**: Separate discovery and verification phases
- **🔍 Comprehensive Discovery**: Uses 100+ Shodan search filters across 10 categories
- **🌐 Multi-Transport Support**: Tests both HTTP and Server-Sent Events (SSE) protocols
- **✅ Protocol Verification**: Validates actual MCP protocol compliance
- **🛠️ Tool Enumeration**: Identifies available tools and capabilities
- **📊 Detailed Reporting**: Generates JSON, CSV, and text summary reports
- **⚙️ Concurrent Verification**: Configurable concurrent verification with rate limiting
- **🎨 Rich Terminal UI**: Beautiful progress tracking and output

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/findmy-mcp.git
cd findmy-mcp

# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Using pip

```bash
pip install -e .
```

## Quick Start

### 1. Set up your Shodan API key

```bash
export MCP_SCANNER_SHODAN_API_KEY="your-api-key-here"
```

Or create a `.env` file:

```env
MCP_SCANNER_SHODAN_API_KEY=your-api-key-here
```

### 2. Run a basic scan

```bash
# Full scan with all filters
mcp-scan scan

# Scan specific category
mcp-scan scan --category core_protocol

# Scan with custom filters
mcp-scan scan --filter '"Model Context Protocol"' --filter 'mcp server'
```

## Two-Step Workflow (Recommended)

For large scans, use the two-step workflow to maximize efficiency:

### Step 1: Discovery (Fast)

```bash
# Discover servers with concurrent API calls
mcp-scan scan --discover-only

# Output: scan_results/scan_xxx_timestamp/discovered_servers.json
```

This runs in ~20-30 seconds for 60+ filters instead of 2+ minutes!

### Step 2: Verification (Can Run Multiple Times)

```bash
# Verify from checkpoint
mcp-scan verify scan_results/scan_xxx_timestamp/discovered_servers.json

# With custom settings (max speed)
mcp-scan verify discovered_servers.json --concurrency 100 --timeout 2.0
```

### Why This Workflow?

- ✅ **5x faster discovery** - Concurrent Shodan API calls
- ✅ **Immediate checkpoints** - See results right after discovery
- ✅ **Resumable** - Interrupt and restart verification without re-scanning
- ✅ **Review first** - Check discovered servers before verification
- ✅ **Reusable** - Run verification multiple times with different settings

## Commands

### `scan` - Discover and/or verify servers

```bash
# Full scan
mcp-scan scan

# Discovery only
mcp-scan scan --discover-only

# Specific category
mcp-scan scan --category transport_sse

# Custom concurrency and timeout
mcp-scan scan --concurrency 100 --timeout 2.0
```

### `verify` - Verify from checkpoint

```bash
# Basic verification
mcp-scan verify scan_results/scan_xxx/discovered_servers.json

# With custom settings (even faster)
mcp-scan verify discovered.json --concurrency 100 --timeout 2.0
```

### `list-filters` - Show available filter categories

```bash
mcp-scan list-filters
```

## Configuration

All settings can be configured via environment variables with the `MCP_SCANNER_` prefix:

```env
MCP_SCANNER_SHODAN_API_KEY=your-key
MCP_SCANNER_MAX_RESULTS_PER_FILTER=100
MCP_SCANNER_MAX_CONCURRENT_VERIFICATIONS=10
MCP_SCANNER_VERIFICATION_TIMEOUT=10.0
MCP_SCANNER_OUTPUT_DIR=scan_results
```

See `.env.example` for all available options.

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `shodan_api_key` | Required | Shodan API key |
| `max_results_per_filter` | 100 | Maximum Shodan results per filter |
| `max_concurrent_verifications` | 50 | Maximum concurrent server verifications |
| `verification_timeout` | 3.0 | Timeout for verification in seconds |
| `output_dir` | `scan_results` | Output directory for results |
| `verify_ssl` | `true` | Verify SSL certificates |

## Output Files

Each scan creates a timestamped directory with:

- **`discovered_servers.json`** - All servers found via Shodan (checkpoint)
- **`verified_servers.json`** - Verified MCP servers with full details
- **`verified_servers.csv`** - CSV format for easy analysis
- **`results.json`** - Complete scan metadata
- **`summary.txt`** - Human-readable summary

## Shodan Filter Categories

FindMyMCP uses 100+ Shodan search filters across 10 categories:

| Category | Filters | Description |
|----------|---------|-------------|
| **core_protocol** | 8 | Direct MCP protocol markers |
| **transport_sse** | 5 | Server-Sent Events indicators |
| **jsonrpc_methods** | 6 | JSON-RPC method calls |
| **endpoints** | 9 | Common MCP endpoint paths |
| **frameworks** | 7 | Known MCP frameworks |
| **ports_combined** | 8 | Port-specific searches |
| **cloud_platforms** | 6 | Cloud provider deployments |
| **capabilities** | 5 | MCP capability markers |
| **http_headers** | 4 | MCP-specific HTTP headers |
| **security_markers** | 5 | Authentication/authorization markers |

## Programmatic Usage

```python
import asyncio
from pathlib import Path
from findmy_mcp import MCPScanner, ScannerConfig

async def main():
    # Create configuration
    config = ScannerConfig(
        shodan_api_key="your-api-key",
        max_results_per_filter=50,
        max_concurrent_verifications=20,
    )

    # Create scanner
    scanner = MCPScanner(config)

    # Validate API key
    scanner.validate_api_key()

    # Load filters
    scanner.load_filters()

    # Discover only
    result = await scanner.scan(category="core_protocol", discover_only=True)
    print(f"Discovered {len(result.discovered_servers)} servers")

    # Later, verify from file
    discovery_file = Path("scan_results/scan_xxx/discovered_servers.json")
    result = await scanner.verify_from_file(discovery_file)
    print(f"Verified {len(result.verified_servers)} MCP servers")

if __name__ == "__main__":
    asyncio.run(main())
```

## Development

### Setup

```bash
# Install with dev dependencies
uv sync --extra dev
```

### Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=findmy_mcp --cov-report=html

# Run specific test
uv run pytest tests/test_models.py -v
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src
```

## Architecture

Built with modern Python practices:

- **Type Safety**: Comprehensive type hints with mypy strict mode
- **Async First**: Proper async/await patterns throughout
- **Pydantic Models**: Validated data models for all entities
- **Concurrent Design**: Parallel Shodan searches and URL verification
- **Modular Structure**: Clean separation of concerns

### Project Structure

```
findmy-mcp/
├── src/findmy_mcp/
│   ├── __init__.py       # Package exports
│   ├── cli.py            # Typer-based CLI
│   ├── config.py         # Pydantic Settings
│   ├── models.py         # Data models
│   ├── scanner.py        # Main scanning logic
│   ├── verifier.py       # MCP verification
│   └── filters.json      # Shodan filters
├── tests/                # Test suite
├── examples/             # Example scripts
└── pyproject.toml        # Project config
```

## Legal & Ethical Use

**⚠️ IMPORTANT**: This tool is intended for:

- ✅ Legitimate security research
- ✅ Authorized penetration testing
- ✅ Educational purposes
- ✅ Identifying misconfigured infrastructure you own

**NOT for**:

- ❌ Unauthorized access to systems
- ❌ Malicious activities
- ❌ Violation of terms of service
- ❌ Any illegal activities

Always obtain proper authorization before scanning systems you don't own.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Support

- 📝 Report issues: [GitHub Issues](https://github.com/yourusername/findmy-mcp/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/findmy-mcp/discussions)
- 📖 Documentation: This README and inline code documentation

---

**Built with**: Python 3.12+ • uv • Typer • Rich • Pydantic • httpx • Shodan
