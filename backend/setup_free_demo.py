#!/usr/bin/env python3
"""
LishFind Backend - Free Demo Data Setup

Creates sample data for demonstrating the free tier functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db_session, init_db
from models.user import User, UserRole
from models.business import Business, BusinessStatus
from models.review import Review, ReviewSource
from core.security import get_password_hash


async def create_sample_users(session: AsyncSession):
    """Create sample users."""
    print("📝 Creating sample users...")
    
    # Admin user
    admin_user = User(
        id=uuid4(),
        email="admin@lishfind.com",
        hashed_password=get_password_hash("admin123"),
        name="LishFind Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    session.add(admin_user)
    
    # Business owner
    business_owner = User(
        id=uuid4(),
        email="owner@restaurant.com",
        hashed_password=get_password_hash("owner123"),
        name="Restaurant Owner",
        role=UserRole.BUSINESS,
        is_active=True,
        is_verified=True
    )
    session.add(business_owner)
    
    # Regular users
    users_data = [
        ("john@example.com", "John Smith", "user123"),
        ("jane@example.com", "Jane Doe", "user123"),
        ("mike@example.com", "Mike Johnson", "user123"),
    ]
    
    sample_users = []
    for email, name, password in users_data:
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=get_password_hash(password),
            name=name,
            role=UserRole.USER,
            is_active=True,
            is_verified=True
        )
        session.add(user)
        sample_users.append(user)
    
    await session.commit()
    print(f"✅ Created {len(users_data) + 2} sample users")
    return admin_user, business_owner, sample_users


async def create_sample_businesses(session: AsyncSession, owner: User):
    """Create sample businesses."""
    print("🏪 Creating sample businesses...")
    
    businesses_data = [
        {
            "name": "Mario's Italian Restaurant",
            "description": "Authentic Italian cuisine in the heart of the city. Family recipes passed down through generations.",
            "category": "Restaurant",
            "subcategory": "Italian",
            "address": "123 Main Street, Downtown",
            "city": "San Francisco",
            "state": "CA",
            "country": "USA",
            "postal_code": "94105",
            "phone": "+1-555-0123",
            "email": "info@marios.com",
            "website": "https://mariositalian.com",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "rating": 4.5,
            "price_range": "$$",
            "hours": {
                "monday": "11:00-22:00",
                "tuesday": "11:00-22:00", 
                "wednesday": "11:00-22:00",
                "thursday": "11:00-22:00",
                "friday": "11:00-23:00",
                "saturday": "11:00-23:00",
                "sunday": "12:00-21:00"
            }
        },
        {
            "name": "TechFix Computer Repair",
            "description": "Professional computer and laptop repair services. Quick turnaround, affordable prices.",
            "category": "Technology",
            "subcategory": "Computer Repair",
            "address": "456 Tech Avenue, Silicon Valley",
            "city": "Palo Alto", 
            "state": "CA",
            "country": "USA",
            "postal_code": "94301",
            "phone": "+1-555-0456",
            "email": "support@techfix.com",
            "website": "https://techfix.com",
            "latitude": 37.4419,
            "longitude": -122.1430,
            "rating": 4.2,
            "price_range": "$",
            "hours": {
                "monday": "09:00-18:00",
                "tuesday": "09:00-18:00",
                "wednesday": "09:00-18:00", 
                "thursday": "09:00-18:00",
                "friday": "09:00-18:00",
                "saturday": "10:00-16:00",
                "sunday": "Closed"
            }
        },
        {
            "name": "Green Leaf Yoga Studio",
            "description": "Peaceful yoga studio offering classes for all levels. Experienced instructors and calming environment.",
            "category": "Health & Fitness",
            "subcategory": "Yoga",
            "address": "789 Wellness Way, Berkeley",
            "city": "Berkeley",
            "state": "CA", 
            "country": "USA",
            "postal_code": "94704",
            "phone": "+1-555-0789",
            "email": "hello@greenleafyoga.com",
            "website": "https://greenleafyoga.com",
            "latitude": 37.8715,
            "longitude": -122.2730,
            "rating": 4.8,
            "price_range": "$",
            "hours": {
                "monday": "06:00-21:00",
                "tuesday": "06:00-21:00",
                "wednesday": "06:00-21:00",
                "thursday": "06:00-21:00", 
                "friday": "06:00-21:00",
                "saturday": "07:00-19:00",
                "sunday": "08:00-18:00"
            }
        },
        {
            "name": "BookNook Café",
            "description": "Cozy bookstore café with great coffee, pastries, and a curated selection of books.",
            "category": "Food & Drink",
            "subcategory": "Café",
            "address": "321 Literary Lane, Oakland",
            "city": "Oakland",
            "state": "CA",
            "country": "USA", 
            "postal_code": "94612",
            "phone": "+1-555-0321",
            "email": "info@booknookcafe.com",
            "website": "https://booknookcafe.com",
            "latitude": 37.8044,
            "longitude": -122.2711,
            "rating": 4.3,
            "price_range": "$",
            "hours": {
                "monday": "07:00-19:00",
                "tuesday": "07:00-19:00",
                "wednesday": "07:00-19:00",
                "thursday": "07:00-19:00",
                "friday": "07:00-20:00",
                "saturday": "08:00-20:00", 
                "sunday": "08:00-18:00"
            }
        },
        {
            "name": "QuickCut Hair Salon",
            "description": "Modern hair salon offering cuts, styling, and coloring services for men and women.",
            "category": "Beauty & Personal Care",
            "subcategory": "Hair Salon",
            "address": "654 Style Street, San Jose",
            "city": "San Jose",
            "state": "CA",
            "country": "USA",
            "postal_code": "95113",
            "phone": "+1-555-0654", 
            "email": "booking@quickcut.com",
            "website": "https://quickcutsalon.com",
            "latitude": 37.3382,
            "longitude": -121.8863,
            "rating": 4.1,
            "price_range": "$$",
            "hours": {
                "monday": "09:00-19:00",
                "tuesday": "09:00-19:00",
                "wednesday": "09:00-19:00",
                "thursday": "09:00-19:00",
                "friday": "09:00-19:00",
                "saturday": "08:00-18:00",
                "sunday": "10:00-16:00"
            }
        }
    ]
    
    businesses = []
    for business_data in businesses_data:
        business = Business(
            id=uuid4(),
            owner_id=owner.id,
            status=BusinessStatus.VERIFIED,
            **business_data
        )
        session.add(business)
        businesses.append(business)
    
    await session.commit()
    print(f"✅ Created {len(businesses_data)} sample businesses")
    return businesses


async def create_sample_reviews(session: AsyncSession, businesses: list, users: list):
    """Create sample reviews."""
    print("⭐ Creating sample reviews...")
    
    reviews_data = [
        # Mario's Italian Restaurant reviews
        (businesses[0].id, users[0].id, 5, "Excellent Food!", "Amazing pasta and great service. Will definitely come back!"),
        (businesses[0].id, users[1].id, 4, "Great atmosphere", "Food was good, nice ambiance. A bit pricey but worth it."),
        (businesses[0].id, users[2].id, 5, "Best Italian in town", "Authentic flavors and excellent wine selection."),
        
        # TechFix Computer Repair reviews  
        (businesses[1].id, users[0].id, 4, "Fixed my laptop quickly", "Professional service, reasonable prices. Fixed my screen in 2 days."),
        (businesses[1].id, users[1].id, 5, "Saved my data!", "Thought my hard drive was dead but they recovered everything!"),
        
        # Green Leaf Yoga Studio reviews
        (businesses[2].id, users[2].id, 5, "Love this place", "Amazing instructors and peaceful environment. Perfect for beginners."),
        (businesses[2].id, users[0].id, 4, "Great classes", "Good variety of classes, clean studio, friendly staff."),
        
        # BookNook Café reviews
        (businesses[3].id, users[1].id, 4, "Perfect study spot", "Great coffee and quiet environment for reading and working."), 
        (businesses[3].id, users[2].id, 5, "Book lover's paradise", "Great selection of books and the pastries are delicious!"),
        
        # QuickCut Hair Salon reviews
        (businesses[4].id, users[0].id, 3, "Decent haircut", "Good service but nothing exceptional. Fair pricing."),
        (businesses[4].id, users[1].id, 4, "Skilled stylists", "Got a great color job done. Happy with the results!"),
    ]
    
    for business_id, user_id, rating, title, content in reviews_data:
        review = Review(
            id=uuid4(),
            business_id=business_id,
            user_id=user_id,
            rating=rating,
            title=title,
            content=content,
            source=ReviewSource.LISHFIND,
            is_verified=True
        )
        session.add(review)
    
    await session.commit() 
    print(f"✅ Created {len(reviews_data)} sample reviews")


async def main():
    """Set up free demo data."""
    print("🆓 LishFind Free Tier - Demo Data Setup")
    print("="*50)
    
    try:
        # Initialize database
        print("🔧 Initializing database...")
        await init_db()
        print("✅ Database initialized")
        
        # Create sample data
        async for session in get_db_session():
            admin_user, business_owner, sample_users = await create_sample_users(session)
            businesses = await create_sample_businesses(session, business_owner)  
            await create_sample_reviews(session, businesses, sample_users)
            break  # Exit after first iteration
        
        print("\n🎉 Demo data setup complete!")
        print("\n📋 Sample Accounts Created:")
        print("   👨‍💼 Admin: admin@lishfind.com / admin123")
        print("   🏪 Business Owner: owner@restaurant.com / owner123") 
        print("   👤 Users: john@example.com, jane@example.com, mike@example.com / user123")
        
        print("\n🏪 Sample Businesses:")
        print("   🍝 Mario's Italian Restaurant")
        print("   💻 TechFix Computer Repair") 
        print("   🧘 Green Leaf Yoga Studio")
        print("   ☕ BookNook Café")
        print("   ✂️ QuickCut Hair Salon")
        
        print("\n🚀 Ready to start! Run: python3 start_free.py")
        
    except Exception as e:
        print(f"❌ Error setting up demo data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())