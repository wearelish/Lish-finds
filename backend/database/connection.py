"""
Database connection management for LishFind Backend.

Handles SQLAlchemy async engine setup, connection pooling, and lifecycle management.
Production-ready with connection pooling, health checks, and performance monitoring.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import DisconnectionError, OperationalError

from core.config import settings

logger = structlog.get_logger(__name__)

# Global database engine and session maker
engine: Optional[Engine] = None
async_session_maker: Optional[async_sessionmaker] = None

# Connection pool statistics
pool_stats = {
    "total_connections": 0,
    "active_connections": 0,
    "checked_out_connections": 0,
}


def get_database_config():
    """Get database configuration based on environment."""
    config = {
        "echo": settings.DEBUG and settings.LOG_LEVEL == "DEBUG",
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # 1 hour
    }
    
    if "sqlite" in settings.DATABASE_URL:
        # SQLite configuration for development
        config.update({
            "poolclass": NullPool,  # SQLite doesn't support connection pooling
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20,
            }
        })
        logger.info("Using SQLite database configuration")
    else:
        # PostgreSQL configuration for production
        config.update({
            "poolclass": QueuePool,
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": 30,
            "pool_reset_on_return": "commit",
        })
        logger.info("Using PostgreSQL database configuration")
    
    return config


@event.listens_for(QueuePool, "connect")
def set_postgres_pragma(dbapi_connection, connection_record):
    """Set PostgreSQL connection parameters for optimal performance."""
    if hasattr(dbapi_connection, "cursor"):
        with dbapi_connection.cursor() as cursor:
            # Set connection encoding
            cursor.execute("SET client_encoding TO 'utf8'")
            # Set timezone
            cursor.execute("SET timezone TO 'UTC'")
            # Set connection timeout
            cursor.execute("SET statement_timeout TO '30s'")
            # Set lock timeout
            cursor.execute("SET lock_timeout TO '10s'")


@event.listens_for(QueuePool, "checkout")
def track_connection_checkout(dbapi_connection, connection_record, connection_proxy):
    """Track connection pool statistics."""
    pool_stats["checked_out_connections"] += 1
    pool_stats["active_connections"] = connection_proxy.pool.checkedout()


@event.listens_for(QueuePool, "checkin")
def track_connection_checkin(dbapi_connection, connection_record):
    """Track connection pool statistics."""
    pool_stats["checked_out_connections"] = max(0, pool_stats["checked_out_connections"] - 1)


async def init_db() -> None:
    """Initialize database connection and session maker with production optimizations."""
    global engine, async_session_maker
    
    try:
        logger.info("Initializing database connection", 
                   environment=settings.ENVIRONMENT,
                   database_type="SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL")
        
        # Get database configuration
        db_config = get_database_config()
        
        # Create async engine with configuration
        engine = create_async_engine(
            settings.DATABASE_URL,
            **db_config
        )
        
        # Create session maker with optimized settings
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Manual flush for better control
        )
        
        # Test connection with retry logic
        await test_database_connection()
        
        # Update pool statistics
        if hasattr(engine.pool, 'size'):
            pool_stats["total_connections"] = engine.pool.size()
        
        logger.info(
            "Database connection initialized successfully",
            database_url=_sanitize_database_url(settings.DATABASE_URL),
            pool_size=getattr(engine.pool, 'size', lambda: 'N/A')(),
            max_overflow=getattr(engine.pool, '_max_overflow', 'N/A'),
            engine_echo=db_config.get('echo', False),
        )
        
    except Exception as e:
        logger.error(
            "Failed to initialize database connection",
            error=str(e),
            database_url=_sanitize_database_url(settings.DATABASE_URL),
            exc_info=True
        )
        raise


async def test_database_connection(max_retries: int = 3, retry_delay: float = 1.0) -> None:
    """Test database connection with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                # Test basic connectivity
                result = await conn.execute(text("SELECT 1 as test_connection"))
                test_value = result.scalar()
                
                if test_value != 1:
                    raise ValueError("Database connection test failed: unexpected result")
                
                # Test database-specific features
                if "postgresql" in settings.DATABASE_URL:
                    await conn.execute(text("SELECT version()"))
                    await conn.execute(text("SELECT current_database()"))
                
            logger.info("Database connection test successful", attempt=attempt)
            return
            
        except (DisconnectionError, OperationalError) as e:
            if attempt == max_retries:
                logger.error(
                    "Database connection test failed after all retries",
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(e)
                )
                raise
            
            logger.warning(
                "Database connection test failed, retrying",
                attempt=attempt,
                max_retries=max_retries,
                error=str(e),
                retry_delay=retry_delay
            )
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5  # Exponential backoff


async def close_db() -> None:
    """Close database connections gracefully."""
    global engine
    
    if engine:
        try:
            logger.info("Closing database connections")
            
            # Wait for active connections to finish (with timeout)
            start_time = time.time()
            timeout = 30  # 30 seconds timeout
            
            while (pool_stats["checked_out_connections"] > 0 and 
                   time.time() - start_time < timeout):
                logger.info(
                    "Waiting for active connections to close",
                    active_connections=pool_stats["checked_out_connections"]
                )
                await asyncio.sleep(1)
            
            # Dispose of the engine
            await engine.dispose()
            
            # Reset global variables
            engine = None
            
            # Reset statistics
            pool_stats.update({
                "total_connections": 0,
                "active_connections": 0,
                "checked_out_connections": 0,
            })
            
            logger.info("Database connections closed successfully")
            
        except Exception as e:
            logger.error(
                "Error closing database connections",
                error=str(e),
                exc_info=True
            )


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper error handling and cleanup."""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    session: AsyncSession = async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(
            "Database session error",
            error=str(e),
            session_id=id(session),
            exc_info=True
        )
        raise
    finally:
        await session.close()


async def get_db_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_db_session() as session:
        yield session


async def health_check() -> dict:
    """Check database health and return statistics."""
    if not engine:
        return {"status": "disconnected", "error": "Database not initialized"}
    
    try:
        start_time = time.time()
        
        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))
            
            # Get database-specific information
            if "postgresql" in settings.DATABASE_URL:
                result = await conn.execute(text("""
                    SELECT 
                        current_database() as database_name,
                        version() as version,
                        pg_database_size(current_database()) as database_size
                """))
                db_info = result.fetchone()
            else:
                db_info = {"database_name": "sqlite", "version": "SQLite", "database_size": "N/A"}
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Pool statistics
        pool_info = {}
        if hasattr(engine.pool, 'size'):
            pool_info = {
                "pool_size": engine.pool.size(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "checked_in": engine.pool.checkedin(),
            }
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "database_info": dict(db_info) if db_info else {},
            "pool_info": pool_info,
            "statistics": pool_stats.copy(),
        }
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "statistics": pool_stats.copy(),
        }


def get_engine():
    """Get the database engine instance."""
    if not engine:
        raise RuntimeError("Database engine not initialized")
    return engine


def _sanitize_database_url(url: str) -> str:
    """Remove sensitive information from database URL for logging."""
    if "@" in url:
        return url.split("@")[-1]
    return url.replace("sqlite:///", "sqlite:///.../")


# Transaction helpers
@asynccontextmanager
async def transaction() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database transactions."""
    async with get_db_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def execute_query(query: str, params: dict = None) -> any:
    """Execute a raw SQL query safely."""
    async with get_db_session() as session:
        result = await session.execute(text(query), params or {})
        return result.fetchall()