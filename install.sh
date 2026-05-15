#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# AI Bot Platform - One-Line Installation
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USER/ai-bot-platform/master/install.sh | bash
#
#   Or clone and run:
#   git clone https://github.com/YOUR_USER/ai-bot-platform.git
#   cd ai-bot-platform
#   chmod +x install.sh && ./install.sh
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
REPO_URL="${REPO_URL:-https://github.com/raimovar/ai-bot-platform.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/ai-bot-platform}"
DOMAIN="${DOMAIN:-localhost}"

# ═══════════════════════════════════════════════════════════════════════════════
# Functions
# ═══════════════════════════════════════════════════════════════════════════════

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        echo "  See: https://docs.docker.com/engine/install/"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed."
        echo "  See: https://docs.docker.com/compose/install/"
        exit 1
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed."
        exit 1
    fi

    log_success "All requirements met"
}

install_platform() {
    log_info "Installing AI Bot Platform..."

    # Create directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Clone or update repo
    if [ -d ".git" ]; then
        log_info "Updating existing installation..."
        BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "master")
        git pull origin "$BRANCH" || git pull origin master
    else
        log_info "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    # Create environment file
    if [ ! -f ".env" ]; then
        log_info "Creating .env file..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
        elif [ -f "docker/.env.example" ]; then
            cp docker/.env.example .env
        else
            log_warning "No .env.example found, creating default..."
            cat > .env << 'EOF'
# AI Bot Platform Environment
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=changeme
TELEGRAM_WEBHOOK_SECRET=changeme
POSTGRES_USER=aibot
POSTGRES_PASSWORD=changeme
POSTGRES_DB=aibotdb
REDIS_PASSWORD=changeme
MINIO_USER=minioadmin
MINIO_PASSWORD=changeme
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EOF
        fi

        # Generate secrets
        SECRET_KEY=$(openssl rand -hex 32)
        TELEGRAM_SECRET=$(openssl rand -hex 32)

        # Update .env
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
        sed -i "s/TELEGRAM_WEBHOOK_SECRET=.*/TELEGRAM_WEBHOOK_SECRET=$TELEGRAM_SECRET/" .env
        sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 16)/" .env
        sed -i "s/MINIO_PASSWORD=.*/MINIO_PASSWORD=$(openssl rand -hex 16)/" .env
    fi

    log_success "Platform installed at $INSTALL_DIR"
}

setup_docker() {
    log_info "Setting up Docker services..."

    # Determine docker compose command
    if command -v docker &> /dev/null; then
        if docker compose version &> /dev/null 2>&1; then
            DOCKER_COMPOSE="docker compose"
        elif command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE="docker-compose"
        else
            log_error "Docker Compose not found"
            exit 1
        fi
    fi

    cd "$INSTALL_DIR"

    # Create necessary directories
    mkdir -p docker/infra/traefik/certs
    mkdir -p docker/infra/nginx
    mkdir -p docker/infra/redis
    mkdir -p docker/infra/postgres

    # Build and start services
    $DOCKER_COMPOSE -f docker/docker-compose.yml build

    log_success "Docker images built"
}

start_platform() {
    log_info "Starting AI Bot Platform..."

    cd "$INSTALL_DIR"

    # Start services
    $DOCKER_COMPOSE -f docker/docker-compose.yml up -d

    # Wait for services
    log_info "Waiting for services to be ready..."
    sleep 10

    # Check status
    $DOCKER_COMPOSE -f docker/docker-compose.yml ps

    log_success "Platform started!"
}

print_next_steps() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo -e "${GREEN}AI Bot Platform has been installed successfully!${NC}"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Configure your environment:"
    echo "   cd $INSTALL_DIR"
    echo "   nano .env"
    echo ""
    echo "2. Add your API keys to .env:"
    echo "   OPENAI_API_KEY=sk-..."
    echo "   ANTHROPIC_API_KEY=sk-ant-..."
    echo ""
    echo "3. Start the platform:"
    echo "   docker compose up -d"
    echo ""
    echo "4. Access the UI:"
    echo "   http://localhost:3000"
    echo ""
    echo "5. Default login:"
    echo "   Email: admin@example.com"
    echo "   Password: admin123"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "For Telegram integration:"
    echo "   1. Create a bot via @BotFather"
    echo "   2. Add the bot token to your bot config"
    echo "   3. Set a webhook URL pointing to this server"
    echo ""
    echo "For local LLM support (optional):"
    echo "   docker compose --profile local-llm up -d"
    echo ""
    echo "For vector search (optional):"
    echo "   docker compose --profile vector up -d"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "Useful commands:"
    echo "   docker compose logs -f backend    # View backend logs"
    echo "   docker compose logs -f frontend   # View frontend logs"
    echo "   docker compose restart             # Restart all services"
    echo "   docker compose down                # Stop all services"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo "              AI Bot Platform - Installation Script"
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""

    # Parse arguments
    case "${1:-}" in
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --help          Show this help"
            echo "  --update        Update existing installation"
            echo "  --no-start      Install but don't start services"
            echo ""
            exit 0
            ;;
        --update)
            NO_START="${2:-false}"
            ;;
        --no-start)
            NO_START="true"
            ;;
    esac

    check_requirements
    install_platform
    setup_docker

    if [ "${NO_START:-false}" != "true" ]; then
        start_platform
    fi

    print_next_steps
}

main "$@"
