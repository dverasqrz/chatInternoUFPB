from datetime import datetime, timezone
from pathlib import Path
import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.utils.security import hash_password


def _generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _write_bootstrap_credentials(path: Path, email: str, password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    content = (
        "Administrador inicial criado com sucesso.\n"
        f"created_at_utc: {created_at}\n"
        f"email: {email}\n"
        f"password: {password}\n"
        "important: altere esta senha assim que possível.\n"
    )
    path.write_text(content, encoding="utf-8")


def ensure_initial_admin_user(db: Session) -> None:
    settings = get_settings()
    existing_admin = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
    if existing_admin:
        return

    generated_password = _generate_password()
    admin = User(
        name=settings.admin_name,
        email=settings.admin_email.lower(),
        password_hash=hash_password(generated_password),
        is_admin=True,
        must_change_password=False,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    _write_bootstrap_credentials(
        path=settings.admin_bootstrap_file,
        email=settings.admin_email.lower(),
        password=generated_password,
    )
