import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.runtime_settings import RuntimeSettings
from app.models.user import User
from app.schemas.admin import WebhookSettingsRead, WebhookSettingsUpdate
from app.services.runtime_settings import get_or_create_runtime_settings
import os
import shutil
from pathlib import Path

router = APIRouter(prefix="/admin", tags=["admin"])


def _token_preview(token: str | None) -> str | None:
    if not token:
        return None
    visible = token[:4]
    return f"{visible}{'*' * max(0, len(token) - 4)}"


def _get_outbound_secret(runtime: RuntimeSettings) -> str | None:
    auth_type = (runtime.outbound_auth_type or "none").lower()
    if auth_type == "header":
        return runtime.outbound_auth_header_value
    if auth_type == "basic":
        return runtime.outbound_auth_basic_password
    if auth_type == "jwt":
        return runtime.outbound_auth_jwt_token
    return None


def _normalize_auth_type(value: str | None) -> str:
    allowed = {"none", "header", "basic", "jwt"}
    normalized = (value or "none").strip().lower()
    if normalized not in allowed:
        return "none"
    return normalized


def _read_payload(runtime: RuntimeSettings) -> WebhookSettingsRead:
    auth_type = _normalize_auth_type(runtime.outbound_auth_type)
    return WebhookSettingsRead(
        outbound_webhook_url=runtime.outbound_webhook_url,
        outbound_auth_type=auth_type,
        outbound_auth_header_name=runtime.outbound_auth_header_name,
        outbound_auth_basic_username=runtime.outbound_auth_basic_username,
        outbound_auth_secret_configured=bool(_get_outbound_secret(runtime)),
        outbound_auth_secret_preview=_token_preview(_get_outbound_secret(runtime)),
        inbound_webhook_token_configured=bool(runtime.inbound_webhook_token),
        inbound_webhook_token_preview=_token_preview(runtime.inbound_webhook_token),
    )


def _validate_outbound_auth(runtime: RuntimeSettings) -> None:
    if not runtime.outbound_webhook_url:
        return

    auth_type = _normalize_auth_type(runtime.outbound_auth_type)
    if auth_type == "none":
        return

    if auth_type == "header":
        if not runtime.outbound_auth_header_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o nome do header para o modo Header Auth.",
            )
        if not re.fullmatch(r"[A-Za-z0-9-]+", runtime.outbound_auth_header_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do header inválido. Use apenas letras, números e hífen.",
            )
        if not runtime.outbound_auth_header_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o token/valor do Header Auth.",
            )
        return

    if auth_type == "basic":
        if not runtime.outbound_auth_basic_username or not runtime.outbound_auth_basic_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para Basic Auth, informe usuário e senha.",
            )
        return

    if auth_type == "jwt" and not runtime.outbound_auth_jwt_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para JWT Auth, informe o token.",
        )


@router.get("/webhook-settings", response_model=WebhookSettingsRead)
def get_webhook_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> WebhookSettingsRead:
    runtime = get_or_create_runtime_settings(db)
    return _read_payload(runtime)


