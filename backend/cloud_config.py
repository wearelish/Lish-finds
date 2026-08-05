"""
Cloud deployment configuration for LishFind Backend

Optimized settings and utilities for cloud deployment on platforms like Render.
"""

import os
import logging
from typing import Dict, Any

# Cloud platform detection
def detect_cloud_platform() -> str:
    """Detect which cloud platform we're running on."""
    
    if os.getenv('RENDER'):
        return 'render'
    elif os.getenv('HEROKU_APP_NAME'):
        return 'heroku'
    elif os.getenv('VERCEL'):
        return 'vercel'
    elif os.getenv('AWS_EXECUTION_ENV'):
        return 'aws'
    elif os.getenv('GOOGLE_CLOUD_PROJECT'):
        return 'gcp'
    else:
        return 'unknown'


def get_cloud_optimized_config() -> Dict[str, Any]:
    """Get configuration optimized for cloud deployment."""
    
    platform = detect_cloud_platform()
    
    base_config = {
        'platform': platform,
        'environment': 'production',
        'debug': False,
        'log_level': 'INFO',
        'worker_processes': 1,  # Free tier optimization
        'max_concurrent_requests': 50,  # Free tier limit
        'database_pool_size': 5,  # Reduced for free tier
        'database_max_overflow': 10,
        'rate_limit_per_minute': 30,  # Conservative for free tier
        'ai_provider': 'disabled',  # Free tier default
    }
    
    # Platform-specific optimizations
    platform_configs = {
        'render': {
            'host': '0.0.0.0',
            'port': int(os.getenv('PORT', 8000)),
            'timeout': 300,  # Render timeout
            'keepalive_timeout': 5,
            'max_keepalive_requests': 100,
        },
        'heroku': {
            'host': '0.0.0.0', 
            'port': int(os.getenv('PORT', 8000)),
            'timeout': 30,  # Heroku timeout
            'keepalive_timeout': 2,
            'max_keepalive_requests': 50,
        }
    }
    
    if platform in platform_configs:
        base_config.update(platform_configs[platform])
    
    return base_config


def setup_cloud_logging():
    """Setup logging optimized for cloud deployment."""
    
    platform = detect_cloud_platform()
    
    # Configure structured logging for cloud platforms
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if platform == 'unknown'
        else '%(levelname)s - %(name)s - %(message)s',  # Cloud platforms add timestamps
        handlers=[logging.StreamHandler()]
    )
    
    # Suppress verbose logs in production
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def get_database_url_for_cloud() -> str:
    """Get properly formatted database URL for cloud deployment."""
    
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required for cloud deployment")
    
    # Handle Heroku postgres URL format
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    # Ensure SSL for cloud databases
    if 'sslmode=' not in db_url and ('amazonaws.com' in db_url or 'supabase' in db_url):
        separator = '&' if '?' in db_url else '?'
        db_url += f'{separator}sslmode=require'
    
    return db_url


def validate_cloud_environment():
    """Validate that all required environment variables are set for cloud deployment."""
    
    required_vars = [
        'DATABASE_URL',
        'SECRET_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Validate SECRET_KEY strength for production
    secret_key = os.getenv('SECRET_KEY')
    if len(secret_key) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters for production deployment")
    
    print("✅ Cloud environment validation passed")


def get_cors_origins_for_cloud() -> list:
    """Get CORS origins appropriate for cloud deployment."""
    
    origins_str = os.getenv('CORS_ORIGINS', '')
    
    if not origins_str:
        # Default origins for development
        return ['http://localhost:3000', 'http://127.0.0.1:3000']
    
    # Parse comma-separated origins
    origins = [origin.strip() for origin in origins_str.split(',') if origin.strip()]
    
    # Always include localhost for development
    if 'http://localhost:3000' not in origins:
        origins.append('http://localhost:3000')
    
    return origins


def optimize_for_free_tier():
    """Apply optimizations specific to free tier deployments."""
    
    optimizations = {
        'database_pool_size': 3,
        'database_max_overflow': 5,
        'max_concurrent_requests': 25,
        'rate_limit_per_minute': 20,
        'cache_ttl_seconds': 3600,  # Longer cache for fewer requests
        'ai_provider': 'disabled',
        'email_enabled': False,
        'file_uploads': False,
        'redis_enabled': False,
    }
    
    # Set environment variables for free tier
    for key, value in optimizations.items():
        env_key = key.upper()
        if not os.getenv(env_key):
            os.environ[env_key] = str(value)
    
    print("🔧 Free tier optimizations applied")


# Health check utilities for cloud platforms
def get_health_check_response() -> Dict[str, Any]:
    """Get standardized health check response for cloud platforms."""
    
    platform = detect_cloud_platform()
    config = get_cloud_optimized_config()
    
    return {
        'status': 'healthy',
        'platform': platform,
        'environment': config['environment'],
        'version': '1.0.0',
        'features': {
            'ai_enabled': config['ai_provider'] != 'disabled',
            'database': True,
            'redis': os.getenv('REDIS_URL') is not None,
            'email': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
        },
        'limits': {
            'rate_limit_per_minute': config['rate_limit_per_minute'],
            'max_concurrent_requests': config['max_concurrent_requests'],
        }
    }