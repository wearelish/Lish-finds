#!/bin/bash

# Production-Specific Post-Switch Hook
# Additional steps for production environment

set -e

ENVIRONMENT=${TARGET_ENVIRONMENT:-production}
PROJECT_ROOT=${PROJECT_ROOT:-$(pwd)}

echo "🔒 Running production-specific post-switch hook"

cd "$PROJECT_ROOT"

# Validate production secrets
echo "🔐 Validating production secrets..."

REQUIRED_SECRETS=(
    "SECRET_KEY"
    "DATABASE_URL" 
    "JWT_SECRET"
    "REDIS_PASSWORD"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! grep -q "^$secret=" .env; then
        echo "❌ Production secret missing: $secret"
        exit 1
    fi
    
    value=$(grep "^$secret=" .env | cut -d'=' -f2-)
    
    # Check for placeholder values
    if [[ "$value" == *"your-"* ]] || [[ "$value" == *"changeme"* ]] || [[ "$value" == *"example"* ]]; then
        echo "❌ Production secret '$secret' appears to be a placeholder"
        exit 1
    fi
    
    # Check minimum length for critical secrets
    if [[ "$secret" == "SECRET_KEY" ]] || [[ "$secret" == "JWT_SECRET" ]]; then
        if [ ${#value} -lt 32 ]; then
            echo "❌ Production secret '$secret' is too short (minimum 32 characters)"
            exit 1
        fi
    fi
done

echo "✅ Production secrets validated"

# Check security configurations
echo "🛡️  Validating security configurations..."

# Check DEBUG is disabled
DEBUG=$(grep "^DEBUG=" .env | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ]; then
    echo "❌ DEBUG mode is enabled in production"
    exit 1
fi

# Check ALLOWED_HOSTS is configured
if ! grep -q "^ALLOWED_HOSTS=" .env; then
    echo "❌ ALLOWED_HOSTS not configured for production"
    exit 1
fi

ALLOWED_HOSTS=$(grep "^ALLOWED_HOSTS=" .env | cut -d'=' -f2-)
if [[ "$ALLOWED_HOSTS" == *"localhost"* ]] || [ "$ALLOWED_HOSTS" = "*" ]; then
    echo "⚠️  ALLOWED_HOSTS contains localhost or wildcard in production"
fi

# Check CORS origins
if grep -q "^CORS_ORIGINS=" .env; then
    CORS_ORIGINS=$(grep "^CORS_ORIGINS=" .env | cut -d'=' -f2-)
    if [ "$CORS_ORIGINS" = "*" ]; then
        echo "⚠️  CORS_ORIGINS is wildcard (*) in production"
    fi
fi

echo "✅ Security configurations validated"

# Check SSL/TLS configuration
echo "🔒 Checking SSL/TLS configuration..."

SSL_VARS=("ENABLE_HTTPS" "SECURE_COOKIES" "CSRF_COOKIE_SECURE" "SESSION_COOKIE_SECURE")

for var in "${SSL_VARS[@]}"; do
    if grep -q "^$var=" .env; then
        value=$(grep "^$var=" .env | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
        if [ "$value" != "true" ] && [ "$value" != "1" ]; then
            echo "⚠️  $var is not enabled in production"
        fi
    else
        echo "⚠️  $var not configured in production"
    fi
done

# Check monitoring configuration
echo "📊 Validating monitoring configuration..."

MONITORING_VARS=("SENTRY_DSN" "LOG_LEVEL")

for var in "${MONITORING_VARS[@]}"; do
    if ! grep -q "^$var=" .env; then
        echo "⚠️  Monitoring variable '$var' not configured"
    fi
done

# Validate log level for production
if grep -q "^LOG_LEVEL=" .env; then
    LOG_LEVEL=$(grep "^LOG_LEVEL=" .env | cut -d'=' -f2-)
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "⚠️  LOG_LEVEL is DEBUG in production (consider INFO or WARNING)"
    fi
fi

echo "✅ Monitoring configuration checked"

# Run production-specific database optimizations
echo "🗃️  Running production database optimizations..."

cd backend

# Run database optimizations if available
if command -v python >/dev/null 2>&1; then
    python -c "
try:
    from database.performance import optimize_database
    optimize_database()
    print('✅ Database optimizations applied')
except Exception as e:
    print(f'⚠️  Database optimization failed: {e}')
" 2>/dev/null || echo "⚠️  Could not run database optimizations"
fi

cd "$PROJECT_ROOT"

# Check file permissions
echo "🔐 Securing file permissions..."

# Secure environment files
find . -name ".env*" -type f -exec chmod 600 {} \;

# Secure secret directories
if [ -d ".secrets" ]; then
    chmod -R 700 .secrets
fi

# Remove world-readable permissions from config files
find . -name "*.conf" -type f -exec chmod 640 {} \; 2>/dev/null || true
find . -name "*.ini" -type f -exec chmod 640 {} \; 2>/dev/null || true

echo "✅ File permissions secured"

# Validate backup configurations
echo "💾 Validating backup configurations..."

if [ -f "scripts/backup.sh" ]; then
    if [ -x "scripts/backup.sh" ]; then
        echo "✅ Backup script is executable"
    else
        echo "⚠️  Backup script is not executable"
        chmod +x scripts/backup.sh
    fi
else
    echo "⚠️  Backup script not found"
fi

# Check if backup destination is configured
if grep -q "BACKUP_" .env; then
    echo "✅ Backup configuration found"
else
    echo "⚠️  No backup configuration found"
fi

# Final production readiness check
echo "🎯 Running final production readiness check..."

READINESS_SCORE=0
TOTAL_CHECKS=10

# Check 1: Environment file exists and is secure
if [ -f ".env" ] && [ "$(stat -f %Mp%Lp .env)" = "100600" ]; then
    ((READINESS_SCORE++))
    echo "✅ Environment file is secure"
else
    echo "❌ Environment file security issue"
fi

# Check 2: Database URL is production-ready
DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
if [[ $DATABASE_URL != *"sqlite"* ]]; then
    ((READINESS_SCORE++))
    echo "✅ Using production database"
else
    echo "⚠️  Using SQLite database in production"
fi

# Check 3: Secret key is strong
SECRET_KEY=$(grep "^SECRET_KEY=" .env | cut -d'=' -f2-)
if [ ${#SECRET_KEY} -ge 32 ]; then
    ((READINESS_SCORE++))
    echo "✅ Secret key is strong"
else
    echo "❌ Secret key is weak"
fi

# Check 4: Debug is disabled
if [ "$DEBUG" != "true" ] && [ "$DEBUG" != "1" ]; then
    ((READINESS_SCORE++))
    echo "✅ Debug mode is disabled"
else
    echo "❌ Debug mode is enabled"
fi

# Check 5: HTTPS is enabled
if grep -q "ENABLE_HTTPS=true" .env; then
    ((READINESS_SCORE++))
    echo "✅ HTTPS is enabled"
else
    echo "⚠️  HTTPS configuration not found"
fi

# Check 6: Monitoring is configured
if grep -q "SENTRY_DSN=" .env && [ -n "$(grep "^SENTRY_DSN=" .env | cut -d'=' -f2-)" ]; then
    ((READINESS_SCORE++))
    echo "✅ Error monitoring is configured"
else
    echo "⚠️  Error monitoring not configured"
fi

# Check 7: Allowed hosts is configured
if grep -q "^ALLOWED_HOSTS=" .env && [[ "$(grep "^ALLOWED_HOSTS=" .env | cut -d'=' -f2-)" != *"localhost"* ]]; then
    ((READINESS_SCORE++))
    echo "✅ Allowed hosts is production-ready"
else
    echo "⚠️  Allowed hosts needs production configuration"
fi

# Check 8: CORS is properly configured
if grep -q "^CORS_ORIGINS=" .env && [ "$(grep "^CORS_ORIGINS=" .env | cut -d'=' -f2-)" != "*" ]; then
    ((READINESS_SCORE++))
    echo "✅ CORS is properly configured"
else
    echo "⚠️  CORS needs production configuration"
fi

# Check 9: Log level is appropriate
LOG_LEVEL=$(grep "^LOG_LEVEL=" .env | cut -d'=' -f2- 2>/dev/null || echo "INFO")
if [ "$LOG_LEVEL" = "INFO" ] || [ "$LOG_LEVEL" = "WARNING" ] || [ "$LOG_LEVEL" = "ERROR" ]; then
    ((READINESS_SCORE++))
    echo "✅ Log level is appropriate for production"
else
    echo "⚠️  Log level may be too verbose for production"
fi

# Check 10: Docker configurations exist
if [ -f "Dockerfile" ] && [ -f "docker-compose.production.yml" ]; then
    ((READINESS_SCORE++))
    echo "✅ Docker configurations are present"
else
    echo "⚠️  Docker configurations incomplete"
fi

# Calculate readiness percentage
READINESS_PERCENT=$((READINESS_SCORE * 100 / TOTAL_CHECKS))

echo ""
echo "📊 Production Readiness Score: $READINESS_SCORE/$TOTAL_CHECKS ($READINESS_PERCENT%)"

if [ $READINESS_SCORE -eq $TOTAL_CHECKS ]; then
    echo "🎉 Production environment is fully ready!"
elif [ $READINESS_SCORE -ge 8 ]; then
    echo "✅ Production environment is mostly ready with minor issues"
elif [ $READINESS_SCORE -ge 6 ]; then
    echo "⚠️  Production environment needs attention before deployment"
else
    echo "❌ Production environment is not ready for deployment"
    exit 1
fi

echo ""
echo "✅ Production post-switch hook completed"
echo "🚀 Production environment '$ENVIRONMENT' is configured!"