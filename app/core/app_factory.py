"""
UFPB Chat System - Application Factory

Implements the Factory Pattern for clean FastAPI application initialization.
Follows SOLID principles with clear separation of concerns and dependency injection.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.bootstrap import ensure_initial_admin_user
from app.services.runtime_settings import get_or_create_runtime_settings
from app.services.schema_maintenance import ensure_schema_compatibility
from app.services.webhook_sync import sync_webhook_urls_on_startup

import re

logger = logging.getLogger(__name__)


class ApplicationFactory:
    """
    Factory class for creating and configuring FastAPI application.
    
    Implements the Factory Pattern to ensure:
    - Single Responsibility: Each method handles one configuration aspect
    - Dependency Injection: Settings and dependencies injected properly
    - Testability: Easy to mock and test individual components
    - Configuration Management: Centralized configuration handling
    """
    
    def __init__(self):
        """Initialize factory with settings and logging configuration."""
        self.settings = get_settings()
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """
        Configure application logging based on environment settings.
        
        Sets up structured logging with appropriate levels and formats
        for development, testing, and production environments.
        """
        setup_logging(self.settings)
    
    def _wait_for_database(self, max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
        """
        Wait for database connection with retry logic.
        
        Args:
            max_attempts: Maximum number of connection attempts
            delay_seconds: Delay between attempts in seconds
            
        Raises:
            Exception: If database connection fails after max attempts
            
        This ensures the application doesn't start without a working database connection.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                logger.info("Database connection established successfully")
                return
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt}/{max_attempts} failed: {e}")
                if attempt == max_attempts:
                    logger.error("Failed to connect to database after maximum attempts")
                    raise
                time.sleep(delay_seconds)
    
    def _setup_cors(self, app: FastAPI) -> None:
        """
        Configure CORS settings."""
        settings = get_settings()
        
        # Parse CORS origins from string
        origins = []
        if settings.cors_origins == "*":
            origins.append("*")
        else:
            origins.extend([origin.strip() for origin in settings.cors_origins.split(",")])
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
        logger.info(f" CORS configured with origins: {origins}")

    def _setup_logging_middleware(self, app: FastAPI) -> None:
        """Setup detailed request logging middleware."""
        from fastapi import Request
        from fastapi.responses import Response
        import time
        import json
        
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            
            # Log detalhado da requisição
            logger.info(f" Request Started:")
            logger.info(f"   Method: {request.method}")
            logger.info(f"   URL: {request.url}")
            logger.info(f"   Headers: {dict(request.headers)}")
            logger.info(f"   Client: {request.client.host if request.client else 'unknown'}")
            
            response = await call_next(request)
            
            # Log detalhado da resposta
            process_time = time.time() - start_time
            logger.info(f" Request Completed:")
            logger.info(f"   Status: {response.status_code}")
            logger.info(f"   Duration: {process_time:.3f}s")
            logger.info(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            return response
    
    def _setup_static_files(self, app: FastAPI) -> None:
        """
        Configure static file serving for frontend and media files.
        
        Mounts directories for:
        - Frontend application (/inbox)
        - User uploads (/uploads)
        
        Ensures directories exist before mounting to prevent startup errors.
        """
        # Ensure media directories exist with proper permissions
        self.settings.media_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Mount frontend static files
        app.mount(
            "/inbox", 
            StaticFiles(directory="app/static/inbox", html=True), 
            name="inbox"
        )
        
        # Mount user uploads directory
        app.mount(
            "/uploads", 
            StaticFiles(directory=str(self.settings.media_storage_path)), 
            name="uploads"
        )
    
    def _setup_routes(self, app: FastAPI) -> None:
        """
        Configure application routes with proper organization.
        
        Routes are organized by feature and versioned for API stability:
        - Health check (no version prefix)
        - Authentication (/api/v1/auth)
        - Users (/api/v1/users)
        - Conversations (/api/v1/conversations)
        - Webhooks (/api/v1/webhook)
        - Admin functions (/api/v1/admin)
        - File uploads (/api/v1/uploads)
        
        Each router is included with appropriate prefix and documentation.
        """
        from app.api.routes import (
            admin, auth, conversations, health,
            templates, uploads_v2, users,
            webhook, whatsapp_tools, ai
        )
        
        api_prefix = self.settings.api_v1_prefix
        
        # Health check (no version prefix for monitoring tools)
        app.include_router(health.router)
        
        # Core API routes
        app.include_router(auth.router, prefix=api_prefix, tags=["Authentication"])
        app.include_router(users.router, prefix=api_prefix, tags=["Users"])
        app.include_router(conversations.router, prefix=api_prefix, tags=["Conversations"])
        app.include_router(webhook.router, prefix=api_prefix, tags=["Webhooks"])
        app.include_router(webhook.public_router, tags=["Public Webhooks"])
        app.include_router(templates.router, prefix=api_prefix, tags=["Templates"])
        
        # Admin functionality
        app.include_router(admin.router, prefix=api_prefix, tags=["Administration"])
        
        # File management
        app.include_router(uploads_v2.router, prefix=api_prefix, tags=["Uploads v2"])
        
        # WhatsApp-specific tools
        app.include_router(whatsapp_tools.router, prefix=api_prefix, tags=["WhatsApp Tools"])
        
        # AI assistance
        app.include_router(ai.router, prefix=api_prefix, tags=["AI Assistance"])
        
        # Root redirect to frontend
        @app.get("/", include_in_schema=False, response_class=RedirectResponse)
        def root() -> RedirectResponse:
            """Redirect root URL to frontend application."""
            return RedirectResponse(url="/inbox")
    
    def _initialize_system_templates(self, db: Session) -> None:
        """
        Initialize system templates.
        
        Drops old system templates and recreates with current versions.
        """
        try:
            from app.models.template import MessageTemplate
            
            existing_templates = db.query(MessageTemplate).filter(
                MessageTemplate.is_system == True
            ).all()
            
            if existing_templates:
                logger.info(f"Dropping {len(existing_templates)} old system templates...")
                for t in existing_templates:
                    db.delete(t)
                db.commit()
            
            logger.info("Creating system templates...")
            
            templates = [
                MessageTemplate(
                    title="LGPD - Bom dia",
                    content="""Bom dia!
Termo de Consentimento para Tratamento de Dados Pessoais
Precisamos do seu consentimento para coletar e tratar dados pessoais (como nome, e-mail,
CPF e informações da solicitação) usados apenas para prestar e aprimorar o atendimento.
Seus dados não serão compartilhados sem autorização, e você pode acessá-los, corrigi-los
ou solicitar sua exclusão a qualquer momento. Ao prosseguir, você concorda com esses
termos. Deseja continuar o atendimento?""",
                    category="LGPD",
                    is_system=True,
                    is_active=True,
                ),
                MessageTemplate(
                    title="LGPD - Boa tarde",
                    content="""Boa tarde!
Termo de Consentimento para Tratamento de Dados Pessoais
Precisamos do seu consentimento para coletar e tratar dados pessoais (como nome, e-mail,
CPF e informações da solicitação) usados apenas para prestar e aprimorar o atendimento.
Seus dados não serão compartilhados sem autorização, e você pode acessá-los, corrigi-los
ou solicitar sua exclusão a qualquer momento. Ao prosseguir, você concorda com esses
termos. Deseja continuar o atendimento?""",
                    category="LGPD",
                    is_system=True,
                    is_active=True,
                ),
                MessageTemplate(
                    title="Pesquisa de Satisfação",
                    content="""Se puder avaliar este atendimento, sua opinião é muito importante para nós! ☺️
Em uma escala de 1 a 5, qual o seu índice de satisfação?

⭐️ 1 – Muito insatisfeito
⭐️⭐️ 2 – Insatisfeito
⭐️⭐️⭐️ 3 – Neutro
⭐️⭐️⭐️⭐️ 4 – Satisfeito
⭐️⭐️⭐️⭐️⭐️ 5 – Muito satisfeito""",
                    category="Pesquisa",
                    is_system=True,
                    is_active=True,
                ),
                MessageTemplate(
                    title="Contatos Secretaria da STI",
                    content="""Contatos Secretaria da STI
secretariaexecutiva@sti.ufpb.br
hermes@sti.ufpb.br
Recepção: 3216-7389
Secretaria: 3216-7390""",
                    category="Contatos",
                    is_system=True,
                    is_active=True,
                ),
                MessageTemplate(
                    title="Abertura de Chamado",
                    content="""Nesse caso, tem que ser aberto um chamado.
Para abrir o chamado, precisamos de algumas confirmações de segurança.
Você deseja abrir o chamado?""",
                    category="Atendimento",
                    is_system=True,
                    is_active=True,
                ),
                MessageTemplate(
                    title="Confirmação de Identidade",
                    content="""Para confirmação da sua identidade, precisamos que você nos envie:
- selfie, segurando um documento de identidade com foto, que fique legível;
- foto ou o pdf do documento mostrado na selfie.""",
                    category="Atendimento",
                    is_system=True,
                    is_active=True,
                ),
                MessageTemplate(
                    title="Permissões SIPAC -PROTOCOLO",
                    content="""Para obter as permissões no módulo de PROTOCOLO do sistema SIPAC, você deve procurar o ARQUIVO CENTRAL. Lembrando que é imprescindível que o servidor anexe, ao pedido, sua portaria de localização ou algum documento assinado pela chefia imediata (declaração, memorando, entre outros) informando sua localização na unidade desejada.
Para realizar o pedido acesse:
https://otrs-arquivo.ufpb.br/suporte/""",
                    category="Atendimento",
                    is_system=True,
                    is_active=True,
                ),
            ]
            
            db.add_all(templates)
            db.commit()
            
            logger.info("System templates created successfully:")
            for t in templates:
                logger.info(f"  - {t.title} ({t.category})")
            
        except Exception as e:
            logger.error(f"Error initializing system templates: {e}")
            db.rollback()
            raise
    
    def _cleanup_invalid_contacts(self, db: Session) -> None:
        """
        Remove conversations with no messages.
        
        Empty conversations may have been created by webhook errors or
        race conditions. They serve no purpose and clutter the contact list.
        """
        try:
            from app.models.conversation import Conversation
            from app.models.message import Message
            
            conv_ids_with_messages = set(
                row[0] for row in db.query(Message.conversation_id).distinct().all()
            )
            all_convs = db.query(Conversation).all()
            empty_convs = [c for c in all_convs if c.id not in conv_ids_with_messages]
            
            if empty_convs:
                logger.info(f"Removing {len(empty_convs)} conversations with no messages...")
                for conv in empty_convs:
                    logger.info(f"  - {conv.contact_phone} ({conv.contact_name or 'Sem Nome'})")
                    db.delete(conv)
                db.commit()
                logger.info(f"Cleanup complete: {len(empty_convs)} empty conversations removed")
            else:
                logger.info("No empty conversations found during cleanup")
                
        except Exception as e:
            logger.error(f"Error during contact cleanup: {e}")
            db.rollback()
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """
        Application lifespan manager for startup and shutdown procedures.
        
        Startup sequence:
        1. Wait for database connection
        2. Create database tables
        3. Ensure schema compatibility
        4. Initialize admin user
        5. Setup runtime settings
        6. Sync webhook configurations
        7. Ensure required directories exist
        
        Shutdown sequence:
        1. Log shutdown initiation
        2. Close database connections (handled by SQLAlchemy)
        3. Cleanup temporary resources
        """
        # Startup procedures
        logger.info("🚀 Starting UFPB Chat System...")
        
        try:
            # Database initialization
            logger.info("📊 Initializing database connection...")
            self._wait_for_database()
            
            logger.info("🔧 Creating database tables...")
            Base.metadata.create_all(bind=engine)
            
            logger.info("🔍 Checking schema compatibility...")
            ensure_schema_compatibility(engine)
            
            # Service initialization
            logger.info("👤 Initializing admin user...")
            with SessionLocal() as db:
                ensure_initial_admin_user(db)
                
                logger.info("⚙️ Setting up runtime configuration...")
                get_or_create_runtime_settings(db)
                
                logger.info("Initializing system templates...")
                self._initialize_system_templates(db)
                
                logger.info("🧹 Cleaning up invalid contacts...")
                self._cleanup_invalid_contacts(db)
                
                logger.info("🔗 Syncing webhook configurations...")
                sync_webhook_urls_on_startup()
            
            # File system setup
            logger.info("📁 Ensuring required directories exist...")
            self.settings.media_storage_path.mkdir(parents=True, exist_ok=True)
            
            logger.info("✅ Application startup completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Application startup failed: {e}")
            raise
        
        yield
        
        # Shutdown procedures
        logger.info("🛑 Shutting down UFPB Chat System...")
        # Database connections are automatically closed by SQLAlchemy
        # Add any additional cleanup logic here if needed
        logger.info("✅ Application shutdown completed")
    
    def create_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application instance.
        
        Returns:
            FastAPI: Configured application instance
            
        The application is configured with:
        - Proper metadata for documentation
        - CORS middleware
        - Logging middleware
        - Static file serving
        - Route registration
        - Exception handling
        - Lifespan management
        """
        app = FastAPI(
            title=self.settings.app_name,
            description="UFPB Chat System - Professional multi-attendant chat platform",
            version="2.0.0",
            lifespan=self.lifespan,
            docs_url="/api/v1/docs",
            redoc_url="/api/v1/redoc",
            openapi_url="/api/v1/openapi.json"
        )
        
        # Configure application components
        self._setup_cors(app)
        self._setup_logging_middleware(app)
        self._setup_static_files(app)
        self._setup_routes(app)
        setup_exception_handlers(app)
        
        return app

def create_application() -> FastAPI:
    """
    Application factory function for external imports.
    
    This function provides a clean interface for creating the application
    instance without exposing the factory class implementation details.
    
    Returns:
        FastAPI: Configured application instance
    """
    factory = ApplicationFactory()
    return factory.create_app()
