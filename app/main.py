"""
UFPB Chat System - Main Application Entry Point

This module serves as the entry point for the FastAPI application.
It uses the factory pattern for clean initialization and configuration.
"""

from app.core.app_factory import create_application

# Create application instance using factory pattern
# This ensures proper dependency injection and configuration loading
app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
