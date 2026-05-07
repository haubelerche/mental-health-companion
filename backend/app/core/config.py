from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import AliasChoices, Field, model_validator
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
        # Docker / IDE thường export JWT_*="" — mặc định pydantic ưu tiên env và ghi đè .env → khóa rỗng.
        env_ignore_empty=True,
    )

    app_name: str = "Serene API"
    app_version: str = "1.0.0"
    api_prefix: str = "/v1"

    database_url: str = Field(default="")
    auto_create_schema: bool = False
    db_pool_size: int = Field(default=4, validation_alias=AliasChoices("DB_POOL_SIZE"))
    db_max_overflow: int = Field(default=2, validation_alias=AliasChoices("DB_MAX_OVERFLOW"))
    db_pool_timeout_seconds: int = Field(default=30, validation_alias=AliasChoices("DB_POOL_TIMEOUT_SECONDS"))
    db_pool_recycle_seconds: int = Field(default=1800, validation_alias=AliasChoices("DB_POOL_RECYCLE_SECONDS"))
    db_pool_pre_ping: bool = Field(default=True, validation_alias=AliasChoices("DB_POOL_PRE_PING"))

    access_token_ttl_seconds: int = 3600
    refresh_token_ttl_days: int = 30
    admin_token_ttl_seconds: int = 900

    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    """Khi không dùng RS256: đặt chuỗi bí mật >= 16 ký tự; API ký JWT bằng HS256 (chỉ nên dùng local)."""
    jwt_dev_secret: str = ""

    cookie_secure: bool = False
    cookie_domain: str | None = None
    csrf_trusted_origins: str = ""

    admin_allowed_ips: str = ""
    admin_login_email: str = ""
    admin_password_hash: str = ""
    admin_totp_secret: str = ""

    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    youtube_api_key: str = Field(default="", validation_alias=AliasChoices("YOUTUBE_API_KEY"))
    openai_model_analyst: str = "gpt-4o-mini"
    openai_model_friend: str = "gpt-4o-mini"
    openai_model_friend_fast: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 10.0
    chat_response_cache_ttl_seconds: int = 45

    distress_voice_hint: float = 0.78
    distress_critical: float = 0.88
    proactive_voice_threshold: float = 0.84
    proactive_voice_delta_threshold: float = 0.22
    proactive_voice_cooldown_seconds: int = 120
    proactive_voice_window_turns: int = 6
    proactive_voice_auto_distress_threshold: float = Field(
        default=0.8,
        validation_alias=AliasChoices("PROACTIVE_VOICE_AUTO_DISTRESS_THRESHOLD"),
    )
    voice_tts_auto_process_on_enqueue: bool = True

    profile_cache_ttl_seconds: int = 30

    tts_timeout_seconds: float = Field(default=4.0, validation_alias=AliasChoices("TTS_TIMEOUT_SECONDS"))
    # elevenlabs | auto (auto currently aliases to elevenlabs-only mode)
    tts_provider: str = Field(default="elevenlabs", validation_alias=AliasChoices("TTS_PROVIDER"))

    # ElevenLabs TTS (optional second provider)
    elevenlabs_feature_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("ELEVENLABS_FEATURE_ENABLED"),
    )
    elevenlabs_api_key: str = Field(default="", validation_alias=AliasChoices("ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str = Field(
        default="iSFxP4Z6YNcx9OXl62Ic",
        validation_alias=AliasChoices("ELEVENLABS_VOICE_ID"),
    )
    elevenlabs_model_id: str = Field(
        default="eleven_multilingual_v2",
        validation_alias=AliasChoices("ELEVENLABS_MODEL_ID"),
    )
    elevenlabs_output_format: str = Field(
        default="mp3_44100_128",
        validation_alias=AliasChoices("ELEVENLABS_OUTPUT_FORMAT"),
    )
    elevenlabs_timeout_seconds: float = Field(
        default=9.0,
        validation_alias=AliasChoices("ELEVENLABS_TIMEOUT_SECONDS"),
    )
    elevenlabs_max_chars_per_job: int = Field(
        default=520,
        validation_alias=AliasChoices("ELEVENLABS_MAX_CHARS_PER_JOB"),
    )
    elevenlabs_use_only_on_tier: str = Field(
        default="voice_recommended,critical",
        validation_alias=AliasChoices("ELEVENLABS_USE_ONLY_ON_TIER"),
    )
    elevenlabs_min_distress: float = Field(
        default=0.8,
        validation_alias=AliasChoices("ELEVENLABS_MIN_DISTRESS"),
    )
    elevenlabs_max_chars_per_user_per_day: int = Field(
        default=12000,
        validation_alias=AliasChoices("ELEVENLABS_MAX_CHARS_PER_USER_PER_DAY"),
    )

    trusted_contact_outbound_enabled: bool = False

    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # Langfuse LLM observability (optional — leave blank to disable)
    langfuse_public_key: str = Field(default="", validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY"))
    langfuse_secret_key: str = Field(default="", validation_alias=AliasChoices("LANGFUSE_SECRET_KEY"))
    langfuse_host: str = Field(default="https://cloud.langfuse.com", validation_alias=AliasChoices("LANGFUSE_HOST"))

    @model_validator(mode="after")
    def _aura_neo4j_defaults(self) -> "Settings":
        """Aura Bolt user and default DB are *neo4j*, not the hostname instance id."""
        uri = (self.neo4j_uri or "").strip()
        inst = _aura_instance_from_uri(uri)
        if not inst:
            return self
        if self.neo4j_user == inst:
            self.neo4j_user = "neo4j"
        if self.neo4j_database == inst:
            self.neo4j_database = "neo4j"
        return self

    @model_validator(mode="after")
    def _local_database_defaults(self) -> "Settings":
        """Không có DATABASE_URL → SQLite file trong cwd (thường là `backend/`) + tạo bảng tự động."""
        if (self.database_url or "").strip():
            return self
        self.database_url = "sqlite:///./serene_local.db"
        self.auto_create_schema = True
        return self

    auth_rate_limit_per_minute: int = 5
    chat_rate_limit_per_minute: int = 30
    auth_lockout_threshold: int = 5
    auth_lockout_minutes: int = 15
    bcrypt_rounds: int = Field(default=12, validation_alias=AliasChoices("BCRYPT_ROUNDS"))

    auth_email_verify_ttl_minutes: int = 30
    auth_password_reset_ttl_minutes: int = 30
    auth_email_resend_cooldown_seconds: int = 60
    auth_allow_signup_without_smtp: bool = True

    google_client_id: str = Field(default="", validation_alias=AliasChoices("GOOGLE_CLIENT_ID"))
    google_client_secret: str = Field(default="", validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET"))
    google_redirect_uri: str = Field(default="", validation_alias=AliasChoices("GOOGLE_REDIRECT_URI"))
    facebook_client_id: str = Field(default="", validation_alias=AliasChoices("FACEBOOK_CLIENT_ID"))
    facebook_client_secret: str = Field(default="", validation_alias=AliasChoices("FACEBOOK_CLIENT_SECRET"))
    facebook_redirect_uri: str = Field(default="", validation_alias=AliasChoices("FACEBOOK_REDIRECT_URI"))
    oauth_state_ttl_seconds: int = Field(default=600, validation_alias=AliasChoices("OAUTH_STATE_TTL_SECONDS"))
    frontend_auth_redirect_url: str = Field(
        default="http://127.0.0.1:5173/auth/callback",
        validation_alias=AliasChoices("FRONTEND_AUTH_REDIRECT_URL"),
    )

    backend_public_base_url: str = "http://127.0.0.1:8000"
    frontend_home_url: str = "http://127.0.0.1:5173/home"
    frontend_reset_password_url: str = "http://127.0.0.1:5173/reset-password"

    # Comma-separated extra CORS origins (e.g. Cloud Run frontend URL)
    cors_extra_origins: str = Field(default="", validation_alias=AliasChoices("CORS_EXTRA_ORIGINS"))

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_from_email: str = ""
    smtp_from_name: str = "Serene"

    def normalized_database_url(self) -> str:
        raw = self.database_url.strip()
        if not raw:
            raise ValueError("DATABASE_URL is required (validator _local_database_defaults should set a default)")
        if raw.startswith("postgresql://"):
            raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
        parsed = urlparse(raw)
        if "supabase.com" not in parsed.netloc:
            return raw

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.setdefault("sslmode", "require")
        return urlunparse(parsed._replace(query=urlencode(query)))


def get_settings() -> Settings:
    return Settings()
