from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "UFPB Chat Multiatendente"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg2://ufpb:ufpb123@db:5432/ufpb_chat"

    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24 * 30

    admin_name: str = "Diego Veras"
    admin_email: str = "diego.veras@gmail.com"
    admin_bootstrap_file: Path = Path("/app/runtime/admin_bootstrap.txt")

    webhook_token: str | None = None
    n8n_inbound_webhook_url: AnyHttpUrl | None = None
    n8n_outbound_webhook_url: AnyHttpUrl | None = None
    n8n_outbound_auth_type: str = "none"
    n8n_outbound_auth_header_name: str | None = None
    n8n_outbound_auth_header_value: str | None = None
    n8n_outbound_auth_basic_username: str | None = None
    n8n_outbound_auth_basic_password: str | None = None
    n8n_outbound_auth_jwt_token: str | None = None
    media_storage_path: Path = Path("/app/uploads")

    cors_origins: str = "*"

    @field_validator("webhook_token", mode="before")
    @classmethod
    def normalize_webhook_token(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("n8n_inbound_webhook_url", "n8n_outbound_webhook_url", mode="before")
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
