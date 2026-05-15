# AI Bot Platform

Self-hosted платформа для создания и управления AI-ботами.

## Возможности

- 🤖 Создание AI-ботов через веб-интерфейс
- 💬 Telegram интеграция
- 🧠 Поддержка памяти (short-term, long-term)
- 🔧 Инструменты и расширения (HTTP, команды)
- 📚 Knowledge Base с RAG
- 🗄️ PostgreSQL + Redis + Vector DB
- 🐳 Полный Docker-стек

## Быстрый старт

```bash
# Установка (один curl)
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/ai-bot-platform/main/scripts/install.sh | bash

# Или клонирование
git clone https://github.com/YOUR_USER/ai-bot-platform.git
cd ai-bot-platform
cp docker/.env.example docker/.env
# Отредактируйте .env
docker-compose up -d
```

## Структура проекта

```
ai-bot-platform/
├── backend/          # FastAPI API
├── bot-runtime/      # Engine исполнения ботов
├── ai-gateway/       # Unified LLM interface
├── frontend/         # React SPA
├── infra/           # Docker configs
└── scripts/         # Установочные скрипты
```

## API Endpoints

- `POST /api/v1/users/auth/login` - Авторизация
- `GET/POST /api/v1/bots` - CRUD ботов
- `POST /api/v1/bots/:id/start` - Запуск бота
- `POST /api/v1/sessions/chat` - Отправка сообщения
- `POST /api/v1/webhooks/telegram/:id` - Telegram webhook

## Переменные окружения

См. `docker/.env.example`

## Разработка

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Лицензия

MIT
