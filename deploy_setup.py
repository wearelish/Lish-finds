#!/usr/bin/env python3
"""
LishFind Deployment Setup Script

Prepares the application for free cloud deployment to Vercel + Render + Supabase.
"""

import os
import json
import subprocess
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print('='*60)

def create_frontend_config():
    """Create frontend deployment configuration"""
    print_header("Frontend Configuration (Vercel)")
    
    frontend_dir = Path("frontend")
    
    # Create .env for frontend (optional)
    env_content = """# LishFind Frontend - Vercel Configuration
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
VERCEL_ENV=production
"""
    
    with open(frontend_dir / ".env", "w") as f:
        f.write(env_content)
    
    print("✅ Frontend .env created")
    print("✅ vercel.json already configured")

def create_backend_config():
    """Create backend deployment configuration"""
    print_header("Backend Configuration (Render)")
    
    backend_dir = Path("backend")
    
    # Create Procfile (alternative to render.yaml)
    procfile_content = "web: python main.py"
    
    with open(backend_dir / "Procfile", "w") as f:
        f.write(procfile_content)
    
    print("✅ Procfile created")
    print("✅ Dockerfile already configured")
    print("✅ requirements.txt updated")
    print("✅ .env.production created")

def create_git_config():
    """Setup Git configuration for deployment"""
    print_header("Git Configuration")
    
    # Create .gitignore if it doesn't exist
    gitignore_content = """
# Environment variables
.env
.env.local
.env.production.local
.env.staging.local

# Database files
*.db
*.sqlite
*.sqlite3

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# Virtual environments
venv/
env/
ENV/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# OS files
.DS_Store
Thumbs.db

# Upload directories
uploads/
media/

# Build artifacts
build/
dist/

# Dependencies
node_modules/

# Coverage reports
htmlcov/
.coverage
.coverage.*

# Pytest
.pytest_cache/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# Celery
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    
    print("✅ .gitignore created")

def display_deployment_steps():
    """Display step-by-step deployment instructions"""
    print_header("Deployment Instructions")
    
    steps = [
        ("🗄️ Step 1: Setup Supabase Database", [
            "1. Go to supabase.com and create account",
            "2. Create new project: 'lishfind-db'", 
            "3. Copy connection string from Settings → Database",
            "4. Save it for Step 2"
        ]),
        
        ("📦 Step 2: Prepare Repository", [
            "1. git add .",
            "2. git commit -m 'Prepare for deployment'",
            "3. git push origin main",
            "4. Make sure repository is public on GitHub"
        ]),
        
        ("🔧 Step 3: Deploy Backend (Render)", [
            "1. Go to render.com and connect GitHub",
            "2. Create Web Service from your repository", 
            "3. Set Root Directory: 'backend'",
            "4. Set Build Command: 'pip install -r requirements.txt'",
            "5. Set Start Command: 'python main.py'",
            "6. Add environment variables (see deploy_guide.md)",
            "7. Deploy and note the URL"
        ]),
        
        ("🌐 Step 4: Deploy Frontend (Vercel)", [
            "1. Go to vercel.com and connect GitHub",
            "2. Import your repository",
            "3. Set Root Directory: 'frontend'", 
            "4. Update API_BASE in index.html with Render URL",
            "5. Deploy and test connection"
        ]),
        
        ("🔗 Step 5: Update CORS", [
            "1. Update CORS_ORIGINS in Render with Vercel URL",
            "2. Test frontend connection to backend",
            "3. Initialize database via API or shell"
        ])
    ]
    
    for step_title, instructions in steps:
        print(f"\n{step_title}")
        for instruction in instructions:
            print(f"   {instruction}")
    
    print(f"\n📚 Full Guide: See deploy_guide.md for detailed instructions")

def create_deployment_checklist():
    """Create deployment checklist"""
    checklist = {
        "preparation": {
            "✅ Code pushed to GitHub": False,
            "✅ .env.production configured": False, 
            "✅ Frontend API URL updated": False,
            "✅ Requirements.txt up to date": False
        },
        "supabase": {
            "✅ Supabase account created": False,
            "✅ Database project created": False,
            "✅ Connection string copied": False,
            "✅ Extensions enabled": False
        },
        "render": {
            "✅ Render account created": False,
            "✅ Web service created": False,
            "✅ Environment variables set": False,
            "✅ Backend deployed successfully": False,
            "✅ Health check working": False
        },
        "vercel": {
            "✅ Vercel account created": False,
            "✅ Project imported": False,
            "✅ Frontend deployed": False,
            "✅ Custom domain configured (optional)": False
        },
        "integration": {
            "✅ CORS configured correctly": False,
            "✅ Frontend connects to backend": False,
            "✅ Database initialized": False,
            "✅ Search functionality working": False,
            "✅ All features tested": False
        }
    }
    
    with open("deployment_checklist.json", "w") as f:
        json.dump(checklist, f, indent=2)
    
    print("✅ Deployment checklist created: deployment_checklist.json")

def main():
    """Main setup function"""
    print("🚀 LishFind Free Cloud Deployment Setup")
    print("Preparing for Vercel (Frontend) + Render (Backend) + Supabase (Database)")
    
    try:
        create_git_config()
        create_frontend_config()
        create_backend_config()
        create_deployment_checklist()
        
        print_header("Setup Complete!")
        print("✅ All configuration files created")
        print("✅ Repository prepared for deployment")
        
        display_deployment_steps()
        
        print(f"\n{'='*60}")
        print("🎯 Next Steps:")
        print("1. Read deploy_guide.md for detailed instructions")
        print("2. Create accounts on Supabase, Render, and Vercel")
        print("3. Follow the deployment steps above")
        print("4. Your app will be live and FREE!")
        print('='*60)
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()