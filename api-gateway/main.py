"""
API Gateway - Simplified Main Application
"""
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
import time
import logging
import hashlib
import json

from core.config import settings
from core.logging import setup_logging, log_request
from core.rate_limiter import RateLimiter
from core.auth import check_access, create_access_token, decode_token
from core.cache import CacheManager
from core.circuit_breaker import CircuitBreaker
from core.service_registry import ServiceRegistry
from core.load_balancer import LoadBalancer
from middleware.metrics import MetricsMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

logger = setup_logging()
security = HTTPBearer(auto_error=False)

# Initialize components
rate_limiter = RateLimiter()
cache_manager = CacheManager()
circuit_breaker = CircuitBreaker()
service_registry = ServiceRegistry()
load_balancer = LoadBalancer(service_registry=service_registry)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting API Gateway...")
    await service_registry.initialize()
    await service_registry.start_health_checks()
    logger.info("API Gateway started successfully")
    
    yield
    
    logger.info("Shutting down API Gateway...")
    await service_registry.stop_health_checks()
    await cache_manager.close()

app = FastAPI(
    title="API Gateway",
    description="Simplified API Gateway for Microservices",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize tracing after app creation
try:
    from middleware.tracing import init_tracing
    init_tracing(app)
    logger.info("Tracing initialized successfully")
except Exception as e:
    logger.warning(f"Tracing initialization failed: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(MetricsMiddleware)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    """Request processing middleware"""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", hashlib.md5(
        f"{time.time()}{request.url}".encode()
    ).hexdigest())
    
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        duration = time.time() - start_time
        await log_request(request, response.status_code, duration)
        
        return response
    except Exception as e:
        logger.error(f"Gateway error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal gateway error", "request_id": request_id}
        )

# ============================================================================
# AUTH ENDPOINTS - Gateway handles login/register flow
# ============================================================================

@app.post("/api/v1/auth/login")
async def login(request: Request):
    """
    Login endpoint - Gateway coordinates with user-service
    1. Forward credentials to user-service for validation
    2. If valid, generate JWT token
    3. Return token to client
    """
    body = await request.json()
    
    # Forward to user-service for validation
    service_url = await load_balancer.get_instance("user-service")
    if not service_url:
        raise HTTPException(status_code=503, detail="User service unavailable")
    
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{service_url}/api/v1/auth/validate-credentials",
                json=body
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", "Invalid credentials")
            )
        
        # Get user data from user-service
        user_data = response.json()
        
        # Generate JWT token in gateway
        token = create_access_token({
            "user_id": user_data["id"],
            "email": user_data["email"],
            "role": user_data["role"]
        })
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "role": user_data["role"]
            }
        }
    
    except httpx.RequestError as e:
        logger.error(f"Error connecting to user-service: {e}")
        raise HTTPException(status_code=502, detail="Authentication service error")

@app.post("/api/v1/auth/register")
async def register(request: Request):
    """
    Register endpoint - Gateway forwards to user-service
    User-service handles all registration logic
    """
    body = await request.json()
    
    service_url = await load_balancer.get_instance("user-service")
    if not service_url:
        raise HTTPException(status_code=503, detail="User service unavailable")
    
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{service_url}/api/v1/auth/register",
                json=body
            )
        
        if response.status_code == 201:
            user_data = response.json()
            
            # Generate token for new user
            token = create_access_token({
                "user_id": user_data["id"],
                "email": user_data["email"],
                "role": user_data["role"]
            })
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": user_data
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", "Registration failed")
            )
    
    except httpx.RequestError as e:
        logger.error(f"Error connecting to user-service: {e}")
        raise HTTPException(status_code=502, detail="Registration service error")

@app.get("/api/v1/auth/me")
async def get_me(request: Request):
    """Get current user info from token"""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = auth_header.replace("Bearer ", "")
    user = decode_token(token)
    
    return {
        "id": user.get("user_id"),
        "email": user.get("email"),
        "role": user.get("role")
    }

# ============================================================================
# GATEWAY ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Gateway health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": await service_registry.get_all_services_health()
    }



# @app.get("/metrics")
# async def metrics():
#     """Prometheus metrics"""
#     from middleware.metrics import get_metrics
#     return Response(content=get_metrics(), media_type="text/plain")

# ============================================================================
# MAIN PROXY ENDPOINT
# ============================================================================

@app.api_route("/api/v1/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service_name: str, path: str, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Main proxy endpoint with simplified access control"""
    request_id = request.state.request_id
    
    # Check access (returns user if authenticated, None if public)
    user = await check_access(
        service_name=service_name,
        path=path,
        method=request.method,
        credentials=credentials
    )
    
    # Rate limiting
    client_id = user.get("user_id") if user else request.client.host
    if not await rate_limiter.check_limit(client_id, service_name):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Check cache for GET requests
    if request.method == "GET":
        cache_key = f"{client_id}:{service_name}:{path}:{request.url.query}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return JSONResponse(
                content=cached["content"],
                status_code=cached["status_code"],
                headers={"X-Cache": "HIT", "X-Request-ID": request_id}
            )
    
    # Circuit breaker check
    if circuit_breaker.is_open(service_name):
        raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")
    
    # Get service instance
    service_url = await load_balancer.get_instance(service_name)
    if not service_url:
        raise HTTPException(status_code=503, detail=f"Service {service_name} not found")
    
    # Build target URL
    target_url = f"{service_url}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    # Prepare headers
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # Add user context headers if authenticated
    if user:
        headers["X-User-ID"] = str(user.get("user_id"))
        headers["X-User-Email"] = str(user.get("email"))
        headers["X-User-Role"] = str(user.get("role"))
    
    # Forward request
    try:
        body = await request.body()
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=False
            )
        
        circuit_breaker.record_success(service_name)
        
        # Cache successful GET responses
        if request.method == "GET" and response.status_code == 200:
            try:
                content = response.json()
                await cache_manager.set(
                    cache_key,
                    {"content": content, "status_code": response.status_code},
                    ttl=settings.CACHE_TTL
                )
            except:
                pass
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    
    except httpx.TimeoutException:
        circuit_breaker.record_failure(service_name)
        raise HTTPException(status_code=504, detail="Gateway timeout")
    
    except httpx.RequestError as e:
        circuit_breaker.record_failure(service_name)
        logger.error(f"Error calling {service_name}: {e}")
        raise HTTPException(status_code=502, detail="Bad gateway")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)