# LishFind Deployment Templates

This directory contains platform-specific deployment configurations and environment variable templates.

## 📁 Files Overview

### Configuration Files
- `railway-vars.txt` - Environment variables for Railway deployment
- `render-vars.txt` - Environment variables for Render.com deployment

### Usage Instructions

1. **Choose your platform** (Railway, Render, Fly.io, etc.)
2. **Copy the appropriate variables** from the template files
3. **Update the placeholder values** with your actual configuration
4. **Set the variables** in your platform's dashboard
5. **Deploy** using the platform's tools or our scripts

## 🚀 Quick Start

### Railway Deployment
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Run our deployment helper
./scripts/deploy-cloud.sh railway

# 3. Set additional variables from deployment/railway-vars.txt
```

### Render.com Deployment
```bash
# 1. Go to render.com
# 2. Create new Blueprint
# 3. Connect your repository
# 4. render.yaml will be automatically detected
# 5. Review variables in deployment/render-vars.txt
```

### Vercel (Frontend)
```bash
# 1. Go to vercel.com
# 2. Import your repository
# 3. Set output directory to "frontend"
# 4. Deploy automatically
```

## ⚙️ Environment Variables Explained

### Required Variables
- `SECRET_KEY` - JWT signing key (32+ characters)
- `CORS_ORIGINS` - Frontend domain for CORS
- `ALLOWED_HOSTS` - Backend domain for security

### Free Tier Settings
```bash
AI_PROVIDER=disabled          # No AI API costs
MAPS_PROVIDER=nominatim      # Free OpenStreetMap
EMAIL_ENABLED=false          # No SMTP costs
STORAGE_TYPE=local           # Local file storage
```

### Paid Enhancements
```bash
AI_PROVIDER=openai           # Enable AI features
MAPS_PROVIDER=google         # Better map accuracy
EMAIL_ENABLED=true           # Email notifications
STORAGE_TYPE=s3              # Cloud file storage
```

## 🔧 Platform-Specific Notes

### Railway
- Automatically provides PostgreSQL and Redis
- Excellent for backend + database deployment
- Great free tier with $5/month credit

### Render.com
- Best for full-stack deployment
- All services (backend, frontend, DB, Redis) together
- Free PostgreSQL and Redis included

### Fly.io
- Modern container platform
- Great for backend deployment
- Global edge deployment

### Vercel
- Perfect for frontend deployment
- Automatic deployments on git push
- Excellent global CDN

### Netlify
- Great for static frontend
- Powerful redirect rules for API proxy
- Generous free tier

## 📊 Cost Comparison

### Free Tier (Recommended Start)
- **Railway**: Backend + PostgreSQL (Free)
- **Vercel**: Frontend (Free)
- **Total**: $0/month

### Enhanced Tier
- **Render.com**: Full stack (Free tier)
- **OpenAI API**: ~$10-20/month
- **Google Maps**: $200 free credit/month
- **Total**: ~$10-20/month

## 🆘 Troubleshooting

### Common Issues

**"Database connection failed"**
- Check DATABASE_URL is set correctly
- Ensure database service is running
- Run migrations: `alembic upgrade head`

**"CORS errors in browser"**
- Add frontend domain to CORS_ORIGINS
- Check protocol (http vs https)
- Verify ALLOWED_HOSTS includes backend domain

**"Health check failing"**
- Ensure app binds to 0.0.0.0:$PORT
- Check /health endpoint is accessible
- Verify no blocking firewall rules

### Getting Help
1. Check platform-specific logs
2. Verify all environment variables are set
3. Test endpoints with curl/Postman
4. Join our Discord for community support

## 🔄 Updates

To update your deployment:
1. Push changes to your git repository
2. Platform automatically redeploys
3. Check deployment logs for any issues
4. Monitor health checks

## 💡 Pro Tips

1. **Start with free tiers** to test everything works
2. **Use staging environments** for testing changes
3. **Monitor your logs** for errors and performance
4. **Set up uptime monitoring** for production
5. **Backup your database** regularly
6. **Use environment-specific configs** for secrets

Happy deploying! 🚀