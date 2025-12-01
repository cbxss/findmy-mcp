"""MCP server verification and validation."""

import asyncio
import json
import time
from typing import Any

import httpx
from rich.console import Console

from findmy_mcp.config import ScannerConfig
from findmy_mcp.models import (
    DiscoveredServer,
    MCPInitializeResponse,
    MCPTool,
    TransportType,
    VerifiedServer,
)

console = Console()


class MCPVerifier:
    """Verifies and validates MCP servers."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize verifier.

        Args:
            config: Scanner configuration
        """
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=config.verification_timeout,
            follow_redirects=config.follow_redirects,
            max_redirects=config.max_redirects,
            verify=config.verify_ssl,
            headers={"User-Agent": config.user_agent},
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    def _construct_candidate_urls(self, server: DiscoveredServer) -> list[str]:
        """Construct candidate MCP endpoint URLs.

        Args:
            server: Discovered server

        Returns:
            List of candidate URLs to test
        """
        urls: list[str] = []
        protocols = ["https", "http"]
        paths = [
            "/mcp",
            "/sse",
            "/messages",
            "/v1/mcp",
            "/api/mcp",
            "/mcp/sse",
            "/mcp/messages",
            "/rpc",
            "/jsonrpc",
            "",  # Try root
        ]

        # Use hostnames if available, otherwise use IP
        hosts = server.hostnames if server.hostnames else [server.ip]

        for protocol in protocols:
            for host in hosts:
                for path in paths:
                    url = f"{protocol}://{host}:{server.port}{path}"
                    urls.append(url)

        return urls

    async def _test_sse_endpoint(self, url: str) -> dict[str, Any] | None:
        """Test if endpoint supports SSE transport.

        Args:
            url: URL to test

        Returns:
            Server response if SSE is detected, None otherwise
        """
        try:
            response = await self.client.get(
                url,
                headers={"Accept": "text/event-stream"},
            )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "").lower()
                if "text/event-stream" in content_type:
                    return {
                        "transport": "sse",
                        "content": response.text[:1000],
                        "headers": dict(response.headers),
                    }
        except Exception:
            pass

        return None

    async def _test_jsonrpc_endpoint(self, url: str) -> dict[str, Any] | None:
        """Test if endpoint supports JSON-RPC (HTTP transport).

        Args:
            url: URL to test

        Returns:
            Server response if JSON-RPC is detected, None otherwise
        """
        # MCP initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-scanner",
                    "version": "2.0.0",
                },
            },
            "id": 1,
        }

        try:
            response = await self.client.post(
                url,
                json=initialize_request,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if it's a valid JSON-RPC response
                    if "jsonrpc" in data and ("result" in data or "error" in data):
                        return {
                            "transport": "http",
                            "response": data,
                            "headers": dict(response.headers),
                        }
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        return None

    async def verify_server(
        self,
        server: DiscoveredServer,
    ) -> VerifiedServer | None:
        """Verify if a discovered server is a valid MCP server.

        Args:
            server: Discovered server to verify

        Returns:
            Verified server if valid MCP server, None otherwise
        """
        candidate_urls = self._construct_candidate_urls(server)

        # Try URLs concurrently and return first successful match
        async def try_url(url: str) -> VerifiedServer | None:
            try:
                start_time = time.perf_counter()

                # Try SSE first
                sse_result = await self._test_sse_endpoint(url)
                if sse_result:
                    response_time = (time.perf_counter() - start_time) * 1000
                    return self._create_verified_server(
                        server=server,
                        url=url,
                        transport=TransportType.SSE,
                        response_time=response_time,
                        result=sse_result,
                    )

                # Try JSON-RPC
                jsonrpc_result = await self._test_jsonrpc_endpoint(url)
                if jsonrpc_result:
                    response_time = (time.perf_counter() - start_time) * 1000
                    return await self._process_jsonrpc_response(
                        server=server,
                        url=url,
                        response_time=response_time,
                        result=jsonrpc_result,
                    )
            except Exception:
                # Silently fail - most URLs will fail
                pass

            return None

        # Try all URLs concurrently
        tasks = [try_url(url) for url in candidate_urls]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                # Found a valid server, return immediately
                return result

        return None

    def _create_verified_server(
        self,
        server: DiscoveredServer,
        url: str,
        transport: TransportType,
        response_time: float,
        _result: dict[str, Any],
    ) -> VerifiedServer:
        """Create a verified server object.

        Args:
            server: Original discovered server
            url: Verified URL
            transport: Transport type
            response_time: Response time in milliseconds
            _result: Verification result (reserved for future use)

        Returns:
            Verified server object
        """
        return VerifiedServer(
            url=url,
            ip=server.ip,
            port=server.port,
            hostnames=server.hostnames,
            transport_type=transport,
            response_time_ms=response_time,
            ssl_enabled=url.startswith("https"),
        )

    async def _process_jsonrpc_response(
        self,
        server: DiscoveredServer,
        url: str,
        response_time: float,
        result: dict[str, Any],
    ) -> VerifiedServer | None:
        """Process JSON-RPC response and extract MCP information.

        Args:
            server: Original discovered server
            url: Verified URL
            response_time: Response time in milliseconds
            result: JSON-RPC result

        Returns:
            Verified server with MCP details
        """
        try:
            response_data = result.get("response", {})

            if "error" in response_data:
                return None

            if "result" not in response_data:
                return None

            # Parse MCP initialize response
            init_response = MCPInitializeResponse.model_validate(response_data["result"])

            verified = VerifiedServer(
                url=url,
                ip=server.ip,
                port=server.port,
                hostnames=server.hostnames,
                transport_type=TransportType.HTTP,
                protocol_version=init_response.protocol_version,
                server_info=init_response.server_info,
                capabilities=init_response.capabilities,
                response_time_ms=response_time,
                ssl_enabled=url.startswith("https"),
            )

            # Get tools if server supports them
            if init_response.capabilities.tools:
                tools = await self._list_tools(url)
                verified.tools = tools

            return verified

        except Exception as e:
            console.print(f"[yellow]Error processing response from {url}: {e!s}[/yellow]")
            return None

    async def _list_tools(self, url: str) -> list[MCPTool]:
        """List available tools from MCP server.

        Args:
            url: Server URL

        Returns:
            List of available tools
        """
        list_tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2,
        }

        try:
            response = await self.client.post(
                url,
                json=list_tools_request,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                if "result" in data and "tools" in data["result"]:
                    return [MCPTool.model_validate(tool) for tool in data["result"]["tools"]]
        except Exception:
            pass

        return []

    async def verify_servers_batch(
        self,
        servers: list[DiscoveredServer],
        progress_callback: Any = None,
    ) -> list[VerifiedServer]:
        """Verify multiple servers concurrently.

        Args:
            servers: List of discovered servers
            progress_callback: Optional callback to report progress (task_id)

        Returns:
            List of verified servers
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrent_verifications)
        verified = []
        verified_lock = asyncio.Lock()

        async def verify_with_semaphore(srv: DiscoveredServer) -> None:
            async with semaphore:
                try:
                    result = await self.verify_server(srv)
                    if result:
                        async with verified_lock:
                            verified.append(result)
                except Exception:
                    # Silently fail - most servers won't be MCP servers
                    pass
                finally:
                    # Update progress after each verification
                    if progress_callback:
                        progress_callback()

        await asyncio.gather(
            *[verify_with_semaphore(server) for server in servers],
            return_exceptions=True,
        )

        return verified
