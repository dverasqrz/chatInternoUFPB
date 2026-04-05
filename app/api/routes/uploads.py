from __future__ import annotations

from pathlib import Path
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_password_changed
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.upload import UploadMediaResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_PREFIXES = ("image/", "audio/", "video/")
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".ogg",
    ".mp3",
    ".wav",
    ".m4a",
    ".webm",
    ".mp4",
    ".mov",
}


def _guess_extension(upload: UploadFile) -> str:
    current_suffix = Path(upload.filename or "").suffix
    if current_suffix:
        return current_suffix.lower()

    mime = (upload.content_type or "").lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/webm": ".webm",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
    }
    return mapping.get(mime, "")


@router.post("/media", response_model=UploadMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user_password_changed),
    __: Session = Depends(get_db),
) -> UploadMediaResponse:
    mime = (file.content_type or "").lower()
    extension = _guess_extension(file)

    mime_allowed = any(mime.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    extension_allowed = extension in ALLOWED_EXTENSIONS
    if not mime_allowed and not extension_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de arquivo não suportado. Use imagem, áudio ou vídeo.",
        )

    settings = get_settings()
    storage_path = settings.media_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)

    generated_name = f"{secrets.token_hex(16)}{extension}"
    destination = storage_path / generated_name

    content = await file.read()
    destination.write_bytes(content)

    return UploadMediaResponse(
        filename=generated_name,
        media_url=f"/uploads/{generated_name}",
        mime_type=file.content_type,
        size_bytes=len(content),
    )
