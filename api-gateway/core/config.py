"""
Core Configuration Module
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "API Gateway"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Caching
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL: int = 300  # seconds
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Circuit Breaker
    CIRCUIT_BREAKER_ENABLED: bool = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Request Settings
    REQUEST_TIMEOUT: float = 30.0
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Service Discovery
    SERVICE_REGISTRY_TYPE: str = "static"  # static, consul, kubernetes

    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://user-service:8001")
    CAMPAIGN_SERVICE_URL: str = os.getenv("CAMPAIGN_SERVICE_URL", "http://campaign-service:8002")
    DONATION_SERVICE_URL: str = os.getenv("DONATION_SERVICE_URL", "http://donation-service:8004")
    PAYMENT_SERVICE_URL: str = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8003")
    NOTIFICATION_SERVICE_URL: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8005")
    
    # Health Check
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_TIMEOUT: int = 5
    
    # Metrics
    METRICS_ENABLED: bool = True
    
    # Tracing
    TRACING_ENABLED: bool = os.getenv("TRACING_ENABLED", "true").lower() == "true"
    JAEGER_ENDPOINT: str = os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "api-gateway")
    
    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True

def get_settings():
    """Get settings instance"""
    return settings

settings = Settings()