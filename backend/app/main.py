"""
AI Bot Platform - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1 import bots, sessions, messages, knowledge, users, webhooks, provider_keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Universal AI Bot Platform API
    
    Features:
    - Bot creation and management
    - Multi-model support (OpenAI, Anthropic, Ollama, etc.)
    - Telegram integration
    - Knowledge base with RAG
    - Session management
    - Role-based access control
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log format: method path status time
    print(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {process_time:.3f}s"
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint."""
    # Could add database/redis checks here
    return {"ready": True}


# ─────────────────────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────────────────────

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    print(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ─────────────────────────────────────────────────────────────
# API Routers
# ─────────────────────────────────────────────────────────────

# Users & Auth
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["users"]
)

# Provider Keys
app.include_router(
    provider_keys.router,
    prefix="/api/v1/users/provider-keys",
    tags=["provider-keys"]
)

# Bots
app.include_router(
    bots.router,
    prefix="/api/v1/bots",
    tags=["bots"]
)

# Sessions
app.include_router(
    sessions.router,
    prefix="/api/v1/sessions",
    tags=["sessions"]
)

# Messages
app.include_router(
    messages.router,
    prefix="/api/v1/messages",
    tags=["messages"]
)

# Knowledge Base
app.include_router(
    knowledge.router,
    prefix="/api/v1/knowledge",
    tags=["knowledge"]
)

# Webhooks (Telegram, etc.)
app.include_router(
    webhooks.router,
    prefix="/api/v1/webhooks",
    tags=["webhooks"]
)


# ─────────────────────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
