"""
Tracing middleware for Banking Service
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.ext.asyncio import AsyncEngine
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

def init_tracing(app: FastAPI, service_name: str, jaeger_endpoint: str):
    """
    Initialize OpenTelemetry tracing with Jaeger
    """
    try:
        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_endpoint.split(":")[0] if ":" in jaeger_endpoint else jaeger_endpoint,
            agent_port=int(jaeger_endpoint.split(":")[1]) if ":" in jaeger_endpoint else 6831,
        )

        # Add span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        
        logger.info(f"Tracing initialized for {service_name}")
        logger.info(f"Jaeger endpoint: {jaeger_endpoint}")
        
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")
        raise

def instrument_database(engine: AsyncEngine):
    """
    Instrument SQLAlchemy engine for tracing
    """
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        logger.info("Database tracing instrumentation added")
    except Exception as e:
        logger.warning(f"Failed to instrument database: {e}")
