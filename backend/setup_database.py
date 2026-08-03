#!/usr/bin/env python3
"""
Database Setup Script for LishFind Backend

Sets up the database with initial data and configurations.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import init_db, get_engine
from models.base import Base


async def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    
    try:
        # Initialize database connection
        await init_db()
        engine = get_engine()
        
        # Import all models to ensure they're registered
        from models import (
            User, Business, Review, SavedBusiness, SearchHistory,
            BusinessAnalytics, SearchAnalytics, UserEngagement
        )
        
        # Create all tables
        async with engine.begin() as conn:
            # Drop all tables (for development)
            print("Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            print("Creating new tables...")
            await conn.run_sync(Base.metadata.create_all)
        
        print("✓ Database tables created successfully!")
        
        # Optional: Add some sample data
        await add_sample_data()
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        sys.exit(1)


async def add_sample_data():
    """Add some sample data for development."""
    print("Adding sample data...")
    
    try:
        from database.connection import async_session_maker
        from models import User, Business, Review, UserRole, BusinessStatus, PriceRange
        from core.security import get_password_hash
        import uuid
        from decimal import Decimal
        
        async with async_session_maker() as session:
            # Sample users
            admin_user = User(
                id=uuid.uuid4(),
                email="admin@lishfind.com",
                hashed_password=get_password_hash("admin123"),
                full_name="LishFind Admin",
                role=UserRole.ADMIN,
                is_verified=True
            )
            
            business_owner = User(
                id=uuid.uuid4(),
                email="owner@example.com", 
                hashed_password=get_password_hash("owner123"),
                full_name="Business Owner",
                role=UserRole.BUSINESS,
                is_verified=True
            )
            
            regular_user = User(
                id=uuid.uuid4(),
                email="user@example.com",
                hashed_password=get_password_hash("user123"),
                full_name="Regular User",
                role=UserRole.USER,
                is_verified=True
            )
            
            session.add_all([admin_user, business_owner, regular_user])
            await session.flush()
            
            # Sample businesses
            cafe_business = Business(
                id=uuid.uuid4(),
                name="The Coffee Corner",
                description="A cozy café serving freshly brewed coffee and homemade pastries.",
                category="café",
                subcategory="coffee_shop",
                latitude=Decimal("28.6139"),
                longitude=Decimal("77.2090"),  # Delhi coordinates
                address="123 Main Street, Connaught Place",
                city="New Delhi",
                state="Delhi",
                postal_code="110001",
                country="India",
                phone="+91-11-12345678",
                email="info@coffeecorner.com",
                website="https://coffeecorner.com",
                opening_hours={
                    "monday": {"open": "08:00", "close": "22:00"},
                    "tuesday": {"open": "08:00", "close": "22:00"},
                    "wednesday": {"open": "08:00", "close": "22:00"}, 
                    "thursday": {"open": "08:00", "close": "22:00"},
                    "friday": {"open": "08:00", "close": "23:00"},
                    "saturday": {"open": "09:00", "close": "23:00"},
                    "sunday": {"open": "09:00", "close": "22:00"}
                },
                services=["Wi-Fi", "Takeaway", "Dine-in", "Outdoor Seating"],
                amenities=["Free Wi-Fi", "Air Conditioning", "Parking Available"],
                price_range=PriceRange.MODERATE,
                status=BusinessStatus.VERIFIED,
                verified=True,
                claimed=True,
                rating=Decimal("4.5"),
                review_count=25,
                owner_id=business_owner.id
            )
            
            restaurant_business = Business(
                id=uuid.uuid4(),
                name="Spice Garden Restaurant",
                description="Authentic Indian cuisine with a modern twist. Family-friendly atmosphere.",
                category="restaurant",
                subcategory="indian_cuisine",
                latitude=Decimal("28.6280"),
                longitude=Decimal("77.2187"),  # Delhi coordinates
                address="456 Restaurant Row, Khan Market",
                city="New Delhi", 
                state="Delhi",
                postal_code="110003",
                country="India",
                phone="+91-11-87654321",
                email="info@spicegarden.com",
                opening_hours={
                    "monday": {"open": "12:00", "close": "23:00"},
                    "tuesday": {"open": "12:00", "close": "23:00"},
                    "wednesday": {"open": "12:00", "close": "23:00"},
                    "thursday": {"open": "12:00", "close": "23:00"},
                    "friday": {"open": "12:00", "close": "24:00"},
                    "saturday": {"open": "12:00", "close": "24:00"},
                    "sunday": {"open": "12:00", "close": "23:00"}
                },
                services=["Dine-in", "Takeaway", "Home Delivery", "Catering"],
                amenities=["Family Seating", "Air Conditioning", "Valet Parking"],
                price_range=PriceRange.EXPENSIVE,
                status=BusinessStatus.VERIFIED,
                verified=True,
                claimed=False,
                rating=Decimal("4.2"),
                review_count=18
            )
            
            session.add_all([cafe_business, restaurant_business])
            await session.flush()
            
            # Sample reviews
            cafe_review1 = Review(
                id=uuid.uuid4(),
                rating=5,
                title="Amazing coffee and atmosphere!",
                content="Love this place! The coffee is excellent and the staff is very friendly. Great place to work with laptop.",
                user_id=regular_user.id,
                business_id=cafe_business.id,
                verified=True
            )
            
            cafe_review2 = Review(
                id=uuid.uuid4(),
                rating=4,
                title="Good coffee, bit crowded",
                content="Coffee quality is good but it gets quite crowded during lunch hours. The pastries are fresh though.",
                user_id=admin_user.id,
                business_id=cafe_business.id,
                verified=True
            )
            
            restaurant_review = Review(
                id=uuid.uuid4(),
                rating=4,
                title="Authentic flavors",
                content="The food is delicious and authentic. Service was good but had to wait a bit longer than expected.",
                user_id=regular_user.id,
                business_id=restaurant_business.id,
                verified=True
            )
            
            session.add_all([cafe_review1, cafe_review2, restaurant_review])
            
            # Commit all changes
            await session.commit()
            
            print("✓ Sample data added successfully!")
            print("\nSample users created:")
            print(f"  Admin: admin@lishfind.com / admin123")
            print(f"  Business Owner: owner@example.com / owner123")
            print(f"  Regular User: user@example.com / user123")
            
    except Exception as e:
        print(f"⚠️  Warning: Could not add sample data: {e}")
        print("   This is not critical for setup.")


def main():
    """Main setup function."""
    print("🏗️  Setting up LishFind Database")
    print("=" * 50)
    
    # Run the async setup
    asyncio.run(create_tables())
    
    print("\n✅ Database setup completed!")
    print("\nNext steps:")
    print("1. Start the development server: make dev")
    print("2. Visit http://localhost:8000/docs for API documentation")
    print("3. Use the sample login credentials above")


if __name__ == "__main__":
    main()