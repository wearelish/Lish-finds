#!/bin/bash

# Production Validation Script
# Comprehensive validation for production deployment

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROJECT_ROOT"

echo "🔍 LishFind Production Validation"
echo "=================================="
echo "Project Root: $PROJECT_ROOT"
echo "Timestamp: $(date)"
echo ""

# Initialize counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
pass_check() {
    echo "✅ $1"
    ((PASSED++))
}

fail_check() {
    echo "❌ $1"
    ((FAILED++))
}

warn_check() {
    echo "⚠️  $1"
    ((WARNINGS++))
}

# 1. Environment Configuration Validation
echo "📋 1. Environment Configuration"
echo "------------------------------"

if [ -f ".env.production" ]; then
    pass_check "Production environment file exists"
    
    # Check required variables
    REQUIRED_VARS=(
        "ENVIRONMENT"
        "SECRET_KEY"
        "DATABASE_URL"
        "ALLOWED_HOSTS"
        "CORS_ORIGINS"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" .env.production; then
            value=$(grep "^$var=" .env.production | cut -d'=' -f2-)
            if [ -n "$value" ] && [[ "$value" != *"your-"* ]] && [[ "$value" != *"changeme"* ]]; then
                pass_check "$var is configured"
            else
                fail_check "$var has placeholder value"
            fi
        else
            fail_check "$var is missing"
        fi
    done
    
    # Check security settings
    DEBUG=$(grep "^DEBUG=" .env.production | cut -d'=' -f2- 2>/dev/null || echo "false")
    if [ "$DEBUG" = "false" ] || [ "$DEBUG" = "0" ]; then
        pass_check "DEBUG is disabled"
    else
        fail_check "DEBUG is enabled in production"
    fi
    
else
    fail_check "Production environment file (.env.production) not found"
fi

echo ""

# 2. Security Configuration Validation
echo "🔒 2. Security Configuration"
echo "---------------------------"

# Check secret key strength
if [ -f ".env.production" ] && grep -q "^SECRET_KEY=" .env.production; then
    SECRET_KEY=$(grep "^SECRET_KEY=" .env.production | cut -d'=' -f2-)
    if [ ${#SECRET_KEY} -ge 32 ]; then
        pass_check "Secret key meets minimum length (32+ chars)"
    else
        fail_check "Secret key is too short (${#SECRET_KEY} chars, need 32+)"
    fi
    
    # Check for common weak secrets
    if [[ "$SECRET_KEY" == *"your-secret"* ]] || [[ "$SECRET_KEY" == *"changeme"* ]]; then
        fail_check "Secret key appears to be default/weak"
    else
        pass_check "Secret key appears to be custom"
    fi
else
    fail_check "SECRET_KEY not found in production config"
fi

# Check HTTPS configuration
if grep -q "ENABLE_HTTPS=true" .env.production 2>/dev/null; then
    pass_check "HTTPS is enabled"
else
    warn_check "HTTPS configuration not found"
fi

# Check secure cookie settings
SECURE_SETTINGS=("SECURE_COOKIES" "CSRF_COOKIE_SECURE" "SESSION_COOKIE_SECURE")
for setting in "${SECURE_SETTINGS[@]}"; do
    if grep -q "^$setting=true" .env.production 2>/dev/null; then
        pass_check "$setting is enabled"
    else
        warn_check "$setting is not configured"
    fi
done

echo ""

# 3. Database Configuration
echo "🗃️  3. Database Configuration"
echo "----------------------------"

if [ -f ".env.production" ] && grep -q "^DATABASE_URL=" .env.production; then
    DATABASE_URL=$(grep "^DATABASE_URL=" .env.production | cut -d'=' -f2-)
    
    if [[ "$DATABASE_URL" == *"postgresql"* ]]; then
        pass_check "Using PostgreSQL database"
        
        # Check for SSL requirement
        if [[ "$DATABASE_URL" == *"sslmode=require"* ]]; then
            pass_check "SSL is required for database connection"
        else
            warn_check "SSL mode not specified for database connection"
        fi
        
    elif [[ "$DATABASE_URL" == *"mysql"* ]]; then
        pass_check "Using MySQL database"
    elif [[ "$DATABASE_URL" == *"sqlite"* ]]; then
        warn_check "Using SQLite database (consider PostgreSQL for production)"
    else
        warn_check "Unknown database type"
    fi
    
    # Check for password in URL
    if [[ "$DATABASE_URL" == *"password=password"* ]] || [[ "$DATABASE_URL" == *":password@"* ]]; then
        fail_check "Database appears to use weak/default password"
    else
        pass_check "Database password appears to be custom"
    fi
else
    fail_check "DATABASE_URL not configured"
fi

echo ""

# 4. Docker Configuration
echo "🐳 4. Docker Configuration"
echo "-------------------------"

if [ -f "backend/Dockerfile" ]; then
    pass_check "Backend Dockerfile exists"
    
    # Check for multi-stage build
    if grep -q "FROM.*as.*" backend/Dockerfile; then
        pass_check "Multi-stage Dockerfile detected"
    else
        warn_check "Single-stage Dockerfile (consider multi-stage for optimization)"
    fi
    
    # Check for security best practices
    if grep -q "USER.*[^r]oot" backend/Dockerfile; then
        pass_check "Non-root user configured in Dockerfile"
    else
        warn_check "No non-root user found in Dockerfile"
    fi
else
    fail_check "Backend Dockerfile not found"
fi

if [ -f "frontend/Dockerfile" ]; then
    pass_check "Frontend Dockerfile exists"
else
    fail_check "Frontend Dockerfile not found"
fi

if [ -f "docker-compose.production.yml" ]; then
    pass_check "Production Docker Compose file exists"
else
    fail_check "Production Docker Compose file not found"
fi

echo ""

# 5. Dependency Security
echo "🔐 5. Dependency Security"
echo "------------------------"

if [ -f "backend/requirements.txt" ]; then
    pass_check "Python requirements file exists"
    
    # Check for known vulnerable packages (basic check)
    if grep -E "(django<2|flask<1\.1|requests<2\.20)" backend/requirements.txt >/dev/null 2>&1; then
        fail_check "Potentially vulnerable Python packages detected"
    else
        pass_check "No known vulnerable Python packages detected"
    fi
else
    warn_check "Python requirements file not found"
fi

if [ -f "frontend/package.json" ]; then
    pass_check "Frontend package.json exists"
    
    # Check for package-lock.json
    if [ -f "frontend/package-lock.json" ]; then
        pass_check "Package-lock.json exists (dependency versions locked)"
    else
        warn_check "Package-lock.json not found (dependency versions not locked)"
    fi
else
    warn_check "Frontend package.json not found"
fi

echo ""

# 6. Monitoring & Logging
echo "📊 6. Monitoring & Logging"
echo "-------------------------"

# Check logging configuration
if grep -q "^LOG_LEVEL=" .env.production 2>/dev/null; then
    LOG_LEVEL=$(grep "^LOG_LEVEL=" .env.production | cut -d'=' -f2-)
    if [ "$LOG_LEVEL" = "INFO" ] || [ "$LOG_LEVEL" = "WARNING" ] || [ "$LOG_LEVEL" = "ERROR" ]; then
        pass_check "Log level is appropriate for production ($LOG_LEVEL)"
    else
        warn_check "Log level may be too verbose for production ($LOG_LEVEL)"
    fi
else
    warn_check "LOG_LEVEL not configured"
fi

# Check monitoring services
if grep -q "^SENTRY_DSN=" .env.production 2>/dev/null && [ -n "$(grep "^SENTRY_DSN=" .env.production | cut -d'=' -f2-)" ]; then
    pass_check "Sentry error monitoring configured"
else
    warn_check "Error monitoring (Sentry) not configured"
fi

# Check for monitoring endpoints
if [ -f "backend/api/v1/endpoints/monitoring.py" ]; then
    pass_check "Monitoring endpoints exist"
else
    warn_check "Monitoring endpoints not found"
fi

echo ""

# 7. Deployment Configuration
echo "🚀 7. Deployment Configuration"
echo "------------------------------"

DEPLOYMENT_CONFIGS=0

# Check various deployment platforms
if [ -f "railway.toml" ]; then
    pass_check "Railway deployment config exists"
    ((DEPLOYMENT_CONFIGS++))
fi

if [ -f "render.yaml" ]; then
    pass_check "Render deployment config exists"
    ((DEPLOYMENT_CONFIGS++))
fi

if [ -f "fly.toml" ]; then
    pass_check "Fly.io deployment config exists"
    ((DEPLOYMENT_CONFIGS++))
fi

if [ -f "vercel.json" ]; then
    pass_check "Vercel deployment config exists"
    ((DEPLOYMENT_CONFIGS++))
fi

if [ -f "heroku.yml" ]; then
    pass_check "Heroku deployment config exists"
    ((DEPLOYMENT_CONFIGS++))
fi

if [ $DEPLOYMENT_CONFIGS -gt 0 ]; then
    pass_check "$DEPLOYMENT_CONFIGS deployment platform(s) configured"
else
    warn_check "No deployment platform configurations found"
fi

# Check deployment scripts
if [ -f "scripts/deploy.sh" ]; then
    pass_check "Deployment script exists"
    
    if [ -x "scripts/deploy.sh" ]; then
        pass_check "Deployment script is executable"
    else
        warn_check "Deployment script is not executable"
    fi
else
    warn_check "Deployment script not found"
fi

echo ""

# 8. Backup & Recovery
echo "💾 8. Backup & Recovery"
echo "----------------------"

if [ -f "scripts/backup.sh" ]; then
    pass_check "Backup script exists"
    
    if [ -x "scripts/backup.sh" ]; then
        pass_check "Backup script is executable"
    else
        warn_check "Backup script is not executable"
    fi
else
    warn_check "Backup script not found"
fi

# Check backup configuration
if grep -q "BACKUP_" .env.production 2>/dev/null; then
    pass_check "Backup configuration found in environment"
else
    warn_check "No backup configuration found"
fi

echo ""

# 9. Performance Configuration
echo "⚡ 9. Performance Configuration"
echo "------------------------------"

# Check Redis configuration
if grep -q "^REDIS_URL=" .env.production 2>/dev/null; then
    pass_check "Redis caching configured"
else
    warn_check "Redis caching not configured"
fi

# Check performance files
if [ -d "backend/performance" ]; then
    pass_check "Performance optimization module exists"
else
    warn_check "Performance optimization module not found"
fi

# Check Nginx configuration
if [ -f "nginx/nginx.conf" ]; then
    pass_check "Nginx configuration exists"
else
    warn_check "Nginx configuration not found"
fi

echo ""

# 10. CI/CD Configuration
echo "🔄 10. CI/CD Configuration"
echo "-------------------------"

if [ -d ".github/workflows" ]; then
    WORKFLOW_COUNT=$(find .github/workflows -name "*.yml" -o -name "*.yaml" | wc -l)
    if [ $WORKFLOW_COUNT -gt 0 ]; then
        pass_check "GitHub Actions workflows configured ($WORKFLOW_COUNT files)"
    fi
else
    warn_check "GitHub Actions workflows not found"
fi

if [ -f ".gitlab-ci.yml" ]; then
    pass_check "GitLab CI configuration exists"
else
    warn_check "GitLab CI configuration not found"
fi

echo ""

# Summary
echo "📊 VALIDATION SUMMARY"
echo "===================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"  
echo "⚠️  Warnings: $WARNINGS"

TOTAL_CHECKS=$((PASSED + FAILED + WARNINGS))
SUCCESS_RATE=$((PASSED * 100 / TOTAL_CHECKS))

echo ""
echo "Success Rate: $SUCCESS_RATE% ($PASSED/$TOTAL_CHECKS)"

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo "🎉 Production environment is fully validated and ready!"
        echo "Status: READY FOR DEPLOYMENT"
    else
        echo "✅ Production environment is ready with minor recommendations"
        echo "Status: READY FOR DEPLOYMENT (with warnings)"
    fi
    exit 0
elif [ $FAILED -le 3 ] && [ $SUCCESS_RATE -ge 70 ]; then
    echo "⚠️  Production environment needs attention before deployment"
    echo "Status: NEEDS FIXES"
    exit 1
else
    echo "❌ Production environment is not ready for deployment"
    echo "Status: NOT READY"
    exit 1
fi