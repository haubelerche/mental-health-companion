from functools import lru_cache
from pathlib import Path
from typing import Self
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]  # backend/app/core -> repo root


def _aura_instance_from_uri(uri: str) -> str | None:
    if "databases.neo4j.io" not in uri:
        return None
    try:
        rest = uri.split("://", 1)[1]
        host = rest.split("/", 1)[0].split(":", 1)[0]
        return host.split(".", 1)[0]
    except (IndexError, ValueError):
        return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    cookie_secure: bool = True
    cookie_domain: str | None = None
    csrf_trusted_origins: str = ""

    admin_allowed_ips: str = ""
    admin_login_email: str = ""
    admin_password_hash: str = ""
    admin_totp_secret: str = ""

    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    openai_model_analyst: str = "gpt-4o-mini"
    openai_model_friend: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 10.0

    distress_voice_hint: float = 0.8
    distress_critical: float = 0.9
    proactive_voice_threshold: float = 0.9
    proactive_voice_delta_threshold: float = 0.3
    proactive_voice_cooldown_seconds: int = 120
    proactive_voice_window_turns: int = 6
    voice_tts_auto_process_on_enqueue: bool = True

    profile_cache_ttl_seconds: int = 30

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "iSFxP4Z6YNcx9OXl62Ic"
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"
    trusted_contact_outbound_enabled: bool = False

    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    @model_validator(mode="after")
    def _aura_neo4j_defaults(self) -> Self:
        """Aura Bolt user and default DB are *neo4j*, not the hostname instance id."""
        uri = (self.neo4j_uri or "").strip()
        inst = _aura_instance_from_uri(uri)
        if not inst:
            return self
        updates: dict[str, str] = {}
        if self.neo4j_user == inst:
            updates["neo4j_user"] = "neo4j"
        if self.neo4j_database == inst:
            updates["neo4j_database"] = "neo4j"
        if updates:
            return self.model_copy(update=updates)
        return self
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
