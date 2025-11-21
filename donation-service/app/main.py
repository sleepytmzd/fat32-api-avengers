from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
import uvicorn

from app.core.config import get_settings
from app.database.database import init_db, close_db
from app.api.orders import router as orders_router
from app.kafka.producer import kafka_producer
from app.middleware.tracing import init_tracing
from app.middleware.metrics import MetricsMiddleware, metrics_endpoint
from app.middleware.logging import logging_middleware

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
    description="E-commerce Order Service API",
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
    logger.info("Starting Order Service", service_name=settings.service_name)
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Initialize Kafka producer
        await kafka_producer.start()
        logger.info("Kafka producer initialized")
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down Order Service")
    
    try:
        # Stop Kafka producer
        await kafka_producer.stop()
        logger.info("Kafka producer stopped")
        
        # Close database connections
        close_db()
        logger.info("Database connections closed")
        
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
    """Readiness check with database connectivity"""
    try:
        from app.database.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "service": settings.service_name,
            "database": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "service": settings.service_name,
                "database": "disconnected",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# Include routers
app.include_router(orders_router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )