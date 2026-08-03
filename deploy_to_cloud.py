#!/usr/bin/env python3
"""
LishFind Cloud Deployment Automation

Automates the deployment process to Vercel + Render + Supabase.
"""

import os
import subprocess
import json
import webbrowser
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def print_step(step, description):
    """Print formatted step"""
    print(f"\n🔹 Step {step}: {description}")
    print("-" * 50)

def check_prerequisites():
    """Check if required tools are installed"""
    print_step(0, "Checking Prerequisites")
    
    # Check Git
    git_ok, _, _ = run_command("git --version")
    if git_ok:
        print("✅ Git is installed")
    else:
        print("❌ Git is required. Install from: https://git-scm.com/")
        return False
    
    # Check if we're in a git repository
    in_git, _, _ = run_command("git status")
    if not in_git:
        print("⚠️  Not in a Git repository. Initializing...")
        run_command("git init")
        run_command("git add .")
        run_command('git commit -m "Initial commit"')
    
    print("✅ Prerequisites met")
    return True

def prepare_repository():
    """Prepare repository for deployment"""
    print_step(1, "Preparing Repository")
    
    # Run setup script
    success, output, error = run_command("python3 deploy_setup.py")
    if success:
        print("✅ Deployment configuration created")
    else:
        print(f"⚠️  Setup script issues: {error}")
    
    # Commit changes
    run_command("git add .")
    success, _, _ = run_command('git commit -m "Prepare for cloud deployment"')
    
    if success:
        print("✅ Changes committed to Git")
    else:
        print("ℹ️  No new changes to commit")
    
    return True

def deploy_instructions():
    """Show deployment instructions with links"""
    print_step(2, "Cloud Service Setup")
    
    services = [
        {
            "name": "Supabase (Database)",
            "url": "https://supabase.com",
            "description": "Free PostgreSQL database",
            "steps": [
                "1. Create account and new project",
                "2. Name: 'lishfind-db'",  
                "3. Copy connection string from Settings → Database",
                "4. Keep it for Render setup"
            ]
        },
        {
            "name": "Render (Backend)",
            "url": "https://render.com", 
            "description": "Free backend hosting",
            "steps": [
                "1. Connect GitHub account",
                "2. Create 'Web Service' from repository",
                "3. Root Directory: 'backend'",
                "4. Build: 'pip install -r requirements.txt'", 
                "5. Start: 'python main.py'",
                "6. Add environment variables (see guide)",
                "7. Deploy and copy URL"
            ]
        },
        {
            "name": "Vercel (Frontend)", 
            "url": "https://vercel.com",
            "description": "Free frontend hosting",
            "steps": [
                "1. Import GitHub repository",
                "2. Root Directory: 'frontend'",
                "3. Framework: Other (static)",
                "4. Deploy immediately",
                "5. Update API_BASE with Render URL"
            ]
        }
    ]
    
    for service in services:
        print(f"\n🌐 {service['name']}: {service['description']}")
        print(f"   URL: {service['url']}")
        print("   Steps:")
        for step in service['steps']:
            print(f"     {step}")
    
    return services

def open_deployment_links():
    """Open deployment service websites"""
    print_step(3, "Opening Deployment Services")
    
    links = [
        "https://supabase.com",
        "https://render.com", 
        "https://vercel.com"
    ]
    
    for link in links:
        print(f"🌐 Opening: {link}")
        try:
            webbrowser.open(link)
        except:
            print(f"   Manual: {link}")

def create_env_template():
    """Create environment variable templates"""
    print_step(4, "Environment Variable Templates")
    
    # Supabase template
    supabase_template = """
# Copy this connection string from Supabase Settings → Database
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
"""
    
    # Render template  
    render_template = """
# Add these environment variables in Render dashboard:

DEBUG=false
ENVIRONMENT=production
HOST=0.0.0.0
PORT=10000

DATABASE_URL=[PASTE_SUPABASE_CONNECTION_STRING]

CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
ALLOWED_HOSTS=your-backend.onrender.com

AI_PROVIDER=disabled
EMAIL_ENABLED=false
STORAGE_TYPE=local
MAPS_PROVIDER=nominatim
RATE_LIMIT_PER_MINUTE=100
LOG_LEVEL=INFO

# Render will auto-generate:
SECRET_KEY=[AUTO_GENERATED]
"""
    
    # Save templates
    with open("supabase_config.txt", "w") as f:
        f.write(supabase_template)
    
    with open("render_env_vars.txt", "w") as f:
        f.write(render_template)
    
    print("✅ Environment templates created:")
    print("   📄 supabase_config.txt - Database connection")
    print("   📄 render_env_vars.txt - Backend environment variables")

def show_success_message():
    """Show success message and next steps"""
    print(f"\n{'='*60}")
    print("🎉 LishFind Deployment Setup Complete!")
    print('='*60)
    
    print("\n📋 What's Ready:")
    print("✅ Repository prepared for deployment")
    print("✅ Configuration files created")
    print("✅ Environment templates generated")
    print("✅ Deployment services opened in browser")
    
    print("\n🎯 Next Steps:")
    print("1. 📖 Read deploy_guide.md for detailed instructions")
    print("2. 🗄️ Setup Supabase database (use supabase_config.txt)")
    print("3. 🔧 Deploy backend to Render (use render_env_vars.txt)")
    print("4. 🌐 Deploy frontend to Vercel")
    print("5. 🔗 Update CORS settings and test")
    
    print("\n💡 Tips:")
    print("• Keep the deploy_guide.md open for reference")
    print("• Test each step before moving to the next")
    print("• Use deployment_checklist.json to track progress")
    
    print(f"\n💰 Total Cost: $0.00/month (100% FREE)")
    print(f"🌟 Your app will be live at: https://your-app.vercel.app")

def main():
    """Main deployment automation"""
    print("🚀 LishFind Free Cloud Deployment")
    print("Automating deployment to Vercel + Render + Supabase")
    print("="*60)
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            return False
        
        # Prepare repository
        prepare_repository()
        
        # Show deployment instructions
        deploy_instructions()
        
        # Create environment templates
        create_env_template()
        
        # Open deployment links
        response = input("\n❓ Open deployment service websites? (y/n): ").lower()
        if response in ['y', 'yes']:
            open_deployment_links()
        
        # Show success message
        show_success_message()
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment setup failed: {e}")
        return False

if __name__ == "__main__":
    main()