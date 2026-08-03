# 🔍 LishFind - AI-Powered Local Business Search Engine

**LishFind** is a modern, AI-powered local search engine that lets users search by intent rather than keywords. Built with FastAPI backend, beautiful frontend, and comprehensive location-based services.

## 🎉 **Live Demo & Deployment**

- **🌐 Frontend**: Deploy to Vercel (Free)
- **🔧 Backend API**: Deploy to Render (Free)  
- **🗄️ Database**: Supabase PostgreSQL (Free)
- **💰 Total Cost**: $0.00/month

## ✨ **Key Features**

### **🧠 AI-Powered Search**
- Natural language query processing
- Intent extraction from user queries
- Smart business matching and ranking
- Mock AI responses (upgradeable to real AI)

### **📍 Advanced Location Services**
- Precise GPS and IP geolocation
- Multi-modal travel time calculation
- Area mapping with metro stations and transport hubs
- Real-time accessibility scoring
- Dynamic pricing based on location factors

### **🎯 Business Intelligence**
- **₹70+ movie ticket minimum** enforced everywhere
- Multi-dimensional verification scoring (location, pricing, data quality)
- Real-time availability and booking management
- Comprehensive business constraint validation
- Dynamic pricing with demand, weather, and event factors

### **🛡️ Data Quality Assurance**
- Location verification with accuracy scoring
- Business data quality assessment
- Comprehensive field-level validation
- Critical issue detection and reporting
- Temporal accuracy validation

### **🎨 Beautiful Interface**
- Modern responsive design
- Interactive search demo
- Real-time API integration
- Mobile-optimized experience
- Live components and animations

### **🔐 Production Ready**
- JWT-based authentication
- Role-based access control
- Rate limiting and security middleware
- Comprehensive API documentation
- Health monitoring and logging

## 🚀 **Quick Start**

### **Local Development**

```bash
# Clone repository
git clone https://github.com/wearelish/Lish-finds.git
cd Lish-finds

# Start full stack (recommended)
python3 start_lishfind.py
```

**URLs:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### **Individual Services**

```bash
# Backend only
cd backend && python3 start_free.py

# Frontend only  
cd frontend && python3 server.py
```

## 🌐 **Free Cloud Deployment**

Deploy your LishFind application completely FREE:

### **Step 1: Check Readiness**
```bash
python3 check_deployment_ready.py
```

### **Step 2: Automated Setup**
```bash
python3 deploy_to_cloud.py
```

### **Step 3: Follow Guide**
- 📖 Read `deploy_guide.md` for detailed instructions
- 🗄️ Setup Supabase (PostgreSQL database)
- 🔧 Deploy to Render (backend API)
- 🌐 Deploy to Vercel (frontend)

**Result**: Live application with global CDN, auto-scaling API, and managed database.

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                    LishFind Full Stack                         │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Frontend (Vercel)                                          │
│  • Beautiful HTML/CSS/JS interface                             │
│  • Interactive search demo                                      │
│  • Real-time API integration                                   │
├─────────────────────────────────────────────────────────────────┤
│  🔧 Backend API (Render)                                       │
│  • FastAPI with async PostgreSQL                               │
│  • Location Enhancement System                                  │
│  • AI-powered search with intent extraction                    │
│  • Real-time pricing and availability                          │
│  • Comprehensive verification scoring                          │
├─────────────────────────────────────────────────────────────────┤
│  🗄️ Database (Supabase)                                       │
│  • PostgreSQL with extensions                                  │
│  • Automatic backups and scaling                               │
│  • Real-time subscriptions                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 **Project Structure**

```
lish-finds/
├── 📁 frontend/                 # Vercel deployment
│   ├── 🌐 index.html           # Beautiful main interface
│   ├── 🐍 server.py            # Development server
│   └── 📄 package.json         # Frontend configuration
│
├── 📁 backend/                  # Render deployment  
│   ├── 🐍 main.py              # FastAPI application
│   ├── 📁 api/                 # API routes and middleware
│   ├── 📁 models/              # Database models
│   ├── 📁 services/            # Business logic & location enhancement
│   │   ├── location_service.py            # GPS/IP geolocation
│   │   ├── location_verification_service.py  # Multi-dimensional verification
│   │   ├── data_accuracy_service.py       # Quality assessment
│   │   ├── business_rules_engine.py       # ₹70+ constraint enforcement
│   │   ├── dynamic_pricing_service.py     # Real-time pricing
│   │   ├── availability_service.py        # Booking management
│   │   ├── area_mapping_service.py        # Transport & accessibility
│   │   └── enhanced_search_service.py     # Location-aware search
│   ├── 📁 database/            # Database setup and migrations
│   └── 📄 requirements.txt     # Python dependencies
│
├── 📁 deployment/              # Cloud deployment configs
│   ├── 📄 vercel.json         # Vercel configuration
│   ├── 📄 render.yaml         # Render service config
│   ├── 📄 Dockerfile          # Container configuration
│   └── 📄 deploy_guide.md     # Step-by-step deployment
│
├── 🚀 Quick Start Scripts
│   ├── start_lishfind.py      # Full stack startup
│   ├── deploy_to_cloud.py     # Automated deployment
│   └── check_deployment_ready.py  # Readiness verification
│
└── 📚 Documentation
    ├── README.md              # This file
    ├── deploy_guide.md        # Deployment instructions
    └── FRONTEND_BACKEND_CONNECTION.md  # Connection troubleshooting
```

## 🎯 **Core Features Deep Dive**

### **Location Enhancement System (7 Components)**

