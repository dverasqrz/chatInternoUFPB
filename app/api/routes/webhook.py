from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.message import WebhookIngestResponse
from app.services.messages import ingest_inbound_message
from app.services.runtime_settings import get_or_create_runtime_settings
from app.services.webhook_utils import get_webhook_token

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
public_router = APIRouter(tags=["webhooks"])


def _validate_inbound_token(
    db: Session,
    x_webhook_token: str | None,
    x_token: str | None,
    authorization: str | None,
    token_query: str | None,
) -> None:
    runtime_settings = get_or_create_runtime_settings(db)
    inbound_token = get_webhook_token(runtime_settings)
    if not inbound_token:
        return

    bearer_token = None
    if authorization:
        raw = authorization.strip()
        if raw.lower().startswith("bearer "):
            bearer_token = raw[7:].strip()

    received_token = x_webhook_token or x_token or bearer_token or token_query
    if received_token != inbound_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook token inválido.")


def _handle_webhook_payload(
    payload: dict[str, Any],
    db: Session,
    x_webhook_token: str | None,
    x_token: str | None,
    authorization: str | None,
    token_query: str | None,
) -> WebhookIngestResponse:
    _validate_inbound_token(
        db=db,
        x_webhook_token=x_webhook_token,
        x_token=x_token,
        authorization=authorization,
        token_query=token_query,
    )
    result = ingest_inbound_message(db=db, payload=payload)
    if result is None:
        return WebhookIngestResponse(
            status="ignored",
            conversation_id=None,
            message_id=None,
            message_type=None,
        )

    if hasattr(result, "message_type"):
        # It's a Message
        return WebhookIngestResponse(
            status="ok",
            conversation_id=result.conversation_id,
            message_id=result.id,
            message_type=result.message_type,
        )
    else:
        # It's a Conversation (contact update)
        return WebhookIngestResponse(
            status="ok",
            conversation_id=result.id,
            message_id=None,
            message_type=None,
        )


@router.post("/evolution", response_model=WebhookIngestResponse)
def evolution_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    token_query: str | None = Query(default=None, alias="token"),
) -> WebhookIngestResponse:
    return _handle_webhook_payload(
        payload=payload,
        db=db,
        x_webhook_token=x_webhook_token,
        x_token=x_token,
        authorization=authorization,
        token_query=token_query,
    )


@public_router.post("/webhook", response_model=WebhookIngestResponse)
@public_router.post("/webhook/", response_model=WebhookIngestResponse, include_in_schema=False)
@public_router.post("/api/inbox", response_model=WebhookIngestResponse)
@public_router.post("/api/inbox/", response_model=WebhookIngestResponse, include_in_schema=False)
def public_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    token_query: str | None = Query(default=None, alias="token"),
) -> WebhookIngestResponse:
    return _handle_webhook_payload(
        payload=payload,
        db=db,
        x_webhook_token=x_webhook_token,
        x_token=x_token,
        authorization=authorization,
        token_query=token_query,
    )
