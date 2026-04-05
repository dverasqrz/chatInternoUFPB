from pydantic import BaseModel


class ConversationExportEntry(BaseModel):
    timestamp_recife: str
    author_name: str
    author_role: str
    message_type: str
    content: str
    media_url: str | None
    embedded_image_data_url: str | None


class ConversationExportResponse(BaseModel):
    conversation_id: int
    contact_name: str
    contact_phone: str
    contact_profile: str
    date: str
    start_time: str
    end_time: str
    entries: list[ConversationExportEntry]