1. **📍 Precise Location Detection**
   - GPS coordinate validation with precision scoring
   - IP-based geolocation with city/area detection
   - Address geocoding with OpenStreetMap integration
   - Distance calculation with multiple transport modes

2. **🏢 Business Data Validation** 
   - **₹70+ movie ticket constraint** enforced at all levels
   - Location-specific pricing tiers and regulations
   - State-wise business rules (dry states, operating hours)
   - Cultural and seasonal constraints

3. **🔍 Multi-Dimensional Verification**
   - Location accuracy scoring (GPS precision, address matching)
   - Business data quality (completeness, consistency, validity) 
   - Pricing compliance with heavy penalties for violations
   - Temporal accuracy (operating hours, seasonal availability)

4. **🗺️ Area Intelligence**
   - Metro station and transport hub mapping
   - Accessibility scoring and wheelchair-friendly detection
   - Catchment area analysis with demographic insights
   - Traffic pattern integration for travel time estimation

5. **💰 Dynamic Pricing Engine**
   - Real-time pricing with demand, weather, and event factors
   - Location-based pricing multipliers
   - Peak hour detection and surge pricing
   - **Strict ₹70 minimum enforcement** for movie tickets

6. **⏰ Real-time Availability**
   - Time-slot booking management
   - Occupancy tracking and capacity management
   - Live availability updates
   - Queue management for popular venues

7. **📊 Comprehensive Scoring**
   - Overall accuracy score (0-100) with weighted components
   - Confidence levels (high/medium/low)
   - Critical issue detection and recommendations
   - Batch verification for large datasets

## 🔧 **API Endpoints**

### **Authentication**
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login  
- `GET /api/v1/auth/me` - Current user profile

### **Enhanced Search**
- `POST /api/v1/search/businesses` - AI-powered business search
- `GET /api/v1/search/suggestions` - Query autocomplete
- `GET /api/v1/search/facets` - Search filters and categories

### **Business Management**
- `GET /api/v1/business/my-business` - User's business
- `POST /api/v1/business/create` - Create business listing
- `PUT /api/v1/business/update` - Update business information

### **Location Services**
- `GET /api/v1/location/detect` - Auto-detect user location
- `POST /api/v1/location/geocode` - Address to coordinates
- `GET /api/v1/location/area-info` - Area details and transport

### **AI & Intelligence**
- `POST /api/v1/ai/test` - Test AI functionality (mock responses)
- `GET /api/v1/ai/status` - AI service status
- `POST /api/v1/recommendations/get` - Personalized recommendations

### **Verification & Quality**
- `GET /api/v1/verification/report` - Business verification report
- `POST /api/v1/quality/assess` - Data quality assessment
- `GET /api/v1/pricing/validate` - Pricing constraint validation

## 💰 **Cost Breakdown**

### **FREE Tier (Current)**
- ✅ Frontend hosting (Vercel)
- ✅ Backend API (Render - 750 hours/month)  
- ✅ PostgreSQL database (Supabase - 500MB)
- ✅ Mock AI responses (no API costs)
- ✅ OpenStreetMap geocoding (unlimited)
- ✅ SSL certificates and CDN
- **Total: $0.00/month**

### **Upgrade Options**
- 🤖 **Real AI**: $20-100/month (OpenAI/Gemini APIs)
- 📈 **Analytics**: $10-30/month (advanced tracking)
- 🚀 **Performance**: $25-50/month (dedicated resources)
- 🗄️ **Enterprise DB**: $15-50/month (larger PostgreSQL)

## 🧪 **Testing & Quality**

### **Run Tests**
```bash
# Connection test
python3 test_connection.py

# Location enhancement integration test
cd backend && python3 test_location_enhancement_integration.py

# API health check
curl http://localhost:8001/health
```

### **Quality Assurance**
- ✅ Multi-dimensional verification scoring
- ✅ Comprehensive data quality metrics  
- ✅ Real-time constraint validation
- ✅ Location accuracy assessment
- ✅ Critical issue detection
- ✅ Automated testing suite

## 🔒 **Security & Production**

### **Security Features**
- JWT authentication with refresh tokens
- Rate limiting (100 requests/minute)
- CORS protection with domain whitelist
- Input validation and sanitization
- SQL injection prevention
- Password hashing with bcrypt

### **Production Hardening**
- Environment-based configuration
- Secure session management  
- HTTPS enforcement
- Security headers middleware
- Database connection pooling
- Error logging and monitoring

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### **Development Setup**
```bash
# Backend setup
cd backend
pip install -r requirements.txt
python3 start_free.py

# Frontend setup  
cd frontend
python3 server.py
```

## 📞 **Support & Documentation**

- **📖 Deployment Guide**: `deploy_guide.md`
- **🔧 API Documentation**: http://localhost:8001/docs
- **💊 Health Monitoring**: http://localhost:8001/health
- **🚨 Troubleshooting**: `FRONTEND_BACKEND_CONNECTION.md`

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 **Acknowledgments**

- Built with FastAPI, SQLAlchemy, and modern web technologies
- Location services powered by OpenStreetMap/Nominatim
- UI inspired by modern design principles
- Deployed on free tier cloud services

---

<div align="center">

**Built with ❤️ by the LishFind Team**

[🌐 Live Demo](https://your-app.vercel.app) • [📚 Documentation](deploy_guide.md) • [🐛 Issues](https://github.com/wearelish/Lish-finds/issues)

**Ready to deploy? Run `python3 deploy_to_cloud.py` and go live in minutes!** 🚀

</div>