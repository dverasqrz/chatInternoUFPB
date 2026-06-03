from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    challenge_id: str = Field(min_length=3, max_length=128)
    challenge_answer: str = Field(min_length=1, max_length=20)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_passwords(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("A nova senha deve ser diferente da atual.")
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    user: UserRead


class LoginChallengeResponse(BaseModel):
    challenge_id: str
    question: str
    expires_in_seconds: int


class LogoutResponse(BaseModel):
    status: str
