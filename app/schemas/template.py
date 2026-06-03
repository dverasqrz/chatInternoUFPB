from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MessageTemplateBase(BaseModel):
    """Base schema for message templates."""
    title: str = Field(..., min_length=1, max_length=200, description="Template title")
    content: str = Field(..., min_length=1, description="Template content")
    category: str = Field(..., min_length=1, max_length=50, description="Template category")


class MessageTemplateCreate(MessageTemplateBase):
    """Schema for creating a new message template."""
    pass


class MessageTemplateUpdate(BaseModel):
    """Schema for updating a message template."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Template title")
    content: Optional[str] = Field(None, min_length=1, description="Template content")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="Template category")
    is_active: Optional[bool] = Field(None, description="Whether the template is active")


class MessageTemplateResponse(MessageTemplateBase):
    """Schema for message template response."""
    id: int
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True


class MessageTemplateList(BaseModel):
    """Schema for list of message templates."""
    templates: list[MessageTemplateResponse]
    total: int
