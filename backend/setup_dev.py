#!/usr/bin/env python3
"""
Development Environment Setup Script for LishFind Backend

This script helps developers set up the development environment with proper
virtual environment, dependencies, and configuration.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    return subprocess.run(command, shell=True, check=check)


def create_virtual_environment():
    """Create a Python virtual environment."""
    print("Creating virtual environment...")
    
    if sys.platform.startswith("win"):
        venv_path = "venv"
        python_exe = "venv/Scripts/python"
        pip_exe = "venv/Scripts/pip"
    else:
        venv_path = "venv"
        python_exe = "venv/bin/python"
        pip_exe = "venv/bin/pip"
    
    # Create virtual environment
    run_command(f"{sys.executable} -m venv {venv_path}")
    
    # Upgrade pip
    run_command(f"{python_exe} -m pip install --upgrade pip")
    
    return python_exe, pip_exe


def install_dependencies(pip_exe: str):
    """Install project dependencies."""
    print("Installing dependencies...")
    
    # Install development dependencies
    run_command(f"{pip_exe} install -r requirements-dev.txt")
    
    # Install pre-commit hooks
    if sys.platform.startswith("win"):
        run_command("venv/Scripts/pre-commit install")
    else:
        run_command("venv/bin/pre-commit install")


def create_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        with open(env_example, 'r') as src:
            content = src.read()
        
        # Generate a basic secret key
        import secrets
        secret_key = secrets.token_urlsafe(32)
        content = content.replace(
            "SECRET_KEY=your-super-secret-key-change-this-in-production",
            f"SECRET_KEY={secret_key}"
        )
        
        with open(env_file, 'w') as dst:
            dst.write(content)
        
        print("✓ Created .env file with generated secret key")
        print("⚠️  Please update the database URL and API keys in .env")
    else:
        print("✓ .env file already exists")


def check_prerequisites():
    """Check if required system dependencies are available."""
    print("Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version.split()[0]} detected")
    
    # Check if PostgreSQL is available
    try:
        run_command("psql --version", check=False)
        print("✓ PostgreSQL client detected")
    except:
        print("⚠️  PostgreSQL client not found. Install PostgreSQL for database management.")
    
    # Check if Redis is available
    try:
        run_command("redis-cli --version", check=False)
        print("✓ Redis client detected")
    except:
        print("⚠️  Redis client not found. Install Redis for caching.")


def main():
    """Main setup function."""
    print("🚀 Setting up LishFind Backend Development Environment")
    print("=" * 60)
    
    # Check prerequisites
    check_prerequisites()
    
    print("\n📦 Setting up Python environment...")
    
    # Create virtual environment if it doesn't exist
    if not Path("venv").exists():
        python_exe, pip_exe = create_virtual_environment()
        install_dependencies(pip_exe)
    else:
        print("✓ Virtual environment already exists")
        if sys.platform.startswith("win"):
            pip_exe = "venv/Scripts/pip"
        else:
            pip_exe = "venv/bin/pip"
    
    # Create .env file
    create_env_file()
    
    print("\n🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Activate virtual environment:")
    if sys.platform.startswith("win"):
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("2. Update .env file with your database URL and API keys")
    print("3. Start PostgreSQL and Redis services")
    print("4. Run database migrations:")
    print("   make migrate")
    print("5. Start the development server:")
    print("   make dev")
    
    print("\nFor more commands, run: make help")


if __name__ == "__main__":
    main()