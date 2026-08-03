#!/bin/bash

# LishFind Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environments: development, staging, production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT="${1:-development}"

echo -e "${BLUE}🚀 LishFind Deployment Script${NC}"
echo -e "${BLUE}Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo ""

# Validate environment
case $ENVIRONMENT in
  development|staging|production)
    echo -e "${GREEN}✅ Valid environment: $ENVIRONMENT${NC}"
    ;;
  *)
    echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
    echo "Valid environments: development, staging, production"
    exit 1
    ;;
esac

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"
echo ""

# Load environment-specific configuration
case $ENVIRONMENT in
  development)
    COMPOSE_FILE="docker-compose.yml"
    ENV_FILE="backend/.env"
    ;;
  staging)
    COMPOSE_FILE="docker-compose.staging.yml"
    ENV_FILE="backend/.env.staging"
    ;;
  production)
    COMPOSE_FILE="docker-compose.production.yml"
    ENV_FILE="backend/.env.production"
    ;;
esac

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}❌ Environment file not found: $ENV_FILE${NC}"
    exit 1
fi

# Production-specific checks
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo -e "${YELLOW}⚠️  Production deployment detected${NC}"
    
    # Check for sensitive default values
    if grep -q "CHANGE_THIS" "$ENV_FILE"; then
        echo -e "${RED}❌ Production environment file contains default values${NC}"
        echo "Please update all CHANGE_THIS placeholders in $ENV_FILE"
        exit 1
    fi
    
    if grep -q "dev-secret-key" "$ENV_FILE"; then
        echo -e "${RED}❌ Production environment file contains development secrets${NC}"
        echo "Please update SECRET_KEY in $ENV_FILE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Production environment file validation passed${NC}"
fi

# Stop existing containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true

# Pull latest images (for production)
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo -e "${BLUE}📥 Pulling latest images...${NC}"
    docker-compose -f "$COMPOSE_FILE" pull
fi

# Build and start services
echo -e "${BLUE}🏗️  Building and starting services...${NC}"
docker-compose -f "$COMPOSE_FILE" up --build -d

# Wait for services to be healthy
echo -e "${BLUE}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
echo -e "${BLUE}🏥 Checking service health...${NC}"

# Function to check service health
check_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T "$service" wget --quiet --tries=1 --spider http://localhost:8000/health 2>/dev/null || \
           docker-compose -f "$COMPOSE_FILE" exec -T "$service" wget --quiet --tries=1 --spider http://localhost/health 2>/dev/null; then
            echo -e "${GREEN}✅ $service is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Waiting for $service... (attempt $attempt/$max_attempts)${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $service failed to become healthy${NC}"
    return 1
}

# Check backend health
if ! check_health backend; then
    echo -e "${RED}❌ Backend service failed health check${NC}"
    docker-compose -f "$COMPOSE_FILE" logs backend
    exit 1
fi

# Check frontend health
if ! check_health frontend; then
    echo -e "${RED}❌ Frontend service failed health check${NC}"
    docker-compose -f "$COMPOSE_FILE" logs frontend
    exit 1
fi

# Show service URLs
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📍 Service URLs:${NC}"

case $ENVIRONMENT in
  development)
    echo -e "  Frontend: ${GREEN}http://localhost:3000${NC}"
    echo -e "  Backend API: ${GREEN}http://localhost:8001${NC}"
    echo -e "  API Docs: ${GREEN}http://localhost:8001/docs${NC}"
    echo -e "  Redis: ${GREEN}localhost:6379${NC}"
    ;;
  staging)
    echo -e "  Frontend: ${GREEN}http://localhost:3000${NC}"
    echo -e "  Backend API: ${GREEN}http://localhost:8001${NC}"
    echo -e "  API Docs: ${GREEN}http://localhost:8001/docs${NC}"
    echo -e "  Database Admin: ${GREEN}http://localhost:8080${NC} (run with --profile admin)"
    echo -e "  PostgreSQL: ${GREEN}localhost:5432${NC}"
    echo -e "  Redis: ${GREEN}localhost:6379${NC}"
    ;;
  production)
    echo -e "  Frontend: ${GREEN}http://localhost${NC}"
    echo -e "  Backend API: ${GREEN}http://localhost/api${NC}"
    echo -e "  Health Check: ${GREEN}http://localhost/health${NC}"
    ;;
esac

echo ""
echo -e "${BLUE}📊 Useful commands:${NC}"
echo -e "  View logs: ${YELLOW}docker-compose -f $COMPOSE_FILE logs -f${NC}"
echo -e "  Stop services: ${YELLOW}docker-compose -f $COMPOSE_FILE down${NC}"
echo -e "  Restart services: ${YELLOW}docker-compose -f $COMPOSE_FILE restart${NC}"
echo -e "  View status: ${YELLOW}docker-compose -f $COMPOSE_FILE ps${NC}"

if [[ "$ENVIRONMENT" == "development" ]]; then
    echo ""
    echo -e "${YELLOW}💡 Development Tips:${NC}"
    echo -e "  - Code changes will auto-reload in the backend"
    echo -e "  - Frontend files are mounted for hot updates"
    echo -e "  - Database data persists in Docker volumes"
fi