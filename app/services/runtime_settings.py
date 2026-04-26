from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.runtime_settings import RuntimeSettings

logger = logging.getLogger(__name__)

# ─── In-memory cache ─────────────────────────────────────────────────────────
# Holds the current RuntimeSettings after startup so that every request
# doesn't hit the database.  Invalidated (set to None) whenever an admin
# saves new settings, so the next request re-hydrates from the DB.
_runtime_cache: RuntimeSettings | None = None


def invalidate_runtime_cache() -> None:
    """Call this after any admin write so the cache is refreshed."""
    global _runtime_cache
    _runtime_cache = None
    logger.debug("Runtime settings cache invalidated.")


def get_cached_runtime() -> RuntimeSettings | None:
    """Return the cached settings without hitting the DB (may be None)."""
    return _runtime_cache


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


# ─── Main loader ─────────────────────────────────────────────────────────────

def get_or_create_runtime_settings(db: Session) -> RuntimeSettings:
    """
    Load RuntimeSettings from DB (or create if missing), apply env overrides
    for webhook fields, populate the in-memory cache, and return the object.
    """
    global _runtime_cache

    # Ensure ai_agent_enabled exists (for dynamic migration)
    from sqlalchemy import text
    try:
        db.execute(text("ALTER TABLE runtime_settings ADD COLUMN IF NOT EXISTS ai_agent_enabled BOOLEAN NOT NULL DEFAULT FALSE;"))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to add ai_agent_enabled column: {e}")

    # Return from cache when available
    if _runtime_cache is not None:
        return _runtime_cache

    existing = db.get(RuntimeSettings, 1)
    settings = get_settings()

    # Env values that always take precedence over what's stored in DB
    env_outbound_url = _normalize_optional_text(
        str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
    )
    env_inbound_token = _normalize_optional_text(settings.webhook_token)

    if existing:
        needs_update = False

        if env_outbound_url and existing.outbound_webhook_url != env_outbound_url:
            existing.outbound_webhook_url = env_outbound_url
            needs_update = True

        if env_inbound_token and existing.inbound_webhook_token != env_inbound_token:
            existing.inbound_webhook_token = env_inbound_token
            needs_update = True

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

        # Expunge from session so the cached object is detached and safe to
        # read from any future request without cross-session issues.
        db.expunge(existing)
        _runtime_cache = existing
        logger.info(
            f"✅ Runtime settings loaded from DB — "
            f"AI provider: {existing.ai_provider}"
        )
        return existing

    # First boot: create from env defaults
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
        # AI defaults
        ai_provider="gemini",
        ai_model=None,
        ai_base_url=settings.ollama_base_url,
    )
    db.add(runtime)
    db.commit()
    db.refresh(runtime)

    db.expunge(runtime)
    _runtime_cache = runtime
    logger.info("✅ Runtime settings created (first boot).")
    return runtime
