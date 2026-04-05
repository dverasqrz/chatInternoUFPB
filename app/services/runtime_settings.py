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
    if existing:
        return existing

    settings = get_settings()
    runtime = RuntimeSettings(
        id=1,
        outbound_webhook_url=_normalize_optional_text(
            str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
        ),
        outbound_auth_type=_normalize_auth_type(settings.n8n_outbound_auth_type),
        outbound_auth_header_name=_normalize_optional_text(settings.n8n_outbound_auth_header_name),
        outbound_auth_header_value=_normalize_optional_text(settings.n8n_outbound_auth_header_value),
        outbound_auth_basic_username=_normalize_optional_text(settings.n8n_outbound_auth_basic_username),
        outbound_auth_basic_password=_normalize_optional_text(settings.n8n_outbound_auth_basic_password),
        outbound_auth_jwt_token=_normalize_optional_text(settings.n8n_outbound_auth_jwt_token),
        inbound_webhook_token=_normalize_optional_text(settings.webhook_token),
    )
    db.add(runtime)
    db.commit()
    db.refresh(runtime)
    return runtime
