#!/usr/bin/env python3
"""
LishFind Deployment Test Suite

Comprehensive testing script to validate deployment configuration
and ensure all components work correctly before production deployment.
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m' 
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

class DeploymentTester:
    """Main deployment testing class."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.deployment_dir = self.project_root / "deployment"
        self.test_results = []
    
    def run_all_tests(self) -> bool:
        """Run all deployment tests."""
        print_header("🧪 LishFind Deployment Test Suite")
        
        tests = [
            ("Project Structure", self.test_project_structure),
            ("Backend Configuration", self.test_backend_config),
            ("Frontend Configuration", self.test_frontend_config),
            ("Dependencies", self.test_dependencies),
            ("Environment Files", self.test_environment_files),
            ("Deployment Files", self.test_deployment_files),
            ("Database Configuration", self.test_database_config),
            ("AI Service Configuration", self.test_ai_service_config),
            ("API Endpoints", self.test_api_endpoints),
            ("Frontend Assets", self.test_frontend_assets),
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            print_info(f"Running: {test_name}")
            try:
                result = test_func()
                if result:
                    print_success(f"{test_name}: PASSED")
                else:
                    print_error(f"{test_name}: FAILED")
                    all_passed = False
            except Exception as e:
                print_error(f"{test_name}: ERROR - {str(e)}")
                all_passed = False
            
            self.test_results.append({
                "name": test_name,
                "passed": result if 'result' in locals() else False,
                "error": str(e) if 'e' in locals() else None
            })
        
        # Print summary
        self.print_test_summary()
        
        if all_passed:
            print_success("\n🎉 All tests passed! Your deployment setup is ready.")
            self.print_next_steps()
        else:
            print_error("\n❌ Some tests failed. Please fix the issues before deploying.")
        
        return all_passed
    
    def test_project_structure(self) -> bool:
        """Test project directory structure."""
        required_files = [
            "index.html",
            "vercel.json", 
            "package.json",
            "deploy_quick_start.py",
            "DEPLOYMENT_GUIDE.md",
            "backend/main.py",
            "backend/requirements.txt",
            "backend/render.yaml",
            "frontend/index.html",
            "frontend/server.py",
            "deployment/README.md",
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print_error(f"Missing files: {', '.join(missing_files)}")
            return False
        
        return True
    
    def test_backend_config(self) -> bool:
        """Test backend configuration files."""
        config_file = self.backend_dir / "core" / "config.py"
        
        if not config_file.exists():
            print_error("Backend config.py not found")
            return False
        
        # Check if configuration has required settings
        config_content = config_file.read_text()
        required_settings = [
            "AI_PROVIDER",
            "DATABASE_URL", 
            "SECRET_KEY",
            "CORS_ORIGINS",
            "ENVIRONMENT"
        ]
        
        missing_settings = []
        for setting in required_settings:
            if setting not in config_content:
                missing_settings.append(setting)
        
        if missing_settings:
            print_error(f"Missing config settings: {', '.join(missing_settings)}")
            return False
        
        # Check for free tier optimizations
        if 'AI_PROVIDER.*disabled' not in config_content:
            print_warning("AI_PROVIDER default should be 'disabled' for free tier")
        
        return True
    
    def test_frontend_config(self) -> bool:
        """Test frontend configuration."""
        # Check root index.html exists (for Vercel)
        root_index = self.project_root / "index.html"
        if not root_index.exists():
            print_error("Root index.html not found (required for Vercel)")
            return False
        
        # Check vercel.json configuration
        vercel_config = self.project_root / "vercel.json"
        if not vercel_config.exists():
            print_error("vercel.json not found")
            return False
        
        try:
            with open(vercel_config) as f:
                config = json.load(f)
            
            # Check required configuration
            if "builds" not in config:
                print_error("vercel.json missing 'builds' configuration")
                return False
            
            if "routes" not in config:
                print_error("vercel.json missing 'routes' configuration") 
                return False
        
        except json.JSONDecodeError:
            print_error("vercel.json is not valid JSON")
            return False
        
        # Check API URL configuration in frontend
        index_content = root_index.read_text()
        if "API_BASE" not in index_content:
            print_error("Frontend missing API_BASE configuration")
            return False
        
        return True
    
    def test_dependencies(self) -> bool:
        """Test Python dependencies."""
        requirements_file = self.backend_dir / "requirements.txt"
        
        if not requirements_file.exists():
            print_error("requirements.txt not found")
            return False
        
        requirements = requirements_file.read_text()
        
        # Check essential dependencies
        essential_deps = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "pydantic",
            "asyncpg",
            "psycopg2-binary"
        ]
        
        missing_deps = []
        for dep in essential_deps:
            if dep not in requirements.lower():
                missing_deps.append(dep)
        
        if missing_deps:
            print_error(f"Missing dependencies: {', '.join(missing_deps)}")
            return False
        
        # Check if requirements are not too heavy for free tier
        lines = requirements.strip().split('\n')
        active_deps = [line for line in lines if line and not line.startswith('#')]
        
        if len(active_deps) > 20:
            print_warning(f"Large number of dependencies ({len(active_deps)}) may slow deployment")
        
        return True
    
    def test_environment_files(self) -> bool:
        """Test environment file templates."""
        env_files = [
            self.backend_dir / ".env.render",
            self.deployment_dir / "SUPABASE_SETUP.md",
            self.deployment_dir / "RENDER_SETUP.md", 
            self.deployment_dir / "VERCEL_SETUP.md"
        ]
        
        for env_file in env_files:
            if not env_file.exists():
                print_error(f"Environment file missing: {env_file}")
                return False
        
        # Check .env.render template
        render_env = (self.backend_dir / ".env.render").read_text()
        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "AI_PROVIDER=disabled",
            "CORS_ORIGINS"
        ]
        
        for var in required_vars:
            if var not in render_env:
                print_error(f"Missing environment variable in .env.render: {var}")
                return False
        
        return True
    
    def test_deployment_files(self) -> bool:
        """Test deployment configuration files."""
        deployment_files = {
            self.backend_dir / "render.yaml": "Render configuration",
            self.project_root / "vercel.json": "Vercel configuration",
            self.project_root / "DEPLOYMENT_GUIDE.md": "Deployment guide",
            self.project_root / "deploy_quick_start.py": "Quick start script"
        }
        
        for file_path, description in deployment_files.items():
            if not file_path.exists():
                print_error(f"{description} missing: {file_path}")
                return False
        
        # Test if quick start script is executable
        quick_start = self.project_root / "deploy_quick_start.py"
        if not os.access(quick_start, os.X_OK):
            print_warning("deploy_quick_start.py is not executable")
        
        return True
    
    def test_database_config(self) -> bool:
        """Test database configuration."""
        # Check if database connection module exists
        db_module = self.backend_dir / "database" / "connection.py"
        
        if not db_module.exists():
            print_error("Database connection module not found")
            return False
        
        db_content = db_module.read_text()
        
        # Check for essential database features
        essential_features = [
            "create_async_engine",
            "async_sessionmaker", 
            "health_check",
            "PostGIS",
            "connection pool"
        ]
        
        missing_features = []
        for feature in essential_features:
            if feature.lower().replace(" ", "_") not in db_content.lower():
                missing_features.append(feature)
        
        if missing_features:
            print_warning(f"Database features not detected: {', '.join(missing_features)}")
        
        return True
    
    def test_ai_service_config(self) -> bool:
        """Test AI service configuration."""
        ai_service = self.backend_dir / "services" / "ai_service.py"
        
        if not ai_service.exists():
            print_error("AI service module not found")
            return False
        
        ai_content = ai_service.read_text()
        
        # Check for mock response capability (free tier)
        if "mock" not in ai_content.lower():
            print_error("AI service missing mock response capability for free tier")
            return False
        
        # Check for provider abstraction
        if "disabled" not in ai_content:
            print_error("AI service missing 'disabled' provider option")
            return False
        
        return True
    
    def test_api_endpoints(self) -> bool:
        """Test API endpoint configuration."""
        api_dir = self.backend_dir / "api" / "v1" / "endpoints"
        
        if not api_dir.exists():
            print_error("API endpoints directory not found")
            return False
        
        # Check essential endpoints
        essential_endpoints = [
            "ai.py",
            "search.py"
        ]
        
        for endpoint in essential_endpoints:
            endpoint_file = api_dir / endpoint
            if not endpoint_file.exists():
                print_error(f"Essential endpoint missing: {endpoint}")
                return False
        
        return True
    
    def test_frontend_assets(self) -> bool:
        """Test frontend assets and configuration."""
        frontend_index = self.frontend_dir / "index.html"
        root_index = self.project_root / "index.html"
        
        if not frontend_index.exists() or not root_index.exists():
            print_error("Frontend index.html files missing")
            return False
        
        # Check if root index.html has the API configuration
        root_content = root_index.read_text()
        
        if "API_BASE" not in root_content:
            print_error("Root index.html missing API configuration")
            return False
        
        if "onrender.com" not in root_content:
            print_error("Root index.html missing Render backend URL")
            return False
        
        # Check for essential frontend features
        if "Try a search" not in root_content:
            print_warning("Frontend missing search demo functionality")
        
        return True
    
    def print_test_summary(self):
        """Print test results summary."""
        print_header("📊 Test Results Summary")
        
        passed = sum(1 for test in self.test_results if test["passed"])
        total = len(self.test_results)
        
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        # Print failed tests
        failed_tests = [test for test in self.test_results if not test["passed"]]
        if failed_tests:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for test in failed_tests:
                print(f"  ❌ {test['name']}")
                if test["error"]:
                    print(f"     Error: {test['error']}")
    
    def print_next_steps(self):
        """Print next steps after successful testing."""
        print_header("🚀 Next Steps")
        
        print("Your LishFind deployment is ready! Here's what to do next:")
        print()
        print("1️⃣  Push to GitHub:")
        print("   git add .")
        print("   git commit -m 'Deployment ready - all tests passed'")
        print("   git push origin main")
        print()
        print("2️⃣  Run deployment setup:")
        print("   python3 deploy_quick_start.py")
        print()
        print("3️⃣  Follow the deployment checklist generated by the script")
        print()
        print("4️⃣  Test your live deployment:")
        print("   - Frontend: https://lishfind-frontend.vercel.app")
        print("   - Backend: https://lishfind-backend.onrender.com/health")
        print("   - API Docs: https://lishfind-backend.onrender.com/docs")
        print()
        print_success("Good luck with your deployment! 🌟")


def main():
    """Main function to run deployment tests."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("LishFind Deployment Test Suite")
        print()
        print("Usage: python3 test_deployment.py")
        print()
        print("This script validates your deployment configuration")
        print("and ensures all components are ready for production deployment.")
        return
    
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("index.html").exists():
        print_error("Please run this script from the LishFind project root directory")
        print_info("Make sure you can see 'backend/' and 'index.html' in the current directory")
        sys.exit(1)
    
    # Run tests
    tester = DeploymentTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()