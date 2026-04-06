from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.runtime_settings import RuntimeSettings


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_auth_type(value: str | None) -> str:
    allowed = {"none", "header", "basic", "jwt"}
    normalized = (value or "none").strip().lower()
    if normalized not in allowed:
        return "none"
    return normalized


def get_or_create_runtime_settings(db: Session) -> RuntimeSettings:
    existing = db.get(RuntimeSettings, 1)
    settings = get_settings()
    
    # Always prioritize environment URLs
    env_outbound_url = _normalize_optional_text(
        str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
    )
    env_inbound_token = _normalize_optional_text(settings.webhook_token)
    
    if existing:
        # Update existing settings with environment values if they exist
        needs_update = False
        
        if env_outbound_url and existing.outbound_webhook_url != env_outbound_url:
            existing.outbound_webhook_url = env_outbound_url
            needs_update = True
        
        if env_inbound_token and existing.inbound_webhook_token != env_inbound_token:
            existing.inbound_webhook_token = env_inbound_token
            needs_update = True
        
        # Update auth settings from environment
        if settings.n8n_outbound_auth_type and existing.outbound_auth_type != settings.n8n_outbound_auth_type:
            existing.outbound_auth_type = settings.n8n_outbound_auth_type
            needs_update = True
        
        if settings.n8n_outbound_auth_header_name and existing.outbound_auth_header_name != _normalize_optional_text(settings.n8n_outbound_auth_header_name):
            existing.outbound_auth_header_name = _normalize_optional_text(settings.n8n_outbound_auth_header_name)
            needs_update = True
        
        if settings.n8n_outbound_auth_header_value and existing.outbound_auth_header_value != _normalize_optional_text(settings.n8n_outbound_auth_header_value):
            existing.outbound_auth_header_value = _normalize_optional_text(settings.n8n_outbound_auth_header_value)
            needs_update = True
        
        if needs_update:
            db.commit()
            db.refresh(existing)
        
        return existing

    # Create new runtime settings with environment values
    runtime = RuntimeSettings(
        id=1,
        outbound_webhook_url=env_outbound_url,
        outbound_auth_type=_normalize_auth_type(settings.n8n_outbound_auth_type),
        outbound_auth_header_name=_normalize_optional_text(settings.n8n_outbound_auth_header_name),
        outbound_auth_header_value=_normalize_optional_text(settings.n8n_outbound_auth_header_value),
        outbound_auth_basic_username=_normalize_optional_text(settings.n8n_outbound_auth_basic_username),
        outbound_auth_basic_password=_normalize_optional_text(settings.n8n_outbound_auth_basic_password),
        outbound_auth_jwt_token=_normalize_optional_text(settings.n8n_outbound_auth_jwt_token),
        inbound_webhook_token=env_inbound_token,
    )
    db.add(runtime)
    db.commit()
    db.refresh(runtime)
    return runtime
