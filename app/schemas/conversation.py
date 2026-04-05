from datetime import datetime

from pydantic import BaseModel


class ConversationRead(BaseModel):
    id: int
    contact_phone: str
    contact_name: str | None
    created_at: datetime
    last_message_at: datetime

    model_config = {"from_attributes": True}
