#!/bin/bash
# Update Script - Pull latest images and restart
# Usage: ./scripts/update.sh

set -e

echo "🔄 Updating AI Bot Platform..."
echo ""

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose pull

# Rebuild custom images
echo "🔨 Rebuilding custom images..."
docker-compose build --parallel

# Restart services
echo "🚀 Restarting services..."
docker-compose up -d

echo ""
echo "✅ Update complete!"
echo ""
echo "Run ./scripts/health-check.sh to verify"
