from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.message import DeliveryStatus, MessageDirection, MessageType


class OutboundMessageCreate(BaseModel):
    message_type: MessageType = MessageType.TEXT
    text_content: str | None = Field(default=None, max_length=6000)
    media_url: str | None = None
    media_mime_type: str | None = Field(default=None, max_length=150)
    media_caption: str | None = Field(default=None, max_length=2000)
    quoted_message_text: str | None = Field(default=None, max_length=200)
    quoted_message_sender: str | None = Field(default=None, max_length=120)
    quoted_message_id: str | None = Field(default=None, max_length=150)
    quoted_message_participant: str | None = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def validate_payload(self) -> "OutboundMessageCreate":
        if self.message_type == MessageType.TEXT and not self.text_content:
            raise ValueError("Mensagem de texto precisa de text_content.")
        if self.message_type in {MessageType.IMAGE, MessageType.AUDIO, MessageType.VIDEO} and not self.media_url:
            raise ValueError("Mensagens de mídia precisam de media_url.")
        return self


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    direction: MessageDirection
    message_type: MessageType
    delivery_status: DeliveryStatus
    text_content: str | None
    media_url: str | None
    media_mime_type: str | None
    media_caption: str | None
    sender_name: str | None
    sender_phone: str | None
    attendant_id: int | None
    external_message_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime | None = None
    is_edited: bool = False
    is_read: bool = False
    quoted_message_text: str | None = None
    quoted_message_sender: str | None = None
    quoted_message_id: str | None = None
    quoted_message_participant: str | None = None

    model_config = {"from_attributes": True}


class WebhookIngestResponse(BaseModel):
    status: str
    conversation_id: int | None = None
    message_id: int | None = None
    message_type: MessageType | None = None


class MessageBulkDeleteRequest(BaseModel):
    message_ids: list[int] = Field(default_factory=list, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_ids(self) -> "MessageBulkDeleteRequest":
        ids = [item for item in self.message_ids if isinstance(item, int) and item > 0]
        unique_sorted = sorted(set(ids))
        if not unique_sorted:
            raise ValueError("Informe pelo menos um ID de mensagem válido.")
        self.message_ids = unique_sorted
        return self


class MessageBulkDeleteResponse(BaseModel):
    status: str = "ok"
    deleted_count: int


class MessageSearchResult(BaseModel):
    message_id: int
    conversation_id: int
    contact_name: str | None = None
    contact_phone: str | None = None
    text_content: str | None = None
    created_at: datetime
    direction: MessageDirection


class MessageEditRequest(BaseModel):
    text_content: str = Field(min_length=1, max_length=6000)
