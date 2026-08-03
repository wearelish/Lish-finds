#!/bin/bash

# LishFind Cloud Deployment Script
# Automated deployment to various cloud platforms

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PLATFORMS=("railway" "render" "fly" "vercel" "netlify")

echo -e "${BLUE}☁️  LishFind Cloud Deployment Assistant${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to display platform options
show_platforms() {
    echo -e "${BLUE}Available deployment platforms:${NC}"
    echo -e "  ${GREEN}1)${NC} Railway (Backend + Database)"
    echo -e "  ${GREEN}2)${NC} Render.com (Full Stack)"
    echo -e "  ${GREEN}3)${NC} Fly.io (Backend)"
    echo -e "  ${GREEN}4)${NC} Vercel (Frontend)"
    echo -e "  ${GREEN}5)${NC} Netlify (Frontend)"
    echo -e "  ${GREEN}6)${NC} Setup All Configs"
    echo ""
}

# Function to setup Railway
setup_railway() {
    echo -e "${BLUE}🚂 Setting up Railway deployment...${NC}"
    
    if ! command_exists railway; then
        echo -e "${YELLOW}⚠️  Railway CLI not found. Install it first:${NC}"
        echo "  npm install -g @railway/cli"
        echo "  Or visit: https://docs.railway.app/develop/cli"
        return 1
    fi
    
    echo -e "${GREEN}✅ Railway CLI found${NC}"
    
    # Login check
    if ! railway whoami >/dev/null 2>&1; then
        echo -e "${BLUE}🔐 Please login to Railway:${NC}"
        railway login
    fi
    
    # Initialize project
    echo -e "${BLUE}📁 Initializing Railway project...${NC}"
    railway init
    
    # Add PostgreSQL service
    echo -e "${BLUE}🗄️  Adding PostgreSQL service...${NC}"
    railway add postgresql
    
    # Set environment variables
    echo -e "${BLUE}⚙️  Setting environment variables...${NC}"
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -base64 32 | tr -d '=' | head -c 32)
    
    railway variables set ENVIRONMENT=production
    railway variables set DEBUG=false
    railway variables set SECRET_KEY="$SECRET_KEY"
    railway variables set AI_PROVIDER=disabled
    railway variables set MAPS_PROVIDER=nominatim
    railway variables set LOG_LEVEL=INFO
    
    echo -e "${YELLOW}⚠️  Remember to set these variables in Railway dashboard:${NC}"
    echo "  - CORS_ORIGINS (your frontend URL)"
    echo "  - ALLOWED_HOSTS (your backend domain)"
    
    # Deploy
    echo -e "${BLUE}🚀 Deploying to Railway...${NC}"
    railway up
    
    echo -e "${GREEN}✅ Railway deployment initiated!${NC}"
    echo -e "${BLUE}🌐 Check your deployment at: https://railway.app/dashboard${NC}"
}

# Function to setup Render
setup_render() {
    echo -e "${BLUE}🎨 Setting up Render.com deployment...${NC}"
    
    echo -e "${GREEN}📋 Steps to deploy on Render.com:${NC}"
    echo ""
    echo -e "${YELLOW}1.${NC} Go to https://render.com and sign up/login"
    echo -e "${YELLOW}2.${NC} Click 'New' → 'Blueprint'"
    echo -e "${YELLOW}3.${NC} Connect your GitHub repository"
    echo -e "${YELLOW}4.${NC} Render will automatically detect render.yaml"
    echo -e "${YELLOW}5.${NC} Review and deploy the blueprint"
    echo ""
    echo -e "${BLUE}🔧 The render.yaml file includes:${NC}"
    echo -e "  • Backend web service (Python/FastAPI)"
    echo -e "  • Frontend web service (Static/Nginx)"
    echo -e "  • PostgreSQL database"
    echo -e "  • Redis cache"
    echo ""
    echo -e "${GREEN}✅ All services will be deployed together automatically!${NC}"
}

# Function to setup Fly.io
setup_fly() {
    echo -e "${BLUE}🪰 Setting up Fly.io deployment...${NC}"
    
    if ! command_exists flyctl; then
        echo -e "${YELLOW}⚠️  Fly CLI not found. Install it first:${NC}"
        echo "  curl -L https://fly.io/install.sh | sh"
        echo "  Or visit: https://fly.io/docs/hands-on/install-flyctl/"
        return 1
    fi
    
    echo -e "${GREEN}✅ Fly CLI found${NC}"
    
    # Login check
    if ! flyctl auth whoami >/dev/null 2>&1; then
        echo -e "${BLUE}🔐 Please login to Fly.io:${NC}"
        flyctl auth login
    fi
    
    # Launch app
    echo -e "${BLUE}🚀 Launching Fly.io app...${NC}"
    cd backend
    flyctl launch --dockerfile Dockerfile --no-deploy
    
    # Set secrets
    echo -e "${BLUE}🔐 Setting secrets...${NC}"
    SECRET_KEY=$(openssl rand -base64 32 | tr -d '=' | head -c 32)
    
    flyctl secrets set SECRET_KEY="$SECRET_KEY"
    flyctl secrets set ENVIRONMENT=production
    flyctl secrets set DEBUG=false
    
    echo -e "${YELLOW}⚠️  You need to set these secrets manually:${NC}"
    echo "  flyctl secrets set DATABASE_URL='postgresql://...'"
    echo "  flyctl secrets set CORS_ORIGINS='https://yourfrontend.com'"
    
    # Deploy
    echo -e "${BLUE}🚀 Deploying to Fly.io...${NC}"
    flyctl deploy
    
    cd ..
    echo -e "${GREEN}✅ Fly.io deployment complete!${NC}"
}

