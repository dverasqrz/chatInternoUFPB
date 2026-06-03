"""
Centralized logging configuration for the application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from app.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure application logging based on settings."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (only in production)
    if settings.environment == "production":
        file_handler = logging.FileHandler(log_dir / "app.log")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    _configure_specific_loggers(log_level)


def _configure_specific_loggers(log_level: int) -> None:
    """Configure specific module loggers with appropriate levels."""
    
    # Database logging
    db_logger = logging.getLogger("sqlalchemy.engine")
    if log_level <= logging.DEBUG:
        db_logger.setLevel(logging.INFO)
    else:
        db_logger.setLevel(logging.WARNING)
    
    # HTTP logging
    http_logger = logging.getLogger("uvicorn.access")
    http_logger.setLevel(logging.INFO)
    
    # Application-specific loggers
    app_loggers = [
        "app.services.video_converter",
        "app.services.messages",
        "app.api.routes",
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)
