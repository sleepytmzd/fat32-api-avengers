"""
Logging middleware for Notification Service
"""
import time
import logging
from fastapi import Request
from opentelemetry import trace

logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next):
    """Logging middleware with trace correlation"""
    start_time = time.time()
    
    # Get trace context if available
    span = trace.get_current_span()
    trace_id = None
    span_id = None
    
    if span and span.get_span_context().is_valid:
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')
    
    # Log request
    logger.info(
        f"Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None,
            "trace_id": trace_id,
            "span_id": span_id
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        f"Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration": f"{duration:.3f}s",
            "trace_id": trace_id,
            "span_id": span_id
        }
    )
    
    # Add trace headers to response
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Span-Id"] = span_id
    
    return response
