# LishFind 🔍
*AI-powered local search engine for the real world*

## Overview

LishFind is a modern, AI-powered local search engine that understands natural language queries and provides intelligent business recommendations. Instead of searching by keywords, users can describe what they actually want: "a quiet café for working" or "a romantic restaurant under ₹1500".

## 🏗️ Architecture

### Frontend (Vercel)
- **Technology**: Vanilla HTML/CSS/JavaScript
- **Features**: Beautiful responsive design, interactive search demo, real-time API integration
- **Deployment**: Static hosting on Vercel
- **URL**: `https://lishfind-frontend.vercel.app`

### Backend (Render) 
- **Technology**: FastAPI (Python)
- **Features**: AI intent extraction, business search, user management, RESTful API
- **Database**: PostgreSQL with PostGIS (via Supabase)
- **Deployment**: Python app hosting on Render
- **URL**: `https://lishfind-backend.onrender.com`

### Database (Supabase)
- **Technology**: PostgreSQL 15 with PostGIS extension
- **Features**: Spatial queries, business data, user analytics
- **Hosting**: Supabase cloud database

## 🚀 Quick Start

### For Users
Visit the live application: **[lishfind-frontend.vercel.app](https://lishfind-frontend.vercel.app)**

### For Developers

1. **Clone the repository**:
   ```bash
   git clone https://github.com/wearelish/Lish-finds.git
   cd Lish-finds
   ```

2. **Run locally**:
   ```bash
   # Start backend (Terminal 1)
   cd backend && python3 main.py
   
   # Start frontend (Terminal 2)  
   cd frontend && python3 server.py
   ```

3. **Access locally**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8001
   - API Docs: http://localhost:8001/docs

### For Deployment
Deploy to free hosting services in ~30 minutes:

```bash
python3 deploy_quick_start.py
```

Follow the generated deployment checklist for step-by-step instructions.

## 📁 Project Structure

```
Lish-finds/
├── frontend/                 # Frontend application
│   ├── index.html           # Main application file
│   └── server.py            # Local development server
├── backend/                 # Backend API
│   ├── main.py             # FastAPI application
│   ├── api/                # API endpoints
│   ├── services/           # Business logic
│   ├── models/             # Database models
│   └── ai/                 # AI services
├── deployment/             # Deployment guides and configs
│   ├── DEPLOYMENT_GUIDE.md # Complete deployment guide
│   ├── SUPABASE_SETUP.md   # Database setup
│   ├── RENDER_SETUP.md     # Backend hosting
│   └── VERCEL_SETUP.md     # Frontend hosting
├── index.html              # Production frontend (root level)
├── vercel.json            # Vercel configuration
└── package.json           # Project metadata
```

## 🎯 Key Features

### For Users
- **Natural Language Search**: "Find a quiet place for a date under ₹1000"  
- **AI-Powered Results**: Intent extraction and intelligent ranking
- **Location Aware**: Automatic location detection and proximity search
- **Rich Business Info**: Photos, reviews, contact details, and AI summaries
- **Mobile Friendly**: Responsive design for all devices

### For Developers  
- **Modern Stack**: FastAPI + PostgreSQL + Vanilla JS
- **Production Ready**: Docker, CI/CD, monitoring, and logging
- **Extensible**: Plugin architecture for AI providers and data sources
- **Free Deployment**: Complete setup for $0/month hosting
- **Comprehensive Docs**: API documentation and deployment guides

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 + PostGIS
- **ORM**: SQLAlchemy with async support
- **Authentication**: JWT tokens with bcrypt hashing
- **AI**: OpenAI/Gemini integration (disabled for free tier)
- **Caching**: Redis (optional)
- **Monitoring**: Structured logging and health checks

### Frontend
- **Technology**: Vanilla HTML5/CSS3/JavaScript
- **Styling**: Modern CSS with custom properties
- **Architecture**: Component-based with clean separation
- **Performance**: Optimized for fast loading and smooth animations
- **Accessibility**: WCAG 2.1 compliant design

### Infrastructure
- **Frontend Hosting**: Vercel (Static)
- **Backend Hosting**: Render (Container)
- **Database**: Supabase (Managed PostgreSQL)
- **CDN**: Automatic via Vercel
- **SSL**: Automatic HTTPS on all services

## 🔧 Development

### Prerequisites
- Python 3.11+
- Node.js 14+ (optional, for package.json)
- Git

### Environment Setup
1. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   ```bash
   cp backend/.env.example backend/.env
   # Edit .env with your database URL and secrets
   ```

3. **Database** (if running locally):
   ```bash
   # Install PostgreSQL with PostGIS
   # Or use Docker: docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgis/postgis
   ```

### Available Scripts
- `python3 backend/main.py` - Start backend server
- `python3 frontend/server.py` - Start frontend server  
- `python3 deploy_quick_start.py` - Interactive deployment setup

## 🧪 Testing

### Manual Testing
- Backend health: `curl http://localhost:8001/health`
- AI service: `curl -X POST http://localhost:8001/api/v1/ai/test -H "Content-Type: application/json" -d '{"prompt":"test"}'`
- Frontend: Open http://localhost:3000 and test search functionality

### Production Testing  
- All services include `/health` endpoints for monitoring
- Comprehensive error handling and logging
- Graceful degradation when services are unavailable

## 📊 Free Tier Limits

| Service | Limit | Impact |
|---------|-------|---------|
| **Vercel** | 100GB bandwidth/month | ~1M page views |
| **Render** | Sleeps after 15min idle | 15s cold start |
| **Supabase** | 500MB storage | ~50K businesses |

**Total Cost**: $0/month for moderate usage

## 🚀 Deployment

### Option 1: Quick Deploy (Recommended)
```bash
python3 deploy_quick_start.py
```

### Option 2: Manual Deploy
Follow the comprehensive guide in `deployment/DEPLOYMENT_GUIDE.md`

### Option 3: Docker Deploy
```bash
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check `/deployment/` folder for detailed guides
- **Issues**: Open GitHub issues for bugs and feature requests  
- **Community**: Join discussions in GitHub Discussions
- **Email**: Contact the team for enterprise inquiries

## 🌟 Star History

If LishFind helps you, please consider giving it a ⭐ star on GitHub!

---

**Made with ❤️ by the LishFind team**  
*Building the future of local search, one query at a time.*