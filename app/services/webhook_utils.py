"""
Webhook URL utilities - prioritizes environment variables over database
"""

from app.core.config import get_settings
from app.services.runtime_settings import _normalize_optional_text


def get_inbound_webhook_url() -> str | None:
    """
    Get inbound webhook URL from environment variables.
    Returns None if not configured.
    """
    settings = get_settings()
    return _normalize_optional_text(
        str(settings.n8n_inbound_webhook_url) if settings.n8n_inbound_webhook_url else None
    )


def get_outbound_webhook_url(db_runtime_settings) -> str | None:
    """
    Get outbound webhook URL, prioritizing environment over database.
    """
    # First check environment
    settings = get_settings()
    env_url = _normalize_optional_text(
        str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
    )
    
    # If environment has a URL, use it
    if env_url:
        return env_url
    
    # Otherwise, use database value
    return db_runtime_settings.outbound_webhook_url


def get_webhook_token(db_runtime_settings) -> str | None:
    """
    Get webhook token, prioritizing environment over database.
    """
    # First check environment
    settings = get_settings()
    env_token = _normalize_optional_text(settings.webhook_token)
    
    # If environment has a token, use it
    if env_token:
        return env_token
    
    # Otherwise, use database value
    return db_runtime_settings.inbound_webhook_token
