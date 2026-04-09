from datetime import datetime

from pydantic import BaseModel


class ConversationRead(BaseModel):
    id: int
    contact_phone: str
    contact_name: str | None
    profile_picture_url: str | None = None
    created_at: datetime
    last_message_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    contact_phone: str
    contact_name: str | None = None