# Function to setup Vercel
setup_vercel() {
    echo -e "${BLUE}▲ Setting up Vercel deployment...${NC}"
    
    echo -e "${GREEN}📋 Steps to deploy frontend on Vercel:${NC}"
    echo ""
    echo -e "${YELLOW}1.${NC} Go to https://vercel.com and sign up/login"
    echo -e "${YELLOW}2.${NC} Click 'New Project'"
    echo -e "${YELLOW}3.${NC} Import your GitHub repository"
    echo -e "${YELLOW}4.${NC} Configure build settings:"
    echo "     • Framework Preset: Other"
    echo "     • Build Command: echo 'Static site'"
    echo "     • Output Directory: frontend"
    echo -e "${YELLOW}5.${NC} Update vercel.json with your backend URL"
    echo -e "${YELLOW}6.${NC} Deploy!"
    echo ""
    echo -e "${BLUE}⚙️  Remember to update vercel.json:${NC}"
    echo "  Replace 'https://your-backend-url.railway.app' with actual backend URL"
    echo ""
    echo -e "${GREEN}✅ Frontend will be deployed automatically on git push!${NC}"
}

# Function to setup Netlify
setup_netlify() {
    echo -e "${BLUE}🌐 Setting up Netlify deployment...${NC}"
    
    echo -e "${GREEN}📋 Steps to deploy frontend on Netlify:${NC}"
    echo ""
    echo -e "${YELLOW}1.${NC} Go to https://netlify.com and sign up/login"
    echo -e "${YELLOW}2.${NC} Click 'New site from Git'"
    echo -e "${YELLOW}3.${NC} Connect your GitHub repository"
    echo -e "${YELLOW}4.${NC} Configure build settings:"
    echo "     • Build command: echo 'Static site'"
    echo "     • Publish directory: frontend"
    echo -e "${YELLOW}5.${NC} Update netlify.toml with your backend URL"
    echo -e "${YELLOW}6.${NC} Deploy!"
    echo ""
    echo -e "${BLUE}⚙️  Remember to update netlify.toml:${NC}"
    echo "  Replace 'https://your-backend-url.railway.app' with actual backend URL"
    echo ""
    echo -e "${GREEN}✅ Frontend will be deployed automatically on git push!${NC}"
}

# Function to setup all configs
setup_all() {
    echo -e "${BLUE}📦 Setting up all deployment configurations...${NC}"
    echo ""
    
    echo -e "${GREEN}✅ Configuration files created:${NC}"
    echo -e "  • ${BLUE}railway.toml${NC} - Railway deployment config"
    echo -e "  • ${BLUE}render.yaml${NC} - Render.com blueprint"
    echo -e "  • ${BLUE}fly.toml${NC} - Fly.io configuration"
    echo -e "  • ${BLUE}vercel.json${NC} - Vercel frontend config"
    echo -e "  • ${BLUE}netlify.toml${NC} - Netlify frontend config"
    echo -e "  • ${BLUE}heroku.yml${NC} - Heroku deployment config"
    echo ""
    
    echo -e "${BLUE}📖 Next steps:${NC}"
    echo -e "1. Choose your preferred platform(s)"
    echo -e "2. Follow the deployment guide: ${YELLOW}docs/DEPLOYMENT.md${NC}"
    echo -e "3. Update platform configs with your URLs"
    echo -e "4. Set environment variables"
    echo -e "5. Deploy!"
    echo ""
    
    echo -e "${GREEN}🚀 Your app is ready for deployment to any platform!${NC}"
}

# Main menu
main() {
    if [[ $# -eq 0 ]]; then
        show_platforms
        read -p "Choose a platform (1-6): " choice
    else
        choice=$1
    fi
    
    case $choice in
        1|railway)
            setup_railway
            ;;
        2|render)
            setup_render
            ;;
        3|fly)
            setup_fly
            ;;
        4|vercel)
            setup_vercel
            ;;
        5|netlify)
            setup_netlify
            ;;
        6|all)
            setup_all
            ;;
        *)
            echo -e "${RED}❌ Invalid choice: $choice${NC}"
            echo "Valid options: 1-6, railway, render, fly, vercel, netlify, all"
            exit 1
            ;;
    esac
}

# Check if git repository exists
if [[ ! -d .git ]]; then
    echo -e "${RED}❌ This is not a git repository${NC}"
    echo "Please initialize git first:"
    echo "  git init"
    echo "  git add ."
    echo "  git commit -m 'Initial commit'"
    exit 1
fi

# Run main function
main "$@"