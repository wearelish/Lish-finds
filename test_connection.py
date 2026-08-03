#!/usr/bin/env python3
"""
Connection Test Script for LishFind Frontend-Backend Integration

Tests the connection between frontend and backend to diagnose issues.
"""

import requests
import time
import json
from urllib.parse import urljoin

# Configuration
BACKEND_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:3000"

def test_backend_connection():
    """Test backend API connectivity"""
    print("🔧 Testing Backend Connection...")
    print("-" * 40)
    
    # Test health endpoint
    try:
        print(f"📡 Connecting to: {BACKEND_URL}/health")
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Backend Health Check: PASSED")
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   Version: {health_data.get('version', 'unknown')}")
            print(f"   Environment: {health_data.get('environment', 'unknown')}")
            return True
        else:
            print(f"❌ Backend Health Check: FAILED (HTTP {response.status_code})")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Backend Connection: FAILED - Cannot connect to backend")
        print("   Make sure the backend is running on port 8001")
        return False
    except requests.exceptions.Timeout:
        print("❌ Backend Connection: TIMEOUT - Backend is not responding")
        return False
    except Exception as e:
        print(f"❌ Backend Connection: ERROR - {str(e)}")
        return False

def test_backend_api():
    """Test backend API endpoints"""
    print("\n🧪 Testing Backend API Endpoints...")
    print("-" * 40)
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/api/v1/health", "API health check"),
        ("/docs", "API documentation"),
        ("/api/v1/ai/status", "AI status (should show disabled)"),
    ]
    
    for endpoint, description in endpoints:
        try:
            url = f"{BACKEND_URL}{endpoint}"
            print(f"📋 Testing: {description}")
            print(f"   URL: {url}")
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code} OK")
            elif response.status_code == 404:
                print(f"   ⚠️  Status: {response.status_code} Not Found (endpoint may not exist)")
            else:
                print(f"   ❌ Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return True

def test_ai_mock_response():
    """Test AI mock response"""
    print("\n🤖 Testing AI Mock Response...")
    print("-" * 40)
    
    try:
        url = f"{BACKEND_URL}/api/v1/ai/test"
        payload = {"prompt": "Find me a restaurant"}
        
        print(f"📡 POST {url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            url, 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ AI Mock Response: SUCCESS")
            print(f"   Response: {data.get('response', 'No response field')[:100]}...")
            return True
        else:
            print(f"❌ AI Mock Response: FAILED (HTTP {response.status_code})")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ AI Mock Response: ERROR - {str(e)}")
        return False

def test_frontend_connection():
    """Test frontend server connectivity"""
    print("\n🎨 Testing Frontend Connection...")
    print("-" * 40)
    
    try:
        print(f"📡 Connecting to: {FRONTEND_URL}")
        response = requests.get(FRONTEND_URL, timeout=5)
        
        if response.status_code == 200:
            print("✅ Frontend Server: RUNNING")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            # Check if it contains LishFind content
            if "LishFind" in response.text:
                print("✅ Frontend Content: Valid LishFind page detected")
                return True
            else:
                print("⚠️  Frontend Content: Does not appear to be LishFind page")
                return False
        else:
            print(f"❌ Frontend Server: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Frontend Connection: FAILED - Cannot connect to frontend")
        print("   Make sure the frontend is running on port 3000")
        return False
    except Exception as e:
        print(f"❌ Frontend Connection: ERROR - {str(e)}")
        return False

def test_cors():
    """Test CORS configuration"""
    print("\n🌐 Testing CORS Configuration...")
    print("-" * 40)
    
    try:
        # Simulate a preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = requests.options(
            f"{BACKEND_URL}/api/v1/ai/test",
            headers=headers,
            timeout=5
        )
        
        cors_headers = {
            "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
            "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
            "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
        }
        
        print("✅ CORS Preflight Response:")
        for header, value in cors_headers.items():
            if value:
                print(f"   {header}: {value}")
            else:
                print(f"   {header}: NOT SET")
        
        return True
        
    except Exception as e:
        print(f"❌ CORS Test: ERROR - {str(e)}")
        return False

def main():
    """Run comprehensive connection tests"""
    print("🔍 LishFind Frontend-Backend Connection Test")
    print("=" * 60)
    
    tests = [
        ("Backend Connection", test_backend_connection),
        ("Backend API", test_backend_api),
        ("AI Mock Response", test_ai_mock_response),
        ("Frontend Connection", test_frontend_connection),
        ("CORS Configuration", test_cors),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print("-" * 60)
    print(f"📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Frontend-Backend connection is working!")
    else:
        print("⚠️  Some tests failed. Check the errors above for troubleshooting.")
        print("\n🔧 Troubleshooting Steps:")
        
        if not results.get("Backend Connection", False):
            print("   1. Start backend: cd /Users/akash/Documents/LISH/backend && python3 start_free.py")
        
        if not results.get("Frontend Connection", False):
            print("   2. Start frontend: cd /Users/akash/Documents/LISH/frontend && python3 server.py")
        
        if not results.get("CORS Configuration", False):
            print("   3. Check CORS settings in backend/.env file")
        
        print("   4. Kill existing processes: lsof -ti:3000 -ti:8001 | xargs kill")
        print("   5. Restart full stack: python3 start_lishfind.py")

if __name__ == "__main__":
    main()