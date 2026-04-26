from typing import Literal
from pydantic import BaseModel, Field, field_validator

OutboundAuthType = Literal["none", "header", "basic", "jwt"]
AIProvider = Literal["gemini", "openai", "groq", "ollama"]

class WebhookSettingsRead(BaseModel):
    outbound_webhook_url: str | None
    outbound_auth_type: OutboundAuthType
    outbound_auth_header_name: str | None
    outbound_auth_basic_username: str | None
    outbound_auth_secret_configured: bool
    outbound_auth_secret_preview: str | None
    inbound_webhook_token_configured: bool
    inbound_webhook_token_preview: str | None

class WebhookSettingsUpdate(BaseModel):
    outbound_webhook_url: str | None = Field(default=None, max_length=1000)
    outbound_auth_type: OutboundAuthType | None = None
    outbound_auth_header_name: str | None = Field(default=None, max_length=100)
    outbound_auth_header_value: str | None = Field(default=None, max_length=1000)
    outbound_auth_basic_username: str | None = Field(default=None, max_length=255)
    outbound_auth_basic_password: str | None = Field(default=None, max_length=1000)
    outbound_auth_jwt_token: str | None = Field(default=None, max_length=2000)
    inbound_webhook_token: str | None = Field(default=None, max_length=255)

    @field_validator(
        "outbound_webhook_url",
        "outbound_auth_header_name",
        "outbound_auth_header_value",
        "outbound_auth_basic_username",
        "outbound_auth_basic_password",
        "outbound_auth_jwt_token",
        "inbound_webhook_token",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

class AISettingsRead(BaseModel):
    ai_provider: str
    ai_agent_enabled: bool

class AISettingsUpdate(BaseModel):
    ai_provider: AIProvider | None = None
    ai_agent_enabled: bool | None = None
