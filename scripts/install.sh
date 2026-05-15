#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Bot Platform - One-line Installer
# 
# Использование:
#   curl -fsSL URL | bash
#   curl -fsSL URL | bash -s -- --dir /opt/ai-bot-platform
#
# ═══════════════════════════════════════════════════════════════

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Настройки по умолчанию
INSTALL_DIR="${INSTALL_DIR:-$HOME/ai-bot-platform}"
GITHUB_REPO="${GITHUB_REPO:-}"

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        --help)
            echo "Использование: $0 [--dir <путь>] [--repo <repo>]"
            exit 0
            ;;
        *)
            echo "Неизвестный аргумент: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  AI Bot Platform Installer${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker не установлен${NC}"
    echo "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker не запущен${NC}"
    echo "Запустите Docker и попробуйте снова"
    exit 1
fi

# Проверка Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose не установлен${NC}"
    echo "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"
echo -e "${GREEN}✓${NC} Docker Compose: $(docker compose version 2>/dev/null || docker-compose --version | cut -d' ' -f4)"
echo ""

# Выбор директории
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Директория $INSTALL_DIR уже существует${NC}"
    read -p "Перезаписать? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Отменено"
        exit 0
    fi
    rm -rf "$INSTALL_DIR"
fi

# Клонирование или создание
if [ -n "$GITHUB_REPO" ]; then
    echo -e "${GREEN}↧ Клонирование репозитория...${NC}"
    git clone "$GITHUB_REPO" "$INSTALL_DIR"
else
    echo -e "${YELLOW}⚠ Git репозиторий не указан${NC}"
    echo "Скрипт ожидает, что проект уже скопирован в $INSTALL_DIR"
    echo ""
    echo "Или используйте:"
    echo "  curl -fsSL URL | bash -s -- --repo https://github.com/user/repo"
    echo ""
    read -p "Создать структуру проекта локально? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

cd "$INSTALL_DIR"

# Проверка структуры
if [ ! -f "docker/docker-compose.yml" ]; then
    echo -e "${RED}✗ docker/docker-compose.yml не найден${NC}"
    exit 1
fi

# Создание .env
if [ ! -f "docker/.env" ]; then
    if [ -f "docker/.env.example" ]; then
        cp docker/.env.example docker/.env
        echo -e "${YELLOW}⚠ Создан docker/.env из шаблона${NC}"
        echo "Отредактируйте docker/.env и добавьте:"
        echo "  - SECRET_KEY"
        echo "  - OPENAI_API_KEY / ANTHROPIC_API_KEY"
        echo "  - POSTGRES_PASSWORD"
    fi
fi

# Запуск
echo ""
echo -e "${GREEN}↥ Запуск сервисов...${NC}"
docker-compose -f docker/docker-compose.yml up -d

# Ожидание
echo -e "${GREEN}✓${NC} Сервисы запущены!"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Установка завершена!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "📁 Проект: $INSTALL_DIR"
echo "🌐 UI:     http://localhost:3000"
echo "📚 API:    http://localhost:8000/docs"
echo ""
echo "Логи:"
echo "  cd $INSTALL_DIR && docker-compose -f docker/docker-compose.yml logs -f"
echo ""
