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
from app.schemas.conversation import ConversationRead, ConversationCreate
from app.schemas.export import ConversationExportResponse
from app.schemas.message import (
    MessageBulkDeleteRequest,
    MessageBulkDeleteResponse,
    MessageRead,
    OutboundMessageCreate,
    MessageSearchResult,
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


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> ConversationRead:
    from app.services.messages import _normalize_phone, _get_or_create_conversation
    
    # Normaliza o telefone enviado
    base_phone = _normalize_phone(payload.contact_phone)
    if not base_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Telefone inválido."
        )
        
    # Tratamento específico para o nono dígito no Brasil (+55)
    # Se for BR e tiver 13 dígitos (ex: +55 83 9XXXX-XXXX), 
    # ou 12 dígitos (ex: +55 83 XXXX-XXXX), buscar pelo outro também.
    phones_to_check = [base_phone]
    if base_phone.startswith("+55") and len(base_phone) == 14 and base_phone[5] == "9":
        # Tem o 9, adicionar versão sem o 9
        phones_to_check.append(base_phone[:5] + base_phone[6:])
    elif base_phone.startswith("+55") and len(base_phone) == 13:
        # Não tem o 9, adicionar versão com o 9
        phones_to_check.append(base_phone[:5] + "9" + base_phone[5:])
        
    # Busca por conversas existentes verificando ambas as variações
    existing = db.scalar(
        select(Conversation).where(Conversation.contact_phone.in_(phones_to_check))
    )
    
    if existing:
        if payload.contact_name and existing.contact_name != payload.contact_name:
            existing.contact_name = payload.contact_name
            db.commit()
            db.refresh(existing)
        return ConversationRead.model_validate(existing)
        
    # Se não existir, cria a conversa usando o formato primário (com o 9 se fornecido)
    conversation = _get_or_create_conversation(
        db=db, 
        contact_phone=base_phone, 
        contact_name=payload.contact_name
    )
    # Garante commit no bd da API
    db.commit()
    db.refresh(conversation)
    
    return ConversationRead.model_validate(conversation)


@router.get("/contacts/all", response_model=list[ConversationRead])
def list_contacts(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> list[ConversationRead]:
    # Returns all users ever interacted with, irrespective of having active messages
    conversations = db.scalars(
        select(Conversation)
        .order_by(Conversation.contact_name.asc(), Conversation.contact_phone.asc())
    ).all()
    return [ConversationRead.model_validate(item) for item in conversations]

@router.get("/search/messages", response_model=list[MessageSearchResult])
def search_messages(
    q: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_password_changed),
) -> list[MessageSearchResult]:
    query_str = f"%{q}%"
    messages_and_convs = db.query(Message, Conversation).\
        join(Conversation, Message.conversation_id == Conversation.id).\
        filter(Message.text_content.ilike(query_str)).\
        order_by(Message.created_at.desc()).\
        limit(50).all()

    results = []
    for msg, conv in messages_and_convs:
        results.append(MessageSearchResult(
            message_id=msg.id,
            conversation_id=conv.id,
            contact_name=conv.contact_name,
            contact_phone=conv.contact_phone,
            text_content=msg.text_content,
            created_at=msg.created_at,
            direction=msg.direction,
        ))
    return results


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

@router.post(
    "/{conversation_id}/messages/{message_id}/revoke",
    response_model=MessageRead,
)
async def revoke_message(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_password_changed),
) -> MessageRead:
    import httpx
    from app.services.runtime_settings import get_or_create_runtime_settings, get_outbound_webhook_url
    from app.services.messages import _build_outbound_request_security
    
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    message = db.scalar(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.id == message_id,
        )
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensagem não encontrada.",
        )

    if not message.external_message_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível revogar uma mensagem que não possui identificador externo no WhatsApp.",
        )

    runtime_settings = get_or_create_runtime_settings(db)
    outbound_webhook_url = get_outbound_webhook_url(runtime_settings)
    
    if outbound_webhook_url:
        outbound_payload = {
            "conversation_id": conversation.id,
            "message_id": message.id,
            "external_message_id": message.external_message_id,
            "to": conversation.contact_phone,
            "message_type": "revoke",
            "text": "Revogar mensagem",
            "attendant": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
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
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Falha ao enviar requisição de revogação para N8N: {exc}",
            )

    # Marca imediatamente como apagada no banco
    message.text_content = "🚫 Essa mensagem foi apagada"
    message.media_url = None
    message.media_mime_type = None
    message.message_type = MessageType.TEXT
    db.commit()
    db.refresh(message)

    return MessageRead.model_validate(message)


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

    db.query(Message).filter(Message.conversation_id == conversation_id).delete(synchronize_session=False)
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

    db.query(Message).delete(synchronize_session=False)
    db.query(Conversation).delete(synchronize_session=False)
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
