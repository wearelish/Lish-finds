#!/usr/bin/env python3
"""
LishFind Quick Start Script

Simple one-click solution to start LishFind with proper frontend-backend connection.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def main():
    print("🚀 LishFind Quick Start")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    
    # Kill existing processes
    print("🔧 Cleaning up existing processes...")
    subprocess.run("lsof -ti:3000 -ti:8001 | xargs kill 2>/dev/null || true", shell=True)
    time.sleep(2)
    
    # Start backend
    print("🔧 Starting backend server...")
    backend_cmd = [sys.executable, "start_free.py"]
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=project_root / "backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Wait for backend
    print("⏳ Waiting for backend...")
    for i in range(20):
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("✅ Backend ready!")
                break
        except:
            pass
        time.sleep(1)
        print(f"   Checking... ({i+1}/20)")
    else:
        print("❌ Backend failed to start")
        return
    
    # Start frontend  
    print("🎨 Starting frontend server...")
    frontend_cmd = [sys.executable, "server.py"]
    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd=project_root / "frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Wait for frontend
    print("⏳ Waiting for frontend...")
    for i in range(10):
        try:
            response = requests.get("http://localhost:3000", timeout=2)
            if response.status_code == 200:
                print("✅ Frontend ready!")
                break
        except:
            pass
        time.sleep(1)
        print(f"   Checking... ({i+1}/10)")
    else:
        print("❌ Frontend failed to start")
        backend_process.terminate()
        return
    
    # Success
    print("\n🎉 LishFind is running!")
    print("🌐 Frontend: http://localhost:3000")
    print("🔧 Backend:  http://localhost:8001")
    print("\nPress Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        backend_process.terminate()
        frontend_process.terminate()
        print("👋 Stopped!")

if __name__ == "__main__":
    main()