# LishFind Backend Makefile
# Development and deployment commands

.PHONY: help install install-dev clean test lint format run dev migrate reset-db

# Default target
help:
	@echo "LishFind Backend Development Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  clean         Clean cache and temporary files"
	@echo ""
	@echo "Development:"
	@echo "  run           Start the server in production mode"
	@echo "  dev           Start the server in development mode (with reload)"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black and isort"
	@echo ""
	@echo "Database:"
	@echo "  setup-db      Set up database with tables and sample data"
	@echo "  migrate       Run database migrations"
	@echo "  reset-db      Reset database (WARNING: destroys data)"
	@echo "  docker-db     Start PostgreSQL and Redis with Docker"
	@echo "  docker-db-stop Stop database containers"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-dev    Start development environment with Docker Compose"
	@echo ""

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

# Cleaning
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage

# Development server
run:
	uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# Testing
test:
	pytest -v --cov=. --cov-report=term-missing --cov-report=html

test-fast:
	pytest -v -x --no-cov

# Code quality
lint:
	flake8 .
	mypy .
	black --check .
	isort --check-only .

format:
	black .
	isort .

# Database management
migrate:
	alembic upgrade head

create-migration:
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

setup-db:
	python setup_database.py

reset-db:
	@echo "WARNING: This will destroy all data in the database!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		python setup_database.py; \
	else \
		echo "Cancelled."; \
	fi

# Docker database services
docker-db:
	docker-compose -f docker-compose.dev.yml up -d postgres redis

docker-db-stop:
	docker-compose -f docker-compose.dev.yml down

docker-db-logs:
	docker-compose -f docker-compose.dev.yml logs -f postgres redis

# Docker commands
docker-build:
	docker build -t lishfind-backend .

docker-dev:
	docker-compose -f docker-compose.dev.yml up --build

docker-prod:
	docker-compose up --build -d

docker-logs:
	docker-compose logs -f

docker-stop:
	docker-compose down

# Pre-commit hooks
pre-commit:
	pre-commit run --all-files