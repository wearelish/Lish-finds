#!/usr/bin/env python3
"""
LishFind Docker Management Script

Easy Docker container management for development and production.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run command and return result"""
    try:
        print(f"🔧 Running: {cmd}")
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_docker():
    """Check if Docker is installed and running"""
    print("🐳 Checking Docker...")
    
    # Check if Docker is installed
    success, stdout, stderr = run_command("docker --version", check=False)
    if not success:
        print("❌ Docker is not installed or not in PATH")
        print("   Install Docker from: https://docs.docker.com/get-docker/")
        return False
    
    print(f"✅ Docker found: {stdout.strip()}")
    
    # Check if Docker daemon is running
    success, stdout, stderr = run_command("docker info", check=False)
    if not success:
        print("❌ Docker daemon is not running")
        print("   Start Docker Desktop or run: sudo systemctl start docker")
        return False
    
    print("✅ Docker daemon is running")
    
    # Check Docker Compose
    success, stdout, stderr = run_command("docker compose version", check=False)
    if not success:
        # Try legacy docker-compose
        success, stdout, stderr = run_command("docker-compose --version", check=False)
        if not success:
            print("❌ Docker Compose not found")
            return False
        else:
            print(f"✅ Docker Compose (legacy): {stdout.strip()}")
    else:
        print(f"✅ Docker Compose: {stdout.strip()}")
    
    return True

def development_setup():
    """Start development environment"""
    print("\n🚀 Starting LishFind Development Environment")
    print("="*50)
    
    # Stop any existing containers
    print("🛑 Stopping existing containers...")
    run_command("docker compose down", check=False)
    
    # Build and start services
    print("🔨 Building and starting services...")
    success, stdout, stderr = run_command("docker compose up --build -d")
    
    if not success:
        print(f"❌ Failed to start services: {stderr}")
        return False
    
    print("✅ Services started successfully!")
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(10)
    
    # Check service health
    services = ["backend", "frontend", "db", "redis"]
    for service in services:
        print(f"   Checking {service}...")
        success, stdout, stderr = run_command(f"docker compose ps {service}", check=False)
        if success and "Up" in stdout:
            print(f"   ✅ {service} is running")
        else:
            print(f"   ⚠️  {service} may have issues")
    
    print("\n🎉 Development Environment Ready!")
    print("📋 Available Services:")
    print("   🌐 Frontend:  http://localhost:3000")
    print("   🔧 Backend:   http://localhost:8001")
    print("   📚 API Docs:  http://localhost:8001/docs")
    print("   🗄️ Database: localhost:5432")
    print("   📦 Redis:    localhost:6379")
    
    return True

def production_setup():
    """Start production environment"""
    print("\n🏭 Starting LishFind Production Environment")
    print("="*50)
    
    # Check for production environment file
    env_file = Path(".env.production")
    if not env_file.exists():
        print("❌ .env.production file not found")
        print("   Create it with production environment variables")
        return False
    
    # Stop any existing containers
    print("🛑 Stopping existing containers...")
    run_command("docker compose -f docker-compose.production.yml down", check=False)
    
    # Build and start production services
    print("🔨 Building production images...")
    success, stdout, stderr = run_command(
        "docker compose -f docker-compose.production.yml up --build -d"
    )
    
    if not success:
        print(f"❌ Failed to start production services: {stderr}")
        return False
    
    print("✅ Production services started!")
    
    print("\n🎉 Production Environment Ready!")
    print("📋 Available Services:")
    print("   🌐 Application: http://localhost")
    print("   🔧 Backend API: http://localhost/api")
    print("   🛡️ SSL ready for HTTPS configuration")
    
    return True

def show_logs():
    """Show container logs"""
    print("\n📋 Container Logs")
    print("="*30)
    
    service = input("Enter service name (backend/frontend/db/redis) or 'all': ").strip()
    
    if service == "all":
        run_command("docker compose logs --tail=50 -f")
    else:
        run_command(f"docker compose logs --tail=50 -f {service}")

def show_status():
    """Show container status"""
    print("\n📊 Container Status")
    print("="*30)
    
    success, stdout, stderr = run_command("docker compose ps")
    if success:
        print(stdout)
    else:
        print("❌ Failed to get container status")
    
    # Show resource usage
    print("\n💾 Resource Usage:")
    success, stdout, stderr = run_command("docker stats --no-stream", check=False)
    if success:
        print(stdout)

def cleanup():
    """Clean up Docker resources"""
    print("\n🧹 Cleaning Up Docker Resources")
    print("="*40)
    
    # Stop containers
    print("🛑 Stopping containers...")
    run_command("docker compose down", check=False)
    run_command("docker compose -f docker-compose.production.yml down", check=False)
    
    # Clean up images
    cleanup_type = input("Choose cleanup level (light/full): ").strip().lower()
    
    if cleanup_type == "full":
        print("🗑️  Removing all LishFind containers and images...")
        run_command("docker system prune -f", check=False)
        run_command("docker image prune -a -f", check=False)
        print("✅ Full cleanup completed")
    else:
        print("🗑️  Light cleanup...")
        run_command("docker system prune -f", check=False)
        print("✅ Light cleanup completed")

def database_management():
    """Database management utilities"""
    print("\n🗄️  Database Management")
    print("="*30)
    
    actions = {
        "1": "View database logs",
        "2": "Connect to database",
        "3": "Backup database",
        "4": "Reset database",
        "5": "Import sample data"
    }
    
    for key, value in actions.items():
        print(f"  {key}. {value}")
    
    choice = input("Choose action (1-5): ").strip()
    
    if choice == "1":
        run_command("docker compose logs db")
    elif choice == "2":
        print("🔗 Connecting to database...")
        run_command("docker compose exec db psql -U lishfind -d lishfind")
    elif choice == "3":
        print("💾 Creating database backup...")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}.sql"
        run_command(f"docker compose exec db pg_dump -U lishfind lishfind > {backup_file}")
        print(f"✅ Backup saved as {backup_file}")
    elif choice == "4":
        confirm = input("⚠️  This will delete all data. Continue? (yes/no): ")
        if confirm.lower() == "yes":
            run_command("docker compose down db")
            run_command("docker volume rm lishfind-postgres-data")
            run_command("docker compose up -d db")
            print("✅ Database reset completed")
    elif choice == "5":
        print("📊 Importing sample data...")
        run_command("docker compose exec backend python setup_free_demo.py")
        print("✅ Sample data imported")

def main():
    """Main menu"""
    print("🐳 LishFind Docker Management")
    print("="*40)
    
    if not check_docker():
        return False
    
    while True:
        print("\n🎛️  Main Menu:")
        print("  1. 🚀 Start Development Environment")
        print("  2. 🏭 Start Production Environment") 
        print("  3. 📋 Show Container Logs")
        print("  4. 📊 Show Container Status")
        print("  5. 🗄️  Database Management")
        print("  6. 🧹 Cleanup Docker Resources")
        print("  7. 🚪 Exit")
        
        choice = input("\nChoose option (1-7): ").strip()
        
        if choice == "1":
            development_setup()
        elif choice == "2":
            production_setup()
        elif choice == "3":
            show_logs()
        elif choice == "4":
            show_status()
        elif choice == "5":
            database_management()
        elif choice == "6":
            cleanup()
        elif choice == "7":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()