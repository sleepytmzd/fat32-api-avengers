"""
Prometheus metrics middleware for Product Service
"""
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)

# Define Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# gRPC metrics
grpc_requests_total = Counter(
    'grpc_requests_total',
    'Total number of gRPC requests',
    ['method', 'status']
)

# Cache metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status']
)

# Database metrics
db_operations_total = Counter(
    'db_operations_total',
    'Total number of database operations',
    ['operation', 'table', 'status']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get the endpoint path (use route if available, otherwise raw path)
        endpoint = request.url.path
        if hasattr(request, 'scope') and 'route' in request.scope:
            route = request.scope.get('route')
            if route and hasattr(route, 'path'):
                endpoint = route.path
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        status = str(response.status_code)
        method = request.method
        
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response


async def metrics_endpoint(request: Request):
    """Endpoint to expose Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
