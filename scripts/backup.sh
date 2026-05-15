#!/bin/bash
# Backup Script
# Usage: ./scripts/backup.sh [output_dir]

set -e

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="aibot_backup_${TIMESTAMP}"

mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

echo "📦 Creating backup: $BACKUP_NAME"
echo ""

# PostgreSQL
echo "💾 Backing up PostgreSQL..."
docker exec aibot_postgres pg_dump -U aibot aibotdb > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
echo "✅ Database backed up"

# Redis (optional - sessions)
if docker exec aibot_redis redis-cli ping > /dev/null 2>&1; then
    echo "💾 Backing up Redis..."
    docker exec aibot_redis redis-cli BGSAVE > /dev/null
    sleep 2
    docker cp aibot_redis:/data/dump.rdb "$BACKUP_DIR/$BACKUP_NAME/redis.rdb" 2>/dev/null || true
    echo "✅ Redis backed up"
fi

# Docker volumes
echo "📦 Backing up volumes..."
docker run --rm -v aibot-platform_postgres_data:/data -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf "/backup/postgres_data.tar.gz" -C /data . 2>/dev/null || true
docker run --rm -v aibot-platform_redis_data:/data -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf "/backup/redis_data.tar.gz" -C /data . 2>/dev/null || true

# Config files
echo "⚙️  Backing up configs..."
cp docker/.env "$BACKUP_DIR/$BACKUP_NAME/.env" 2>/dev/null || true

# Create archive
cd "$BACKUP_DIR"
tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo ""
echo "✅ Backup complete: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo ""
echo "To restore:"
echo "  tar -xzf ${BACKUP_NAME}.tar.gz"
echo "  docker exec -i aibot_postgres psql -U aibot aibotdb < database.sql"
