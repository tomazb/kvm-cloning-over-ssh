import json
import logging
import sys
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

class StructuredLogger:
    """
    A logger that outputs logs in a structured JSON format.
    """

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Clear existing handlers to avoid duplicate logs
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.JsonFormatter())
        self.logger.addHandler(handler)

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_entry: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)
            
            # Add extra fields if present
            if hasattr(record, "extra"):
                log_entry.update(record.extra)

            return json.dumps(log_entry)

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, extra={"extra": kwargs})

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        self.logger.error(message, exc_info=exc_info, extra={"extra": kwargs})

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, extra={"extra": kwargs})

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, extra={"extra": kwargs})

    def critical(self, message: str, exc_info: bool = True, **kwargs: Any) -> None:
        self.logger.critical(message, exc_info=exc_info, extra={"extra": kwargs})

# Global logger instance
logger = StructuredLogger("kvm_clone")
