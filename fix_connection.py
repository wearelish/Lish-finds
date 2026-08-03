#!/usr/bin/env python3
"""
LishFind Connection Fix Script

Diagnoses and fixes common frontend-backend connection issues.
"""

import subprocess
import time
import os
import sys
import requests
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_PORT = 8001
FRONTEND_PORT = 3000

def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)

def run_command(cmd, cwd=None, timeout=10):
    """Run command and return result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def kill_processes_on_ports():
    """Kill existing processes on ports 3000 and 8001"""
    print_header("Killing Existing Processes")
    
    for port in [FRONTEND_PORT, BACKEND_PORT]:
        print(f"🔍 Checking port {port}...")
        
        # Find processes on port
        success, stdout, stderr = run_command(f"lsof -ti:{port}")
        
        if success and stdout.strip():
            pids = stdout.strip().split('\n')
            print(f"   Found {len(pids)} process(es) on port {port}")
            
            for pid in pids:
                if pid:
                    print(f"   Killing process {pid}...")
                    kill_success, _, _ = run_command(f"kill {pid}")
                    if kill_success:
                        print(f"   ✅ Process {pid} killed")
                    else:
                        print(f"   ⚠️  Failed to kill process {pid}, trying force kill...")
                        run_command(f"kill -9 {pid}")
        else:
            print(f"   ✅ Port {port} is free")
    
    time.sleep(2)  # Wait for processes to fully terminate

def check_dependencies():
    """Check if required dependencies are available"""
    print_header("Checking Dependencies")
    
    # Check Python
    python_ok, python_version, _ = run_command("python3 --version")
    if python_ok:
        print(f"✅ Python: {python_version.strip()}")
    else:
        print("❌ Python 3 not found")
        return False
    
    # Check backend directory
    if BACKEND_DIR.exists():
        print(f"✅ Backend directory: {BACKEND_DIR}")
    else:
        print(f"❌ Backend directory not found: {BACKEND_DIR}")
        return False
    
    # Check frontend directory  
    if FRONTEND_DIR.exists():
        print(f"✅ Frontend directory: {FRONTEND_DIR}")
    else:
        print(f"❌ Frontend directory not found: {FRONTEND_DIR}")
        return False
    
    # Check backend requirements
    backend_main = BACKEND_DIR / "main.py"
    if backend_main.exists():
        print("✅ Backend main.py found")
    else:
        print("❌ Backend main.py not found")
        return False
    
    # Check frontend server
    frontend_server = FRONTEND_DIR / "server.py"
    if frontend_server.exists():
        print("✅ Frontend server.py found")
    else:
        print("❌ Frontend server.py not found")
        return False
    
    return True

def fix_backend_config():
    """Check and fix backend configuration"""
    print_header("Checking Backend Configuration")
    
    env_file = BACKEND_DIR / ".env"
    
    if not env_file.exists():
        print("❌ Backend .env file missing")
        print("   Copying from .env.example...")
        
        env_example = BACKEND_DIR / ".env.example"
        if env_example.exists():
            # Copy and modify for free tier
            with open(env_example, 'r') as f:
                content = f.read()
            
            # Modify for free tier
            content = content.replace('PORT=8000', 'PORT=8001')
            content = content.replace('AI_PROVIDER=openai', 'AI_PROVIDER=disabled')
            content = content.replace('DATABASE_URL=postgresql:', '# DATABASE_URL=postgresql:')
            content += '\nDATABASE_URL=sqlite+aiosqlite:///./lishfind_demo.db\n'
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("✅ .env file created with free tier settings")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ Backend .env file exists")
    
    # Check port configuration
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    if 'PORT=8001' in env_content:
        print("✅ Backend configured for port 8001")
    else:
        print("⚠️  Backend port configuration might be incorrect")
        
    return True

def test_backend():
    """Start backend and test connection"""
    print_header("Testing Backend")
    
    print("🚀 Starting backend server...")
    
    # Start backend in background
    backend_process = subprocess.Popen(
        [sys.executable, "start_free.py"],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Wait for backend to start
    print("⏳ Waiting for backend to start...")
    
    for attempt in range(30):  # 30 seconds timeout
        try:
            response = requests.get(f"http://localhost:{BACKEND_PORT}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Backend is running and responding!")
                health_data = response.json()
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Version: {health_data.get('version', 'unknown')}")
                return backend_process
        except:
            pass
        
        time.sleep(1)
        print(f"   Attempt {attempt + 1}/30...")
    
    # Backend failed to start
    print("❌ Backend failed to start within 30 seconds")
    
    # Get error output
    backend_process.terminate()
    try:
        stdout, _ = backend_process.communicate(timeout=5)
        if stdout:
            print("Backend output:")
            print(stdout[-1000:])  # Last 1000 characters
    except:
        pass
    
    return None

def test_frontend():
    """Start frontend and test connection"""
    print_header("Testing Frontend")
    
    print("🎨 Starting frontend server...")
    
    # Start frontend in background
    frontend_process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Wait for frontend to start
    print("⏳ Waiting for frontend to start...")
    
    for attempt in range(15):  # 15 seconds timeout
        try:
            response = requests.get(f"http://localhost:{FRONTEND_PORT}", timeout=2)
            if response.status_code == 200 and "LishFind" in response.text:
                print("✅ Frontend is running and serving LishFind page!")
                return frontend_process
        except:
            pass
        
        time.sleep(1)
        print(f"   Attempt {attempt + 1}/15...")
    
    # Frontend failed to start
    print("❌ Frontend failed to start within 15 seconds")
    
    # Get error output
    frontend_process.terminate()
    try:
        stdout, _ = frontend_process.communicate(timeout=5)
        if stdout:
            print("Frontend output:")
            print(stdout[-500:])  # Last 500 characters
    except:
        pass
    
    return None

def test_integration():
    """Test frontend-backend integration"""
    print_header("Testing Integration")
    
    try:
        print("🔗 Testing API call from frontend perspective...")
        
        # Test health endpoint
        response = requests.get(f"http://localhost:{BACKEND_PORT}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint returned {response.status_code}")
            return False
        
        # Test AI endpoint
        ai_response = requests.post(
            f"http://localhost:{BACKEND_PORT}/api/v1/ai/test",
            json={"prompt": "test"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if ai_response.status_code == 200:
            print("✅ AI endpoint working")
            ai_data = ai_response.json()
            print(f"   Response: {ai_data.get('response', 'No response')[:100]}...")
        else:
            print(f"❌ AI endpoint returned {ai_response.status_code}")
            return False
        
        print("✅ All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Main fix procedure"""
    print("🔧 LishFind Connection Fix Script")
    print("This script will diagnose and fix frontend-backend connection issues.")
    
    # Step 1: Kill existing processes
    kill_processes_on_ports()
    
    # Step 2: Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please ensure Python 3 and all files are present.")
        return False
    
    # Step 3: Fix backend config
    if not fix_backend_config():
        print("\n❌ Backend configuration failed.")
        return False
    
    # Step 4: Test backend
    backend_process = test_backend()
    if not backend_process:
        print("\n❌ Backend test failed.")
        return False
    
    # Step 5: Test frontend
    frontend_process = test_frontend()
    if not frontend_process:
        print("\n❌ Frontend test failed.")
        backend_process.terminate()
        return False
    
    # Step 6: Test integration
    if not test_integration():
        print("\n❌ Integration test failed.")
        backend_process.terminate()
        frontend_process.terminate()
        return False
    
    # Success!
    print_header("SUCCESS!")
    print("🎉 LishFind is now running successfully!")
    print()
    print("🌐 Frontend: http://localhost:3000")
    print("🔧 Backend:  http://localhost:8001")
    print("📚 API Docs: http://localhost:8001/docs")
    print()
    print("✨ Try the search demo on the frontend page!")
    print()
    print("Press Ctrl+C to stop both servers...")
    
    try:
        # Keep running until interrupted
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend process died")
                break
            
            if frontend_process.poll() is not None:
                print("❌ Frontend process died") 
                break
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        
    finally:
        # Clean up
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        
        print("👋 Servers stopped!")
    
    return True

if __name__ == "__main__":
    main()