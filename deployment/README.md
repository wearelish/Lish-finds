# LishFind Deployment Files

This folder contains all the files and documentation needed to deploy LishFind to free hosting services.

## 📁 Files Overview

| File | Purpose |
|------|---------|
| `DEPLOYMENT_GUIDE.md` | Complete step-by-step deployment guide |
| `SUPABASE_SETUP.md` | Database setup instructions and SQL schema |
| `RENDER_SETUP.md` | Backend hosting setup for Render.com |
| `VERCEL_SETUP.md` | Frontend hosting setup for Vercel.com |

## 🚀 Quick Start

1. **Run the setup script** from project root:
   ```bash
   python3 deploy_quick_start.py
   ```

2. **Follow the generated checklist** in `DEPLOYMENT_CHECKLIST.md`

3. **Deploy in order**:
   - Database (Supabase)
   - Backend (Render)  
   - Frontend (Vercel)

## 🎯 Deployment Stack

- **Frontend**: Vercel (Static hosting)
- **Backend**: Render (Python/FastAPI)
- **Database**: Supabase (PostgreSQL + PostGIS)

## 💰 Cost

**$0/month** using free tiers:
- Vercel: 100GB bandwidth/month
- Render: 512MB RAM, sleeps after 15min
- Supabase: 500MB database storage

## 🔗 Live URLs (after deployment)

- Frontend: `https://lishfind-frontend.vercel.app`
- Backend: `https://lishfind-backend.onrender.com`
- API Docs: `https://lishfind-backend.onrender.com/docs`

## 🆘 Need Help?

1. Check the complete guide: `DEPLOYMENT_GUIDE.md`
2. Review service-specific guides for detailed instructions
3. Check GitHub issues for common problems
4. Use the troubleshooting sections in each guide

---

*Ready to deploy? Start with `python3 deploy_quick_start.py` from the project root!*