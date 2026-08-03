#!/usr/bin/env python3
"""
Simple HTTP server for LishFind Frontend
Serves the HTML file and handles CORS for API integration
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path

# Configuration
PORT = 3000
HOST = 'localhost'
FRONTEND_DIR = Path(__file__).parent

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support for API integration"""
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Customize log format
        print(f"📡 {self.address_string()} - {format % args}")

def main():
    """Start the frontend server"""
    
    print("🎨 LishFind Frontend Server")
    print("=" * 40)
    
    # Change to frontend directory
    import os
    os.chdir(FRONTEND_DIR)
    
    try:
        # Create server
        with socketserver.TCPServer((HOST, PORT), CORSHTTPRequestHandler) as httpd:
            print(f"🌐 Server running at: http://{HOST}:{PORT}")
            print(f"📁 Serving files from: {FRONTEND_DIR}")
            print(f"🔗 Backend API: http://localhost:8001")
            print()
            print("📋 Available URLs:")
            print(f"   • Frontend: http://{HOST}:{PORT}")
            print(f"   • Backend API: http://localhost:8001")
            print(f"   • API Docs: http://localhost:8001/docs")
            print()
            print("✨ Features:")
            print("   • Beautiful responsive design")
            print("   • Connected to your LishFind backend")
            print("   • Real API integration with mock responses")
            print("   • Interactive search demo")
            print()
            print("Press Ctrl+C to stop the server")
            print("=" * 40)
            
            # Open browser automatically
            try:
                webbrowser.open(f'http://{HOST}:{PORT}')
                print(f"🚀 Opening browser to http://{HOST}:{PORT}")
            except:
                print("💡 Manually open your browser to the URL above")
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n👋 Frontend server stopped. Thanks for using LishFind!")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use!")
            print("💡 Try:")
            print(f"   • Kill existing process: lsof -ti:{PORT} | xargs kill")
            print(f"   • Use different port: python3 server.py --port 3001")
        else:
            print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main()