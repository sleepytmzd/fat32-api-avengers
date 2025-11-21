from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Service
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "payment-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8003"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://payment_user:payment_pass@localhost:5436/payment_db"
    )
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # Tracing
    TRACING_ENABLED: bool = os.getenv("TRACING_ENABLED", "true").lower() == "true"
    JAEGER_ENDPOINT: str = os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
    BANKING_SERVICE_URL: str = os.getenv("BANKING_SERVICE_URL", "http://banking-service:8006")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
settings = Settings()
