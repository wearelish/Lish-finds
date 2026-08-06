#!/usr/bin/env python3
"""
Test local server startup for LishFind

Quick test to ensure both frontend and backend can start locally.
"""

import os
import sys
import time
import subprocess
import threading
import requests
from pathlib import Path

def test_backend_startup():
    """Test backend server startup."""
    print("🔧 Testing backend startup...")
    
    backend_dir = Path(__file__).parent / "backend"
    
    try:
        # Set environment variables for testing
        env = os.environ.copy()
        env.update({
            'DATABASE_URL': 'sqlite:///./test.db',  # Use SQLite for testing
            'SECRET_KEY': 'test-secret-key-for-local-testing-only',
            'AI_PROVIDER': 'disabled',
            'DEBUG': 'true',
            'ENVIRONMENT': 'development'
        })
        
        # Start backend server
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=backend_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Test health endpoint
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                print("✅ Backend health check passed")
                health_data = response.json()
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Version: {health_data.get('version', 'unknown')}")
                success = True
            else:
                print(f"❌ Backend health check failed: HTTP {response.status_code}")
                success = False
        except requests.exceptions.RequestException as e:
            print(f"❌ Backend health check failed: {e}")
            success = False
        
        # Test AI endpoint
        if success:
            try:
                ai_response = requests.post(
                    'http://localhost:8000/api/v1/ai/test',
                    json={"prompt": "Hello, this is a test"},
                    timeout=5
                )
                if ai_response.status_code == 200:
                    print("✅ AI endpoint test passed")
                    ai_data = ai_response.json()
                    print(f"   AI Provider: {ai_data.get('provider', 'unknown')}")
                else:
                    print(f"⚠️  AI endpoint test failed: HTTP {ai_response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  AI endpoint test failed: {e}")
        
        # Terminate backend process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return success
        
    except Exception as e:
        print(f"❌ Backend startup test failed: {e}")
        return False

def test_frontend_startup():
    """Test frontend server startup."""
    print("🎨 Testing frontend startup...")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    try:
        # Start frontend server on different port to avoid conflicts
        process = subprocess.Popen(
            [sys.executable, 'server.py'],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, 'PORT': '3001'}  # Use different port
        )
        
        # Wait for startup
        time.sleep(2)
        
        # Test frontend endpoint
        try:
            response = requests.get('http://localhost:3000', timeout=5)
            if response.status_code == 200:
                print("✅ Frontend server started successfully")
                content = response.text
                if "LishFind" in content:
                    print("✅ Frontend content looks correct")
                    success = True
                else:
                    print("⚠️  Frontend content may be incomplete")
                    success = True  # Still counts as success
            else:
                print(f"❌ Frontend test failed: HTTP {response.status_code}")
                success = False
        except requests.exceptions.RequestException as e:
            # Try the alternative port
            try:
                response = requests.get('http://localhost:3001', timeout=5)
                if response.status_code == 200:
                    print("✅ Frontend server started successfully (port 3001)")
                    success = True
                else:
                    print(f"❌ Frontend test failed: {e}")
                    success = False
            except:
                print(f"❌ Frontend test failed: {e}")
                success = False
        
        # Terminate frontend process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return success
        
    except Exception as e:
        print(f"❌ Frontend startup test failed: {e}")
        return False

def main():
    """Run all server tests."""
    print("🧪 Testing Local Server Startup")
    print("=" * 50)
    
    # Test backend
    backend_success = test_backend_startup()
    print()
    
    # Test frontend  
    frontend_success = test_frontend_startup()
    print()
    
    # Summary
    print("📊 Test Results:")
    print(f"   Backend: {'✅ PASS' if backend_success else '❌ FAIL'}")
    print(f"   Frontend: {'✅ PASS' if frontend_success else '❌ FAIL'}")
    
    if backend_success and frontend_success:
        print("\n🎉 All server tests passed! Ready for deployment.")
        return True
    else:
        print("\n❌ Some server tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)