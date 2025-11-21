"""
Structured Logging Module
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from fastapi import Request

from core.config import settings

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, "service"):
            log_data["service"] = record.service
        
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging() -> logging.Logger:
    """Setup structured logging"""
    logger = logging.getLogger("api_gateway")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.DEBUG:
        # Human-readable format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        # JSON format for production
        formatter = JSONFormatter()
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

async def log_request(
    request: Request,
    status_code: int,
    duration: float
):
    """Log HTTP request"""
    logger = logging.getLogger("api_gateway")
    
    log_data = {
        "method": request.method,
        "path": str(request.url.path),
        "query": str(request.url.query) if request.url.query else None,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    
    if hasattr(request.state, "request_id"):
        log_data["request_id"] = request.state.request_id
    
    # Log at appropriate level
    if status_code >= 500:
        logger.error("Request completed", extra=log_data)
    elif status_code >= 400:
        logger.warning("Request completed", extra=log_data)
    else:
        logger.info("Request completed", extra=log_data)

class RequestLogger:
    """Context manager for request logging"""
    
    def __init__(self, request: Request):
        self.request = request
        self.logger = logging.getLogger("api_gateway")
        self.start_time = None
    
    async def __aenter__(self):
        import time
        self.start_time = time.time()
        
        self.logger.info(
            f"Request started: {self.request.method} {self.request.url.path}",
            extra={
                "request_id": getattr(self.request.state, "request_id", None),
                "method": self.request.method,
                "path": str(self.request.url.path)
            }
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                f"Request failed: {str(exc_val)}",
                extra={
                    "request_id": getattr(self.request.state, "request_id", None),
                    "duration_ms": round(duration * 1000, 2),
                    "exception": str(exc_val)
                }
            )
        else:
            self.logger.info(
                f"Request completed successfully",
                extra={
                    "request_id": getattr(self.request.state, "request_id", None),
                    "duration_ms": round(duration * 1000, 2)
                }
            )

def log_service_call(
    service_name: str,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    request_id: str = None
):
    """Log backend service call"""
    logger = logging.getLogger("api_gateway")
    
    log_data = {
        "service": service_name,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
    }
    
    if request_id:
        log_data["request_id"] = request_id
    
    if status_code >= 500:
        logger.error("Service call failed", extra=log_data)
    elif status_code >= 400:
        logger.warning("Service call returned error", extra=log_data)
    else:
        logger.debug("Service call completed", extra=log_data)