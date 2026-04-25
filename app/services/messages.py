from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
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
        
    # Auto-add 55 for local Brazilian numbers
    if len(phone) in (10, 11) and not phone.startswith("55"):
        phone = f"55{phone}"
        
    # WhatsApp Brazil rule: JIDs for DDD > 28 usually drop the 9th digit.
    if phone.startswith("55") and len(phone) == 13 and phone[4] == "9":
        try:
            ddd = int(phone[2:4])
            if ddd > 28:
                phone = phone[:4] + phone[5:]
        except ValueError:
            pass
            
    return f"+{phone}"


def _first_text_value(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_type(raw_type: Any, has_media: bool, message: dict[str, Any]) -> MessageType:
    raw = str(raw_type or "").lower()
    if "document" in raw or "file" in raw:
        return MessageType.DOCUMENT
    if "image" in raw:
        return MessageType.IMAGE
    if "audio" in raw or "ptt" in raw:
        return MessageType.AUDIO
    if "video" in raw:
        return MessageType.VIDEO
    if "documentMessage" in message:
        return MessageType.DOCUMENT
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
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.ms-powerpoint": ".ppt",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "text/plain": ".txt",
            "text/csv": ".csv",
            "application/zip": ".zip",
            "application/x-rar-compressed": ".rar",
        }
        if mime_type in known:
            return known[mime_type]
        if mime_type.startswith("audio/"):
            return ".ogg"
        if mime_type.startswith("video/"):
            return ".mp4"
        if mime_type.startswith("image/"):
            return ".jpg"
        if mime_type.startswith("text/"):
            return ".txt"

    if message_type == MessageType.AUDIO:
        return ".ogg"
    if message_type == MessageType.VIDEO:
        return ".mp4"
    if message_type == MessageType.IMAGE:
        return ".jpg"
    if message_type == MessageType.DOCUMENT:
        return ".pdf"
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
    if message_type not in {MessageType.IMAGE, MessageType.AUDIO, MessageType.VIDEO, MessageType.DOCUMENT}:
        return None

    base64_payload = _find_base64_in_payload(payload)
    media_bytes = None

    if base64_payload:
        media_bytes = _decode_base64_media(base64_payload)
    else:
        server_url = payload.get("server_url")
        apikey = payload.get("apikey")
        instance = payload.get("instance")
        root = _get_nested_dict(payload.get("data")) or _get_nested_dict(payload.get("body")) or payload
        key = _get_nested_dict(root.get("key"))
        message_id = _first_text_value(root.get("id"), root.get("messageId"), key.get("id"))

        if server_url and apikey and instance and message_id:
            try:
                import httpx
                import logging
                logger = logging.getLogger(__name__)
                
                download_url = f"{str(server_url).rstrip('/')}/chat/getBase64FromMediaMessage/{instance}"
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        download_url,
                        json={"message": {"key": {"id": message_id}}},
                        headers={"apikey": str(apikey)}
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        fetched_base64 = data.get("base64")
                        if fetched_base64:
                            media_bytes = _decode_base64_media(fetched_base64)
                    else:
                        logger.error(f"Evolution API HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to fetch base64 from EvolutionAPI: {e}")

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
    event = payload.get("event")
    if event in ("contacts.upsert", "contacts.update"):
        data = payload.get("data", [])
        if isinstance(data, list) and len(data) > 0:
            contact = data[0]
        elif isinstance(data, dict):
            contact = data
        else:
            contact = {}
        
        return {
            "event": event,
            "contact_phone": _normalize_phone(contact.get("id", "")),
            "contact_name": contact.get("name") or contact.get("pushName") or contact.get("verifiedName"),
            "profile_picture_url": contact.get("profilePicUrl") or contact.get("profilePictureUrl"),
            "raw_payload": payload,
        }

    # Novo tratamento para update
    if event == "messages.update":
        data_list = payload.get("data", [])
        if isinstance(data_list, list) and len(data_list) > 0:
            item = data_list[0]
        elif isinstance(data_list, dict):
            item = data_list
        else:
            item = {}
        
        key = item.get("key") or {}
        update = item.get("update") or {}
        
        remote_jid = key.get("remoteJid") or item.get("remoteJid") or payload.get("remoteJid")
        external_id = key.get("id") or item.get("keyId") or item.get("messageId") or payload.get("id") or payload.get("messageId") or payload.get("key", {}).get("id")
        status_raw = update.get("status") or item.get("status") or payload.get("status") or payload.get("update", {}).get("status")
        
        status_num = None
        if isinstance(status_raw, int):
            status_num = status_raw
        elif isinstance(status_raw, str):
            status_str = status_raw.upper()
            if status_str in ("ERROR", "FAILED"):
                status_num = 0
            elif status_str in ("PENDING", "QUEUED"):
                status_num = 1
            elif status_str in ("SERVER_ACK", "SENT"):
                status_num = 2
            elif status_str in ("DELIVERY_ACK", "DELIVERED"):
                status_num = 3
            elif status_str in ("READ", "PLAYED"):
                status_num = 4
        
        return {
            "event": event,
            "contact_phone": _normalize_phone(remote_jid),
            "external_message_id": external_id,
            "status": status_num,
            "raw_payload": payload,
        }

    # Novo tratamento para delete
    if event == "messages.delete":
        msg_data = payload.get("data", {})
        msg_id = msg_data.get("id") or msg_data.get("keyId") or msg_data.get("messageId") or payload.get("id") or payload.get("messageId") or payload.get("key", {}).get("id")
        remote_jid = msg_data.get("remoteJid") or payload.get("remoteJid") or payload.get("key", {}).get("remoteJid")
        return {
            "event": event,
            "contact_phone": _normalize_phone(remote_jid),
            "external_message_id": msg_id,
            "raw_payload": payload,
        }

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

    from_me = bool(key.get("fromMe") or root.get("fromMe"))
    raw_sender = _first_text_value(
        sender.get("phone"), sender.get("id"), root.get("participant"), key.get("participant")
    )
    if _normalize_phone(raw_sender) == "+558332167336":
        from_me = True

    direction = MessageDirection.OUTBOUND if from_me else MessageDirection.INBOUND

    contact_phone = _normalize_phone(
        _first_text_value(
            key.get("remoteJid"),
            root.get("remoteJid"),
            payload.get("remoteJid"),
            root.get("phone"),
            root.get("from"),
            sender.get("phone"),
            sender.get("id"),
            key.get("participant"),
            message.get("from"),
            payload.get("phone"),
            payload.get("from"),
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
        "event": event,
        "contact_phone": contact_phone,
        "contact_name": contact_name,
        "direction": direction,
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


def ingest_inbound_message(db: Session, payload: dict[str, Any]) -> Conversation | Message | None:
    normalized = normalize_webhook_payload(payload)
    
    if not normalized.get("contact_phone"):
        raise HTTPException(status_code=400, detail="Webhook sem telefone do contato.")

    contact_phone = normalized["contact_phone"]
    direction = normalized.get("direction", MessageDirection.INBOUND)
    
    # Ignore webhooks where the contact phone is the UFPB system bot itself
    if contact_phone == "+558332167336":
        return None
        
    # Ignore webhooks where the contact phone matches the instance's own number
    sender_phone = _normalize_phone(payload.get("sender"))
    if sender_phone and contact_phone == sender_phone:
        return None

    # Tratamento especial de Eventos Atualização e Deleção
    event = normalized.get("event")
    if event == "messages.update":
        msg_id = normalized.get("external_message_id")
        status_num = normalized.get("status")
        if msg_id and status_num is not None:
            # Evolution API status codes: 2: sent, 3: delivered, 4: read
            message = db.scalar(select(Message).where(Message.external_message_id == msg_id))
            if message:
                if status_num == 0:
                    message.delivery_status = DeliveryStatus.FAILED
                elif status_num == 1:
                    message.delivery_status = DeliveryStatus.QUEUED
                elif status_num == 2:
                    message.delivery_status = DeliveryStatus.SENT
                elif status_num == 3:
                    message.delivery_status = DeliveryStatus.DELIVERED
                elif status_num >= 4:
                    message.delivery_status = DeliveryStatus.READ
                db.commit()
                db.refresh(message)
                return message
        return None

    if event == "messages.delete":
        msg_id = normalized.get("external_message_id")
        if msg_id:
            message = db.scalar(select(Message).where(Message.external_message_id == msg_id))
            if message:
                message.text_content = "🚫 Essa mensagem foi apagada"
                message.media_url = None
                message.media_mime_type = None
                # Se for imagem ou outro tipo de mídia, mudamos para texto para ficar mais fácil
                message.message_type = MessageType.TEXT
                db.commit()
                db.refresh(message)
                return message
        return None

    contact_name = normalized.get("contact_name")
    if direction == MessageDirection.OUTBOUND and contact_name and contact_name.strip().upper() == "CAU":
        contact_name = None

    conversation = _get_or_create_conversation(
        db=db,
        contact_phone=normalized["contact_phone"],
        contact_name=contact_name,
    )
    
    profile_pic = normalized.get("profile_picture_url")
    if profile_pic:
        conversation.profile_picture_url = profile_pic
        db.commit()
        db.refresh(conversation)
    elif not conversation.profile_picture_url:
        # Tenta buscar a foto na API da Evolution de forma ativa
        server_url = payload.get("server_url")
        apikey = payload.get("apikey")
        instance = payload.get("instance")
        if server_url and apikey and instance:
            try:
                import httpx
                import logging
                logger = logging.getLogger(__name__)
                
                download_url = f"{str(server_url).rstrip('/')}/chat/fetchProfilePictureUrl/{instance}"
                clean_phone = contact_phone.replace("+", "")
                
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        download_url,
                        json={"number": clean_phone},
                        headers={"apikey": str(apikey)}
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        fetched_url = data.get("profilePictureUrl")
                        if fetched_url:
                            conversation.profile_picture_url = fetched_url
                            db.commit()
                            db.refresh(conversation)
                    else:
                        logger.error(f"Evolution API fetchProfile fail: {resp.status_code}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao tentar cachear foto de perfil: {e}")
    
    if event in ("contacts.upsert", "contacts.update"):
        return conversation

    conversation.last_message_at = datetime.now(timezone.utc)

    # Verificar se mensagem já existe (evitar duplicatas)
    external_id = normalized.get("external_message_id")
    if external_id:
        existing_message = db.scalar(
            select(Message).where(Message.external_message_id == external_id)
        )
        if existing_message:
            # Mensagem já existe, não criar duplicata
            # Apenas atualizar o status se necessário
            if existing_message.delivery_status == DeliveryStatus.SENT and direction == MessageDirection.OUTBOUND:
                existing_message.delivery_status = DeliveryStatus.DELIVERED
                db.commit()
                db.refresh(existing_message)
            return existing_message

    # Se for mensagem OUTBOUND (enviada pelo dashboard), verificar se existe mensagem
    # recente sem external_message_id na mesma conversa (evita duplicata quando
    # o webhook de confirmação chega com external_id mas a mensagem original foi criada sem)
    if direction == MessageDirection.OUTBOUND and external_id:
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        existing_outbound = db.scalar(
            select(Message).where(
                Message.conversation_id == conversation.id,
                Message.direction == MessageDirection.OUTBOUND,
                Message.external_message_id.is_(None),
                Message.created_at >= recent_cutoff,
                Message.text_content == normalized.get("text_content"),
            )
        )
        if existing_outbound:
            # Atualizar a mensagem existente com o external_id e marcar como DELIVERED
            existing_outbound.external_message_id = external_id
            existing_outbound.delivery_status = DeliveryStatus.DELIVERED
            existing_outbound.raw_payload = normalized.get("raw_payload")
            db.commit()
            db.refresh(existing_outbound)
            return existing_outbound

    sender_name = normalized.get("contact_name")
    delivery_status = DeliveryStatus.RECEIVED
    if direction == MessageDirection.OUTBOUND:
        if sender_name and sender_name.strip().upper() == "CAU":
            sender_name = None
        delivery_status = DeliveryStatus.SENT

    message = Message(
        conversation_id=conversation.id,
        direction=direction,
        message_type=normalized["message_type"],
        delivery_status=delivery_status,
        text_content=normalized["text_content"],
        media_url=normalized["media_url"],
        media_mime_type=normalized["media_mime_type"],
        media_caption=normalized["media_caption"],
        sender_name=sender_name,
        sender_phone=normalized["contact_phone"],
        external_message_id=external_id,
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
