# 🤖 AI Bot Platform

Self-hosted platform for creating, managing, and deploying AI chatbots with Telegram integration, RAG knowledge bases, and multi-model support.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 🎨 **Web UI** - Create and manage bots with an intuitive interface
- 🤖 **Multiple AI Providers** - OpenAI GPT-4, Anthropic Claude, Ollama (local)
- 💬 **Telegram Integration** - Webhook-based bot communication
- 📚 **Knowledge Base** - RAG with document upload and semantic search
- 🧠 **Memory Management** - Short-term and long-term conversation memory
- 🔧 **Tools & Extensions** - HTTP requests, commands, custom functions
- 📊 **Analytics** - Message history, token usage, cost tracking
- 🔒 **Multi-tenant** - User management with RBAC
- 🐳 **Docker Ready** - One-command deployment

## 🚀 Quick Start

### One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/youruser/ai-bot-platform/master/install.sh | bash
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/youruser/ai-bot-platform.git
cd ai-bot-platform

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start with Docker
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000) and login with:
- **Email:** admin@example.com
- **Password:** admin123

## 📁 Project Structure

```
ai-bot-platform/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── integrations/  # Telegram, etc.
│   │   ├── ai_providers/  # LLM providers
│   │   ├── knowledge/     # RAG components
│   │   └── bot_runtime/   # Bot execution
│   └── requirements.txt
│
├── frontend/             # React SPA
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/         # App pages
│   │   ├── stores/        # Zustand stores
│   │   └── api/           # API client
│   └── package.json
│
├── docker/               # Docker configurations
│   ├── docker-compose.yml
│   └── infra/           # Service configs
│
├── ai-gateway/          # Unified LLM interface
├── bot-runtime/         # Bot execution engine
└── install.sh           # Installation script
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                         │
│                     (localhost:3000)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST / WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Traefik)                     │
│                     (localhost:80)                          │
└──┬──────────────────┬──────────────────┬────────────────────┘
   │                  │                  │
   ▼                  ▼                  ▼
┌──────────┐   ┌────────────┐   ┌────────────┐
│ Backend  │   │ Bot Runtime│   │ AI Gateway │
│ FastAPI  │   │  Engine    │   │            │
│  :8000   │   │   :8001    │   │   :8002    │
└────┬─────┘   └─────┬──────┘   └─────┬──────┘
     │               │                 │
     └───────────────┼─────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────────┐
│PostgreSQL│   │  Redis   │   │  Vector DB   │
│ pgvector │   │ Sessions │   │ Qdrant/pgvec │
└──────────┘   └──────────┘   └──────────────┘
```

## 🤖 Creating a Bot

1. **Dashboard** → Click "Create Bot"
2. **Configure:**
   - Name and description
   - Choose AI provider (OpenAI, Anthropic, Ollama)
   - Select model
   - Write system prompt
   - Set temperature, max tokens
3. **Add Knowledge (optional):**
   - Upload PDF, TXT, or MD files
   - Add URLs to scrape
   - Paste text directly
4. **Connect Telegram (optional):**
   - Add bot token from @BotFather
   - Set webhook URL
5. **Start the bot!**

## 📚 Knowledge Base

Upload documents and let your bot use RAG to answer questions about them.

### Supported Formats
- PDF files
- Plain text (.txt)
- Markdown (.md)
- HTML files
- URLs (web scraping)

### How It Works
1. Documents are chunked into segments
2. Each chunk is embedded (OpenAI, Ollama, or HuggingFace)
3. On query, relevant chunks are retrieved via vector search
4. Context is injected into the prompt

## 🔌 Telegram Integration

### Setup
1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your bot token
3. Add token to bot configuration in UI
4. Set webhook URL to your server

### Webhook Configuration
```bash
# Your domain should point to:
https://your-domain.com/api/v1/webhook/bot/{token}

# Or use ngrok for local development:
ngrok http 80
```

### Bot Commands
- `/start` - Start conversation
- `/help` - Show help
- `/reset` - Reset conversation memory
- `/stats` - Show bot statistics

## 🧠 Memory Types

| Type | Description |
|------|-------------|
| `none` | No memory, each conversation is fresh |
| `short_term` | Rolling window of recent messages |
| `long_term` | Vector-based semantic memory |
| `hybrid` | Combines short and long term |

## 🔧 Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/aibotdb

# Redis
REDIS_URL=redis://:password@redis:6379/0

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://ollama:11434

# Storage
STORAGE_URL=http://minio:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin

# Security
SECRET_KEY=your-secret-key-here
TELEGRAM_WEBHOOK_SECRET=your-secret

# CORS
CORS_ORIGINS=http://localhost:3000
```

### Docker Profiles

```bash
# Basic services only
docker compose up -d

# With local LLM (Ollama)
docker compose --profile local-llm up -d

# With vector database (Qdrant)
docker compose --profile vector up -d

# All services
docker compose --profile local-llm --profile vector up -d
```

## 📡 API Reference

### Bots
- `GET /api/v1/bots` - List bots
- `POST /api/v1/bots` - Create bot
- `GET /api/v1/bots/{id}` - Get bot
- `PUT /api/v1/bots/{id}` - Update bot
- `DELETE /api/v1/bots/{id}` - Delete bot
- `POST /api/v1/bots/{id}/start` - Start bot
- `POST /api/v1/bots/{id}/stop` - Stop bot

### Sessions & Messages
- `GET /api/v1/sessions` - List sessions
- `GET /api/v1/sessions/{id}/messages` - Get messages
- `POST /api/v1/sessions/{id}/messages` - Send message

### Knowledge
- `GET /api/v1/knowledge/bots/{id}/sources` - List sources
- `POST /api/v1/knowledge/bots/{id}/sources` - Add source
- `POST /api/v1/knowledge/bots/{id}/search` - Search knowledge
- `DELETE /api/v1/knowledge/bots/{id}/sources/{sid}` - Delete source

### Telegram
- `POST /api/v1/telegram/bots/{id}/connect` - Connect bot
- `POST /api/v1/telegram/bots/{id}/webhook/set` - Set webhook
- `GET /api/v1/telegram/bots/{id}/webhook/info` - Webhook status

## 🛠️ Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
cd backend
pytest tests/ -v
```

## 📊 Monitoring

### Health Checks
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Logs
```bash
docker compose logs -f backend
docker compose logs -f bot-runtime
docker compose logs -f ai-gateway
```

## 🔒 Security

- JWT authentication with refresh tokens
- Role-based access control (Admin, User, Viewer)
- Secrets stored in environment variables
- Telegram webhook verification
- Rate limiting on API endpoints

## 🚢 Deployment

### Production Checklist

1. [ ] Change all default passwords
2. [ ] Set up SSL/TLS (Traefik handles this)
3. [ ] Configure firewall (only 80, 443)
4. [ ] Set up backups for PostgreSQL
5. [ ] Configure monitoring (Prometheus, Grafana)
6. [ ] Set up log aggregation
7. [ ] Configure CDN for static assets

### Recommended Specs
- **CPU:** 4+ cores
- **RAM:** 8+ GB (16 GB for local LLMs)
- **Storage:** 50+ GB SSD
- **GPU:** Optional (for local LLM inference)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library
- [Telegram Bot API](https://core.telegram.org/bots/api) - Bot platform
- [pgvector](https://github.com/pgvector/pgvector) - Vector search in PostgreSQL
