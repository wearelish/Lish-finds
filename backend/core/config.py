"""
Configuration settings for LishFind Backend

Environment-based configuration management using Pydantic settings.
All sensitive data should be loaded from environment variables.
"""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "LishFind"
    VERSION: str = Field(default="1.0.0", env="VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")  # development, staging, production
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Production Security Settings
    HTTPS_ONLY: bool = Field(default=False, env="HTTPS_ONLY")
    SECURE_COOKIES: bool = Field(default=False, env="SECURE_COOKIES")
    CSRF_PROTECTION: bool = Field(default=True, env="CSRF_PROTECTION")
    TRUST_HOST_HEADERS: bool = Field(default=False, env="TRUST_HOST_HEADERS")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Enhanced Security for Production
    BCRYPT_ROUNDS: int = Field(default=12, env="BCRYPT_ROUNDS")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    LOGIN_LOCKOUT_MINUTES: int = Field(default=30, env="LOGIN_LOCKOUT_MINUTES")
    JWT_BLACKLIST_ENABLED: bool = Field(default=True, env="JWT_BLACKLIST_ENABLED")
    PASSWORD_MIN_LENGTH: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    
    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000", env="CORS_ORIGINS")
    ALLOWED_HOSTS: str = Field(default="*", env="ALLOWED_HOSTS")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list."""
        if isinstance(self.CORS_ORIGINS, str):
            return [i.strip() for i in self.CORS_ORIGINS.split(",")]
        return [self.CORS_ORIGINS]
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Convert ALLOWED_HOSTS string to list."""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [i.strip() for i in self.ALLOWED_HOSTS.split(",")]
        return [self.ALLOWED_HOSTS]
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Cache
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hour default
    
    # AI Providers
    AI_PROVIDER: str = Field(default="openai", env="AI_PROVIDER")  # openai or gemini
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    OPENAI_MAX_TOKENS: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    
    # Google Gemini Configuration
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    
    # Email Configuration (for verification and notifications)
    EMAIL_ENABLED: bool = Field(default=False, env="EMAIL_ENABLED")
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAIL_FROM: Optional[str] = Field(default=None, env="EMAIL_FROM")
    
    # File Storage
    STORAGE_TYPE: str = Field(default="local", env="STORAGE_TYPE")  # local or s3
    LOCAL_STORAGE_PATH: str = Field(default="./uploads", env="LOCAL_STORAGE_PATH")
    
    # S3 Configuration (for production)
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: Optional[str] = Field(default=None, env="AWS_REGION")
    S3_BUCKET: Optional[str] = Field(default=None, env="S3_BUCKET")
    
    # Maps Provider Configuration
    MAPS_PROVIDER: str = Field(default="nominatim", env="MAPS_PROVIDER")  # nominatim (free) or google
    GOOGLE_MAPS_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_MAPS_API_KEY")
    
    # Rate Limiting - Enhanced for Production
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=100, env="RATE_LIMIT_BURST")
    API_RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="API_RATE_LIMIT_PER_HOUR")
    
    # DDoS Protection
    MAX_REQUEST_SIZE: int = Field(default=1048576, env="MAX_REQUEST_SIZE")  # 1MB
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    REQUEST_TIMEOUT_SECONDS: int = Field(default=30, env="REQUEST_TIMEOUT_SECONDS")
    
    # Search Configuration
    DEFAULT_SEARCH_RADIUS_KM: float = Field(default=10.0, env="DEFAULT_SEARCH_RADIUS_KM")
    MAX_SEARCH_RESULTS: int = Field(default=50, env="MAX_SEARCH_RESULTS")
    
    # Logging - Enhanced for Production
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    ENABLE_ACCESS_LOGS: bool = Field(default=True, env="ENABLE_ACCESS_LOGS")
    LOG_RETENTION_DAYS: int = Field(default=30, env="LOG_RETENTION_DAYS")
    
    # Monitoring and Health Checks
    HEALTH_CHECK_INTERVAL: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")  # seconds
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    
    # Performance Settings
    WORKER_PROCESSES: int = Field(default=1, env="WORKER_PROCESSES")
    KEEPALIVE_TIMEOUT: int = Field(default=5, env="KEEPALIVE_TIMEOUT")
    MAX_KEEPALIVE_REQUESTS: int = Field(default=1000, env="MAX_KEEPALIVE_REQUESTS")
    GZIP_COMPRESSION: bool = Field(default=True, env="GZIP_COMPRESSION")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        """Validate secret key strength for production."""
        if values.get("ENVIRONMENT", "").lower() == "production":
            if len(v) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if v in ["dev-secret-key", "change-me", "secret"]:
                raise ValueError("SECRET_KEY cannot be a common/default value in production")
        return v
    
    @validator("ALLOWED_HOSTS")
    def validate_allowed_hosts(cls, v, values):
        """Validate allowed hosts for production."""
        if values.get("ENVIRONMENT", "").lower() == "production" and v == "*":
            raise ValueError("ALLOWED_HOSTS cannot be '*' in production - specify exact domains")
        return v
    
    @validator("DEBUG")
    def validate_debug(cls, v, values):
        """Ensure DEBUG is False in production."""
        if values.get("ENVIRONMENT", "").lower() == "production" and v is True:
            raise ValueError("DEBUG must be False in production")
        return v
    
    @validator("AI_PROVIDER")
    def validate_ai_provider(cls, v):
        if v not in ["openai", "gemini", "disabled"]:
            raise ValueError("AI_PROVIDER must be 'openai', 'gemini', or 'disabled'")
        return v
    
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v, values):
        if values.get("AI_PROVIDER") == "openai" and not v:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        return v
    
    @validator("GEMINI_API_KEY")
    def validate_gemini_key(cls, v, values):
        if values.get("AI_PROVIDER") == "gemini" and not v:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")
        return v


# Global settings instance
settings = Settings()