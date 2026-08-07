"""
Configuration settings for LishFind Backend

Simple Pydantic 1.8 compatible configuration for Render deployment.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "LishFind"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    ALLOWED_HOSTS: str = "*"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis Cache
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 1800
    
    # AI Provider - Disabled for free tier
    AI_PROVIDER: str = "disabled"
    
    # Email Configuration
    EMAIL_ENABLED: bool = False
    
    # File Storage
    STORAGE_TYPE: str = "local"
    
    # Maps Provider Configuration
    MAPS_PROVIDER: str = "nominatim"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30
    
    # Search Configuration
    DEFAULT_SEARCH_RADIUS_KM: float = 10.0
    MAX_SEARCH_RESULTS: int = 20
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Performance Settings
    WORKER_PROCESSES: int = 1
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list."""
        return [i.strip() for i in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Convert ALLOWED_HOSTS string to list."""
        return [i.strip() for i in self.ALLOWED_HOSTS.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    @validator("AI_PROVIDER")
    def validate_ai_provider(cls, v):
        if v not in ["openai", "gemini", "disabled"]:
            raise ValueError("AI_PROVIDER must be 'openai', 'gemini', or 'disabled'")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()