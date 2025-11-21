"""
OpenTelemetry tracing configuration for API Gateway
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import logging

# Disable verbose logging from OpenTelemetry
logging.getLogger("opentelemetry").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def init_tracing(app):
    """Initialize OpenTelemetry tracing with Jaeger exporter"""
    try:
        from core.config import settings
        
        if not settings.TRACING_ENABLED:
            logger.info("Tracing disabled by configuration")
            return False
        
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: settings.SERVICE_NAME
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure Jaeger exporter - use HTTP collector endpoint
        jaeger_exporter = JaegerExporter(
            collector_endpoint=settings.JAEGER_ENDPOINT,
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
            excluded_urls="/health,/metrics,/api/health,/api/metrics"
        )
        
        # Instrument HTTPX (for proxying requests to backend services)
        HTTPXClientInstrumentor().instrument()
        
        logger.info(
            f"OpenTelemetry tracing initialized - Service: {settings.SERVICE_NAME}, Endpoint: {settings.JAEGER_ENDPOINT}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        # Don't fail startup if tracing fails
        return False


def get_tracer(name: str = __name__):
    """Get a tracer instance"""
    return trace.get_tracer(name)
