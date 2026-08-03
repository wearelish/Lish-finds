#!/usr/bin/env python3
"""
LishFind Full Stack Startup Script

Starts both frontend and backend servers for complete development environment.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
BACKEND_PORT = 8001
FRONTEND_PORT = 3000

def print_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   🚀 LishFind Full Stack                     ║
║                Starting Frontend + Backend                   ║
║                                                              ║
║  🎨 Frontend: http://localhost:3000                         ║
║  🔧 Backend API: http://localhost:8001                      ║
║  📚 API Docs: http://localhost:8001/docs                    ║
║                                                              ║
║  💰 Cost: $0.00/month (Free Tier)                          ║
║                                                              ║
║  Press Ctrl+C to stop both servers                          ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

class ProcessManager:
    """Manages frontend and backend processes"""
    
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.processes = []
    
    def start_backend(self):
        """Start the backend server"""
        print("🔧 Starting Backend Server...")
        
        try:
            # Change to backend directory and start
            cmd = [
                sys.executable, 'start_free.py'
            ]
            
            self.backend_process = subprocess.Popen(
                cmd,
                cwd=BACKEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append(self.backend_process)
            print(f"✅ Backend started (PID: {self.backend_process.pid})")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
    
    def start_frontend(self):
        """Start the frontend server"""
        print("🎨 Starting Frontend Server...")
        
        try:
            # Start frontend server
            cmd = [
                sys.executable, 'server.py'
            ]
            
            self.frontend_process = subprocess.Popen(
                cmd,
                cwd=FRONTEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append(self.frontend_process)
            print(f"✅ Frontend started (PID: {self.frontend_process.pid})")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False
    
    def check_ports(self):
        """Check if ports are available"""
        import socket
        
        def is_port_open(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', port))
                return result != 0
        
        if not is_port_open(BACKEND_PORT):
            print(f"⚠️  Port {BACKEND_PORT} is already in use (Backend)")
            return False
            
        if not is_port_open(FRONTEND_PORT):
            print(f"⚠️  Port {FRONTEND_PORT} is already in use (Frontend)")
            return False
        
        return True
    
    def wait_for_backend(self, timeout=30):
        """Wait for backend to be ready"""
        import urllib.request
        import urllib.error
        
        print("⏳ Waiting for backend to be ready...")
        
        for i in range(timeout):
            try:
                response = urllib.request.urlopen(f'http://localhost:{BACKEND_PORT}/health', timeout=2)
                if response.status == 200:
                    print("✅ Backend is ready!")
                    return True
            except urllib.error.URLError:
                time.sleep(1)
                print(f"   Checking... ({i+1}/{timeout})")
        
        print("❌ Backend startup timeout")
        return False
    
    def stop_all(self):
        """Stop all processes"""
        print("\n🛑 Stopping all servers...")
        
        for process in self.processes:
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✅ Process {process.pid} stopped")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"🔨 Process {process.pid} force killed")
                except Exception as e:
                    print(f"⚠️  Error stopping process: {e}")
        
        print("👋 All servers stopped!")

def main():
    """Main startup function"""
    print_banner()
    
    # Check directories exist
    if not BACKEND_DIR.exists():
        print(f"❌ Backend directory not found: {BACKEND_DIR}")
        sys.exit(1)
    
    if not FRONTEND_DIR.exists():
        print(f"❌ Frontend directory not found: {FRONTEND_DIR}")
        sys.exit(1)
    
    # Initialize process manager
    manager = ProcessManager()
    
    # Set up signal handling
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Check ports
        if not manager.check_ports():
            print("💡 Kill existing processes or use different ports")
            sys.exit(1)
        
        # Start backend
        if not manager.start_backend():
            sys.exit(1)
        
        # Wait for backend to be ready
        if not manager.wait_for_backend():
            manager.stop_all()
            sys.exit(1)
        
        # Start frontend
        if not manager.start_frontend():
            manager.stop_all()
            sys.exit(1)
        
        # Wait a bit for frontend to start
        time.sleep(2)
        
        print("\n🎉 LishFind Full Stack Ready!")
        print("=" * 50)
        print("🌐 Frontend: http://localhost:3000")
        print("🔧 Backend: http://localhost:8001")
        print("📚 API Docs: http://localhost:8001/docs")
        print("💊 Health Check: http://localhost:8001/health")
        print("=" * 50)
        print("Press Ctrl+C to stop all servers")
        print()
        
        # Keep running until interrupted
        while True:
            # Check if processes are still running
            if manager.backend_process and manager.backend_process.poll() is not None:
                print("❌ Backend process died")
                break
            
            if manager.frontend_process and manager.frontend_process.poll() is not None:
                print("❌ Frontend process died")
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        manager.stop_all()

if __name__ == "__main__":
    main()