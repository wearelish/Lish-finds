#!/bin/bash

# Post-Switch Hook Script
# Runs after switching environments

set -e

# Get environment variables
ENVIRONMENT=${TARGET_ENVIRONMENT:-development}
PROJECT_ROOT=${PROJECT_ROOT:-$(pwd)}

echo "🔄 Running post-switch hook for environment: $ENVIRONMENT"

# Change to project root
cd "$PROJECT_ROOT"

# Install/update dependencies if requirements changed
if [ -f "backend/requirements.txt" ]; then
    echo "📦 Checking Python dependencies..."
    
    # Check if we're in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        pip install -r backend/requirements.txt --quiet
        echo "✅ Python dependencies updated"
    else
        echo "⚠️  Not in virtual environment - skipping dependency installation"
    fi
fi

# Install/update frontend dependencies if needed
if [ -f "frontend/package.json" ]; then
    echo "📦 Checking frontend dependencies..."
    cd frontend
    
    if command -v npm >/dev/null 2>&1; then
        npm install --silent
        echo "✅ Frontend dependencies updated"
    else
        echo "⚠️  npm not found - skipping frontend dependency installation"
    fi
    
    cd "$PROJECT_ROOT"
fi

# Run database migrations if needed
if [ "$ENVIRONMENT" != "development" ]; then
    echo "🗃️  Running database migrations..."
    
    # Check if alembic is available
    if command -v alembic >/dev/null 2>&1; then
        cd backend
        alembic upgrade head
        echo "✅ Database migrations completed"
        cd "$PROJECT_ROOT"
    else
        echo "⚠️  Alembic not found - skipping migrations"
    fi
fi

# Clear cache directories
echo "🧹 Clearing cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
fi

echo "✅ Cache cleared"

# Update environment-specific configurations
case $ENVIRONMENT in
    "production")
        echo "🔒 Applying production configurations..."
        
        # Ensure secure file permissions
        if [ -f ".env" ]; then
            chmod 600 .env
        fi
        
        # Check for required production files
        if [ ! -f "backend/.env.production" ]; then
            echo "❌ Production environment file not found"
            exit 1
        fi
        
        echo "✅ Production configurations applied"
        ;;
        
    "staging")
        echo "🧪 Applying staging configurations..."
        
        # Check for required staging files
        if [ ! -f "backend/.env.staging" ]; then
            echo "❌ Staging environment file not found"
            exit 1
        fi
        
        echo "✅ Staging configurations applied"
        ;;
        
    "development")
        echo "🛠️  Applying development configurations..."
        
        # Create development database if it doesn't exist
        if [ ! -f "backend/lishfind_development.db" ]; then
            echo "📄 Creating development database..."
            cd backend
            python -c "
from database.connection import create_database
create_database()
print('Development database created')
" 2>/dev/null || echo "⚠️  Could not create development database"
            cd "$PROJECT_ROOT"
        fi
        
        echo "✅ Development configurations applied"
        ;;
esac

# Validate the environment setup
echo "🔍 Validating environment setup..."

# Check if main environment file exists and is readable
if [ -f ".env" ]; then
    if [ -r ".env" ]; then
        echo "✅ Environment file is readable"
    else
        echo "❌ Environment file is not readable"
        exit 1
    fi
else
    echo "❌ Environment file not found"
    exit 1
fi

# Validate required environment variables
REQUIRED_VARS="ENVIRONMENT DATABASE_URL SECRET_KEY"

for var in $REQUIRED_VARS; do
    if grep -q "^$var=" .env; then
        value=$(grep "^$var=" .env | cut -d'=' -f2-)
        if [ -n "$value" ] && [ "$value" != "your-${var,,}-here" ]; then
            echo "✅ $var is configured"
        else
            echo "❌ $var is not properly configured"
            exit 1
        fi
    else
        echo "❌ $var is not set"
        exit 1
    fi
done

# Check database connectivity (if not SQLite)
DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
if [[ $DATABASE_URL == *"postgresql"* ]] || [[ $DATABASE_URL == *"mysql"* ]]; then
    echo "🔗 Checking database connectivity..."
    
    # Use Python to test database connection
    cd backend
    python -c "
try:
    from database.connection import get_database_url, test_connection
    if test_connection():
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')
        exit(1)
except Exception as e:
    print(f'⚠️  Database connection test failed: {e}')
" 2>/dev/null || echo "⚠️  Could not test database connection"
    cd "$PROJECT_ROOT"
fi

# Show environment information
echo ""
echo "📋 Environment Information:"
echo "   Environment: $ENVIRONMENT"
echo "   Project Root: $PROJECT_ROOT"
echo "   Database: $(echo $DATABASE_URL | sed 's/:[^@]*@/:***@/')"  # Hide password
echo "   Python Path: $(which python 2>/dev/null || echo 'Not found')"
echo "   Node Path: $(which node 2>/dev/null || echo 'Not found')"

echo ""
echo "✅ Post-switch hook completed successfully"
echo "🚀 Environment '$ENVIRONMENT' is ready!"