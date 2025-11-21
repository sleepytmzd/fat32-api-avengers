"""
OpenTelemetry tracing configuration for Notification Service
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import logging

logger = logging.getLogger(__name__)

# Disable verbose logging from OpenTelemetry
logging.getLogger("opentelemetry").setLevel(logging.WARNING)


def init_tracing(app, service_name: str = "notification-service", jaeger_endpoint: str = None):
    """Initialize OpenTelemetry tracing with Jaeger exporter"""
    try:
        # Default Jaeger endpoint
        if not jaeger_endpoint:
            jaeger_endpoint = "http://jaeger:14268/api/traces"
        
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: service_name
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            collector_endpoint=jaeger_endpoint,
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
            excluded_urls="/health,/metrics"
        )
        
        # Instrument SQLAlchemy
        try:
            from database import engine
            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                enable_commenter=True,
                engine_hook=None
            )
        except Exception as db_error:
            logger.warning(f"Failed to instrument SQLAlchemy: {db_error}")
        
        logger.info(
            f"OpenTelemetry tracing initialized successfully - "
            f"Service: {service_name}, Jaeger: {jaeger_endpoint}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        # Don't fail startup if tracing fails
        return False


def get_tracer(name: str = __name__):
    """Get a tracer instance"""
    return trace.get_tracer(name)
