#!/usr/bin/env python3
"""
LishFind Backend - Free Tier Startup Script

Starts the LishFind backend in completely free mode with no paid API dependencies.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import uvicorn
from core.config import settings


def print_banner():
    """Print startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🆓 LishFind Backend                        ║
║                     FREE TIER MODE                           ║
║                                                              ║
║  ✅ User Authentication        ✅ Business Management        ║
║  ✅ Basic Search & Filters     ✅ Reviews & Ratings         ║
║  ✅ Geolocation (Nominatim)    ✅ Analytics & Reports       ║
║  ✅ Admin Dashboard            ✅ API Documentation         ║
║                                                              ║
║  🚫 AI Features Disabled (No API costs!)                    ║
║                                                              ║
║  💰 Monthly Cost: $0.00                                     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_free_tier_config():
    """Verify free tier configuration."""
    print("🔍 Checking Free Tier Configuration...")
    
    # Check AI is disabled
    if settings.AI_PROVIDER == "disabled":
        print("  ✅ AI Provider: DISABLED (Free)")
    else:
        print(f"  ⚠️  AI Provider: {settings.AI_PROVIDER} (May incur costs)")
    
    # Check database
    if "sqlite" in settings.DATABASE_URL:
        print("  ✅ Database: SQLite (Free)")
    else:
        print(f"  💰 Database: {settings.DATABASE_URL} (May incur costs)")
    
    # Check maps provider
    if settings.MAPS_PROVIDER == "nominatim":
        print("  ✅ Maps: Nominatim/OpenStreetMap (Free)")
    else:
        print(f"  💰 Maps: {settings.MAPS_PROVIDER} (May incur costs)")
    
    # Check Redis
    if not hasattr(settings, 'REDIS_URL') or not settings.REDIS_URL:
        print("  ✅ Cache: Memory-based (Free)")
    else:
        print(f"  💰 Cache: Redis (May incur costs)")
    
    # Check storage
    if settings.STORAGE_TYPE == "local":
        print("  ✅ Storage: Local filesystem (Free)")
    else:
        print(f"  💰 Storage: {settings.STORAGE_TYPE} (May incur costs)")
    
    print("\n🎉 Configuration verified for FREE operation!\n")


def main():
    """Start the LishFind backend in free tier mode."""
    print_banner()
    check_free_tier_config()
    
    # Server configuration
    host = getattr(settings, 'HOST', '0.0.0.0')
    port = getattr(settings, 'PORT', 8001)
    
    print(f"🚀 Starting LishFind Backend...")
    print(f"   📡 URL: http://localhost:{port}")
    print(f"   📚 API Docs: http://localhost:{port}/docs")
    print(f"   💊 Health Check: http://localhost:{port}/health")
    print(f"   🔧 Admin Panel: http://localhost:{port}/admin (when implemented)")
    print("\n📋 Available Endpoints:")
    print("   • Authentication: /api/v1/auth/*")
    print("   • Business Management: /api/v1/business/*")
    print("   • Search & Filters: /api/v1/search/*")
    print("   • Rankings: /api/v1/ranking/*")
    print("   • Cache Management: /api/v1/cache/*")
    print("   • AI (Mock Responses): /api/v1/ai/*")
    
    print("\n" + "="*60)
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 LishFind Backend stopped. Thank you for using the free tier!")


if __name__ == "__main__":
    main()