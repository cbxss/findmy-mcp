"""Configuration management for FindMyMCP scanner."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScannerConfig(BaseSettings):
    """FindMyMCP Scanner configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_SCANNER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Shodan API settings
    shodan_api_key: str = Field(
        description="Shodan API key for server discovery",
    )

    # Scan settings
    max_results_per_filter: int = Field(
        default=100,
        description="Maximum Shodan results per filter",
        ge=1,
        le=1000,
    )

    max_concurrent_verifications: int = Field(
        default=50,
        description="Maximum concurrent server verifications",
        ge=1,
        le=200,
    )

    verification_timeout: float = Field(
        default=3.0,
        description="Timeout for server verification in seconds",
        ge=0.5,
        le=60.0,
    )

    # Output settings
    output_dir: Path = Field(
        default=Path("scan_results"),
        description="Directory for scan results",
    )

    # Network settings
    user_agent: str = Field(
        default="FindMyMCP/1.0 (Security Research)",
        description="User agent for HTTP requests",
    )

    # Filter settings
    filters_file: Path = Field(
        default=Path(__file__).parent / "filters.json",
        description="Path to Shodan filters JSON file",
    )

    # Advanced options
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates",
    )

    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects",
    )

    max_redirects: int = Field(
        default=5,
        description="Maximum number of redirects to follow",
        ge=0,
        le=20,
    )
