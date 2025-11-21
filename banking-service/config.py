"""
Configuration for Banking Service
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Service
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "banking-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8004"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://banking_user:banking_pass@localhost:5437/banking_db"
    )
    
    # Tracing
    TRACING_ENABLED: bool = os.getenv("TRACING_ENABLED", "true").lower() == "true"
    JAEGER_ENDPOINT: str = os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
