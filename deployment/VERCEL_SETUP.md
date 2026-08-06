# Vercel Frontend Setup for LishFind

## Step 1: Prepare Repository Structure

The frontend is now configured to be deployed from the root directory with `index.html` at the top level. This structure is required for Vercel's static site deployment.

**File Structure:**
```
/Users/akash/Documents/LISH/
├── index.html              # Main frontend file (moved from frontend/)
├── vercel.json            # Vercel deployment configuration
├── frontend/              # Original frontend folder (kept for reference)
└── backend/               # Backend folder (not deployed to Vercel)
```

## Step 2: Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Sign up with your GitHub account
3. Authorize Vercel to access your repositories

## Step 3: Deploy to Vercel

### Option A: Deploy from GitHub (Recommended)

1. Make sure your code is pushed to GitHub: `wearelish/Lish-finds`
2. In Vercel dashboard, click "New Project"
3. Import your GitHub repository: `wearelish/Lish-finds`
4. Configure deployment:

**Build Settings:**
- **Framework Preset**: Other
- **Root Directory**: `.` (root)
- **Build Command**: Leave empty (static site)
- **Output Directory**: Leave empty
- **Install Command**: Leave empty

**Environment Variables:**
- `BACKEND_URL`: `https://lishfind-backend.onrender.com`

5. Click "Deploy"

### Option B: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to project root
cd /Users/akash/Documents/LISH

# Deploy
vercel

# Follow the prompts:
# - Set up and deploy? Y
# - Which scope? Your account
# - Link to existing project? N
# - Project name: lishfind-frontend
# - Directory: ./
# - Override settings? Y
# - Build Command: (leave empty)
# - Output Directory: (leave empty)
# - Development Command: python3 frontend/server.py
```

## Step 4: Configure Custom Domain (Optional)

1. In Vercel dashboard → Settings → Domains
2. Add your custom domain (e.g., `lishfind.com`)
3. Follow DNS configuration instructions
4. Update CORS settings in backend to include your domain

## Step 5: Environment Variables

In your Vercel project dashboard:

1. Go to Settings → Environment Variables
2. Add:
   - **Name**: `BACKEND_URL`
   - **Value**: `https://lishfind-backend.onrender.com`
   - **Environments**: Production, Preview, Development

## Step 6: Update Backend CORS

After deployment, update your backend environment variables on Render:

```
CORS_ORIGINS=https://lishfind-frontend.vercel.app,https://your-custom-domain.com,http://localhost:3000
ALLOWED_HOSTS=lishfind-backend.onrender.com
```

## Verification

After successful deployment:

1. **Frontend URL**: `https://lishfind-frontend.vercel.app` (or your custom domain)
2. **Test these features**:
   - Page loads correctly with animations
   - "Try a search" button works
   - Backend connection status shows in console
   - Demo search functionality works

## Vercel Configuration Details

The `vercel.json` file configures:

- **Static Site**: Serves `index.html` for all routes
- **Security Headers**: X-Frame-Options, X-Content-Type-Options
- **Environment**: Backend URL injection
- **Caching**: Automatic edge caching for static assets

## Free Tier Limitations

Vercel free tier includes:
- **Bandwidth**: 100GB/month
- **Build Time**: 6,000 minutes/month
- **Deployments**: Unlimited
- **Custom Domains**: 1 per project
- **Edge Functions**: 100GB-hours/month

## Troubleshooting

**Deployment Fails**:
- Ensure `index.html` is in root directory
- Check `vercel.json` syntax is valid
- Verify no build commands are required

**Frontend Loads but API Fails**:
- Check backend URL in browser console
- Verify backend is running on Render
- Check CORS configuration

**Custom Domain Issues**:
- Verify DNS settings
- Update backend CORS to include new domain
- Check SSL certificate status

## Local Development vs Production

**Local Development**:
```bash
# Start frontend (serves on localhost:3000)
cd frontend && python3 server.py

# Start backend (serves on localhost:8001)
cd backend && python3 main.py
```

**Production**:
- **Frontend**: Vercel serves static files with CDN
- **Backend**: Render serves API with auto-scaling
- **Database**: Supabase provides PostgreSQL with PostGIS

## Next Steps

After successful deployment:
1. Test full search functionality
2. Monitor performance in Vercel Analytics
3. Set up custom domain if needed
4. Configure monitoring and alerts