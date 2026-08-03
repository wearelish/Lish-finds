# LishFind Deployment Guide

This guide covers deploying LishFind to various cloud platforms. The application is designed to be **free-tier friendly** with optional paid services for enhanced features.

## 🎯 Quick Deployment Options

### Option 1: All-in-One Platforms (Easiest)
- **Render.com** - Deploy backend, frontend, and database together
- **Railway** - Great for backend with automatic PostgreSQL
- **Fly.io** - Modern container platform with edge deployment

### Option 2: Specialized Platforms (Most Flexible)
- **Backend**: Railway/Render/Fly.io + **Frontend**: Vercel/Netlify
- **Database**: Railway PostgreSQL / Render PostgreSQL / Supabase

## 🚀 Platform-Specific Deployment

### Railway (Recommended for Backend)

Railway offers excellent PostgreSQL integration and simple deployment.

1. **Prepare your project**:
   ```bash
   git add .
   git commit -m "Production ready"
   ```

2. **Deploy to Railway**:
   - Connect your GitHub repo to Railway
   - Railway will auto-detect the `railway.toml` configuration
   - Add PostgreSQL service from Railway dashboard
   - Set environment variables in Railway dashboard:
     ```
     SECRET_KEY=your-super-secret-key-32-chars-minimum
     ENVIRONMENT=production
     CORS_ORIGINS=https://your-frontend-domain.vercel.app
     ALLOWED_HOSTS=your-app.railway.app
     ```

3. **Database setup**:
   - Railway automatically provides `DATABASE_URL`
   - Run migrations: `railway run python -m alembic upgrade head`

**Cost**: Free tier includes PostgreSQL + Backend hosting

---

### Render.com (Easiest All-in-One)

Deploy everything together using the `render.yaml` blueprint.

1. **Deploy with Blueprint**:
   - Fork/clone the repository
   - Connect to Render.com
   - Use the `render.yaml` blueprint for automatic setup
   - All services (backend, frontend, database, Redis) deploy together

2. **Configure environment**:
   - Render auto-generates `SECRET_KEY`
   - Update `CORS_ORIGINS` to match your frontend URL
   - All database connections are automatic

**Cost**: Free tier includes PostgreSQL + Redis + 2 web services

---

### Vercel (Frontend) + Railway (Backend)

Perfect combination for modern web apps.

1. **Deploy Backend to Railway** (see Railway section above)

2. **Deploy Frontend to Vercel**:
   - Connect GitHub repo to Vercel
   - Set build settings:
     - Framework: Other
     - Build Command: `echo "Static site"`
     - Output Directory: `frontend`
   - Update `vercel.json` with your backend URL
   - Deploy automatically on git push

**Cost**: Both platforms have generous free tiers

---

### Fly.io (Advanced)

Modern container platform with global edge deployment.

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Deploy**:
   ```bash
   fly launch --dockerfile backend/Dockerfile
   fly deploy
   ```

3. **Set secrets**:
   ```bash
   fly secrets set SECRET_KEY="your-secret-key"
   fly secrets set DATABASE_URL="postgresql://..."
   ```

**Cost**: Free tier includes 3 small VMs

---

### Netlify (Frontend Only)

Great for frontend with serverless functions.

1. **Deploy**:
   - Connect GitHub repo to Netlify
   - Set publish directory: `frontend`
   - Update backend URL in `netlify.toml`
   - Deploy automatically

2. **Configure redirects**:
   - Update the backend URL in `netlify.toml`
   - All API calls redirect to your backend

**Cost**: Free tier is very generous

## 🔧 Environment Configuration

### Required Environment Variables

**Production (All Platforms)**:
```bash
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-minimum-32-characters

# Database (provided by platform)
DATABASE_URL=postgresql://user:password@host:port/database

# Security
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Optional: AI Features
AI_PROVIDER=disabled  # or openai/gemini with API keys
OPENAI_API_KEY=sk-...  # if using OpenAI

# Optional: Enhanced Maps
MAPS_PROVIDER=nominatim  # free, or 'google' with API key
GOOGLE_MAPS_API_KEY=AIza...  # if using Google Maps
```

### Free Tier Configuration

For **zero-cost operation**, use these settings:
```bash
AI_PROVIDER=disabled
MAPS_PROVIDER=nominatim
EMAIL_ENABLED=false
STORAGE_TYPE=local
```

### Paid Tier Enhancements

For **enhanced features**:
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
MAPS_PROVIDER=google
GOOGLE_MAPS_API_KEY=AIza-your-key
EMAIL_ENABLED=true
SMTP_HOST=smtp.sendgrid.net
```

## 📋 Pre-Deployment Checklist

### Security Checklist
- [ ] Change all default passwords and secrets
- [ ] Set strong `SECRET_KEY` (32+ characters)
- [ ] Configure `CORS_ORIGINS` with exact domains
- [ ] Set `ALLOWED_HOSTS` to specific domains (no wildcards)
- [ ] Enable HTTPS in production
- [ ] Review rate limiting settings

### Performance Checklist
- [ ] Configure database connection pooling
- [ ] Enable Redis caching (if available)
- [ ] Set up CDN for static assets
- [ ] Enable gzip compression
- [ ] Configure proper cache headers

### Monitoring Checklist
- [ ] Set up health check endpoints
- [ ] Configure log aggregation
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Monitor database performance
- [ ] Set up uptime monitoring

## 🆘 Troubleshooting

### Common Issues

**Database Connection Errors**:
- Verify `DATABASE_URL` is correctly set
- Check database service is running
- Ensure migrations are applied: `alembic upgrade head`

**CORS Errors**:
- Add frontend domain to `CORS_ORIGINS`
- Check `ALLOWED_HOSTS` includes backend domain
- Verify protocol (http vs https) matches

**Health Check Failures**:
- Ensure `/health` endpoint is accessible
- Check application is binding to `0.0.0.0:$PORT`
- Verify no firewall blocking health checks

**Performance Issues**:
- Enable database connection pooling
- Add Redis caching
- Check query performance with database logs
- Monitor memory usage

### Getting Help

1. Check application logs first
2. Verify environment variables are set correctly
3. Test endpoints manually with curl/Postman
4. Check platform-specific documentation
5. Create an issue in the repository with:
   - Platform used
   - Error messages
   - Environment configuration (without secrets)

## 🔄 Continuous Deployment

All platforms support automatic deployment on git push:

1. **Connect repository** to your platform
2. **Configure environment** variables
3. **Push to main branch** triggers deployment
4. **Monitor deployment** logs for issues

For advanced CI/CD, see the GitHub Actions workflows in `.github/workflows/`.

## 💡 Pro Tips

1. **Start with free tiers** to test deployment
2. **Use staging environments** for testing
3. **Monitor costs** as you scale
4. **Enable caching** for better performance
5. **Set up monitoring** early
6. **Backup your database** regularly
7. **Use environment-specific configs** for secrets
8. **Test locally with Docker** before deploying

## 📊 Cost Optimization

### Free Tier Strategy
- Use Render.com or Railway for backend (includes PostgreSQL)
- Use Vercel or Netlify for frontend
- Disable AI features initially
- Use Nominatim for maps (free)
- Use local file storage

### Scaling Strategy
- Add Redis when traffic grows
- Enable AI features for better UX
- Switch to Google Maps for accuracy
- Add email notifications
- Use S3 for file storage
- Set up monitoring and alerting

This deployment guide ensures you can start free and scale as needed! 🚀