import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_password_changed
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import AIQuestionRequest, AIAnswerResponse
from app.core.config import get_settings
from app.services.runtime_settings import get_cached_runtime, get_or_create_runtime_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/ask", response_model=AIAnswerResponse)
async def ask_ai(
    request: AIQuestionRequest,
    current_user: User = Depends(get_current_user_password_changed),
    db: Session = Depends(get_db),
) -> AIAnswerResponse:
    """
    Ask the AI a question for assistance via n8n webhook.
    """
    settings = get_settings()
    # Use cached runtime (loaded from DB at startup, updated when admin saves)
    runtime = get_cached_runtime() or get_or_create_runtime_settings(db)
    
    # Select webhook based on environment
    webhook_url = settings.ai_webhook_url_prod if settings.environment == "production" else settings.ai_webhook_url_test
    
    if not webhook_url:
        logger.error("AI webhook URL not configured in .env")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service is not properly configured."
        )

    try:
        logger.info(f"🤖 User {current_user.email} asking AI via n8n: {request.question}")
        
        # Prepare payload for n8n
        payload = {
            "question": request.question,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name
            },
            "config": {
                "provider": runtime.ai_provider if runtime else "gemini",
            }
        }

        # Build Basic Auth if credentials are configured
        auth = None
        if settings.ai_webhook_username and settings.ai_webhook_password:
            auth = (settings.ai_webhook_username, settings.ai_webhook_password)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                str(webhook_url),
                json=payload,
                auth=auth,
                timeout=120.0  # AI can take a while, generous timeout
            )
            response.raise_for_status()

            # Guard against empty responses (n8n may return 200 with no body)
            raw_text = response.text.strip()
            if not raw_text:
                logger.warning("n8n returned an empty response body (200 OK but no content)")
                return AIAnswerResponse(
                    answer="A IA processou a solicitação, mas retornou uma resposta vazia. "
                           "Verifique o nó 'Respond to Webhook' no n8n."
                )

            # Try to parse JSON
            try:
                data = response.json()
            except Exception:
                # Response is not valid JSON – treat the raw text as the answer
                logger.warning(f"n8n response is not JSON, using raw text: {raw_text[:300]}")
                return AIAnswerResponse(answer=raw_text)

            # n8n usually returns data in 'output', 'response', or 'answer'
            answer = data.get("output") or data.get("response") or data.get("answer")

            if not answer:
                if isinstance(data, dict):
                    answer = str(data)
                else:
                    answer = "A IA retornou uma resposta em um formato inesperado."

            return AIAnswerResponse(answer=answer)
            
    except httpx.HTTPStatusError as e:
        detail = (
            f"[n8n HTTP {e.response.status_code}] "
            f"URL: {str(webhook_url)} | "
            f"Resposta: {e.response.text[:500]}"
        )
        logger.error(f"n8n webhook HTTP error: {detail}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail
        )
    except httpx.ConnectError as e:
        detail = f"[Conexão recusada] Não foi possível conectar ao n8n em {str(webhook_url)}: {str(e)}"
        logger.error(detail)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    except httpx.TimeoutException as e:
        detail = f"[Timeout] O n8n demorou mais de 120s para responder. Tente novamente ou verifique o fluxo no n8n."
        logger.error(f"Timeout calling n8n: {str(e)}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=detail)
    except Exception as e:
        import traceback
        detail = f"[Erro inesperado] {type(e).__name__}: {str(e)}"
        logger.error(f"Unexpected error in ask_ai:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

@router.get("/fetch-models")
async def fetch_models(
    provider: str,
    key: str = None,
    current_user: User = Depends(get_current_user_password_changed),
):
    """
    Proxy to fetch available models from the selected provider.
    For Ollama, uses the URL from env (settings.ollama_base_url).
    """
    settings = get_settings()

    if provider == "ollama":
        try:
            url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=5.0)
                if res.status_code == 200:
                    models_data = res.json()
                    return {"models": [m["name"] for m in models_data.get("models", [])]}
        except Exception:
            return {"models": ["llama3", "mistral", "gemma"]}

    # Default common models for others
    defaults = {
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "groq": ["llama3-70b-8192", "llama3-8b-8200", "mixtral-8x7b-32768", "gemma-7b-it"]
    }

    return {"models": defaults.get(provider, [])}
