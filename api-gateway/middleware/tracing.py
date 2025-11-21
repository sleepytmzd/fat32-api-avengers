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
import structlog
import logging

from core.config import get_settings

# Disable verbose logging from OpenTelemetry
logging.getLogger("opentelemetry").setLevel(logging.WARNING)

logger = structlog.get_logger(__name__)
settings = get_settings()


def init_tracing(app):
    """Initialize OpenTelemetry tracing with Jaeger exporter"""
    try:
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: "api-gateway"
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure Jaeger exporter - use HTTP collector endpoint
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
        
        # Custom request hook to exclude health and metrics endpoints
        def exclude_health_metrics(span, scope):
            if scope:
                path = scope.get("path", "")
                # Don't trace health and metrics endpoints
                if path in ["/health", "/metrics", "/api/health", "/api/metrics"]:
                    span.set_attribute("http.route", "excluded")
                    # Mark span to be dropped by setting sampling decision
                    return
        
        # Instrument FastAPI with custom hook
        FastAPIInstrumentor.instrument_app(
            app, 
            server_request_hook=exclude_health_metrics,
            excluded_urls="/health,/metrics,/api/health,/api/metrics"
        )
        
        # Instrument HTTPX (for proxying requests to backend services)
        HTTPXClientInstrumentor().instrument()
        
        logger.info(
            "OpenTelemetry tracing initialized successfully",
            service_name="api-gateway",
            jaeger_endpoint=settings.jaeger_endpoint
        )
        
        return True
        
    except Exception as e:
        logger.error("Failed to initialize tracing", error=str(e), exc_info=True)
        # Don't fail startup if tracing fails
        return False


def get_tracer(name: str = __name__):
    """Get a tracer instance"""
    return trace.get_tracer(name)
