from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
import uvicorn
import asyncio
import threading

from app.core.config import get_settings
from app.database.database import init_db, close_db
from app.api.campaign import router as campaigns_router
from app.cache.redis import redis_cache
from app.middleware.tracing import init_tracing
from app.middleware.metrics import MetricsMiddleware, metrics_endpoint
from app.middleware.logging import logging_middleware

# Try to import gRPC server, but don't fail if it's not available
try:
    from app.services.grpc_server import serve_grpc_sync
    GRPC_AVAILABLE = True
except ImportError as e:
    logger = structlog.get_logger(__name__)
    logger.warning("gRPC server not available", error=str(e))
    GRPC_AVAILABLE = False
    serve_grpc_sync = None

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Campaign Service API for fundraising campaigns",
    version="1.0.0",
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tracing (must be done before startup events)
init_tracing(app)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Logging middleware with trace correlation"""
    return await logging_middleware(request, call_next)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        method=request.method,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": "An unexpected error occurred"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Campaign Service", service_name=settings.service_name)
    
    try:
        # Initialize database
        init_db()
        
        # Initialize Redis cache
        try:
            redis_cache.init_redis()
            logger.info("Redis cache initialized successfully")
        except Exception as redis_error:
            logger.warning("Failed to initialize Redis cache", error=str(redis_error))
            logger.info("Campaign service will continue without cache")
        
        # Start gRPC server in a separate thread
        if GRPC_AVAILABLE and serve_grpc_sync:
            def start_grpc_with_logging():
                try:
                    logger.info("Starting gRPC server thread...")
                    serve_grpc_sync()
                except Exception as grpc_error:
                    logger.error(
                        "gRPC server crashed",
                        error=str(grpc_error),
                        error_type=type(grpc_error).__name__
                    )
                    import traceback
                    logger.error("gRPC server traceback", traceback=traceback.format_exc())
            
            try:
                grpc_thread = threading.Thread(target=start_grpc_with_logging, daemon=True, name="gRPC-Server")
                grpc_thread.start()
                logger.info("gRPC server thread started")
                # Give it a moment to start
                import time as time_mod
                time_mod.sleep(1)
                if grpc_thread.is_alive():
                    logger.info("gRPC server thread is running")
                else:
                    logger.error("gRPC server thread exited immediately")
            except Exception as thread_error:
                logger.error("Failed to start gRPC server thread", error=str(thread_error))
                logger.info("Campaign service will continue without gRPC support")
        else:
            logger.info("gRPC server not available, continuing with HTTP only")
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down Campaign Service")
    
    try:
        # Close Redis connection
        redis_cache.close()
        
        # Close database connections
        close_db()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error("Error during application shutdown", error=str(e))


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": time.time()
    }


@app.get("/metrics")
async def metrics(request: Request):
    """Prometheus metrics endpoint"""
    return await metrics_endpoint(request)


@app.get("/health/ready")
async def readiness_check():
    """Readiness check with database, redis, and circuit breaker status"""
    try:
        from app.database.database import engine
        from app.core.circuit_breaker import db_circuit_breaker
        from sqlalchemy import text
        
        health_status = {
            "status": "ready",
            "service": settings.service_name,
            "timestamp": time.time(),
            "database": "disconnected",
            "cache": "disconnected",
            "circuit_breaker": db_circuit_breaker.get_state()
        }
        
        # Check database
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status["database"] = "connected"
        except Exception as db_e:
            logger.warning("Database health check failed", error=str(db_e))
            health_status["database"] = f"error: {str(db_e)}"
        
        # Check Redis cache
        try:
            if redis_cache.redis_client:
                await redis_cache.redis_client.ping()
                health_status["cache"] = "connected"
            else:
                health_status["cache"] = "not_initialized"
        except Exception as cache_e:
            logger.warning("Cache health check failed", error=str(cache_e))
            health_status["cache"] = f"error: {str(cache_e)}"
        
        # Determine overall status
        if health_status["database"] != "connected":
            health_status["status"] = "not ready"
            return JSONResponse(status_code=503, content=health_status)
        
        return health_status
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "service": settings.service_name,
                "error": str(e),
                "timestamp": time.time()
            }
        )


# Include routers
app.include_router(campaigns_router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )