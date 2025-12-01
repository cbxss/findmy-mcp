"""Pydantic models for FindMyMCP scanner."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """MCP transport types."""

    HTTP = "http"
    SSE = "sse"
    STDIO = "stdio"


class MCPCapability(BaseModel):
    """MCP server capability."""

    experimental: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")


class MCPInitializeResponse(BaseModel):
    """MCP initialize response."""

    protocol_version: str = Field(alias="protocolVersion")
    capabilities: MCPCapability
    server_info: dict[str, str] = Field(alias="serverInfo")


class ShodanResult(BaseModel):
    """Shodan search result."""

    ip_str: str
    port: int
    hostnames: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    transport: str | None = None
    product: str | None = None
    version: str | None = None
    data: str | None = None
    http: dict[str, Any] | None = None
    ssl: dict[str, Any] | None = None
    location: dict[str, Any] | None = None
    org: str | None = None
    isp: str | None = None
    asn: str | None = None


class DiscoveredServer(BaseModel):
    """A server discovered via Shodan."""

    ip: str
    port: int
    hostnames: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    shodan_data: dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    search_filter: str | None = None


class VerifiedServer(BaseModel):
    """A verified MCP server."""

    url: str
    ip: str
    port: int
    hostnames: list[str] = Field(default_factory=list)
    transport_type: TransportType
    protocol_version: str | None = None
    server_info: dict[str, str] = Field(default_factory=dict)
    capabilities: MCPCapability | None = None
    tools: list[MCPTool] = Field(default_factory=list)
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    response_time_ms: float | None = None
    ssl_enabled: bool = False
    error: str | None = None


class ScanResult(BaseModel):
    """Complete scan results."""

    scan_id: str
    started_at: datetime
    completed_at: datetime | None = None
    total_shodan_results: int = 0
    discovered_servers: list[DiscoveredServer] = Field(default_factory=list)
    verified_servers: list[VerifiedServer] = Field(default_factory=list)
    filters_used: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
