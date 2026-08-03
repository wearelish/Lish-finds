#!/bin/bash

# LishFind Database Backup Script
# Creates timestamped backups of PostgreSQL database

set -e

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="lishfind_backup_${TIMESTAMP}.sql"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🗄️  LishFind Database Backup${NC}"
echo -e "${BLUE}Timestamp: ${YELLOW}$(date)${NC}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create database backup
echo -e "${BLUE}📦 Creating database backup...${NC}"
pg_dump --no-password --clean --if-exists --create --verbose \
    --file="$BACKUP_DIR/$BACKUP_FILE" \
    "$PGDATABASE"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
    
    # Compress the backup
    echo -e "${BLUE}🗜️  Compressing backup...${NC}"
    gzip "$BACKUP_DIR/$BACKUP_FILE"
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Backup compressed: ${BACKUP_FILE}.gz${NC}"
    else
        echo -e "${YELLOW}⚠️  Compression failed, keeping uncompressed backup${NC}"
    fi
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Clean old backups
echo -e "${BLUE}🧹 Cleaning old backups (older than $RETENTION_DAYS days)...${NC}"
find "$BACKUP_DIR" -name "lishfind_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "lishfind_backup_*.sql" -mtime +$RETENTION_DAYS -delete

# List current backups
echo -e "${BLUE}📋 Current backups:${NC}"
ls -lah "$BACKUP_DIR"/lishfind_backup_* 2>/dev/null || echo "No backups found"

echo -e "${GREEN}✅ Backup process completed${NC}"