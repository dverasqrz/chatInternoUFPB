from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from pathlib import Path
import re
import secrets
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.message import DeliveryStatus, Message, MessageDirection, MessageType
from app.models.runtime_settings import RuntimeSettings
from app.models.user import User
from app.schemas.message import OutboundMessageCreate
from app.services.runtime_settings import get_or_create_runtime_settings
from app.services.webhook_utils import get_outbound_webhook_url


def _normalize_phone(raw: Any) -> str | None:
    if not raw:
        return None
    phone = re.sub(r"\D", "", str(raw))
    if not phone:
        return None
    if phone.startswith("55"):
        return f"+{phone}"
    return f"+{phone}"


def _first_text_value(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_type(raw_type: Any, has_media: bool, message: dict[str, Any]) -> MessageType:
    raw = str(raw_type or "").lower()
    if "image" in raw:
        return MessageType.IMAGE
    if "audio" in raw or "ptt" in raw:
        return MessageType.AUDIO
    if "video" in raw:
        return MessageType.VIDEO
    if "imageMessage" in message:
        return MessageType.IMAGE
    if "audioMessage" in message or "pttMessage" in message:
        return MessageType.AUDIO
    if "videoMessage" in message:
        return MessageType.VIDEO
    if has_media:
        return MessageType.IMAGE
    return MessageType.TEXT


def _get_nested_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _normalize_media_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("/v/"):
        return f"https://mmg.whatsapp.net{value}"
    return value


def _normalize_mime_type(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower() or None


def _extension_for_media(message_type: MessageType, mime_type: str | None) -> str:
    if mime_type:
        known = {
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/wav": ".wav",
            "audio/webm": ".webm",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        if mime_type in known:
            return known[mime_type]
        if mime_type.startswith("audio/"):
            return ".ogg"
        if mime_type.startswith("video/"):
            return ".mp4"
        if mime_type.startswith("image/"):
            return ".jpg"

    if message_type == MessageType.AUDIO:
        return ".ogg"
    if message_type == MessageType.VIDEO:
        return ".mp4"
    if message_type == MessageType.IMAGE:
        return ".jpg"
    return ".bin"


def _find_base64_in_payload(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in {"base64", "media_base64", "file_base64", "mediabase64", "filebase64"}:
                if isinstance(child, str) and child.strip():
                    return child.strip()
            nested_found = _find_base64_in_payload(child)
            if nested_found:
                return nested_found
    elif isinstance(value, list):
        for child in value:
            nested_found = _find_base64_in_payload(child)
            if nested_found:
                return nested_found
    return None


def _decode_base64_media(value: str) -> bytes | None:
    if not value:
        return None

    raw = value.strip()
    if raw.startswith("data:") and ";base64," in raw:
        raw = raw.split(";base64,", 1)[1]

    raw = "".join(raw.split())
    if not raw:
        return None

    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        padded = raw + ("=" * (-len(raw) % 4))
        try:
            return base64.b64decode(padded, validate=False)
        except (binascii.Error, ValueError):
            return None


def _persist_inbound_media_from_base64(
    payload: dict[str, Any],
    message_type: MessageType,
    mime_type: str | None,
) -> str | None:
    if message_type not in {MessageType.IMAGE, MessageType.AUDIO, MessageType.VIDEO}:
        return None

    base64_payload = _find_base64_in_payload(payload)
    if not base64_payload:
        return None

    media_bytes = _decode_base64_media(base64_payload)
    if not media_bytes:
        return None
    if len(media_bytes) > 25 * 1024 * 1024:
        return None

    settings = get_settings()
    storage_path = settings.media_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)

    extension = _extension_for_media(message_type, mime_type)
    filename = f"{secrets.token_hex(16)}{extension}"
    destination = storage_path / filename
    Path(destination).write_bytes(media_bytes)
    
    # TESTE: Sem conversão de vídeos - usa arquivo bruto direto
    if message_type == MessageType.VIDEO:
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"TESTE SEM CONVERSÃO: Processando vídeo bruto: {filename}")
            logger.info(f"MIME type: {mime_type}")
            logger.info(f"File size: {len(media_bytes)} bytes")
            
            # Sem conversão - retorna URL direta do arquivo bruto
            return f"/uploads/{filename}"
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing video: {e}")
            # Use original file if there's any error
    
    return f"/uploads/{filename}"


def _build_outbound_request_security(runtime_settings: RuntimeSettings) -> tuple[dict[str, str], tuple[str, str] | None]:
    headers: dict[str, str] = {}
    auth: tuple[str, str] | None = None

    auth_type = (runtime_settings.outbound_auth_type or "none").lower()
    if auth_type == "header" and runtime_settings.outbound_auth_header_name and runtime_settings.outbound_auth_header_value:
        headers[runtime_settings.outbound_auth_header_name] = runtime_settings.outbound_auth_header_value
    elif auth_type == "basic" and runtime_settings.outbound_auth_basic_username and runtime_settings.outbound_auth_basic_password:
        auth = (runtime_settings.outbound_auth_basic_username, runtime_settings.outbound_auth_basic_password)
    elif auth_type == "jwt" and runtime_settings.outbound_auth_jwt_token:
        headers["Authorization"] = f"Bearer {runtime_settings.outbound_auth_jwt_token}"

    return headers, auth


def normalize_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = _get_nested_dict(payload.get("body"))
    root = _get_nested_dict(payload.get("data")) or _get_nested_dict(body.get("data")) or body or payload
    sender = _get_nested_dict(root.get("sender"))
    message = _get_nested_dict(root.get("message"))
    key = _get_nested_dict(root.get("key"))
    extended_text_message = _get_nested_dict(message.get("extendedTextMessage"))
    image_message = _get_nested_dict(message.get("imageMessage"))
    audio_message = _get_nested_dict(message.get("audioMessage"))
    video_message = _get_nested_dict(message.get("videoMessage"))
    document_message = _get_nested_dict(message.get("documentMessage"))

    contact_phone = _normalize_phone(
        _first_text_value(
            root.get("phone"),
            root.get("from"),
            sender.get("phone"),
            sender.get("id"),
            key.get("remoteJid"),
            key.get("participant"),
            message.get("from"),
            payload.get("phone"),
            payload.get("from"),
            payload.get("remoteJid"),
            payload.get("remote_jid"),
        )
    )
    if not contact_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook sem telefone do contato.",
        )

    media_url = _first_text_value(
        root.get("mediaUrl"),
        root.get("media_url"),
        root.get("url"),
        message.get("url"),
        message.get("mediaUrl"),
        message.get("downloadUrl"),
        image_message.get("url"),
        image_message.get("directPath"),
        audio_message.get("url"),
        audio_message.get("directPath"),
        video_message.get("url"),
        video_message.get("directPath"),
        document_message.get("url"),
        document_message.get("directPath"),
    )
    media_url = _normalize_media_url(media_url)
    text_content = _first_text_value(
        root.get("text"),
        root.get("message"),
        message.get("conversation"),
        extended_text_message.get("text"),
        message.get("text"),
        message.get("body"),
        message.get("caption"),
        image_message.get("caption"),
        video_message.get("caption"),
        payload.get("message"),
    )
    message_type = _extract_type(
        _first_text_value(root.get("type"), root.get("messageType"), message.get("type"), payload.get("type")),
        has_media=bool(media_url),
        message=message,
    )
    if message_type == MessageType.TEXT and not text_content:
        text_content = "[mensagem sem texto]"

    contact_name = _first_text_value(
        root.get("name"),
        root.get("pushName"),
        root.get("senderName"),
        sender.get("name"),
        payload.get("name"),
    )
    external_message_id = _first_text_value(
        root.get("id"),
        root.get("messageId"),
        key.get("id"),
        payload.get("id"),
    )
    media_mime_type = _first_text_value(
        root.get("mimetype"),
        root.get("mimeType"),
        message.get("mimetype"),
        message.get("mimeType"),
        image_message.get("mimetype"),
        image_message.get("mimeType"),
        audio_message.get("mimetype"),
        audio_message.get("mimeType"),
        video_message.get("mimetype"),
        video_message.get("mimeType"),
        document_message.get("mimetype"),
        document_message.get("mimeType"),
    )
    media_mime_type = _normalize_mime_type(media_mime_type)
    media_caption = _first_text_value(root.get("caption"), message.get("caption"))

    persisted_media_url = _persist_inbound_media_from_base64(
        payload=payload,
        message_type=message_type,
        mime_type=media_mime_type,
    )
    if persisted_media_url:
        media_url = persisted_media_url

    return {
        "contact_phone": contact_phone,
        "contact_name": contact_name,
        "message_type": message_type,
        "text_content": text_content,
        "media_url": media_url,
        "media_mime_type": media_mime_type,
        "media_caption": media_caption,
        "external_message_id": external_message_id,
        "raw_payload": payload,
    }


def _get_or_create_conversation(db: Session, contact_phone: str, contact_name: str | None) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(Conversation.contact_phone == contact_phone)
    )
    if conversation:
        if contact_name and conversation.contact_name != contact_name:
            conversation.contact_name = contact_name
        return conversation

    conversation = Conversation(contact_phone=contact_phone, contact_name=contact_name)
    db.add(conversation)
    db.flush()
    return conversation


