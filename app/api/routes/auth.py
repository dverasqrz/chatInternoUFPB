from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginChallengeResponse,
    LoginRequest,
    LogoutResponse,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.login_challenge import generate_login_challenge, verify_login_challenge
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/challenge", response_model=LoginChallengeResponse)
def login_challenge(response: Response) -> LoginChallengeResponse:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    challenge = generate_login_challenge()
    return LoginChallengeResponse(**challenge)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if not verify_login_challenge(payload.challenge_id, payload.challenge_answer):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Charada inválida ou expirada.")

    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário desativado.")

    now = datetime.now(timezone.utc)
    user.last_login_at = now
    user.last_interaction_at = now
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=token,
        must_change_password=user.must_change_password,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Get current authenticated user information."""
    return UserRead.model_validate(current_user)


@router.get("/config", response_model=dict)
def get_public_config() -> dict:
    """Get public configuration for frontend (domain, etc.)."""
    from app.core.config import get_settings
    
    settings = get_settings()
    
    return {
        "public_domain": settings.public_domain,
        "api_prefix": settings.api_v1_prefix,
        "environment": settings.environment,
        "debug": settings.debug,
    }


@router.post("/change-password", response_model=UserRead)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    current_user.last_interaction_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    return UserRead.model_validate(current_user)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    current_user.last_logout_at = datetime.now(timezone.utc)
    db.commit()
    return LogoutResponse(status="ok")
