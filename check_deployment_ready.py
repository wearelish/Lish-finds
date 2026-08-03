#!/usr/bin/env python3
"""
LishFind Deployment Readiness Checker

Verifies that your application is ready for cloud deployment.
"""

import os
import json
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and return status"""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description} missing: {file_path}")
        return False

def check_file_content(file_path, required_content, description):
    """Check if file contains required content"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        for requirement in required_content:
            if requirement in content:
                print(f"✅ {description}: {requirement}")
            else:
                print(f"❌ {description} missing: {requirement}")
                return False
        return True
    except Exception as e:
        print(f"❌ Error checking {file_path}: {e}")
        return False

def check_frontend_config():
    """Check frontend deployment readiness"""
    print("\n🎨 Frontend Configuration Check")
    print("-" * 40)
    
    checks = []
    
    # Check files exist
    checks.append(check_file_exists("frontend/index.html", "Main HTML file"))
    checks.append(check_file_exists("frontend/server.py", "Frontend server"))
    checks.append(check_file_exists("vercel.json", "Vercel config"))
    
    # Check HTML content
    if Path("frontend/index.html").exists():
        checks.append(check_file_content(
            "frontend/index.html",
            ["API_BASE", "localhost", "onrender.com"],
            "API configuration"
        ))
    
    return all(checks)

def check_backend_config():
    """Check backend deployment readiness"""
    print("\n🔧 Backend Configuration Check")
    print("-" * 40)
    
    checks = []
    
    # Check files exist
    checks.append(check_file_exists("backend/main.py", "Main application"))
    checks.append(check_file_exists("backend/requirements.txt", "Dependencies"))
    checks.append(check_file_exists("backend/Dockerfile", "Docker config"))
    checks.append(check_file_exists("backend/Procfile", "Render config"))
    checks.append(check_file_exists("backend/.env.production", "Production env"))
    
    # Check requirements.txt content
    if Path("backend/requirements.txt").exists():
        checks.append(check_file_content(
            "backend/requirements.txt",
            ["fastapi", "uvicorn", "asyncpg", "sqlalchemy"],
            "Required packages"
        ))
    
    return all(checks)

def check_database_config():
    """Check database configuration"""
    print("\n🗄️ Database Configuration Check")
    print("-" * 40)
    
    checks = []
    
    # Check migration files
    checks.append(check_file_exists("backend/database/init_production.py", "DB initialization"))
    checks.append(check_file_exists("backend/alembic.ini", "Alembic config"))
    
    # Check models exist
    models_dir = Path("backend/models")
    if models_dir.exists():
        model_files = ["user.py", "business.py", "base.py"]
        for model_file in model_files:
            checks.append(check_file_exists(f"backend/models/{model_file}", f"Model: {model_file}"))
    else:
        print("❌ Models directory missing")
        checks.append(False)
    
    return all(checks)

def check_deployment_files():
    """Check deployment configuration files"""
    print("\n📦 Deployment Files Check")
    print("-" * 40)
    
    checks = []
    
    # Check deployment configs
    checks.append(check_file_exists("deploy_guide.md", "Deployment guide"))
    checks.append(check_file_exists(".gitignore", "Git ignore file"))
    
    # Check if sensitive files are properly ignored
    if Path(".gitignore").exists():
        checks.append(check_file_content(
            ".gitignore",
            [".env", "*.db", "__pycache__"],
            "Sensitive files ignored"
        ))
    
    return all(checks)

def check_environment_vars():
    """Check environment variable configuration"""
    print("\n🔑 Environment Variables Check")
    print("-" * 40)
    
    checks = []
    
    # Check production env file
    if Path("backend/.env.production").exists():
        checks.append(check_file_content(
            "backend/.env.production",
            ["DATABASE_URL", "CORS_ORIGINS", "AI_PROVIDER=disabled"],
            "Production environment"
        ))
    
    # Check local env doesn't have production secrets
    if Path("backend/.env").exists():
        with open("backend/.env", 'r') as f:
            content = f.read()
            if "production" in content.lower():
                print("⚠️  Local .env contains production references")
            else:
                print("✅ Local .env is for development only")
                checks.append(True)
    
    return all(checks)

def generate_deployment_report():
    """Generate a deployment readiness report"""
    print("\n📊 Deployment Readiness Report")
    print("=" * 60)
    
    # Run all checks
    frontend_ready = check_frontend_config()
    backend_ready = check_backend_config()
    database_ready = check_database_config()
    deployment_ready = check_deployment_files()
    env_ready = check_environment_vars()
    
    # Calculate overall readiness
    checks = [frontend_ready, backend_ready, database_ready, deployment_ready, env_ready]
    ready_count = sum(checks)
    total_checks = len(checks)
    
    print(f"\n🎯 Overall Readiness: {ready_count}/{total_checks} ({ready_count/total_checks*100:.0f}%)")
    
    if ready_count == total_checks:
        print("\n🎉 READY FOR DEPLOYMENT!")
        print("✅ All checks passed")
        print("✅ You can proceed with cloud deployment")
        
        print("\n🚀 Next Steps:")
        print("1. Run: python3 deploy_to_cloud.py")
        print("2. Follow the deployment guide")
        print("3. Your app will be live!")
        
    else:
        print("\n⚠️  NOT READY FOR DEPLOYMENT")
        print(f"❌ {total_checks - ready_count} issues need to be fixed")
        
        print("\n🔧 How to Fix:")
        if not frontend_ready:
            print("• Run: python3 deploy_setup.py (fixes frontend config)")
        if not backend_ready:
            print("• Ensure all backend files are present")
        if not database_ready:
            print("• Check models and database files")
        if not deployment_ready:
            print("• Create missing deployment configuration")
        if not env_ready:
            print("• Fix environment variable issues")
    
    return ready_count == total_checks

def main():
    """Main checker function"""
    print("🔍 LishFind Deployment Readiness Check")
    print("Verifying configuration for Vercel + Render + Supabase deployment")
    
    try:
        is_ready = generate_deployment_report()
        
        if is_ready:
            print(f"\n💰 Estimated Monthly Cost: $0.00 (100% FREE)")
            print(f"🌍 Global Deployment: Frontend CDN + Backend API + Database")
        
        return is_ready
        
    except Exception as e:
        print(f"❌ Readiness check failed: {e}")
        return False

if __name__ == "__main__":
    main()