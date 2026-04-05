from pydantic import BaseModel


class UploadMediaResponse(BaseModel):
    filename: str
    media_url: str
    mime_type: str | None
    size_bytes: int
