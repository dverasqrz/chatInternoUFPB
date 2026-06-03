from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_admin: bool
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    last_logout_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool
