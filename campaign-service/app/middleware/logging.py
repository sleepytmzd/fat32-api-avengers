"""
Structured logging middleware with trace correlation for Product Service
"""
import time
from fastapi import Request
from opentelemetry import trace
import structlog

logger = structlog.get_logger(__name__)


async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with trace correlation"""
    start_time = time.time()
    
    # Extract trace ID from OpenTelemetry context
    span = trace.get_current_span()
    trace_id = ""
    if span and span.get_span_context().is_valid:
        trace_id = format(span.get_span_context().trace_id, '032x')
    
    # Log request
    logger.info(
        "Request started",
        trace_id=trace_id,
        method=request.method,
        path=request.url.path,
        query=str(request.query_params) if request.query_params else "",
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent", "")
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    latency = time.time() - start_time
    logger.info(
        "Request completed",
        trace_id=trace_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_seconds=round(latency, 3)
    )
    
    return response
