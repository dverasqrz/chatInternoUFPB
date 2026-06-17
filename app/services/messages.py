from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
import logging
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

logger = logging.getLogger(__name__)


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
                download_url = f"{str(server_url).rstrip('/')}/chat/getBase64FromMediaMessage/{instance}"
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        download_url,
                        json={"messageId": message_id},
                        headers={"apikey": str(apikey)},
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        b64 = data.get("base64") or data.get("data", {}).get("base64")
                        if b64:
                            media_bytes = _decode_base64_media(b64)
            except Exception as exc:
                logger.warning("Failed to fetch media from Evolution API: %s", exc)

    if not media_bytes:
        return None

    if len(media_bytes) > 25 * 1024 * 1024:
        logger.warning("Media too large (%d bytes), skipping", len(media_bytes))
        return None

    settings = get_settings()
    ext = _extension_for_media(message_type, mime_type)
    filename = f"{secrets.token_hex(16)}{ext}"
    dest = Path(settings.media_storage_path) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(media_bytes)
    return f"/uploads/{filename}"


def normalize_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normaliza payloads variados da EvolutionAPI em formato interno padronizado."""

    event = payload.get("event", "")

    # --- contacts.upsert / contacts.update ---
    if event in ("contacts.upsert", "contacts.update"):
        contacts = payload.get("data") or payload.get("body", {}).get("data") or []
        if isinstance(contacts, dict):
            contacts = [contacts]
        for contact in contacts:
            phone = _normalize_phone(
                contact.get("phone")
                or contact.get("wa_id")
                or contact.get("id")
                or contact.get("remoteJid", "").replace("@s.whatsapp.net", "").replace("@lid", "")
            )
            if phone:
                return {
                    "event": event,
                    "contact_phone": phone,
                    "contact_name": contact.get("name") or contact.get("pushName"),
                    "profile_picture_url": contact.get("profilePictureUrl") or contact.get("profilePicUrl"),
                    "direction": None,
                    "message_type": None,
                    "text_content": None,
                    "media_url": None,
                    "media_mime_type": None,
                    "media_caption": None,
                    "external_message_id": None,
                    "raw_payload": payload,
                }
        return {"event": event, "contact_phone": None, "raw_payload": payload}

    # --- messages.edited (MESSAGES_EDITED - EvolutionAPI evento separado de edição) ---
    if event == "messages.edited":
        data = payload.get("data") or {}
        key = data.get("key") or {}
        msg_id = key.get("id") or data.get("keyId") or data.get("id")
        edited_msg = data.get("editedMessage") or {}

        logger.info(f"[NORM] messages.edited keyId={msg_id}, keys_in_data={list(data.keys())}, editedMessage={edited_msg}")

        # Extrair texto de múltiplos caminhos
        new_text = (
            edited_msg.get("conversation")
            or edited_msg.get("text")
            or (edited_msg.get("extendedTextMessage") or {}).get("text")
            or ""
        )
        # Tentar em editedMessage.message se existir
        if not new_text:
            edited_inner = edited_msg.get("message") or {}
            new_text = (
                edited_inner.get("conversation")
                or edited_inner.get("text")
                or (edited_inner.get("extendedTextMessage") or {}).get("text")
                or ""
            )
        # Tentar diretamente no data se editedMessage não tiver texto
        if not new_text:
            new_text = (
                data.get("conversation")
                or data.get("text")
                or (data.get("extendedTextMessage") or {}).get("text")
                or ""
            )

        logger.info(f"[NORM] messages.edited new_text={new_text!r}")

        raw_jid = key.get("remoteJid", "") or data.get("remoteJid", "")
        is_lid = "@lid" in str(raw_jid)
        phone = None
        if not is_lid:
            phone = _normalize_phone(raw_jid.replace("@lid", ""))
        if not phone:
            phone = _normalize_phone(
                data.get("remoteJidAlt")
                or key.get("remoteJidAlt")
                or data.get("sender")
                or payload.get("sender")
            )

        return {
            "event": "messages.edited",
            "contact_phone": phone,
            "external_message_id": msg_id,
            "edited_text": new_text if new_text else None,
            "direction": None,
            "message_type": MessageType.TEXT if new_text else None,
            "text_content": new_text,
            "media_url": None,
            "media_mime_type": None,
            "media_caption": None,
            "raw_payload": payload,
        }

    # --- messages.update (status) ---
    if event == "messages.update":
        data = payload.get("data") or {}
        key = data.get("key") or {}
        # Na edição, o ID do WhatsApp vem em "keyId", não em "key.id"
        msg_id = data.get("keyId") or key.get("id") or data.get("id") or data.get("messageId")

        # Log completo para debug de edições
        logger.info(f"[NORM] messages.update keyId={msg_id}, keys_in_data={list(data.keys())}, update_keys={list((data.get('update') or {}).keys())}, raw_data={data}")

        # Detectar se é edição de mensagem (editedMessage)
        # EvolutionAPI v2.3.x envia editedMessage em data.update.message.editedMessage
        update_block = data.get("update") or {}
        update_msg = update_block.get("message") or {}
        edited_msg = (
            update_msg.get("editedMessage")
            or data.get("message", {}).get("editedMessage")
            or data.get("editedMessage")
            or {}
        )
        logger.info(f"[NORM] messages.update update_block_keys={list(update_block.keys()) if update_block else []}, update_msg_keys={list(update_msg.keys()) if update_msg else []}, edited_msg={edited_msg}")

        # Tentar extrair novo texto de múltiplos caminhos possíveis
        new_text = ""
        if edited_msg:
            # Caminho 1: editedMessage.message.conversation (estrutura nested)
            new_text = (
                edited_msg.get("message", {}).get("conversation")
                or edited_msg.get("message", {}).get("extendedTextMessage", {}).get("text")
                or edited_msg.get("message", {}).get("text")
                or ""
            )
            # Caminho 2: editedMessage.conversation (sem wrapper message)
            if not new_text:
                new_text = (
                    edited_msg.get("conversation")
                    or edited_msg.get("text")
                    or (edited_msg.get("extendedTextMessage") or {}).get("text")
                    or ""
                )
            # Caminho 3: editedMessage direto pode ser string
            if not new_text and isinstance(edited_msg, str):
                new_text = edited_msg
            # Caminho 4: percorrer edited_msg recursivamente procurando 'conversation' ou 'text'
            if not new_text and isinstance(edited_msg, dict):
                for k, v in edited_msg.items():
                    if k in ("conversation", "text") and isinstance(v, str) and v.strip():
                        new_text = v
                        break
                    if isinstance(v, dict):
                        for k2, v2 in v.items():
                            if k2 in ("conversation", "text") and isinstance(v2, str) and v2.strip():
                                new_text = v2
                                break
                        if new_text:
                            break
            logger.info(f"[NORM] edited_msg path: new_text={new_text!r}, edited_msg_type={type(edited_msg).__name__}")

        # Caminho 3: update.message.conversation direto (sem editedMessage wrapper)
        if not new_text and update_msg:
            new_text = (
                update_msg.get("conversation")
                or update_msg.get("text")
                or (update_msg.get("extendedTextMessage") or {}).get("text")
                or ""
            )
            if new_text:
                logger.info(f"[NORM] update_msg direct path: new_text={new_text!r}")

        # Caminho 4: buscar diretamente no update_block (toda message dentro de update é edição)
        if not new_text and update_block:
            new_text = (
                update_block.get("conversation")
                or update_block.get("text")
                or (update_block.get("extendedTextMessage") or {}).get("text")
                or ""
            )
            if new_text:
                logger.info(f"[NORM] update_block direct path: new_text={new_text!r}")

        # Caminho 5: data.message pode ter conversation direto (edição simples)
        if not new_text:
            data_msg = data.get("message") or {}
            if data_msg and isinstance(data_msg, dict):
                new_text = (
                    data_msg.get("conversation")
                    or data_msg.get("text")
                    or (data_msg.get("extendedTextMessage") or {}).get("text")
                    or ""
                )
                if new_text:
                    logger.info(f"[NORM] data.message direct path: new_text={new_text!r}")

        if new_text:
            # Priorizar remoteJidAlt (quando remoteJid é LID) e sender
            raw_jid = data.get("remoteJid", "") or key.get("remoteJid", "")
            is_lid = "@lid" in str(raw_jid)
            phone = None
            if not is_lid:
                phone = _normalize_phone(raw_jid.replace("@lid", ""))
            if not phone:
                phone = _normalize_phone(
                    data.get("remoteJidAlt")
                    or key.get("remoteJidAlt")
                    or data.get("sender")
                    or payload.get("sender")
                )
            logger.info(f"[NORM] messages.update editado detectado: msg_id={msg_id}, phone={phone}, is_lid={is_lid}, new_text={new_text!r}")
            return {
                "event": "messages.edited",
                "contact_phone": phone,
                "external_message_id": msg_id,
                "edited_text": new_text,
                "direction": None,
                "message_type": MessageType.TEXT,
                "text_content": new_text,
                "media_url": None,
                "media_mime_type": None,
                "media_caption": None,
                "raw_payload": payload,
            }

        # Se edited_msg foi encontrado mas new_text vazio, mesmo assim marcar como editado
        # (pode ser edição de mídia ou estrutura diferente)
        if edited_msg:
            raw_jid = data.get("remoteJid", "") or key.get("remoteJid", "")
            is_lid = "@lid" in str(raw_jid)
            phone = None
            if not is_lid:
                phone = _normalize_phone(raw_jid.replace("@lid", ""))
            if not phone:
                phone = _normalize_phone(
                    data.get("remoteJidAlt")
                    or key.get("remoteJidAlt")
                    or data.get("sender")
                    or payload.get("sender")
                )
            logger.info(f"[NORM] messages.update edited_msg sem texto: msg_id={msg_id}, phone={phone}, edited_msg_keys={list(edited_msg.keys()) if isinstance(edited_msg, dict) else 'not_dict'}")
            return {
                "event": "messages.edited",
                "contact_phone": phone,
                "external_message_id": msg_id,
                "edited_text": None,
                "direction": None,
                "message_type": None,
                "text_content": None,
                "media_url": None,
                "media_mime_type": None,
                "media_caption": None,
                "raw_payload": payload,
            }

        # Detectar delete
        if data.get("update", {}).get("message", {}) is True or data.get("message", {}) is True:
            phone = _normalize_phone(
                key.get("remoteJid", "").replace("@lid", "")
                or data.get("remoteJid", "").replace("@lid", "")
                or data.get("sender")
                or payload.get("sender")
            )
            return {
                "event": "messages.delete",
                "contact_phone": phone,
                "external_message_id": msg_id,
                "direction": None,
                "message_type": None,
                "text_content": None,
                "media_url": None,
                "media_mime_type": None,
                "media_caption": None,
                "raw_payload": payload,
            }

        # Status update normal - EvolutionAPI envia string ou número
        status_string_map = {
            "ERROR": DeliveryStatus.FAILED,
            "PENDING": DeliveryStatus.QUEUED,
            "SENT": DeliveryStatus.SENT,
            "SERVER_ACK": DeliveryStatus.SENT,
            "DELIVERY_ACK": DeliveryStatus.DELIVERED,
            "PLAYED": DeliveryStatus.READ,
            "READ": DeliveryStatus.READ,
        }
        status_numeric_map = {0: DeliveryStatus.FAILED, 1: DeliveryStatus.QUEUED, 2: DeliveryStatus.SENT, 3: DeliveryStatus.DELIVERED, 4: DeliveryStatus.READ, 5: DeliveryStatus.FAILED}
        raw_status = (
            data.get("status")
            or data.get("update", {}).get("status")
            or data.get("messageStatus")
        )
        delivery_status = None
        if raw_status is not None:
            raw_str = str(raw_status).strip().upper()
            delivery_status = status_string_map.get(raw_str)
            if delivery_status is None:
                try:
                    delivery_status = status_numeric_map.get(int(raw_status))
                except (ValueError, TypeError):
                    pass

        phone = _normalize_phone(
            data.get("remoteJid", "").replace("@lid", "")
            or key.get("remoteJid", "").replace("@lid", "")
            or data.get("sender")
            or payload.get("sender")
        )

        return {
            "event": event,
            "contact_phone": phone,
            "external_message_id": msg_id,
            "delivery_status": delivery_status,
            "direction": None,
            "message_type": None,
            "text_content": None,
            "media_url": None,
            "media_mime_type": None,
            "media_caption": None,
            "raw_payload": payload,
        }

    # --- messages.delete ---
    if event == "messages.delete":
        data = payload.get("data") or {}
        key = data.get("key") or {}
        msg_id = key.get("id") or data.get("id")
        phone = _normalize_phone(
            key.get("remoteJid", "").replace("@lid", "")
            or data.get("remoteJid", "").replace("@lid", "")
            or data.get("sender")
            or payload.get("sender")
        )
        return {
            "event": event,
            "contact_phone": phone,
            "external_message_id": msg_id,
            "direction": None,
            "message_type": None,
            "text_content": None,
            "media_url": None,
            "media_mime_type": None,
            "media_caption": None,
            "raw_payload": payload,
        }

    # --- Mensagens regulares (messages.upsert, etc.) ---
    root = (
        _get_nested_dict(payload.get("data"))
        or _get_nested_dict(payload.get("body", {}).get("data"))
        or _get_nested_dict(payload.get("body"))
        or payload
    )

    key = _get_nested_dict(root.get("key"))
    sender_raw = (
        root.get("sender")
        or key.get("participant")
        or payload.get("sender")
        or ""
    )
    message = _get_nested_dict(root.get("message")) or _get_nested_dict(root.get("message", {}))
    if not message:
        message = root

    # Detectar editedMessage dentro de messages.upsert (EvolutionAPI pode enviar edição como upsert)
    edited_wrap = message.get("editedMessage") or root.get("editedMessage") or {}
    edited_inner = _get_nested_dict(edited_wrap.get("message")) or edited_wrap
    is_edited_upsert = False
    if edited_wrap and (edited_inner.get("conversation") or edited_inner.get("text")
                        or (edited_inner.get("extendedTextMessage") or {}).get("text")):
        message = edited_inner
        is_edited_upsert = True

    from_me = key.get("fromMe", False)
    if str(sender_raw).replace("+", "").strip() == "558332167336":
        from_me = True

    direction = MessageDirection.OUTBOUND if from_me else MessageDirection.INBOUND

    phone = _normalize_phone(
        key.get("remoteJid", "").replace("@lid", "")
        or root.get("remoteJid", "").replace("@lid", "")
        or sender_raw
    )

    has_media = any(
        message.get(k)
        for k in ("imageMessage", "audioMessage", "videoMessage", "documentMessage", "pttMessage", "stickerMessage")
    )
    raw_type = root.get("type") or root.get("messageType")

    # Treat stickerMessage as imageMessage for n8n compatibility
    if message.get("stickerMessage") and not message.get("imageMessage"):
        message["imageMessage"] = message["stickerMessage"]

    message_type = _extract_type(raw_type, has_media, message)

    # Detectar secretEncryptedMessage (edição criptografada do WhatsApp)
    # Quando usuário edita mensagem no WhatsApp, EvolutionAPI envia esse tipo
    # com targetMessageKey.id apontando para a mensagem original editada.
    # Não podemos descriptografar o conteúdo, então ignoramos para não criar duplicata.
    if raw_type == "secretEncryptedMessage":
        enc_msg = message.get("secretEncryptedMessage") or {}
        target_key = enc_msg.get("targetMessageKey") or {}
        target_msg_id = target_key.get("id")
        logger.info(f"[ENCRYPTED] secretEncryptedMessage recebido, target_msg_id={target_msg_id}, ignorando para não criar duplicata")
        return {
            "event": "messages.secret_encrypted",
            "contact_phone": phone,
            "contact_name": root.get("pushName") or root.get("notify"),
            "profile_picture_url": None,
            "direction": direction,
            "message_type": None,
            "text_content": None,
            "media_url": None,
            "media_mime_type": None,
            "media_caption": None,
            "external_message_id": target_msg_id or key.get("id"),
            "sender": sender_raw,
            "quoted_message_text": None,
            "quoted_message_sender": None,
            "is_edited": False,
            "raw_payload": payload,
        }

    text_content = (
        message.get("conversation")
        or message.get("text")
        or (message.get("extendedTextMessage") or {}).get("text")
    )

    # Extrair referência da mensagem original (quotedMessage)
    quoted_text = None
    quoted_sender = None
    quoted_message_id = None
    quoted_message_participant = None
    # Verificar contextInfo em todos os tipos de mensagem + fallback no root (data level)
    context_info = (
        (message.get("extendedTextMessage") or {}).get("contextInfo")
        or (message.get("imageMessage") or {}).get("contextInfo")
        or (message.get("videoMessage") or {}).get("contextInfo")
        or (message.get("documentMessage") or {}).get("contextInfo")
        or (message.get("audioMessage") or {}).get("contextInfo")
        or root.get("contextInfo")
        or {}
    )

    # Extrair stanzaId e participant do contextInfo (sempre, independente de quotedMessage)
    # Esses campos sao irmãos de quotedMessage, nao filhos
    quoted_message_id = context_info.get("stanzaId")
    quoted_message_participant = context_info.get("participant")
    if quoted_message_participant:
        quoted_sender = quoted_message_participant.split("@")[0] if "@" in quoted_message_participant else quoted_message_participant

    quoted_msg = context_info.get("quotedMessage") or {}
    if quoted_msg:
        quoted_text = (
            quoted_msg.get("conversation")
            or quoted_msg.get("text")
            or (quoted_msg.get("extendedTextMessage") or {}).get("text")
            or (quoted_msg.get("imageMessage") or {}).get("caption")
            or (quoted_msg.get("videoMessage") or {}).get("caption")
        )
        if quoted_text:
            quoted_text = quoted_text[:200]  # Limitar tamanho

    if quoted_message_id or quoted_message_participant or quoted_text:
        logger.info(f"[QUOTE] stanzaId={quoted_message_id}, participant={quoted_message_participant}, text={quoted_text[:50] if quoted_text else None}")

    # Tratar reações (emoji como resposta/reação a mensagem)
    reaction = message.get("reactionMessage") or {}
    if reaction:
        reaction_text = reaction.get("text") or ""
        if reaction_text:
            text_content = text_content or reaction_text

    # Tratar viewOnceMessage (mensagem com visualização única)
    view_once = message.get("viewOnceMessage") or message.get("viewOnceMessageV2") or {}
    if view_once:
        view_msg = view_once.get("message") or {}
        if not text_content:
            text_content = (
                view_msg.get("conversation")
                or view_msg.get("text")
                or (view_msg.get("extendedTextMessage") or {}).get("text")
            )

    # Se ainda não tem texto e é mensagem de texto, marcar como sem texto
    if not text_content and message_type == MessageType.TEXT and not has_media:
        # Log para debug de emojis/reactions
        logger.debug(f"[TEXT] msg_keys={list(message.keys())}, conversation={message.get('conversation')!r}, extendedText={(message.get('extendedTextMessage') or {}).get('text')!r}, reaction={message.get('reactionMessage')}")
        text_content = "[mensagem sem texto]"

    media_url = None
    media_mime_type = None
    media_caption = None

    if message_type == MessageType.IMAGE:
        img = message.get("imageMessage") or {}
        media_url = _normalize_media_url(img.get("url") or img.get("mimetype"))
        media_mime_type = _normalize_mime_type(img.get("mimetype"))
        media_caption = img.get("caption")
    elif message_type == MessageType.AUDIO:
        aud = message.get("audioMessage") or message.get("pttMessage") or {}
        media_url = _normalize_media_url(aud.get("url"))
        media_mime_type = _normalize_mime_type(aud.get("mimetype"))
    elif message_type == MessageType.VIDEO:
        vid = message.get("videoMessage") or {}
        media_url = _normalize_media_url(vid.get("url"))
        media_mime_type = _normalize_mime_type(vid.get("mimetype"))
        media_caption = vid.get("caption")
    elif message_type == MessageType.DOCUMENT:
        doc = message.get("documentMessage") or {}
        media_url = _normalize_media_url(doc.get("url"))
        media_mime_type = _normalize_mime_type(doc.get("mimetype"))
        media_caption = doc.get("fileName") or doc.get("caption")

    msg_id = key.get("id") or root.get("id") or root.get("messageId")

    return {
        "event": event or "messages.upsert",
        "contact_phone": phone,
        "contact_name": root.get("pushName") or root.get("notify"),
        "profile_picture_url": root.get("profilePictureUrl"),
        "direction": direction,
        "message_type": message_type,
        "text_content": text_content,
        "media_url": media_url,
        "media_mime_type": media_mime_type,
        "media_caption": media_caption,
        "external_message_id": msg_id,
        "sender": sender_raw,
        "quoted_message_text": quoted_text,
        "quoted_message_sender": quoted_sender,
        "quoted_message_id": quoted_message_id,
        "quoted_message_participant": quoted_message_participant,
        "is_edited": is_edited_upsert,
        "raw_payload": payload,
    }


def _download_profile_picture(url: str | None, server_url: str | None = None, apikey: str | None = None, instance: str | None = None) -> str | None:
    """Download profile picture and store locally. Returns local path or None."""
    if not url:
        return None

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Failed to download profile picture: {resp.status_code}")
                return None

            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                logger.warning(f"Profile picture URL returned non-image content: {content_type}")
                return None

            image_bytes = resp.content
            if len(image_bytes) < 100:
                logger.warning(f"Profile picture too small ({len(image_bytes)} bytes), likely invalid")
                return None

            # Determine extension from content type or URL
            ext = ".jpg"
            if "png" in content_type or url.lower().endswith(".png"):
                ext = ".png"
            elif "webp" in content_type or url.lower().endswith(".webp"):
                ext = ".webp"
            elif "gif" in content_type or url.lower().endswith(".gif"):
                ext = ".gif"

            filename = f"profile_{secrets.token_hex(8)}{ext}"
            dest = Path(get_settings().media_storage_path) / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(image_bytes)
            return f"/uploads/{filename}"
    except Exception as e:
        logger.warning(f"Error downloading profile picture: {e}")
        return None


def _download_whatsapp_media(url: str | None, mime_type: str | None = None, message_type: MessageType | None = None, raw_payload: dict[str, Any] | None = None) -> str | None:
    """Download media from WhatsApp CDN and store locally. Returns local path or None.
    
    Prioritizes base64 data from the raw payload (which WhatsApp sends directly).
    Falls back to downloading from CDN URL if base64 is not available.
    """
    media_bytes = None

    # First, try to get base64 from the raw payload (EvolutionAPI sends this)
    if raw_payload:
        # Navigate through the payload structure to find base64
        root = raw_payload.get("data") or raw_payload.get("body", {}).get("data") or raw_payload
        message = root.get("message") or {}
        
        # Check for base64 in imageMessage, videoMessage, audioMessage, documentMessage, stickerMessage
        for msg_type in ["imageMessage", "videoMessage", "audioMessage", "documentMessage", "stickerMessage"]:
            msg_data = message.get(msg_type) or {}
            b64_data = msg_data.get("base64")
            if b64_data:
                # base64 might be a dict with numeric keys (from WhatsApp protocol)
                if isinstance(b64_data, dict):
                    # Convert dict with numeric keys to bytes
                    try:
                        media_bytes = bytes(b64_data.values())
                    except Exception:
                        # Try decoding as base64 string if it's encoded
                        pass
                elif isinstance(b64_data, str):
                    # It's a base64 string
                    media_bytes = _decode_base64_media(b64_data)
                if media_bytes:
                    logger.info(f"Extracted {len(media_bytes)} bytes from payload base64 for {msg_type}")
                    break
        
        # Also check for base64 at message root level (some EvolutionAPI versions)
        if not media_bytes:
            msg_b64 = message.get("base64")
            if msg_b64:
                if isinstance(msg_b64, str):
                    media_bytes = _decode_base64_media(msg_b64)
                elif isinstance(msg_b64, dict):
                    try:
                        media_bytes = bytes(msg_b64.values())
                    except Exception:
                        pass
                if media_bytes:
                    logger.info(f"Extracted {len(media_bytes)} bytes from message.base64")

        # Also check for base64 at data root level
        if not media_bytes:
            root_b64 = root.get("base64")
            if root_b64:
                if isinstance(root_b64, str):
                    media_bytes = _decode_base64_media(root_b64)
                elif isinstance(root_b64, dict):
                    try:
                        media_bytes = bytes(root_b64.values())
                    except Exception:
                        pass

    # Fallback: try to download from CDN URL
    if not media_bytes and url and url.startswith("https://mmg.whatsapp.net"):
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    media_bytes = resp.content
                else:
                    logger.warning(f"Failed to download WhatsApp media from CDN: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Error downloading from WhatsApp CDN: {e}")

    if not media_bytes:
        logger.warning(f"[MEDIA] No media bytes extracted from payload. URL={url[:80] if url else None}")
        return None

    logger.info(f"[MEDIA] Extracted {len(media_bytes)} bytes of media data")

    if len(media_bytes) < 100:
        logger.warning(f"WhatsApp media too small ({len(media_bytes)} bytes), likely invalid")
        return None

    if len(media_bytes) > 25 * 1024 * 1024:
        logger.warning(f"WhatsApp media too large ({len(media_bytes)} bytes), skipping")
        return None

    # Determine extension
    ext = ".jpg"  # default
    if mime_type:
        mime_ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "application/pdf": ".pdf",
        }
        ext = mime_ext_map.get(mime_type, ".bin")
    elif message_type == MessageType.IMAGE:
        ext = ".jpg"
    elif message_type == MessageType.VIDEO:
        ext = ".mp4"
    elif message_type == MessageType.AUDIO:
        ext = ".ogg"
    elif message_type == MessageType.DOCUMENT:
        ext = ".pdf"

    filename = f"{secrets.token_hex(16)}{ext}"
    dest = Path(get_settings().media_storage_path) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(media_bytes)
    return f"/uploads/{filename}"


def _get_or_create_conversation(
    db: Session,
    contact_phone: str,
    contact_name: str | None = None,
) -> Conversation:
    phone = _normalize_phone(contact_phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Telefone inválido.")

    conversation = db.scalar(
        select(Conversation).where(Conversation.contact_phone == phone)
    )
    if conversation:
        if contact_name and not conversation.contact_name:
            conversation.contact_name = contact_name
            db.commit()
            db.refresh(conversation)
        return conversation

    conversation = Conversation(contact_phone=phone, contact_name=contact_name)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def ingest_inbound_message(db: Session, payload: dict[str, Any]) -> Conversation | Message | None:
    normalized = normalize_webhook_payload(payload)

    if not normalized.get("contact_phone"):
        raise HTTPException(status_code=400, detail="Webhook sem telefone do contato.")

    contact_phone = normalized["contact_phone"]
    direction = normalized.get("direction", MessageDirection.INBOUND)
    direction = normalized.get("direction", MessageDirection.INBOUND)
    event = normalized.get("event")

    logger.info(f"[INGEST] event={event}, direction={direction}, phone={contact_phone}, ext_id={normalized.get('external_message_id')}, msg_type={normalized.get('message_type')}, text={str(normalized.get('text_content'))[:30] if normalized.get('text_content') else None}, media={str(normalized.get('media_url'))[:50] if normalized.get('media_url') else None}")

    # secretEncryptedMessage: mensagem criptografada de edição do WhatsApp
    # Não podemos ler o conteúdo, mas podemos marcar a original como editada
    if event == "messages.secret_encrypted":
        target_msg_id = normalized.get("external_message_id")
        logger.info(f"[ENCRYPTED] secretEncryptedMessage para {contact_phone}, target_msg_id={target_msg_id}")
        if target_msg_id:
            message = db.scalar(select(Message).where(Message.external_message_id == target_msg_id))
            if message:
                logger.info(f"[ENCRYPTED] Mensagem original encontrada id={message.id}, marcando como editada")
                message.is_edited = True
                db.commit()
                db.refresh(message)
                return message
            else:
                logger.info(f"[ENCRYPTED] Mensagem original não encontrada para {target_msg_id}")
        return None

    # Para eventos de edição/deleção, buscar por external_message_id primeiro
    # (LID pode não corresponder ao telefone da conversa)
    if event in ("messages.edited", "messages.edit", "messages.delete"):
        msg_id = normalized.get("external_message_id")
        new_text = normalized.get("edited_text") if event != "messages.delete" else None

        logger.info(f"[EDIT-IN] event={event}, external_id={msg_id}, phone={contact_phone}, new_text={new_text!r}, raw_keys={list(normalized.keys())}")

        if msg_id:
            # Buscar por external_message_id (WhatsApp key ID)
            message = db.scalar(select(Message).where(Message.external_message_id == msg_id))
            logger.info(f"[EDIT-IN] Buscando external_id={msg_id}, encontrou={message is not None}")
            if message:
                logger.info(f"[EDIT-IN] Msg encontrada: id={message.id}, text_old={message.text_content[:50] if message.text_content else None}, is_edited={message.is_edited}")

            # Fallback: tentar buscar por messageId (interno EvolutionAPI)
            if not message:
                evo_msg_id = normalized.get("raw_payload", {}).get("data", {}).get("messageId")
                if evo_msg_id and evo_msg_id != msg_id:
                    logger.info(f"[EDIT-IN] Tentando fallback com messageId={evo_msg_id}")
                    message = db.scalar(select(Message).where(Message.external_message_id == evo_msg_id))

            # Fallback 2: buscar na conversa por texto similar nos ultimos 5 min
            if not message and contact_phone:
                five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
                conversation = db.scalar(select(Conversation).where(Conversation.contact_phone == contact_phone))
                if conversation:
                    # Log para debug: listar external_ids recentes da conversa
                    recent_msgs = db.scalars(
                        select(Message).where(
                            Message.conversation_id == conversation.id,
                            Message.created_at >= five_min_ago,
                        ).order_by(Message.created_at.desc())
                    ).all()
                    for rm in recent_msgs[:5]:
                        logger.info(f"[EDIT-IN] Msg recente id={rm.id} ext_id={rm.external_message_id} dir={rm.direction} text={rm.text_content[:30] if rm.text_content else None}")
                    
                    message = db.scalar(
                        select(Message).where(
                            Message.conversation_id == conversation.id,
                            Message.direction == MessageDirection.INBOUND,
                            Message.created_at >= five_min_ago,
                        ).order_by(Message.created_at.desc())
                    )
                    if message:
                        logger.info(f"[EDIT-IN] Fallback 2: mensagem encontrada por conversa+tempo id={message.id} ext_id={message.external_message_id}")

            if message and event in ("messages.edited", "messages.edit"):
                if new_text:
                    logger.info(f"[EDIT-IN] Mensagem encontrada id={message.id}, atualizando texto: {new_text!r}")
                    message.text_content = new_text
                    message.is_edited = True
                    message.message_type = MessageType.TEXT
                    db.commit()
                    db.refresh(message)
                    return message
                else:
                    # Mesmo sem novo texto, marcar como editado (pode ser edição de mídia)
                    logger.info(f"[EDIT-IN] Mensagem encontrada id={message.id}, sem novo texto mas marcando como editada")
                    message.is_edited = True
                    db.commit()
                    db.refresh(message)
                    return message
            elif message and event == "messages.delete":
                logger.info(f"[EDIT-IN] Deletando mensagem id={message.id}")
                message.text_content = "🚫 Essa mensagem foi apagada"
                message.media_url = None
                message.media_mime_type = None
                message.message_type = MessageType.TEXT
                db.commit()
                db.refresh(message)
                return message
            else:
                logger.warning(f"[EDIT-IN] Nenhuma mensagem encontrada para external_id={msg_id}")
        return None

    # Ignore webhooks where the contact phone is the UFPB system bot itself
    if contact_phone == "+558332167336":
        return None

    # Ignore webhooks where the contact phone matches the instance's own number
    sender_phone = _normalize_phone(payload.get("sender"))
    if sender_phone and contact_phone == sender_phone:
        return None

    # Tratamento especial de Eventos Atualização (status)
    if event == "messages.update":
        msg_id = normalized.get("external_message_id")
        delivery_status = normalized.get("delivery_status")
        if msg_id and delivery_status is not None:
            message = db.scalar(select(Message).where(Message.external_message_id == msg_id))
            if message:
                message.delivery_status = delivery_status
                db.commit()
                db.refresh(message)
                return message
        return None

    contact_name = normalized.get("contact_name")
    if direction == MessageDirection.OUTBOUND and contact_name and contact_name.strip().upper() == "CAU":
        contact_name = None

    # For contact sync events, only update existing conversations (don't create empty ones)
    if event in ("contacts.upsert", "contacts.update"):
        existing = db.scalar(
            select(Conversation).where(Conversation.contact_phone == normalized["contact_phone"])
        )
        if existing:
            if contact_name and not existing.contact_name:
                existing.contact_name = contact_name
                db.commit()
            profile_pic = normalized.get("profile_picture_url")
            if profile_pic:
                local_path = _download_profile_picture(profile_pic, server_url=payload.get("server_url"), apikey=payload.get("apikey"), instance=payload.get("instance"))
                if local_path:
                    existing.profile_picture_url = local_path
                elif not existing.profile_picture_url:
                    existing.profile_picture_url = profile_pic
                db.commit()
            return existing
        return None

    conversation = _get_or_create_conversation(
        db=db,
        contact_phone=normalized["contact_phone"],
        contact_name=contact_name,
    )
    logger.info(f"[INGEST] conversation id={conversation.id}, phone={conversation.contact_phone}")

    profile_pic = normalized.get("profile_picture_url")
    if profile_pic:
        # Sempre tentar baixar e armazenar localmente
        local_path = _download_profile_picture(profile_pic, server_url=payload.get("server_url"), apikey=payload.get("apikey"), instance=payload.get("instance"))
        if local_path:
            conversation.profile_picture_url = local_path
        elif not conversation.profile_picture_url:
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
                            local_path = _download_profile_picture(fetched_url)
                            conversation.profile_picture_url = local_path or fetched_url
                            db.commit()
                            db.refresh(conversation)
                    else:
                        logger.error(f"Evolution API fetchProfile fail: {resp.status_code}")
            except Exception as e:
                logger.error(f"Erro ao tentar cachear foto de perfil: {e}")

    conversation.last_message_at = datetime.now(timezone.utc)

    # Verificar se mensagem já existe (evitar duplicatas)
    external_id = normalized.get("external_message_id")
    is_edited_upsert = normalized.get("is_edited", False)
    if external_id:
        existing_message = db.scalar(
            select(Message).where(Message.external_message_id == external_id)
        )
        if existing_message:
            # Se é edição via upsert, atualizar o texto
            if is_edited_upsert and normalized.get("text_content"):
                existing_message.text_content = normalized["text_content"]
                existing_message.is_edited = True
                existing_message.message_type = normalized.get("message_type") or existing_message.message_type
                db.commit()
                db.refresh(existing_message)
                return existing_message
            # Mensagem já existe, não criar duplicata
            # Apenas atualizar o status se necessário
            if existing_message.delivery_status == DeliveryStatus.SENT and direction == MessageDirection.OUTBOUND:
                existing_message.delivery_status = DeliveryStatus.DELIVERED
                db.commit()
                db.refresh(existing_message)
            return existing_message

    # DEDUP universal: verificar se existe mensagem recente sem external_message_id
    # na mesma conversa com mesmo tipo/texto (evita duplicata para inbound e outbound)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    txt = normalized.get("text_content")
    mtype = normalized.get("message_type")
    candidates = db.scalars(
        select(Message).where(
            Message.conversation_id == conversation.id,
            Message.external_message_id.is_(None),
            Message.created_at >= recent_cutoff,
        ).order_by(Message.created_at.desc())
    ).all()

    for candidate in candidates:
        # Ignorar candidatos com direction diferente (a menos que ambos sejam OUTBOUND)
        if candidate.direction != direction and not (candidate.direction == MessageDirection.OUTBOUND and direction == MessageDirection.OUTBOUND):
            continue

        # Para mídia sem texto, matching por message_type é suficiente
        if txt is None and mtype is not None and candidate.message_type == mtype:
            logger.info(f"[DEDUP] Duplicata evitada (tipo mídia): id={candidate.id}, ext_id={external_id}, conv_id={conversation.id}")
            candidate.external_message_id = external_id
            candidate.delivery_status = DeliveryStatus.DELIVERED if direction == MessageDirection.OUTBOUND else candidate.delivery_status
            candidate.raw_payload = normalized.get("raw_payload")
            db.commit()
            db.refresh(candidate)
            return candidate

        # Para texto, matching por text_content
        if txt is not None:
            txt_match = (candidate.text_content == txt) or (txt is None and candidate.text_content is None)
            if txt_match:
                logger.info(f"[DEDUP] Duplicata evitada (texto): id={candidate.id}, ext_id={external_id}, conv_id={conversation.id}")
                candidate.external_message_id = external_id
                candidate.delivery_status = DeliveryStatus.DELIVERED if direction == MessageDirection.OUTBOUND else candidate.delivery_status
                candidate.raw_payload = normalized.get("raw_payload")
                db.commit()
                db.refresh(candidate)
                return candidate

        # Se não tem texto nem tipo, qualquer mensagem recente sem ext_id é candidata
        if txt is None and mtype is None and candidate.text_content is None and candidate.message_type is None:
            logger.info(f"[DEDUP] Duplicata evitada (sem dados): id={candidate.id}, ext_id={external_id}, conv_id={conversation.id}")
            candidate.external_message_id = external_id
            candidate.delivery_status = DeliveryStatus.DELIVERED if direction == MessageDirection.OUTBOUND else candidate.delivery_status
            candidate.raw_payload = normalized.get("raw_payload")
            db.commit()
            db.refresh(candidate)
            return candidate

    sender_name = normalized.get("contact_name")
    delivery_status = DeliveryStatus.RECEIVED
    if direction == MessageDirection.OUTBOUND:
        if sender_name and sender_name.strip().upper() == "CAU":
            sender_name = None
        delivery_status = DeliveryStatus.SENT

    # Para mensagens inbound com mídia, tentar baixar e armazenar localmente
    media_url = normalized.get("media_url")
    if direction == MessageDirection.INBOUND and media_url:
        local_media_path = _download_whatsapp_media(
            media_url,
            mime_type=normalized.get("media_mime_type"),
            message_type=normalized.get("message_type"),
            raw_payload=normalized.get("raw_payload"),
        )
        if local_media_path:
            media_url = local_media_path

    message = Message(
        conversation_id=conversation.id,
        direction=direction,
        message_type=normalized["message_type"],
        delivery_status=delivery_status,
        text_content=normalized["text_content"],
        media_url=media_url,
        media_mime_type=normalized["media_mime_type"],
        media_caption=normalized["media_caption"],
        sender_name=sender_name,
        sender_phone=normalized["contact_phone"],
        external_message_id=external_id,
        raw_payload=normalized.get("raw_payload"),
        quoted_message_text=normalized.get("quoted_message_text"),
        quoted_message_sender=normalized.get("quoted_message_sender"),
        quoted_message_id=normalized.get("quoted_message_id"),
        quoted_message_participant=normalized.get("quoted_message_participant"),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def _build_outbound_request_security(
    runtime_settings: RuntimeSettings,
) -> tuple[dict[str, str] | None, httpx.Auth | None]:
    """Build headers and auth for outbound webhook request."""
    headers = None
    auth = None

    auth_type = runtime_settings.outbound_auth_type or "none"

    if auth_type == "header" and runtime_settings.outbound_auth_header_name:
        headers = {runtime_settings.outbound_auth_header_name: runtime_settings.outbound_auth_header_value or ""}
    elif auth_type == "basic" and runtime_settings.outbound_auth_basic_username:
        auth = httpx.BasicAuth(
            username=runtime_settings.outbound_auth_basic_username or "",
            password=runtime_settings.outbound_auth_basic_password or "",
        )
    elif auth_type == "jwt" and runtime_settings.outbound_auth_jwt_token:
        headers = {"Authorization": f"Bearer {runtime_settings.outbound_auth_jwt_token}"}

    return headers, auth


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
        quoted_message_text=data.quoted_message_text,
        quoted_message_sender=data.quoted_message_sender,
        quoted_message_id=data.quoted_message_id,
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
            # TESTE: Sem conversão - usa URL direta do vídeo bruto
            logger.info(f"TESTE SEM CONVERSÃO: Usando URL direta do vídeo: {data.media_url}")
            logger.info(f"MIME type: {data.media_mime_type}")
            final_media_url = data.media_url
            final_mime_type = data.media_mime_type  # Mantém MIME original

        except Exception as e:
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

    # Incluir contexto de reply/quote para WhatsApp (n8n deve repassar ao EvolutionAPI)
    if data.quoted_message_id:
        outbound_payload["contextInfo"] = {
            "stanzaId": data.quoted_message_id,
            "participant": data.quoted_message_participant or "",
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
