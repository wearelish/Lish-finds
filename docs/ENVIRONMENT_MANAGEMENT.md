# Environment Management Guide

This guide covers LishFind's comprehensive environment management system for production-ready deployments.

## Table of Contents

- [Overview](#overview)
- [Environment Management CLI](#environment-management-cli)
- [Secrets Management](#secrets-management)
- [Configuration Validation](#configuration-validation)
- [Environment Switching](#environment-switching)
- [Production Validation](#production-validation)
- [Deployment Preparation](#deployment-preparation)
- [Best Practices](#best-practices)

## Overview

LishFind includes a comprehensive environment management system that provides:

- **Secrets Management**: Secure storage, rotation, and management of application secrets
- **Configuration Validation**: Automated validation of environment configurations
- **Environment Switching**: Easy switching between development, staging, and production environments
- **Production Validation**: Comprehensive production readiness checks
- **Deployment Preparation**: Automated deployment preparation and validation

## Environment Management CLI

The environment management CLI (`backend/cli/env_manager.py`) provides a unified interface for all environment operations.

### Installation

```bash
# Install additional dependencies
pip install -r backend/requirements-env.txt

# Make CLI executable
chmod +x backend/cli/env_manager.py
```

### Basic Usage

```bash
# Get help
python backend/cli/env_manager.py --help

# Use specific environment
python backend/cli/env_manager.py -e production secrets list
```

## Secrets Management

### Adding Secrets

```bash
# Add a secret interactively
python backend/cli/env_manager.py secrets add -k jwt_secret

# Add with value
python backend/cli/env_manager.py secrets add -k api_key -v "your-api-key"

# Add unencrypted (not recommended)
python backend/cli/env_manager.py secrets add -k public_key -v "key-value" --no-encrypt
```

### Managing Secrets

```bash
# List all secrets
python backend/cli/env_manager.py secrets list

# Get a secret value
python backend/cli/env_manager.py secrets get -k jwt_secret

# Rotate a secret (generates new value)
python backend/cli/env_manager.py secrets rotate -k jwt_secret

# Delete a secret
python backend/cli/env_manager.py secrets delete -k old_secret
```

### Production Setup

```bash
# Setup initial production secrets
python backend/cli/env_manager.py -e production secrets setup

# Check secrets health
python backend/cli/env_manager.py -e production secrets health
```

### Secrets Storage

Secrets are stored in `.secrets/{environment}/` with the following structure:

```
.secrets/
├── development/
│   ├── jwt_secret.json
│   └── api_key.json
├── staging/
│   └── jwt_secret.json
└── production/
    ├── jwt_secret.json
    ├── database_password.json
    └── api_key.json
```

Each secret file contains:
- Encrypted/plain value
- Creation timestamp
- Environment metadata
- Encryption status

## Configuration Validation

### Validating Environment

```bash
# Validate current environment
python backend/cli/env_manager.py config validate

# Validate with specific config file
python backend/cli/env_manager.py config validate -f .env.production

# Generate validation report
python backend/cli/env_manager.py config report -o validation_report.json
```

### Validation Checks

The validator checks for:

- **Required Variables**: Environment-specific required variables
- **Format Validation**: URL, email, port, boolean formats
- **Security Issues**: Weak passwords, debug mode in production
- **Dependencies**: Package conflicts and vulnerabilities
- **Configuration Schema**: Proper configuration structure

### Example Validation Output

```
Configuration Validation - production
====================================
✅ Configuration is valid
Errors: 0
Warnings: 2

Issues:
⚠️ CORS is configured to allow all origins
   Suggestion: Specify exact origins for better security
⚠️ Secret 'api_key' is 45 days old
   Suggestion: Consider rotating secrets older than 90 days
```

## Environment Switching

### Managing Environments

```bash
# List available environments
python backend/cli/env_manager.py env list

# Switch to production
python backend/cli/env_manager.py env switch production

# Switch without backup
python backend/cli/env_manager.py env switch staging --no-backup
```

### Creating New Environments

```bash
# Create new environment from template
python backend/cli/env_manager.py env create testing

# Copy from existing environment
python backend/cli/env_manager.py env create testing --from-env staging
```

### Environment Validation

```bash
# Validate environment setup
python backend/cli/env_manager.py env validate production

# Compare environments
python backend/cli/env_manager.py env diff development production
```

### Post-Switch Hooks

Environment switching triggers automatic hooks:

1. **Global Hook** (`scripts/env-hooks/post-switch.sh`):
   - Updates dependencies
   - Runs migrations
   - Clears cache
   - Validates configuration

2. **Environment-Specific Hooks** (`scripts/env-hooks/post-switch-{env}.sh`):
   - Production: Security validation, file permissions
   - Staging: Integration setup
   - Development: Local database creation

## Production Validation

### Comprehensive Validation Script

```bash
# Run full production validation
./scripts/validate-production.sh
```

### Validation Categories

1. **Environment Configuration**
   - Required variables present
   - Security settings
   - Debug mode disabled

2. **Security Configuration**
   - Strong secret keys
   - HTTPS enabled
   - Secure cookie settings

3. **Database Configuration**
   - Production database type
   - SSL requirements
   - Strong passwords

4. **Docker Configuration**
   - Dockerfiles present
   - Multi-stage builds
   - Security best practices

5. **Dependency Security**
   - No vulnerable packages
   - Locked versions

6. **Monitoring & Logging**
   - Appropriate log levels
   - Error monitoring
   - Health endpoints

7. **Deployment Configuration**
   - Platform configs present
   - Deployment scripts

8. **Backup & Recovery**
   - Backup scripts
   - Recovery procedures

9. **Performance Configuration**
   - Caching configured
   - Optimization settings

10. **CI/CD Configuration**
    - Automated workflows
    - Testing pipelines

### Validation Output

```
🔍 LishFind Production Validation
==================================
Project Root: /path/to/project
Timestamp: 2024-08-02T10:30:00Z

📋 1. Environment Configuration
------------------------------
✅ Production environment file exists
✅ ENVIRONMENT is configured
✅ SECRET_KEY is configured
✅ DATABASE_URL is configured
✅ ALLOWED_HOSTS is configured
✅ CORS_ORIGINS is configured
✅ DEBUG is disabled

📊 VALIDATION SUMMARY
====================
✅ Passed: 45
❌ Failed: 2
⚠️  Warnings: 8

Success Rate: 82% (45/55)
✅ Production environment is ready with minor recommendations
Status: READY FOR DEPLOYMENT (with warnings)
```

## Deployment Preparation

### Pre-Deployment Validation

```bash
# Validate and prepare for deployment
python backend/cli/env_manager.py deploy prepare -e production -p railway

# Validation only
python backend/cli/env_manager.py deploy prepare -e production --validate-only
```

### Platform-Specific Steps

The deployment preparation shows platform-specific next steps:

**Railway:**
```
1. Install Railway CLI: npm install -g @railway/cli
2. Login: railway login
3. Deploy: railway up --service backend
```

**Render:**
```
1. Connect GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy using render.yaml configuration
```

**Fly.io:**
```
1. Install Fly CLI: curl -L https://fly.io/install.sh | sh
2. Login: flyctl auth login
3. Deploy: flyctl deploy
```

## Best Practices

### Secrets Management

1. **Use Strong Secrets**:
   - Minimum 32 characters for critical secrets
   - Use cryptographically secure generation
   - Avoid dictionary words or patterns

2. **Regular Rotation**:
   - Rotate secrets every 90 days
   - Automated rotation for non-breaking secrets
   - Document rotation procedures

3. **Environment Separation**:
   - Separate secrets per environment
   - Never share production secrets
   - Use different encryption passwords

4. **Cloud Integration**:
   - Use cloud secret managers in production
   - AWS Secrets Manager, Google Secret Manager
   - Azure Key Vault integration

### Configuration Management

1. **Environment Files**:
   - Separate file per environment
   - Never commit production secrets
   - Use templates for new environments

2. **Validation**:
   - Validate before deployment
   - Automated validation in CI/CD
   - Regular configuration audits

3. **Documentation**:
   - Document all configuration options
   - Maintain configuration schemas
   - Version control for config templates

### Environment Switching

1. **Safe Switching**:
   - Always backup before switching
   - Validate target environment first
   - Use post-switch hooks for automation

2. **Testing**:
   - Test environment switching in CI/CD
   - Validate application starts after switch
   - Check database connectivity

3. **Rollback Procedures**:
   - Keep environment backups
   - Document rollback procedures
   - Test rollback scenarios

### Production Deployment

1. **Pre-Deployment**:
   - Run full validation
   - Check all dependencies
   - Verify backup procedures

2. **Deployment**:
   - Use blue-green deployment
   - Monitor deployment progress
   - Have rollback plan ready

3. **Post-Deployment**:
   - Verify application health
   - Check all integrations
   - Monitor error rates

## Environment Variables Reference

### Required Variables (All Environments)

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Current environment | `production` |
| `SECRET_KEY` | Application secret key | `your-32-char-secret` |
| `DATABASE_URL` | Database connection URL | `postgresql://...` |

### Production-Specific Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ALLOWED_HOSTS` | Allowed host domains | `api.yourdomain.com` |
| `CORS_ORIGINS` | CORS allowed origins | `https://yourdomain.com` |
| `ENABLE_HTTPS` | Enable HTTPS features | `true` |
| `SECURE_COOKIES` | Use secure cookies | `true` |
| `SENTRY_DSN` | Error monitoring DSN | `https://...@sentry.io/...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | None |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENAI_API_KEY` | OpenAI API key | None |
| `GEMINI_API_KEY` | Google Gemini API key | None |

## Troubleshooting

### Common Issues

1. **Secret Decryption Fails**:
   - Check encryption password
   - Verify secret file permissions
   - Ensure consistent environment

2. **Environment Switch Fails**:
   - Validate target environment first
   - Check file permissions
   - Review post-switch hook logs

3. **Validation Errors**:
   - Review specific error messages
   - Check configuration syntax
   - Verify all required variables

4. **Deployment Preparation Fails**:
   - Run validation separately
   - Check platform-specific requirements
   - Verify network connectivity

### Getting Help

1. **CLI Help**:
   ```bash
   python backend/cli/env_manager.py --help
   python backend/cli/env_manager.py secrets --help
   ```

2. **Validation Reports**:
   ```bash
   python backend/cli/env_manager.py config report -o debug_report.json
   ```

3. **Verbose Logging**:
   ```bash
   LOG_LEVEL=DEBUG python backend/cli/env_manager.py ...
   ```

## Security Considerations

1. **File Permissions**:
   - Environment files: `600` (owner read/write only)
   - Secret directories: `700` (owner access only)
   - Script files: `755` (executable by owner)

2. **Encryption**:
   - All secrets encrypted by default
   - Strong encryption passwords
   - Regular key rotation

3. **Access Control**:
   - Limit access to production secrets
   - Use role-based access in cloud
   - Audit secret access logs

4. **Network Security**:
   - Use HTTPS for all communications
   - Enable database SSL
   - Restrict network access

This comprehensive environment management system ensures your LishFind application is production-ready with enterprise-grade security and reliability.