# Database Migration Environment Configuration
# Enhanced for production with better error handling and logging

import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

# Import your models here
from models.base import Base
from core.config import settings

# Alembic Config object
config = context.config

# Set the SQLAlchemy URL from our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # For SQLite compatibility
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # For SQLite compatibility
        
        # Production optimizations
        transaction_per_migration=True,
        transactional_ddl=True,
        
        # Include object name in generated migrations
        include_object=include_object,
        
        # Custom naming conventions
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()

def include_object(object, name, type_, reflected, compare_to):
    """Include/exclude objects from auto-generation."""
    # Skip alembic version table
    if type_ == "table" and name == "alembic_version":
        return False
    
    # Skip temporary tables
    if name and name.startswith("temp_"):
        return False
        
    # Skip indexes on SQLite (they're auto-created)
    if type_ == "index" and "sqlite" in str(context.get_bind().engine.url):
        return False
    
    return True

def process_revision_directives(context, revision, directives):
    """Process revision directives to customize migration generation."""
    # Auto-generate better revision messages
    if getattr(config.cmd_opts, 'autogenerate', False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("No schema changes detected.")

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    
    # Create async engine configuration
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    
    # Handle async engine creation
    if "postgresql" in settings.DATABASE_URL:
        # PostgreSQL async configuration
        connectable = AsyncEngine(
            engine_from_config(
                configuration,
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
        )
        
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        
        await connectable.dispose()
    else:
        # SQLite synchronous configuration
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        
        with connectable.connect() as connection:
            do_run_migrations(connection)

def run_migrations():
    """Main migration runner with environment detection."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        if "postgresql" in settings.DATABASE_URL:
            asyncio.run(run_migrations_online())
        else:
            # SQLite runs synchronously
            configuration = config.get_section(config.config_ini_section)
            configuration["sqlalchemy.url"] = settings.DATABASE_URL
            
            connectable = engine_from_config(
                configuration,
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
            
            with connectable.connect() as connection:
                do_run_migrations(connection)

# Run migrations
run_migrations()