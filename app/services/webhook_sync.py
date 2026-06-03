"""
Automatic webhook synchronization service
Runs on app startup to ensure environment webhook URLs are prioritized
"""

import logging
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.runtime_settings import RuntimeSettings
from app.services.runtime_settings import _normalize_optional_text

logger = logging.getLogger(__name__)


def sync_webhook_urls_on_startup():
    """
    Sync webhook URLs from environment to database on app startup.
    This ensures environment variables always take priority.
    """
    try:
        settings = get_settings()
        
        with SessionLocal() as db:
            runtime_settings = db.get(RuntimeSettings, 1)
            
            if not runtime_settings:
                logger.warning("Runtime settings not found, will be created on first use")
                return
            
            changes = []
            
            # Sync outbound webhook URL
            env_outbound = _normalize_optional_text(
                str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
            )
            
            if env_outbound and runtime_settings.outbound_webhook_url != env_outbound:
                logger.info(f"Updating outbound webhook URL: {runtime_settings.outbound_webhook_url} -> {env_outbound}")
                runtime_settings.outbound_webhook_url = env_outbound
                changes.append("outbound_webhook_url")
            
            # Sync inbound webhook token
            env_token = _normalize_optional_text(settings.webhook_token)
            
            if env_token and runtime_settings.inbound_webhook_token != env_token:
                logger.info("Updating inbound webhook token")
                runtime_settings.inbound_webhook_token = env_token
                changes.append("inbound_webhook_token")
            
            # Sync auth settings
            if settings.n8n_outbound_auth_type and runtime_settings.outbound_auth_type != settings.n8n_outbound_auth_type:
                runtime_settings.outbound_auth_type = settings.n8n_outbound_auth_type
                changes.append("outbound_auth_type")
            
            if settings.n8n_outbound_auth_header_name and runtime_settings.outbound_auth_header_name != _normalize_optional_text(settings.n8n_outbound_auth_header_name):
                runtime_settings.outbound_auth_header_name = _normalize_optional_text(settings.n8n_outbound_auth_header_name)
                changes.append("outbound_auth_header_name")
            
            if settings.n8n_outbound_auth_header_value and runtime_settings.outbound_auth_header_value != _normalize_optional_text(settings.n8n_outbound_auth_header_value):
                runtime_settings.outbound_auth_header_value = _normalize_optional_text(settings.n8n_outbound_auth_header_value)
                changes.append("outbound_auth_header_value")
            
            # Commit changes if any
            if changes:
                db.commit()
                db.refresh(runtime_settings)
                logger.info(f"Synced {len(changes)} webhook settings from environment: {', '.join(changes)}")
            else:
                logger.debug("Webhook settings already in sync with environment")
                
    except Exception as e:
        logger.error(f"Failed to sync webhook URLs on startup: {e}")


def get_effective_webhook_config():
    """
    Get the effective webhook configuration (environment prioritized)
    Returns a dict with current webhook settings
    """
    settings = get_settings()
    
    return {
        "inbound_url": _normalize_optional_text(
            str(settings.n8n_inbound_webhook_url) if settings.n8n_inbound_webhook_url else None
        ),
        "outbound_url": _normalize_optional_text(
            str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
        ),
        "webhook_token": _normalize_optional_text(settings.webhook_token),
        "outbound_auth_type": settings.n8n_outbound_auth_type or "none",
        "outbound_auth_header_name": _normalize_optional_text(settings.n8n_outbound_auth_header_name),
        "outbound_auth_header_value": _normalize_optional_text(settings.n8n_outbound_auth_header_value),
    }
