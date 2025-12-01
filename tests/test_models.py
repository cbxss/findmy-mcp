"""Tests for Pydantic models."""

from datetime import datetime

from findmy_mcp.models import (
    DiscoveredServer,
    MCPTool,
    TransportType,
    VerifiedServer,
)


def test_transport_type_enum():
    """Test TransportType enum."""
    assert TransportType.HTTP == "http"
    assert TransportType.SSE == "sse"
    assert TransportType.STDIO == "stdio"


def test_mcp_tool_creation():
    """Test MCPTool model creation."""
    tool = MCPTool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object"},
    )

    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.input_schema == {"type": "object"}


def test_discovered_server_creation():
    """Test DiscoveredServer model creation."""
    server = DiscoveredServer(
        ip="192.168.1.1",
        port=8000,
        hostnames=["example.com"],
        domains=["example.com"],
    )

    assert server.ip == "192.168.1.1"
    assert server.port == 8000
    assert server.hostnames == ["example.com"]
    assert isinstance(server.discovered_at, datetime)


def test_verified_server_creation():
    """Test VerifiedServer model creation."""
    server = VerifiedServer(
        url="http://example.com:8000/mcp",
        ip="192.168.1.1",
        port=8000,
        transport_type=TransportType.HTTP,
        protocol_version="2024-11-05",
        server_info={"name": "test-server", "version": "1.0.0"},
    )

    assert server.url == "http://example.com:8000/mcp"
    assert server.transport_type == TransportType.HTTP
    assert server.protocol_version == "2024-11-05"
    assert server.server_info["name"] == "test-server"


def test_verified_server_with_tools():
    """Test VerifiedServer with tools."""
    tools = [
        MCPTool(name="tool1", description="Tool 1", inputSchema={}),
        MCPTool(name="tool2", description="Tool 2", inputSchema={}),
    ]

    server = VerifiedServer(
        url="http://example.com:8000/mcp",
        ip="192.168.1.1",
        port=8000,
        transport_type=TransportType.HTTP,
        tools=tools,
    )

    assert len(server.tools) == 2
    assert server.tools[0].name == "tool1"
    assert server.tools[1].name == "tool2"
