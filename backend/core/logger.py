import sys
import os
from loguru import logger
from backend.core.configs import settings

# Ensure logs directory exists
os.makedirs(settings.LOG_DIR, exist_ok=True)

# Remove default handler
logger.remove()

# Console Handler
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# File Handler (storage/logs/app.log) - JSON Structured Logging (GAP-LOG-01 Fix)
log_file_path = os.path.join(settings.LOG_DIR, "app.log")

logger.add(
    log_file_path,
    rotation="50 MB",  # Size-based rotation (not time-based)
    retention="30 days",  # Keep logs for 30 days
    compression="gz",  # Compress rotated files
    level="INFO",  # Production level (WARNING is too restrictive)
    serialize=True,  # JSON format for structured logging
    backtrace=True,
    diagnose=True,
)

# Error Log
error_log_path = os.path.join(settings.LOG_DIR, "errors.log")
logger.add(
    error_log_path,
    rotation="10 MB",
    retention="30 days",  # Updated to 30 days
    compression="gz",  # Add compression
    level="ERROR",
    serialize=True,  # JSON format
    backtrace=True,
    diagnose=True,
)

# Export logger
log = logger
