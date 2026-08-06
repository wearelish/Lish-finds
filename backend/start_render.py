#!/usr/bin/env python3
"""
Render.com startup script for LishFind Backend
Handles database migration and app startup for Render deployment
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def run_migrations():
    """Run database migrations if needed."""
    try:
        # Check if DATABASE_URL is set
        if not os.getenv('DATABASE_URL'):
            print("⚠️  DATABASE_URL not set, skipping migrations")
            return
        
        print("🔄 Running database migrations...")
        
        # Run Alembic migrations
        result = subprocess.run([
            'alembic', 'upgrade', 'head'
        ], cwd=backend_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database migrations completed successfully")
        else:
            print(f"❌ Migration error: {result.stderr}")
            # Don't fail startup if migrations fail in production
            print("⚠️  Continuing with app startup despite migration issues")
            
    except Exception as e:
        print(f"⚠️  Migration exception: {e}")
        print("⚠️  Continuing with app startup despite migration issues")

def main():
    """Main startup function for Render."""
    print("🚀 Starting LishFind Backend on Render...")
    
    # Set default environment variables for Render
    os.environ.setdefault('ENVIRONMENT', 'production')
    os.environ.setdefault('DEBUG', 'false')
    os.environ.setdefault('HOST', '0.0.0.0')
    os.environ.setdefault('PORT', '8000')
    
    # Run migrations
    try:
        asyncio.run(run_migrations())
    except Exception as e:
        print(f"⚠️  Migration setup failed: {e}")
    
    # Start the application
    print("🌟 Starting FastAPI application...")
    
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Import and run the app
    try:
        from main import app
        import uvicorn
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()