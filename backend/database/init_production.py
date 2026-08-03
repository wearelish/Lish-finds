#!/usr/bin/env python3
"""
Production Database Initialization Script for Supabase

Initializes the database schema and creates sample data for production deployment.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.connection import get_database_url, create_tables, init_db
from core.config import settings
from models import *  # Import all models
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_production_database():
    """Initialize production database with schema and sample data"""
    
    logger.info("🗄️  Initializing Production Database (Supabase)")
    logger.info(f"Database URL: {get_database_url()}")
    
    try:
        # Initialize database connection
        await init_db()
        logger.info("✅ Database connection established")
        
        # Create all tables
        await create_tables()
        logger.info("✅ Database tables created")
        
        # Create sample data for demonstration
        await create_sample_data()
        logger.info("✅ Sample data created")
        
        logger.info("🎉 Production database initialization completed!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

async def create_sample_data():
    """Create sample data for demonstration"""
    from database.connection import get_db_session
    from models.business import Business
    from models.user import User
    from sqlalchemy import select
    
    async for session in get_db_session():
        try:
            # Check if sample data already exists
            result = await session.execute(select(User).limit(1))
            if result.first():
                logger.info("Sample data already exists, skipping...")
                return
            
            # Create sample admin user
            from repositories.user import UserRepository
            user_repo = UserRepository(session)
            
            admin_user = await user_repo.create_user(
                email="admin@lishfind.com",
                password="admin123",  # Will be hashed
                full_name="LishFind Admin",
                is_admin=True
            )
            logger.info(f"✅ Created admin user: {admin_user.email}")
            
            # Create sample business
            sample_business = Business(
                name="Demo Restaurant",
                category="restaurant",
                description="A sample restaurant for testing",
                address="123 Main Street, Mumbai, Maharashtra",
                city="Mumbai",
                state="Maharashtra",
                latitude=19.0760,
                longitude=72.8777,
                phone="+91-9876543210",
                email="demo@restaurant.com",
                owner_id=admin_user.id,
                is_active=True,
                is_verified=True
            )
            
            session.add(sample_business)
            await session.commit()
            logger.info(f"✅ Created sample business: {sample_business.name}")
            
        except Exception as e:
            logger.error(f"Error creating sample data: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(init_production_database())