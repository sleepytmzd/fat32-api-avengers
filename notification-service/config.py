"""
Configuration for Notification Service
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://notification_user:notification_pass@localhost:5432/notification_db"
    )
    
    # Service
    SERVICE_NAME: str = "notification-service"
    SERVICE_PORT: int = 8005
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
