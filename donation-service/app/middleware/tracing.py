"""
OpenTelemetry tracing configuration for Order Service
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient, GrpcAioInstrumentorClient
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import structlog
import logging

from app.core.config import get_settings

# Disable verbose logging from OpenTelemetry
logging.getLogger("opentelemetry").setLevel(logging.WARNING)

logger = structlog.get_logger(__name__)
settings = get_settings()


def init_tracing(app):
    """Initialize OpenTelemetry tracing with Jaeger exporter"""
    try:
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: settings.service_name
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure Jaeger exporter - use collector endpoint from settings
        jaeger_exporter = JaegerExporter(
            collector_endpoint=settings.jaeger_endpoint,
        )
        
        # Add span processor with batching
        provider.add_span_processor(
            BatchSpanProcessor(
                jaeger_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000
            )
        )
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI - exclude health and metrics endpoints
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/metrics,/health/ready"
        )
        
        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument(engine_hook=None)
        
        # Instrument sync gRPC client (if used)
        GrpcInstrumentorClient().instrument()
        
        # Instrument async gRPC client (grpc.aio) - THIS IS WHAT WE USE
        GrpcAioInstrumentorClient().instrument()
        
        # Instrument HTTPX client for HTTP calls to product-service
        HTTPXClientInstrumentor().instrument()
        
        logger.info(
            "OpenTelemetry tracing initialized successfully",
            service_name=settings.service_name,
            jaeger_endpoint="http://jaeger:14268/api/traces"
        )
        
        return True
        
    except Exception as e:
        logger.error("Failed to initialize tracing", error=str(e), exc_info=True)
        # Don't fail startup if tracing fails
        return False


def get_tracer(name: str = __name__):
    """Get a tracer instance"""
    return trace.get_tracer(name)
