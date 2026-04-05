from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes import admin, auth, conversations, health, uploads, users, webhook
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Conversation, Message, RuntimeSettings, User  # noqa: F401
from app.services.bootstrap import ensure_initial_admin_user
from app.services.runtime_settings import get_or_create_runtime_settings
from app.services.schema_maintenance import ensure_schema_compatibility


def _wait_for_database(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception:
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _wait_for_database()
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)
    with SessionLocal() as db:
        ensure_initial_admin_user(db)
        get_or_create_runtime_settings(db)
    settings.media_storage_path.mkdir(parents=True, exist_ok=True)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not origins:
    origins = ["*"]
allow_credentials = origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(conversations.router, prefix=settings.api_v1_prefix)
app.include_router(webhook.router, prefix=settings.api_v1_prefix)
app.include_router(webhook.public_router)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(uploads.router, prefix=settings.api_v1_prefix)

app.mount("/inbox", StaticFiles(directory="app/static/inbox", html=True), name="inbox")
app.mount("/uploads", StaticFiles(directory=str(settings.media_storage_path)), name="uploads")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/inbox")
