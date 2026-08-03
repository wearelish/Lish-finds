# LishFind Project Makefile
# Convenient commands for development, testing, and deployment

.PHONY: help install test lint format clean docker deploy

# Default target
help:
	@echo "LishFind Project Commands"
	@echo "========================="
	@echo ""
	@echo "Development:"
	@echo "  install        Install all dependencies"
	@echo "  dev            Start development environment"
	@echo "  test           Run all tests"
	@echo "  lint           Run linting checks"
	@echo "  format         Format code"
	@echo "  clean          Clean up temporary files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build Docker images"
	@echo "  docker-dev     Start development with Docker"
	@echo "  docker-prod    Start production stack"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-dev     Deploy to development environment"
	@echo "  deploy-staging Deploy to staging environment"
	@echo "  deploy-prod    Deploy to production environment"
	@echo "  deploy-prepare Validate deployment readiness"
	@echo "  deploy-railway Deploy to Railway"
	@echo "  deploy-render  Deploy to Render"
	@echo "  deploy-fly     Deploy to Fly.io"
	@echo ""
	@echo "Environment Management:"
	@echo "  env-setup          Install environment management dependencies"
	@echo "  env-list           List available environments"
	@echo "  env-switch-dev     Switch to development environment"
	@echo "  env-switch-staging Switch to staging environment"
	@echo "  env-switch-prod    Switch to production environment"
	@echo "  env-validate       Validate current environment"
	@echo "  env-validate-prod  Run comprehensive production validation"
	@echo ""
	@echo "Secrets Management:"
	@echo "  secrets-list       List secrets in current environment"
	@echo "  secrets-setup-prod Setup production secrets"
	@echo "  secrets-health     Check secrets health"
	@echo "  secrets-health-prod Check production secrets health"
	@echo ""
	@echo "Database:"
	@echo "  db-migrate     Run database migrations"
	@echo "  db-backup      Create database backup"
	@echo "  db-restore     Restore database from backup"
	@echo ""
	@echo "Monitoring:"
	@echo "  monitoring     Start monitoring stack"
	@echo "  logs           View application logs"

# Installation
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Setting up pre-commit hooks..."
	cd backend && pre-commit install

# Development
dev:
	@echo "Starting development environment..."
	docker-compose up --build

dev-backend:
	@echo "Starting backend development server..."
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001

dev-frontend:
	@echo "Starting frontend development server..."
	cd frontend && python -m http.server 3000

# Testing
test:
	@echo "Running backend tests..."
	cd backend && pytest -v --cov=. --cov-report=term-missing
	@echo "Running frontend tests..."
	cd frontend && npm test

test-backend:
	cd backend && pytest -v --cov=. --cov-report=html --cov-report=term-missing

test-frontend:
	cd frontend && npm test

test-integration:
	@echo "Running integration tests..."
	docker-compose -f docker-compose.yml up -d
	sleep 30
	curl -f http://localhost:8001/health
	curl -f http://localhost:3000/health
	docker-compose down

test-performance:
	@echo "Running performance tests..."
	k6 run tests/performance/load-test.js

# Code quality
lint:
	@echo "Running backend linting..."
	cd backend && black --check . && isort --check-only . && flake8 . && mypy .
	@echo "Running frontend linting..."
	cd frontend && npm run lint

format:
	@echo "Formatting backend code..."
	cd backend && black . && isort .
	@echo "Formatting frontend code..."
	cd frontend && prettier --write .

security:
	@echo "Running security checks..."
	cd backend && safety check && bandit -r .

# Docker
docker-build:
	@echo "Building Docker images..."
	docker build -t lishfind-backend:latest ./backend
	docker build -t lishfind-frontend:latest ./frontend

docker-dev:
	@echo "Starting development environment with Docker..."
	docker-compose -f docker-compose.yml up --build

docker-staging:
	@echo "Starting staging environment..."
	docker-compose -f docker-compose.staging.yml up --build -d

docker-prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.production.yml up --build -d

# Database
db-migrate:
	@echo "Running database migrations..."
	cd backend && python -m alembic upgrade head

db-migrate-create:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " msg; \
	cd backend && python -m alembic revision --autogenerate -m "$$msg"

