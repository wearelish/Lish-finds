#!/usr/bin/env python3
"""
LishFind Quick Start Deployment Script

Interactive script to help set up LishFind for free hosting deployment.
Generates environment files and provides deployment instructions.
"""

import os
import sys
import secrets
import string
from pathlib import Path

def print_banner():
    """Print the LishFind banner."""
    banner = """
██╗     ██╗███████╗██╗  ██╗███████╗██╗███╗   ██╗██████╗ 
██║     ██║██╔════╝██║  ██║██╔════╝██║████╗  ██║██╔══██╗
██║     ██║███████╗███████║█████╗  ██║██╔██╗ ██║██║  ██║
██║     ██║╚════██║██╔══██║██╔══╝  ██║██║╚██╗██║██║  ██║
███████╗██║███████║██║  ██║██║     ██║██║ ╚████║██████╔╝
╚══════╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ 

🚀 Free Hosting Deployment Setup
Vercel + Render + Supabase
"""
    print(banner)
    print("=" * 60)

def generate_secret_key() -> str:
    """Generate a secure secret key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def collect_deployment_info():
    """Collect deployment information from user."""
    print("📋 Let's collect your deployment information...")
    print()
    
    info = {}
    
    # Supabase Database URL
    print("🗄️  SUPABASE DATABASE")
    print("1. Create your Supabase project at: https://supabase.com")
    print("2. Enable PostGIS extension")
    print("3. Get your connection string from Settings > Database")
    print()
    
    while True:
        db_url = input("Enter your Supabase DATABASE_URL: ").strip()
        if db_url and db_url.startswith('postgresql://'):
            info['database_url'] = db_url
            break
        print("❌ Please enter a valid PostgreSQL URL starting with 'postgresql://'")
    
    print("✅ Database URL configured")
    print()
    
    # Frontend Domain
    print("🌐 FRONTEND DOMAIN")
    print("After deploying to Vercel, you'll get a URL like: lishfind-frontend.vercel.app")
    
    frontend_domain = input("Enter your Vercel domain (or press Enter for default): ").strip()
    if not frontend_domain:
        frontend_domain = "lishfind-frontend.vercel.app"
    
    info['frontend_domain'] = frontend_domain
    print(f"✅ Frontend domain: https://{frontend_domain}")
    print()
    
    # Generate secret key
    info['secret_key'] = generate_secret_key()
    print(f"✅ Generated secure secret key")
    print()
    
    return info

def create_render_env_file(info: dict):
    """Create Render environment configuration."""
    
    env_content = f"""# LishFind Backend - Render Environment Variables
# Copy these to your Render service environment variables

# Application Settings
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY={info['secret_key']}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database (Supabase)
DATABASE_URL={info['database_url']}

# CORS and Security
CORS_ORIGINS=https://{info['frontend_domain']},http://localhost:3000
ALLOWED_HOSTS=lishfind-backend.onrender.com,localhost

# Free Tier Optimizations
AI_PROVIDER=disabled
REDIS_URL=
EMAIL_ENABLED=false
STORAGE_TYPE=local
MAPS_PROVIDER=nominatim
RATE_LIMIT_PER_MINUTE=30
LOG_LEVEL=INFO
WORKER_PROCESSES=1

# Database Optimizations
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
MAX_SEARCH_RESULTS=20
CACHE_TTL_SECONDS=1800
"""
    
    env_file = Path("deployment/render_environment_variables.txt")
    env_file.parent.mkdir(exist_ok=True)
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Render environment file created: {env_file}")
    return env_file

def create_vercel_env_file(info: dict):
    """Create Vercel environment configuration."""
    
    env_content = f"""# LishFind Frontend - Vercel Environment Variables
# Add these in your Vercel project settings

BACKEND_URL=https://lishfind-backend.onrender.com
"""
    
    env_file = Path("deployment/vercel_environment_variables.txt")
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Vercel environment file created: {env_file}")
    return env_file

def create_deployment_checklist(info: dict):
    """Create a deployment checklist."""
    
    checklist = f"""# LishFind Deployment Checklist

## 🎯 Quick Deployment Guide

### 1. Database Setup (Supabase)
- [ ] Create Supabase project: https://supabase.com
- [ ] Enable PostGIS extension (Database > Extensions)
- [ ] Run SQL schema from `deployment/SUPABASE_SETUP.md`
- [ ] Verify connection string: {info['database_url'][:50]}...

