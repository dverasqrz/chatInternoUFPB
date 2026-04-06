from fastapi import APIRouter

from app.core.config import get_settings
from app.services.runtime_settings import get_or_create_runtime_settings
from app.services.webhook_utils import get_inbound_webhook_url, get_outbound_webhook_url

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _detect_n8n_mode(url: str | None) -> str:
    if not url:
        return "not_configured"
    if "/webhook-test/" in url:
        return "test"
    if "/webhook/" in url:
        return "production"
    return "custom"


@router.get("/health/integrations")
def health_integrations() -> dict[str, str | None]:
    settings = get_settings()
    
    # Get inbound URL from environment
    inbound = get_inbound_webhook_url()
    
    # Get outbound URL from environment (will show environment if set, otherwise None)
    outbound_env = str(settings.n8n_outbound_webhook_url) if settings.n8n_outbound_webhook_url else None
    
    return {
        "status": "ok",
        "n8n_inbound_webhook_url": inbound,
        "n8n_inbound_mode": _detect_n8n_mode(inbound),
        "n8n_outbound_webhook_url_env": outbound_env,
        "n8n_outbound_mode_env": _detect_n8n_mode(outbound_env),
    }