db-backup:
	@echo "Creating database backup..."
	cd backend && python -m cli.db_manager backup --compress

db-restore:
	@echo "Restoring database from backup..."
	@read -p "Enter backup file path: " backup_path; \
	cd backend && python -m cli.db_manager restore "$$backup_path"

db-reset:
	@echo "Resetting database (development only)..."
	cd backend && python -m alembic downgrade base && python -m alembic upgrade head

# Deployment
deploy-dev:
	@echo "Deploying to development environment..."
	./scripts/deploy.sh development

deploy-staging:
	@echo "Deploying to staging environment..."
	./scripts/deploy.sh staging

deploy-prod:
	@echo "Deploying to production environment..."
	./scripts/deploy.sh production

deploy-cloud:
	@echo "Deploying to cloud platforms..."
	./scripts/deploy-cloud.sh all

# Monitoring
monitoring:
	@echo "Starting monitoring stack..."
	docker-compose -f monitoring/docker-compose.monitoring.yml up -d

logs:
	@echo "Viewing application logs..."
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

# Maintenance
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete
	rm -rf backend/htmlcov/
	rm -rf backend/.mypy_cache/
	rm -rf frontend/node_modules/.cache/

clean-docker:
	@echo "Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f

# Release
release-patch:
	@echo "Creating patch release..."
	cd backend && bump2version patch

release-minor:
	@echo "Creating minor release..."
	cd backend && bump2version minor

release-major:
	@echo "Creating major release..."
	cd backend && bump2version major

# Environment setup
setup-dev:
	@echo "Setting up development environment..."
	cp backend/.env.example backend/.env
	make install
	make db-migrate
	@echo "Development environment ready!"

setup-production:
	@echo "Setting up production environment..."
	@echo "Please configure production environment variables manually."
	@echo "See deployment/README.md for details."

# Environment Management
env-setup:
	@echo "Installing environment management dependencies..."
	cd backend && pip install -r requirements-env.txt

env-list:
	@echo "Available environments:"
	python backend/cli/env_manager.py env list

env-switch-dev:
	@echo "Switching to development environment..."
	python backend/cli/env_manager.py env switch development

env-switch-staging:
	@echo "Switching to staging environment..."
	python backend/cli/env_manager.py env switch staging

env-switch-prod:
	@echo "Switching to production environment..."
	python backend/cli/env_manager.py env switch production

env-validate:
	@echo "Validating current environment configuration..."
	python backend/cli/env_manager.py config validate

env-validate-prod:
	@echo "Running comprehensive production validation..."
	./scripts/validate-production.sh

# Secrets Management
secrets-list:
	@echo "Listing secrets in current environment..."
	python backend/cli/env_manager.py secrets list

secrets-setup-prod:
	@echo "Setting up production secrets..."
	python backend/cli/env_manager.py -e production secrets setup

secrets-health:
	@echo "Checking secrets health in current environment..."
	python backend/cli/env_manager.py secrets health

secrets-health-prod:
	@echo "Checking production secrets health..."
	python backend/cli/env_manager.py -e production secrets health

# Deployment Preparation
deploy-prepare:
	@echo "Validating deployment readiness..."
	python backend/cli/env_manager.py deploy prepare -e production --validate-only

deploy-railway:
	@echo "Deploying to Railway..."
	./scripts/deploy-cloud.sh railway

deploy-render:
	@echo "Deploying to Render..."
	./scripts/deploy-cloud.sh render

deploy-fly:
	@echo "Deploying to Fly.io..."
	./scripts/deploy-cloud.sh fly

# Health checks
health:
	@echo "Checking application health..."
	@if curl -f http://localhost:8001/health > /dev/null 2>&1; then \
		echo "✅ Backend is healthy"; \
	else \
		echo "❌ Backend is not responding"; \
	fi
	@if curl -f http://localhost:3000/health > /dev/null 2>&1; then \
		echo "✅ Frontend is healthy"; \
	else \
		echo "❌ Frontend is not responding"; \
	fi

# Documentation
docs:
	@echo "Generating documentation..."
	cd backend && sphinx-build -b html docs docs/_build

docs-serve:
	@echo "Serving documentation..."
	cd backend/docs/_build && python -m http.server 8080