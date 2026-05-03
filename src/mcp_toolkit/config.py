from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    transport: str = "stdio"
    auth: str = "none"
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    sarmalink_base_url: str = "https://api.sarmalink.ai/v1"
    sarmalink_api_key: str = ""

    otel_endpoint: str = ""

    class Config:
        env_prefix = "MCP_"
        env_file = ".env"