@router.put("/webhook-settings", response_model=WebhookSettingsRead)
def update_webhook_settings(
    payload: WebhookSettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> WebhookSettingsRead:
    runtime = get_or_create_runtime_settings(db)

    if "outbound_webhook_url" in payload.model_fields_set:
        runtime.outbound_webhook_url = payload.outbound_webhook_url.strip() if payload.outbound_webhook_url else None

    if "outbound_auth_type" in payload.model_fields_set:
        runtime.outbound_auth_type = _normalize_auth_type(payload.outbound_auth_type)

    if "outbound_auth_header_name" in payload.model_fields_set:
        runtime.outbound_auth_header_name = (
            payload.outbound_auth_header_name.strip() if payload.outbound_auth_header_name else None
        )

    if "outbound_auth_header_value" in payload.model_fields_set:
        runtime.outbound_auth_header_value = (
            payload.outbound_auth_header_value.strip() if payload.outbound_auth_header_value else None
        )

    if "outbound_auth_basic_username" in payload.model_fields_set:
        runtime.outbound_auth_basic_username = (
            payload.outbound_auth_basic_username.strip() if payload.outbound_auth_basic_username else None
        )

    if "outbound_auth_basic_password" in payload.model_fields_set:
        runtime.outbound_auth_basic_password = (
            payload.outbound_auth_basic_password.strip() if payload.outbound_auth_basic_password else None
        )

    if "outbound_auth_jwt_token" in payload.model_fields_set:
        runtime.outbound_auth_jwt_token = payload.outbound_auth_jwt_token.strip() if payload.outbound_auth_jwt_token else None

    if "inbound_webhook_token" in payload.model_fields_set:
        runtime.inbound_webhook_token = payload.inbound_webhook_token.strip() if payload.inbound_webhook_token else None

    _validate_outbound_auth(runtime)

    db.commit()
    db.refresh(runtime)
    return _read_payload(runtime)


@router.delete("/cleanup/messages", status_code=status.HTTP_200_OK)
async def cleanup_messages(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    """
    Delete all messages from the system.
    
    This endpoint permanently deletes all messages from all conversations.
    Only administrators can access this endpoint.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Iniciando limpeza de mensagens...")
        
        # Importar modelos para usar ORM
        from app.models.message import Message
        
        # Deletar todas as mensagens usando ORM
        messages_count = db.query(Message).count()
        logger.info(f"Total de mensagens encontradas: {messages_count}")
        
        if messages_count > 0:
            db.query(Message).delete(synchronize_session=False)
            db.commit()
            logger.info(f"{messages_count} mensagens deletadas com sucesso")
        else:
            logger.info("Nenhuma mensagem encontrada para deletar")
        
        return {
            "message": "Todas as mensagens foram apagadas com sucesso.",
            "deleted_count": messages_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao apagar mensagens: {str(e)}")
        logger.error(f"Tipo do erro: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao apagar mensagens: {str(e)}"
        )


@router.delete("/cleanup/uploads", status_code=status.HTTP_200_OK)
async def cleanup_uploads(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    """
    Delete all uploaded files from the system.
    
    This endpoint permanently deletes all files from the uploads directory.
    Only administrators can access this endpoint.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Iniciando limpeza de arquivos...")
        
        # Get uploads directory path
        uploads_dir = Path("/app/uploads")
        logger.info(f"Diretório uploads: {uploads_dir.absolute()}")
        
        deleted_files = []
        deleted_size = 0
        
        # Delete all files and directories in uploads folder
        if uploads_dir.exists():
            try:
                # List all items first
                items = list(uploads_dir.iterdir())
                logger.info(f"Items encontrados: {len(items)}")
                
                for item in items:
                    item_path = uploads_dir / item
                    try:
                        logger.info(f"Processando item: {item_path} (tipo: {item_path.stat().st_mode if item_path.exists() else 'não existe'})")
                        
                        if item_path.is_file():
                            file_size = item_path.stat().st_size
                            logger.info(f"Tentando deletar arquivo: {item.name} ({file_size} bytes)")
                            item_path.unlink()
                            deleted_files.append(str(item.name))
                            deleted_size += file_size
                            logger.info(f" Arquivo deletado: {item.name}")
                        elif item_path.is_dir():
                            logger.info(f"Tentando deletar diretório: {item.name}")
                            shutil.rmtree(item_path)
                            deleted_files.append(f"{item.name}/")
                            logger.info(f" Diretório deletado: {item.name}")
                        else:
                            logger.warning(f"Item não é arquivo nem diretório: {item_path}")
                    except Exception as e:
                        logger.error(f" Erro ao deletar {item.name}: {type(e).__name__}: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        
            except Exception as e:
                logger.error(f"Erro ao listar diretório: {e}")
                raise e
        else:
            logger.info("Diretório uploads não existe ou já vazio")
        
        result = {
            "message": "Todos os arquivos de upload foram apagados com sucesso.",
            "deleted_files": deleted_files,
            "deleted_count": len(deleted_files),
            "freed_space_mb": round(deleted_size / (1024 * 1024), 2) if deleted_size > 0 else 0
        }
        
        logger.info(f"Limpeza concluída: {len(deleted_files)} itens, {result['freed_space_mb']}MB liberados")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao apagar arquivos: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao apagar arquivos: {str(e)}"
        )