### 2. Backend Setup (Render)
- [ ] Create Render account: https://render.com
- [ ] Create Web Service from GitHub: wearelish/Lish-finds
- [ ] Set Root Directory: `backend`
- [ ] Copy environment variables from: `deployment/render_environment_variables.txt`
- [ ] Deploy and wait for completion
- [ ] Test: https://lishfind-backend.onrender.com/health

### 3. Frontend Setup (Vercel)
- [ ] Create Vercel account: https://vercel.com  
- [ ] Import project from GitHub: wearelish/Lish-finds
- [ ] Set Root Directory: `.` (root)
- [ ] Copy environment variables from: `deployment/vercel_environment_variables.txt`
- [ ] Deploy and get URL: https://{info['frontend_domain']}

### 4. Final Configuration
- [ ] Update CORS_ORIGINS in Render with your Vercel URL
- [ ] Test frontend connection to backend
- [ ] Verify search functionality works
- [ ] Check all health endpoints

## 🚨 Important Notes

1. **Render Service Sleep**: Free tier sleeps after 15 minutes of inactivity
2. **Database Limits**: Supabase free tier has 500MB storage limit
3. **CORS**: Make sure frontend domain is in CORS_ORIGINS
4. **Logs**: Check service logs if deployment fails

## 🔗 Service URLs (Update after deployment)

- Frontend: https://{info['frontend_domain']}
- Backend: https://lishfind-backend.onrender.com
- Database: Supabase dashboard
- API Docs: https://lishfind-backend.onrender.com/docs

## 🧪 Testing Commands

```bash
# Test backend health
curl https://lishfind-backend.onrender.com/health

# Test AI service
curl -X POST https://lishfind-backend.onrender.com/api/v1/ai/test \\
  -H "Content-Type: application/json" \\
  -d '{{"prompt": "Hello, test"}}'
```

## ✅ Success Criteria

- [ ] All health checks return 200 OK
- [ ] Frontend loads and shows LishFind interface
- [ ] Search demo works and connects to backend
- [ ] No CORS errors in browser console
- [ ] Database contains sample data

---
Generated by LishFind Quick Start Script
Follow the full guide in: DEPLOYMENT_GUIDE.md
"""
    
    checklist_file = Path("deployment/DEPLOYMENT_CHECKLIST.md")
    
    with open(checklist_file, 'w') as f:
        f.write(checklist)
    
    print(f"✅ Deployment checklist created: {checklist_file}")
    return checklist_file

def show_next_steps(render_env_file: Path, vercel_env_file: Path, checklist_file: Path):
    """Show next steps to user."""
    
    print()
    print("🎉 Setup Complete! Here's what to do next:")
    print()
    print("📁 Files Created:")
    print(f"  • {render_env_file} - Backend environment variables")
    print(f"  • {vercel_env_file} - Frontend environment variables") 
    print(f"  • {checklist_file} - Step-by-step deployment guide")
    print()
    print("🚀 Next Steps:")
    print("  1. Follow the checklist in deployment/DEPLOYMENT_CHECKLIST.md")
    print("  2. Deploy database (Supabase) → backend (Render) → frontend (Vercel)")
    print("  3. Copy environment variables from the generated files")
    print("  4. Test your deployment")
    print()
    print("📖 Need help? Check the full guide: DEPLOYMENT_GUIDE.md")
    print()
    print("🌟 Happy deploying!")

def main():
    """Main setup function."""
    
    print_banner()
    
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("index.html").exists():
        print("❌ Error: Please run this script from the LishFind project root directory")
        print("   Make sure you can see 'backend/' and 'index.html' in the current directory")
        sys.exit(1)
    
    print("🏠 Project structure looks good!")
    print()
    
    try:
        # Collect information
        info = collect_deployment_info()
        
        # Create configuration files
        print("📝 Creating deployment configuration files...")
        render_env = create_render_env_file(info)
        vercel_env = create_vercel_env_file(info)
        checklist = create_deployment_checklist(info)
        
        # Show next steps
        show_next_steps(render_env, vercel_env, checklist)
        
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled. Run the script again when ready!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please try again or check the manual deployment guide.")
        sys.exit(1)

if __name__ == "__main__":
    main()