#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# AI Bot Platform - One-Line Installation
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/raimovar/ai-bot-platform/master/install.sh | bash
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Config
REPO_URL="${REPO_URL:-https://github.com/raimovar/ai-bot-platform.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/ai-bot-platform}"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_requirements() {
    log_info "Checking requirements..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed."
        exit 1
    fi
    if ! docker compose version &> /dev/null 2>&1 && ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed."
        exit 1
    fi
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed."
        exit 1
    fi
    log_success "All requirements met"
}

install_platform() {
    log_info "Installing AI Bot Platform..."
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    if [ -d ".git" ]; then
        log_info "Updating existing installation..."
        git pull
    else
        log_info "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    # Create .env if not exists
    if [ ! -f ".env" ]; then
        log_info "Creating .env file..."
        
        # Generate secure random values
        local secret_key=$(openssl rand -hex 32)
        local telegram_secret=$(openssl rand -hex 32)
        local postgres_password=$(openssl rand -hex 16)
        local redis_password=$(openssl rand -hex 16)
        local minio_password=$(openssl rand -hex 16)
        
        cat > .env << ENVEOF
# AI Bot Platform - Environment Configuration
DEBUG=false
LOG_LEVEL=INFO
DOMAIN=localhost

SECRET_KEY=${secret_key}
TELEGRAM_WEBHOOK_SECRET=${telegram_secret}

POSTGRES_USER=aibot
POSTGRES_PASSWORD=${postgres_password}
POSTGRES_DB=aibotdb

REDIS_PASSWORD=${redis_password}

MINIO_USER=minioadmin
MINIO_PASSWORD=${minio_password}

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
HF_TOKEN=
OLLAMA_BASE_URL=http://ollama:11434

CORS_ORIGINS=http://localhost:3000,http://localhost
RATE_LIMIT_PER_MINUTE=60
ENVEOF
    fi
    
    log_success "Platform installed at $INSTALL_DIR"
}

setup_docker() {
    log_info "Setting up Docker services..."
    
    # Determine compose command
    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker-compose"
    fi
    
    # Copy .env to docker directory
    if [ -f "$INSTALL_DIR/.env" ]; then
        cp "$INSTALL_DIR/.env" "$INSTALL_DIR/docker/.env"
        log_info "Copied .env to docker directory"
    fi
    
    # Create necessary directories
    mkdir -p "$INSTALL_DIR/docker/infra/traefik/certs"
    mkdir -p "$INSTALL_DIR/docker/infra/nginx"
    mkdir -p "$INSTALL_DIR/docker/infra/redis"
    mkdir -p "$INSTALL_DIR/docker/infra/postgres"
    
    # Build services
    (cd "$INSTALL_DIR" && $compose_cmd -f docker/docker-compose.yml build)
    log_success "Docker images built"
}

create_admin_user() {
    log_info "Creating admin user..."
    
    # Wait for postgres to be ready
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec aibot_postgres pg_isready -U aibot -d aibotdb &>/dev/null; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    # Create admin user with pre-generated bcrypt hash for "admin123"
    docker exec aibot_postgres psql -U aibot -d aibotdb -c "
    INSERT INTO users (id, email, username, password_hash, full_name, role, is_active, max_bots) 
    VALUES (
        gen_random_uuid(), 
        'admin@aibot.local', 
        'admin', 
        '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYL0Bq8Mm/G', 
        'Admin', 
        'admin', 
        true, 
        100
    ) ON CONFLICT (email) DO NOTHING;" &>/dev/null || true
    
    log_success "Admin user created"
}

start_platform() {
    log_info "Starting AI Bot Platform..."
    
    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker-compose"
    fi
    
    (cd "$INSTALL_DIR" && $compose_cmd -f docker/docker-compose.yml up -d)
    
    log_info "Waiting for services..."
    sleep 15
    
    (cd "$INSTALL_DIR" && $compose_cmd -f docker/docker-compose.yml ps)
    log_success "Platform started!"
}

print_next_steps() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo -e "${GREEN}AI Bot Platform installed successfully!${NC}"
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "Access the UI: http://$(curl -s ifconfig.me 2>/dev/null || echo 'localhost'):3000"
    echo ""
    echo "Default login:"
    echo "  Email: admin@aibot.local"
    echo "  Password: admin123"
    echo ""
    echo "Add your API keys:"
    echo "  nano $INSTALL_DIR/.env"
    echo ""
    echo "Useful commands:"
    echo "  cd $INSTALL_DIR && docker compose logs -f backend"
    echo "  cd $INSTALL_DIR && docker compose restart"
    echo ""
}

main() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo "              AI Bot Platform - Installation Script"
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    
    check_requirements
    install_platform
    setup_docker
    start_platform
    create_admin_user
    print_next_steps
}

main "$@"
