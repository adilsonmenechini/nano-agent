import logging
import sys
from logging.handlers import TimedRotatingFileHandler

# Configure root logger with rotating file handler
def configure_logging(log_path="/var/log/nanoagent/app.log", level=logging.INFO):
    """
    Configures logging with rotation.
    - Logs are rotated daily (when they reach midnight)
    - Keeps 7 days of history
    - Includes timestamps and module names
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if called multiple times
    if logger.handlers:
        return
    
    # Create formatter
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, "%Y-%m-%d")
    
    # Console handler (stderr for immediate feedback)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Timed rotating file handler (rotates daily, keeps 7 days)
    file_handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)
    
    return logger

# Initialize global logger
log = configure_logging()