def ingest_inbound_message(db: Session, payload: dict[str, Any]) -> Message:
    normalized = normalize_webhook_payload(payload)
    conversation = _get_or_create_conversation(
        db=db,
        contact_phone=normalized["contact_phone"],
        contact_name=normalized["contact_name"],
    )
    conversation.last_message_at = datetime.now(timezone.utc)

    message = Message(
        conversation_id=conversation.id,
        direction=MessageDirection.INBOUND,
        message_type=normalized["message_type"],
        delivery_status=DeliveryStatus.RECEIVED,
        text_content=normalized["text_content"],
        media_url=normalized["media_url"],
        media_mime_type=normalized["media_mime_type"],
        media_caption=normalized["media_caption"],
        sender_name=normalized["contact_name"],
        sender_phone=normalized["contact_phone"],
        external_message_id=normalized["external_message_id"],
        raw_payload=normalized["raw_payload"],
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


async def create_outbound_message(
    db: Session,
    conversation: Conversation,
    attendant: User,
    data: OutboundMessageCreate,
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND,
        message_type=data.message_type,
        delivery_status=DeliveryStatus.QUEUED,
        text_content=data.text_content,
        media_url=data.media_url,
        media_mime_type=data.media_mime_type,
        media_caption=data.media_caption,
        sender_name=attendant.name,
        attendant_id=attendant.id,
        raw_payload={
            "source": "api",
            "requested_by": attendant.email,
        },
    )

    db.add(message)
    conversation.last_message_at = datetime.now(timezone.utc)
    attendant.last_interaction_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)

    runtime_settings = get_or_create_runtime_settings(db)
    outbound_webhook_url = get_outbound_webhook_url(runtime_settings)
    
    if not outbound_webhook_url:
        message.delivery_status = DeliveryStatus.SENT
        db.commit()
        db.refresh(message)
        return message

    # TESTE: Sem conversão de vídeos - usa URL direta
    final_media_url = data.media_url
    final_mime_type = data.media_mime_type
    
    if data.message_type.value == "video" and data.media_url:
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # TESTE: Sem conversão - usa URL direta do vídeo bruto
            logger.info(f"TESTE SEM CONVERSÃO: Usando URL direta do vídeo: {data.media_url}")
            logger.info(f"MIME type: {data.media_mime_type}")
            final_media_url = data.media_url
            final_mime_type = data.media_mime_type  # Mantém MIME original
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing video URL: {e}")

    outbound_payload = {
        "conversation_id": conversation.id,
        "message_id": message.id,
        "to": conversation.contact_phone,
        "message_type": data.message_type.value,
        "text": data.text_content,
        "media_url": final_media_url,
        "media_mime_type": final_mime_type,
        "media_caption": data.media_caption,
        "attendant": {
            "id": attendant.id,
            "name": attendant.name,
            "email": attendant.email,
        },
    }

    try:
        outbound_headers, outbound_auth = _build_outbound_request_security(runtime_settings)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                outbound_webhook_url,
                json=outbound_payload,
                headers=outbound_headers or None,
                auth=outbound_auth,
            )
            response.raise_for_status()
        message.delivery_status = DeliveryStatus.SENT
        message.error_message = None
    except httpx.HTTPError as exc:
        message.delivery_status = DeliveryStatus.FAILED
        message.error_message = str(exc)

    db.commit()
    db.refresh(message)
    return message
