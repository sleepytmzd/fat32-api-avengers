from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # App
    app_name: str = "Product Service API"
    debug: bool = False
    service_name: str = "product-service"
    
    # Redis
    redis_url: str
    redis_password: str = ""
    
    # Tracing
    jaeger_endpoint: str
    
    class Config:
        # Look for .env.local file in the product-service directory
        env_file = os.path.join(Path(__file__).parent.parent.parent, ".env.local")
        case_sensitive = False
        
    def __post_init__(self):
        """Validate critical settings on startup"""
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

@lru_cache()
def get_settings():
    return Settings()