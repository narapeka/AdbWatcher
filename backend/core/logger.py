import os
import logging
import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from backend.core.config import get_config

class ADBProtocolFilter(logging.Filter):
    """Filter to exclude ADB protocol logs"""
    def filter(self, record):
        # Exclude logs containing ADB protocol messages
        if record.getMessage().startswith(('bulk_write', 'bulk_read')):
            return False
        return True

def setup_logging():
    """Set up logging based on configuration."""
    # Check if the root logger already has handlers configured
    if logging.getLogger().hasHandlers():
        # Logging is already configured, just return
        return
        
    config = get_config()
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a daily log file
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(logs_dir, f"{today}.log")
    
    # Configure handlers
    handlers = [
        logging.StreamHandler(),  # Console output
        TimedRotatingFileHandler(
            log_file,
            when='midnight',
            backupCount=7,  # Keep logs for 7 days
            encoding="utf-8"
        )
    ]
    
    # Add the ADB protocol filter to each handler
    adb_filter = ADBProtocolFilter()
    for handler in handlers:
        handler.addFilter(adb_filter)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
def get_logger(name):
    """Get a logger with the specified name."""
    # Ensure logging is set up
    setup_logging()
    return logging.getLogger(name) 