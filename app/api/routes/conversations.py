from datetime import date, time
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user_password_changed
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ConversationRead
from app.schemas.export import ConversationExportResponse
from app.schemas.message import (
    MessageBulkDeleteRequest,
    MessageBulkDeleteResponse,
    MessageRead,
    OutboundMessageCreate,
)
from app.services.conversation_export import (
    build_export_payload,
    build_pdf_bytes,
    get_conversation_and_messages_for_range,
)
from app.services.messages import create_outbound_message

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _refresh_or_remove_empty_conversation(db: Session, conversation: Conversation) -> bool:
    latest_message_at = db.scalar(
        select(Message.created_at)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    if latest_message_at is None:
        db.delete(conversation)
        return True

    conversation.last_message_at = latest_message_at
    return False


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> list[ConversationRead]:
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.messages.any())
        .order_by(Conversation.last_message_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [ConversationRead.model_validate(item) for item in conversations]


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
def list_messages(
    conversation_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> list[MessageRead]:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    return [MessageRead.model_validate(item) for item in reversed(messages)]


@router.post("/{conversation_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: int,
    payload: OutboundMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_password_changed),
) -> MessageRead:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    message = await create_outbound_message(
        db=db,
        conversation=conversation,
        attendant=current_user,
        data=payload,
    )
    return MessageRead.model_validate(message)


@router.post(
    "/{conversation_id}/messages/delete-selected",
    response_model=MessageBulkDeleteResponse,
)
def delete_selected_messages(
    conversation_id: int,
    payload: MessageBulkDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> MessageBulkDeleteResponse:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    messages = db.scalars(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.id.in_(payload.message_ids),
        )
    ).all()
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma mensagem encontrada para os IDs informados.",
        )

    for message in messages:
        db.delete(message)

    db.flush()
    _refresh_or_remove_empty_conversation(db, conversation)
    db.commit()

    return MessageBulkDeleteResponse(deleted_count=len(messages))


@router.delete(
    "/{conversation_id}/messages/all",
    response_model=MessageBulkDeleteResponse,
)
def delete_all_messages_from_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> MessageBulkDeleteResponse:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    total_messages = db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    ) or 0

    db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    db.flush()
    _refresh_or_remove_empty_conversation(db, conversation)
    db.commit()

    return MessageBulkDeleteResponse(deleted_count=total_messages)


@router.delete("/messages/all", response_model=MessageBulkDeleteResponse)
def delete_all_messages(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> MessageBulkDeleteResponse:
    total_messages = db.scalar(select(func.count()).select_from(Message)) or 0

    db.execute(delete(Message))
    db.execute(delete(Conversation))
    db.commit()

    return MessageBulkDeleteResponse(deleted_count=total_messages)


@router.get("/{conversation_id}/export", response_model=ConversationExportResponse)
def export_conversation_data(
    conversation_id: int,
    export_date: date,
    start_time: time = Query(default=time(0, 0)),
    end_time: time = Query(default=time(23, 59)),
    contact_profile: str = Query(default="indefinido"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> ConversationExportResponse:
    try:
        conversation, messages = get_conversation_and_messages_for_range(
            db=db,
            conversation_id=conversation_id,
            export_date=export_date,
            start_time=start_time,
            end_time=end_time,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Conversa não encontrada.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    return build_export_payload(
        conversation=conversation,
        messages=messages,
        export_date=export_date,
        start_time=start_time,
        end_time=end_time,
        contact_profile=contact_profile,
    )


@router.get("/{conversation_id}/export/pdf")
def export_conversation_pdf(
    conversation_id: int,
    export_date: date,
    start_time: time = Query(default=time(0, 0)),
    end_time: time = Query(default=time(23, 59)),
    contact_profile: str = Query(default="indefinido"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> StreamingResponse:
    try:
        conversation, messages = get_conversation_and_messages_for_range(
            db=db,
            conversation_id=conversation_id,
            export_date=export_date,
            start_time=start_time,
            end_time=end_time,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Conversa não encontrada.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    export_data = build_export_payload(
        conversation=conversation,
        messages=messages,
        export_date=export_date,
        start_time=start_time,
        end_time=end_time,
        contact_profile=contact_profile,
    )
    pdf_bytes = build_pdf_bytes(export_data)
    filename = (
        f"conversa_{conversation_id}_{export_date.isoformat()}_{start_time.strftime('%H%M')}"
        f"_{end_time.strftime('%H%M')}.pdf"
    )
    stream = BytesIO(pdf_bytes)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(stream, media_type="application/pdf", headers=headers)
