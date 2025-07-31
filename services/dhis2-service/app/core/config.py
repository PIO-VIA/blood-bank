from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings configuration."""
    
    # Application
    APP_NAME: str = "DHIS2 Blood Bank Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://user:password@localhost:5432/blood_bank_db"
    )
    
    # DHIS2 Configuration
    DHIS2_BASE_URL: str = os.getenv("DHIS2_BASE_URL", "https://play.dhis2.org/dev")
    DHIS2_USERNAME: str = os.getenv("DHIS2_USERNAME", "admin")
    DHIS2_PASSWORD: str = os.getenv("DHIS2_PASSWORD", "district")
    DHIS2_API_VERSION: str = "40"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 8002
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 1
    
    # Health Check
    HEALTH_CHECK_TIMEOUT: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()