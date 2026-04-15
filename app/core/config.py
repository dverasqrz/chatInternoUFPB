from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and defaults."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = "UFPB Chat Multiatendente"
    app_version: str = "2.0.0"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["development", "production", "testing"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database settings
    database_url: str = "postgresql+psycopg2://postgres:s4MFwYYUz5kY3B9W@db.rcfjdwtwfbrlfaosvvno.supabase.co:5432/postgres"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    
    # Security settings
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    
    # Admin settings
    admin_name: str = "Diego Veras"
    admin_email: str = "diego.veras@gmail.com"
    admin_bootstrap_file: Path = Path("/app/runtime/admin_bootstrap.txt")
    
    # Webhook settings
    webhook_token: str | None = None
    webhook_timeout: int = 30
    webhook_retry_attempts: int = 3
    
    # N8N integration settings
    n8n_inbound_webhook_url: AnyHttpUrl | None = None
    n8n_outbound_webhook_url: AnyHttpUrl | None = None
    n8n_outbound_auth_type: Literal["none", "header", "basic", "jwt"] = "none"
    n8n_outbound_auth_header_name: str | None = None
    n8n_outbound_auth_header_value: str | None = None
    n8n_outbound_auth_basic_username: str | None = None
    n8n_outbound_auth_basic_password: str | None = None
    n8n_outbound_auth_jwt_token: str | None = None
    
    # AI Webhook settings
    ai_webhook_url_test: AnyHttpUrl | None = None
    ai_webhook_url_prod: AnyHttpUrl | None = None
    ai_webhook_username: str | None = None
    ai_webhook_password: str | None = None
    ollama_base_url: str = "https://ollama.sti.ufpb.br/"
    
    # Media settings
    media_storage_path: Path = Path("/app/uploads")
    media_max_file_size: int = 25 * 1024 * 1024  # 25MB
    media_allowed_extensions: list[str] = [
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",  # Images
        ".ogg", ".mp3", ".wav", ".m4a", ".webm",           # Audio
        ".mp4", ".mov", ".avi", ".mkv"                      # Video
    ]
    
    # CORS settings
    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # Rate limiting settings
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10
    
    # External services
    public_domain: str | None = None
    redis_url: str | None = None
    celery_broker_url: str | None = None

    @field_validator("webhook_token", mode="before")
    @classmethod
    def normalize_webhook_token(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("n8n_inbound_webhook_url", "n8n_outbound_webhook_url", "ai_webhook_url_test", "ai_webhook_url_prod", mode="before")
    @classmethod
    def normalize_outbound_url(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "n8n_outbound_auth_header_name",
        "n8n_outbound_auth_header_value",
        "n8n_outbound_auth_basic_username",
        "n8n_outbound_auth_basic_password",
        "n8n_outbound_auth_jwt_token",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("n8n_outbound_auth_type", mode="before")
    @classmethod
    def normalize_outbound_auth_type(cls, value: object) -> str:
        allowed = {"none", "header", "basic", "jwt"}
        normalized = str(value or "none").strip().lower()
        if normalized not in allowed:
            return "none"
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
