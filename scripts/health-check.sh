#!/bin/bash
# Health Check Script
# Usage: ./scripts/health-check.sh

set -e

ENDPOINT="${1:-http://localhost}"

echo "🔍 Checking AI Bot Platform services..."
echo ""

check_service() {
    local name=$1
    local url=$2
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "✅ $name"
        return 0
    else
        echo "❌ $name"
        return 1
    fi
}

# Check all services
FAILED=0

check_service "Frontend" "$ENDPOINT/" || FAILED=1
check_service "Backend API" "$ENDPOINT/api/v1/health" || FAILED=1
check_service "Backend Ready" "$ENDPOINT/api/v1/ready" || FAILED=1
check_service "Bot Runtime" "$ENDPOINT:8001/health" || FAILED=1
check_service "AI Gateway" "$ENDPOINT:8002/health" || FAILED=1

# Check Docker containers
echo ""
echo "🐳 Docker Containers:"
docker ps --filter "name=aibot_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not available"

echo ""
if [ $FAILED -eq 0 ]; then
    echo "✅ All checks passed!"
    exit 0
else
    echo "❌ Some checks failed"
    exit 1
fi
