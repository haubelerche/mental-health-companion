from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Serene API"
    app_version: str = "1.0.0"
    api_prefix: str = "/v1"

    database_url: str = Field(default="")
    auto_create_schema: bool = False

    access_token_ttl_seconds: int = 3600
    refresh_token_ttl_days: int = 30
    admin_token_ttl_seconds: int = 900

    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"

    cookie_secure: bool = False
    cookie_domain: str | None = None

    admin_allowed_ips: str = ""

    redis_url: str = "redis://localhost:6379/0"
    auth_rate_limit_per_minute: int = 5
    chat_rate_limit_per_minute: int = 30
    auth_lockout_threshold: int = 5
    auth_lockout_minutes: int = 15

    def normalized_database_url(self) -> str:
        raw = self.database_url.strip()
        if not raw:
            raise ValueError("DATABASE_URL is required")
        if raw.startswith("postgresql://"):
            raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
        parsed = urlparse(raw)
        if "supabase.com" not in parsed.netloc:
            return raw

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.setdefault("sslmode", "require")
        return urlunparse(parsed._replace(query=urlencode(query)))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
