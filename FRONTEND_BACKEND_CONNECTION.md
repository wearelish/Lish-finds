# 🔗 Frontend-Backend Connection Guide

This guide helps you troubleshoot and fix connection issues between the LishFind frontend and backend.

## 🚀 Quick Fix (Try This First)

```bash
cd /Users/akash/Documents/LISH

# Option 1: Quick Start (Recommended)
python3 quick_start.py

# Option 2: Full Diagnostic Fix
python3 fix_connection.py

# Option 3: Manual Full Stack Start
python3 start_lishfind.py
```

## 🔍 Diagnosing Connection Issues

### Test Connection Status

```bash
# Test the connection
python3 test_connection.py
```

This will check:
- ✅ Backend health endpoint
- ✅ Frontend server status  
- ✅ API endpoint functionality
- ✅ CORS configuration
- ✅ Mock AI responses

## 🐛 Common Issues & Solutions

### Issue 1: "Connection Failed" in Frontend

**Symptoms:**
- Frontend shows "Connection Failed" error
- Browser console shows fetch errors
- Backend API calls timeout

**Solutions:**

```bash
# 1. Check if backend is running
curl http://localhost:8001/health

# 2. If not running, start backend
cd backend
python3 start_free.py

# 3. Check backend logs for errors
# Look for startup errors in terminal
```

### Issue 2: Port Already in Use

**Symptoms:**
- Error: "Port 8001 already in use"  
- Error: "Port 3000 already in use"

**Solutions:**

```bash
# Kill processes on both ports
lsof -ti:3000 -ti:8001 | xargs kill

# Or kill specific port
lsof -ti:8001 | xargs kill  # Backend
lsof -ti:3000 | xargs kill  # Frontend

# Then restart
python3 quick_start.py
```

### Issue 3: CORS Errors

**Symptoms:**
- Browser console: "CORS policy blocked"
- "Access-Control-Allow-Origin" errors

**Solutions:**

1. **Check backend CORS settings:**
```bash
# In backend/.env file, ensure:
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
ALLOWED_HOSTS=*
```

2. **Restart backend after CORS changes:**
```bash
cd backend
python3 start_free.py
```

### Issue 4: Backend Database Errors

**Symptoms:**
- Backend fails to start
- Database connection errors
- SQLite permission issues

**Solutions:**

```bash
# Reset database
cd backend
rm -f lishfind_demo.db
python3 start_free.py  # Will recreate database
```

### Issue 5: Missing Dependencies

**Symptoms:**
- ModuleNotFoundError  
- Import errors
- Package not found

**Solutions:**

```bash
# Install backend requirements
cd backend
pip3 install -r requirements.txt

# If pip issues, try:
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## 📋 Manual Step-by-Step Startup

If automated scripts don't work, try manual startup:

### 1. Start Backend

```bash
cd /Users/akash/Documents/LISH/backend

# Check configuration
cat .env | grep -E "(PORT|CORS|DATABASE)"

# Start server
python3 start_free.py
```

**Expected output:**
```
🆓 LishFind Backend - FREE TIER MODE
✅ Database: SQLite (Free)
✅ AI Provider: DISABLED (Free)
🚀 Starting LishFind Backend...
📡 URL: http://localhost:8001
```

### 2. Test Backend

```bash
# In new terminal
curl http://localhost:8001/health

# Expected response:
{"status":"healthy","version":"1.0.0",...}
```

### 3. Start Frontend

```bash
cd /Users/akash/Documents/LISH/frontend
python3 server.py
```

**Expected output:**
```
🎨 LishFind Frontend Server
🌐 Server running at: http://localhost:3000
🔗 Backend API: http://localhost:8001
```

### 4. Test Integration

1. Open browser: http://localhost:3000
2. Click "Try a search →" button
3. Should show search modal and connect to backend
4. Check browser console for any errors

## 🔧 Configuration Files

### Backend Configuration (`backend/.env`)

```bash
# Critical settings for frontend connection:
PORT=8001
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
ALLOWED_HOSTS=*
DATABASE_URL=sqlite+aiosqlite:///./lishfind_demo.db
AI_PROVIDER=disabled
```

### Frontend Configuration (`frontend/index.html`)

```javascript
// API configuration (line ~625)
const API_BASE = 'http://localhost:8001';
```

## 🌐 Network Troubleshooting

### Check Port Status

```bash
# List processes on ports
lsof -i :3000 -i :8001

# Check if ports are accessible
curl -I http://localhost:8001/health
curl -I http://localhost:3000
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8001/health

# AI test endpoint  
curl -X POST http://localhost:8001/api/v1/ai/test \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test"}'

# API documentation
open http://localhost:8001/docs
```

## 🚨 Emergency Reset

If nothing works, try complete reset:

```bash
cd /Users/akash/Documents/LISH

# 1. Kill all processes
sudo lsof -ti:3000 -ti:8001 | xargs sudo kill -9

# 2. Reset backend database  
rm -f backend/lishfind_demo.db

# 3. Clean Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# 4. Restart fresh
python3 quick_start.py
```

## 📞 Getting Help

### Check Logs

```bash
# Backend logs (in terminal running backend)
# Look for:
# - Port binding errors
# - Database connection issues  
# - Import/module errors

# Frontend logs (browser console)
# Look for:
# - Network errors
# - CORS errors
# - 404/500 API responses
```

### Debug Information

When asking for help, provide:

1. **Error messages** from both backend and frontend
2. **Browser console output** (F12 → Console)  
3. **Test results** from `python3 test_connection.py`
4. **Port status** from `lsof -i :3000 -i :8001`
5. **Configuration** from `backend/.env`

## ✅ Success Indicators

When everything is working correctly:

- ✅ Backend responds to http://localhost:8001/health
- ✅ Frontend loads at http://localhost:3000  
- ✅ "Try a search" button works without errors
- ✅ Browser console shows "✅ Backend connected"
- ✅ Search modal shows "Connected to Backend"
- ✅ Mock AI responses are received

## 🎯 Testing Your Fix

After fixing issues:

1. **Basic Test:**
   - Open http://localhost:3000
   - Click "Try a search" 
   - Should see successful connection

2. **Full Test:**
   - Run `python3 test_connection.py`
   - All tests should pass

3. **Integration Test:**
   - Test different search queries
   - Check browser network tab for API calls
   - Verify responses are received

Your LishFind application should now have a working frontend-backend connection! 🎉