# 🚀 LishFind Free Cloud Deployment Guide

Deploy your LishFind application for **FREE** using:
- **Frontend**: Vercel (Free tier)
- **Backend**: Render (Free tier)  
- **Database**: Supabase (Free tier)

**Total Monthly Cost: $0.00** ✨

---

## 📋 Prerequisites

- GitHub account
- Vercel account (free)
- Render account (free)
- Supabase account (free)

---

## 🗄️ Step 1: Setup Supabase Database (FREE PostgreSQL)

### 1.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up/Login with GitHub
3. Click "New Project"
4. Fill in:
   - **Name**: `lishfind-db`
   - **Database Password**: Create a strong password
   - **Region**: Choose closest to your users
5. Click "Create new project"
6. Wait for setup to complete (~2 minutes)

### 1.2 Get Database Connection

1. In your Supabase dashboard, go to **Settings** → **Database**
2. Copy the **Connection String** (URI format)
3. It looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres`
4. Save this - you'll need it for Render

### 1.3 Configure Database

1. Go to **SQL Editor** in Supabase
2. Run this to enable required extensions:

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create initial admin user (optional)
-- This will be done automatically by the app
```

---

## 🔧 Step 2: Deploy Backend to Render (FREE)

### 2.1 Prepare Repository

1. Push your code to GitHub:

```bash
cd /Users/akash/Documents/LISH
git add .
git commit -m "Prepare for cloud deployment"
git push origin main
```

### 2.2 Create Render Service

1. Go to [render.com](https://render.com)
2. Sign up/Login with GitHub
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Select `/Users/akash/Documents/LISH` repository

### 2.3 Configure Render Service

**Basic Settings:**
- **Name**: `lishfind-backend`
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: `backend`

**Build & Deploy:**
- **Build Command**: 
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

- **Start Command**:
```bash
python main.py
```

### 2.4 Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

```bash
# Application
DEBUG=false
ENVIRONMENT=production
HOST=0.0.0.0
PORT=10000

# Security (Render will generate SECRET_KEY automatically)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (paste your Supabase connection string)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres

# CORS (update with your Vercel domain later)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
ALLOWED_HOSTS=your-backend.onrender.com

# AI and other services
AI_PROVIDER=disabled
EMAIL_ENABLED=false
STORAGE_TYPE=local
MAPS_PROVIDER=nominatim
RATE_LIMIT_PER_MINUTE=100
LOG_LEVEL=INFO
```

### 2.5 Deploy Backend

1. Click **"Create Web Service"**
2. Wait for deployment (~5-10 minutes)
3. Your backend will be at: `https://your-backend.onrender.com`
4. Test: `https://your-backend.onrender.com/health`

---

## 🌐 Step 3: Deploy Frontend to Vercel (FREE)

### 3.1 Update Frontend Configuration

1. Edit `frontend/index.html` line ~627:

```javascript
// Replace with your actual Render backend URL
const API_BASE = window.location.hostname === 'localhost' 
  ? 'http://localhost:8001'  // Local development
  : 'https://your-lishfind-backend.onrender.com';  // Your Render URL
```

2. Commit changes:

```bash
git add .
git commit -m "Update API URL for production"
git push origin main
```

### 3.2 Deploy to Vercel

1. Go to [vercel.com](https://vercel.com)
2. Sign up/Login with GitHub
3. Click "New Project"
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend`
   - **Build Command**: Leave empty (static site)
   - **Output Directory**: Leave empty
   - **Install Command**: Leave empty

### 3.3 Deploy Frontend

1. Click **"Deploy"**
2. Wait for deployment (~2-3 minutes)
3. Your frontend will be at: `https://your-app.vercel.app`

---

## 🔗 Step 4: Update CORS Configuration

### 4.1 Update Backend CORS

1. Go back to your Render dashboard
2. Update the `CORS_ORIGINS` environment variable:

```bash
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

3. Your service will automatically redeploy

### 4.2 Test Integration

1. Visit your Vercel frontend: `https://your-app.vercel.app`
2. Click "Try a search" button
3. Should connect successfully to your Render backend
4. Check browser console for connection status

---

## ✅ Step 5: Initialize Database

### 5.1 Run Database Initialization

Your backend will automatically create tables on first run. To add sample data:

1. In Render dashboard, go to **Shell** tab
2. Run:

```bash
python database/init_production.py
```

Or trigger it via API:

```bash
curl -X POST https://your-backend.onrender.com/admin/init-db
```

---

## 🎯 Final URLs

After successful deployment:

- **🌐 Frontend**: `https://your-app.vercel.app`
- **🔧 Backend API**: `https://your-backend.onrender.com`
- **📚 API Docs**: `https://your-backend.onrender.com/docs`
- **🗄️ Database**: Supabase dashboard
- **💊 Health Check**: `https://your-backend.onrender.com/health`

---

## 💰 Free Tier Limits

### Vercel (Frontend)
- ✅ 100GB bandwidth/month
- ✅ Unlimited sites
- ✅ Custom domains
- ✅ Global CDN

### Render (Backend)  
- ✅ 750 hours/month (enough for 24/7)
- ✅ 512MB RAM
- ✅ Custom domains
- ⚠️ Sleeps after 15min inactivity (wakes on request)

### Supabase (Database)
- ✅ 500MB database storage
- ✅ 2GB bandwidth/month  
- ✅ 50,000 monthly active users
- ✅ Real-time subscriptions

---

## 🚨 Important Notes

### Render Sleep Mode
- Free tier services sleep after 15 minutes of inactivity
- First request after sleep takes ~30 seconds to wake up
- Consider using a service like [UptimeRobot](https://uptimerobot.com) to ping your backend every 14 minutes

### Environment Variables Security
- Never commit `.env` files to GitHub
- Use Render's environment variables for secrets
- Supabase connection strings contain passwords

### Database Backups
- Supabase automatically backs up your database
- Export data regularly for extra safety
- Free tier has 7-day point-in-time recovery

---

## 🔧 Troubleshooting

### Backend Won't Start
```bash
# Check Render logs for errors
# Common issues:
# - Missing environment variables
# - Database connection errors
# - Python package conflicts
```

### Frontend Can't Connect to Backend
```bash
# Check CORS configuration
# Ensure API_BASE URL is correct
# Verify backend is responding: curl https://your-backend.onrender.com/health
```

### Database Connection Errors
```bash
# Verify Supabase connection string
# Check if database service is running
# Ensure DATABASE_URL is set correctly in Render
```

### First Request Slow
```bash
# This is normal - Render free tier sleeps
# Subsequent requests will be fast
# Consider keep-alive service for production
```

---

## 🎉 Success!

Your LishFind application is now running **100% free** in the cloud!

- ✅ **Frontend**: Fast global CDN via Vercel
- ✅ **Backend**: Scalable API via Render  
- ✅ **Database**: Reliable PostgreSQL via Supabase
- ✅ **SSL/HTTPS**: Automatic certificates
- ✅ **Custom Domains**: Available on all platforms
- ✅ **Monitoring**: Built-in dashboards and logs

**Total Cost: $0.00/month** 🎯

Share your live application with the world! 🌟