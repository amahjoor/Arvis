"""
Arvis Logging Configuration

Configures loguru for structured logging with:
- Console output (colored, readable)
- File output (rotating, JSON-friendly)
- Different log levels for debug vs production
"""

import sys
from pathlib import Path
from loguru import logger

from src.config import DEBUG, LOGS_DIR


def setup_logging() -> None:
    """
    Configure loguru logging for Arvis.
    
    Call this once at application startup.
    """
    # Remove default handler
    logger.remove()
    
    # Console handler - always enabled
    log_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stderr,
        format=log_format,
        level="DEBUG" if DEBUG else "INFO",
        colorize=True,
    )
    
    # File handler - rotating daily, keep 7 days
    log_file = LOGS_DIR / "arvis.log"
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="gz",
        serialize=False,  # Set to True for JSON logs
    )
    
    # Log startup
    logger.info("Logging initialized")
    if DEBUG:
        logger.debug("Debug mode enabled")


def get_logger(name: str):
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance bound to the module name
    """
    return logger.bind(module=name)

