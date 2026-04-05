from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RuntimeSettings(Base):
    __tablename__ = "runtime_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    outbound_webhook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    outbound_auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="none", server_default="none")
    outbound_auth_header_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outbound_auth_header_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    outbound_auth_basic_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outbound_auth_basic_password: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    outbound_auth_jwt_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    inbound_webhook_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
