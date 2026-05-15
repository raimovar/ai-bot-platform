# ═══════════════════════════════════════════════════════════════════════════════
# AI Bot Platform - Make Commands
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help install dev prod stop clean logs restart status backup restore update

# Default target
help:
	@echo "AI Bot Platform - Available Commands:"
	@echo ""
	@echo "  make install    - Install and start (production)"
	@echo "  make dev        - Start in development mode"
	@echo "  make prod       - Start in production mode"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make clean      - Remove all containers and volumes"
	@echo "  make logs       - Show logs (all services)"
	@echo "  make status     - Show service status"
	@echo "  make health     - Run health check"
	@echo "  make backup     - Create backup"
	@echo "  make restore    - Restore from backup"
	@echo "  make update     - Update to latest version"
	@echo ""
	@echo "  make logs-frontend  - Frontend logs only"
	@echo "  make logs-backend   - Backend logs only"
	@echo "  make psql          - Open PostgreSQL shell"
	@echo "  make redis-cli      - Open Redis CLI"
	@echo ""

# Install and start
install:
	@if [ ! -f docker/.env ]; then cp docker/.env.example docker/.env; fi
	@echo "⚠️  Edit docker/.env and add your API keys before continuing"
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then exit 1; fi
	docker-compose -f docker/docker-compose.yml up -d
	@echo ""
	@echo "✅ Started! Access:"
	@echo "   UI:      http://localhost:3000"
	@echo "   API:     http://localhost:8000/docs"
	@echo "   Admin:   http://localhost:8080 (Traefik)"

# Development mode
dev:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
	@echo "✅ Development mode started"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"

# Production mode
prod:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
	@echo "✅ Production mode started"

# Stop services
stop:
	docker-compose -f docker/docker-compose.yml stop
	@echo "✅ Services stopped"

# Restart services
restart:
	docker-compose -f docker/docker-compose.yml restart
	@echo "✅ Services restarted"

# Remove everything
clean:
	@echo "⚠️  This will delete ALL data!"
	@read -p "Are you sure? (y/n) " -n 1 -r; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then exit 1; fi
	docker-compose -f docker/docker-compose.yml down -v --remove-orphans
	docker volume rm $$(docker volume ls -q -f name=aibot_) 2>/dev/null || true
	@echo "✅ Everything cleaned"

# Show logs
logs:
	docker-compose -f docker/docker-compose.yml logs -f --tail=100

# Service-specific logs
logs-backend:
	docker-compose -f docker/docker-compose.yml logs -f backend --tail=50

logs-frontend:
	docker-compose -f docker/docker-compose.yml logs -f frontend --tail=50

logs-runtime:
	docker-compose -f docker/docker-compose.yml logs -f bot-runtime --tail=50

# Show status
status:
	docker-compose -f docker/docker-compose.yml ps

# Health check
health:
	./scripts/health-check.sh http://localhost

# Backup
backup:
	./scripts/backup.sh

# Restore
restore:
	@read -p "Enter backup file path: " path; \
	./scripts/restore.sh "$$path"

# Update
update:
	./scripts/update.sh

# Database tools
psql:
	docker exec -it aibot_postgres psql -U aibot -d aibotdb

redis-cli:
	docker exec -it aibot_redis redis-cli

# Shell into containers
shell-backend:
	docker exec -it aibot_backend /bin/bash

shell-frontend:
	docker exec -it aibot_frontend /bin/sh

# Quick chat test
test-api:
	curl -X POST http://localhost:8000/api/v1/users/auth/login \
		-H "Content-Type: application/json" \
		-d '{"username":"admin","password":"admin123"}'

# Help
.DEFAULT_GOAL := help
