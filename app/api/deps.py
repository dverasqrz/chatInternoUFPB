from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
INACTIVITY_LIMIT = timedelta(days=7)


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise credentials_error from exc

    subject = payload.get("sub")
    if not subject or not subject.isdigit():
        raise credentials_error

    user = db.get(User, int(subject))
    if not user:
        raise credentials_error

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")

    reference = user.last_interaction_at or user.last_login_at
    if reference and datetime.now(timezone.utc) - reference > INACTIVITY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada por 7 dias sem interação. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user_password_changed(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Troca de senha obrigatória antes de continuar.",
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user_password_changed),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para administradores.",
        )
    return current_user
