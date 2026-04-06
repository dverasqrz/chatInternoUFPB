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

from app.core.config import get_settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.bootstrap import ensure_initial_admin_user
from app.services.runtime_settings import get_or_create_runtime_settings
from app.services.schema_maintenance import ensure_schema_compatibility
from app.services.webhook_sync import sync_webhook_urls_on_startup

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
        Configure CORS middleware for cross-origin requests.
        
        Parses CORS origins from settings and configures appropriate headers.
        Supports both development (wildcard) and production (specific origins) modes.
        """
        origins = [origin.strip() for origin in self.settings.cors_origins.split(",") if origin.strip()]
        if not origins:
            origins = ["*"]
        
        # Allow credentials only when not using wildcard origins
        allow_credentials = origins != ["*"]
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
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
            uploads, uploads_v2, users, webhook, whatsapp_tools
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
        
        # Admin functionality
        app.include_router(admin.router, prefix=api_prefix, tags=["Administration"])
        
        # File management
        app.include_router(uploads.router, prefix=api_prefix, tags=["Uploads"])
        app.include_router(uploads_v2.router, prefix=api_prefix, tags=["Uploads v2"])
        
        # WhatsApp-specific tools
        app.include_router(whatsapp_tools.router, prefix=api_prefix, tags=["WhatsApp Tools"])
        
        # Root redirect to frontend
        @app.get("/", include_in_schema=False, response_class=RedirectResponse)
        def root() -> RedirectResponse:
            """Redirect root URL to frontend application."""
            return RedirectResponse(url="/inbox")
    
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
