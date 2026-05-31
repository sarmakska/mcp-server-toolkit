"""Runtime configuration, populated from the environment with the MCP_ prefix."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Transport
    transport: str = "stdio"
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    # Auth: none | api_key | oauth
    auth: str = "none"
    api_key: str = ""
    oauth_issuer: str = ""
    oauth_audience: str = ""
    oauth_jwks_uri: str = ""

    # Per-client rate limiting (HTTP transport). 0 disables it.
    rate_limit_rps: float = 0.0
    rate_limit_burst: int = 0

    # OAuth client flow (mcp-toolkit login)
    oauth_client_id: str = ""
    oauth_redirect_uri: str = "http://127.0.0.1:8765/callback"
    oauth_scope: str = "openid profile"

    # SarmaLink-AI plugin
    sarmalink_base_url: str = "https://api.sarmalink.ai/v1"
    sarmalink_api_key: str = ""

    # Observability
    otel_endpoint: str = ""
    service_name: str = "mcp-server-toolkit"

    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env", extra="ignore")
