from __future__ import annotations

import base64
from datetime import date, datetime, time, timezone
from io import BytesIO
import mimetypes
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.message import Message, MessageDirection, MessageType
from app.schemas.export import ConversationExportEntry, ConversationExportResponse

RECIFE_TZ = ZoneInfo("America/Recife")
PROFILE_LABELS = {
    "aluno": "Aluno",
    "professor": "Professor",
    "funcionario": "Funcionário",
    "funcionário": "Funcionário",
    "externo": "Externo",
    "ex-aluno": "Ex-aluno",
    "ex_aluno": "Ex-aluno",
    "multiplos": "Múltiplos",
    "múltiplos": "Múltiplos",
    "indefinido": "Indefinido",
}


def _normalized_contact_profile(raw_profile: str | None) -> str:
    candidate = (raw_profile or "").strip().lower()
    return PROFILE_LABELS.get(candidate, "Indefinido")


def _message_content(message: Message) -> str:
    text = (message.text_content or "").strip()
    if text:
        return text
    if message.message_type == MessageType.IMAGE:
        return "[imagem]"
    if message.media_url:
        return f"[{message.message_type.value}] {message.media_url}"
    return "[sem conteúdo textual]"


def _author_label(message: Message, conversation: Conversation, contact_profile: str) -> tuple[str, str]:
    if message.direction == MessageDirection.INBOUND:
        display_name = conversation.contact_name or "Cliente sem nome"
        role_label = contact_profile
        return display_name, role_label
    display_name = message.sender_name or "Funcionário"
    return display_name, "funcionário"


def _resolve_local_media_path(media_url: str | None) -> Path | None:
    if not media_url:
        return None
    if not media_url.startswith("/uploads/"):
        return None

    settings = get_settings()
    file_name = Path(media_url).name
    if not file_name:
        return None
    candidate = (settings.media_storage_path / file_name).resolve()
    storage_resolved = settings.media_storage_path.resolve()
    if storage_resolved not in candidate.parents and candidate != storage_resolved:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def _embedded_image_data(message: Message) -> tuple[str | None, bytes | None]:
    if message.message_type != MessageType.IMAGE:
        return None, None

    local_path = _resolve_local_media_path(message.media_url)
    if not local_path:
        return None, None

    try:
        image_bytes = local_path.read_bytes()
    except OSError:
        return None, None

    guessed_mime = message.media_mime_type or mimetypes.guess_type(local_path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{guessed_mime};base64,{encoded}"
    return data_url, image_bytes


def _image_bytes_from_data_url(data_url: str | None) -> bytes | None:
    if not data_url or "," not in data_url:
        return None
    try:
        _, encoded = data_url.split(",", 1)
        return base64.b64decode(encoded)
    except (ValueError, base64.binascii.Error):
        return None


def build_export_payload(
    conversation: Conversation,
    messages: list[Message],
    export_date: date,
    start_time: time,
    end_time: time,
    contact_profile: str | None,
) -> ConversationExportResponse:
    normalized_profile = _normalized_contact_profile(contact_profile)
    entries: list[ConversationExportEntry] = []
    for message in messages:
        created_local = message.created_at.astimezone(RECIFE_TZ)
        author_name, author_role = _author_label(message, conversation, normalized_profile)
        embedded_image_data_url, _ = _embedded_image_data(message)
        entries.append(
            ConversationExportEntry(
                timestamp_recife=created_local.strftime("%d/%m/%Y %H:%M"),
                author_name=author_name,
                author_role=author_role,
                message_type=message.message_type.value,
                content=_message_content(message),
                media_url=message.media_url,
                embedded_image_data_url=embedded_image_data_url,
            )
        )

    return ConversationExportResponse(
        conversation_id=conversation.id,
        contact_name=conversation.contact_name or "Cliente sem nome",
        contact_phone=conversation.contact_phone,
        contact_profile=normalized_profile,
        date=export_date.isoformat(),
        start_time=start_time.strftime("%H:%M"),
        end_time=end_time.strftime("%H:%M"),
        entries=entries,
    )


def get_conversation_and_messages_for_range(
    db: Session,
    conversation_id: int,
    export_date: date,
    start_time: time,
    end_time: time,
) -> tuple[Conversation, list[Message]]:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise ValueError("Conversa não encontrada.")

    start_local = datetime.combine(export_date, start_time, tzinfo=RECIFE_TZ)
    end_local = datetime.combine(export_date, end_time, tzinfo=RECIFE_TZ)
    if end_local < start_local:
        raise ValueError("Intervalo inválido: horário final anterior ao inicial.")

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    messages = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.created_at >= start_utc,
            Message.created_at <= end_utc,
        )
        .order_by(Message.created_at.asc())
    ).all()
    return conversation, messages


def build_pdf_bytes(export_data: ConversationExportResponse) -> bytes:
    buffer = BytesIO()
    safe_name = export_data.contact_name.replace(" ", "_")
    document = SimpleDocTemplate(buffer, pagesize=A4, title=f"{safe_name}_{export_data.date}")
    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    body_style.leading = 14

    story: list[object] = []
    story.append(Paragraph("<b>Relatório de Conversa</b>", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            escape(
                f"Cliente: {export_data.contact_name} | Perfil: {export_data.contact_profile} | "
                f"Telefone: {export_data.contact_phone}"
            ),
            body_style,
        )
    )
    story.append(
        Paragraph(
            escape(f"Intervalo: {export_data.date} de {export_data.start_time} até {export_data.end_time}"),
            body_style,
        )
    )
    story.append(Spacer(1, 12))

    if not export_data.entries:
        story.append(Paragraph("Sem mensagens no intervalo selecionado.", body_style))
    else:
        for item in export_data.entries:
            line = (
                f"[{item.timestamp_recife}] {item.author_name} ({item.author_role}) - "
                f"{item.content}"
            )
            story.append(Paragraph(escape(line), body_style))
            image_bytes = _image_bytes_from_data_url(item.embedded_image_data_url)
            if image_bytes:
                try:
                    reader = ImageReader(BytesIO(image_bytes))
                    width, height = reader.getSize()
                    max_width = 380
                    max_height = 280
                    ratio = min(max_width / width, max_height / height, 1.0)
                    image = RLImage(BytesIO(image_bytes), width=width * ratio, height=height * ratio)
                    story.append(Spacer(1, 4))
                    story.append(image)
                except Exception:
                    story.append(Paragraph("Imagem não pôde ser incorporada ao PDF.", body_style))
            elif item.media_url:
                story.append(Paragraph(escape(f"Mídia: {item.media_url}"), body_style))
            story.append(Spacer(1, 6))

    document.build(story)
    return buffer.getvalue()
