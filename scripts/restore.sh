#!/bin/bash
# Restore Script
# Usage: ./scripts/restore.sh <backup_file>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/aibot_backup_20240101_120000.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: File not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  This will restore from: $BACKUP_FILE"
echo "⚠️  Current data will be replaced!"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Extract backup
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)

echo "🔄 Restoring..."

# Stop services
docker-compose stop backend bot-runtime

# Restore PostgreSQL
echo "💾 Restoring PostgreSQL..."
docker exec -i aibot_postgres psql -U aibot aibotdb < "$TEMP_DIR/$BACKUP_NAME/database.sql"

# Restore Redis
if [ -f "$TEMP_DIR/$BACKUP_NAME/redis.rdb" ]; then
    echo "💾 Restoring Redis..."
    docker cp "$TEMP_DIR/$BACKUP_NAME/redis.rdb" aibot_redis:/data/dump.rdb
    docker exec aibot_redis redis-cli SHUTDOWN NOSAVE || true
fi

# Cleanup
rm -rf "$TEMP_DIR"

# Start services
docker-compose start backend bot-runtime

echo ""
echo "✅ Restore complete!"
echo "Run ./scripts/health-check.sh to verify"
