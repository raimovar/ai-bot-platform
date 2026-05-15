-- ═══════════════════════════════════════════════════════════════════════════════
-- AI Bot Platform - PostgreSQL Schema
-- Version: 1.0.0
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ═══════════════════════════════════════════════════════════════════════════════
-- ENUMS
-- ═══════════════════════════════════════════════════════════════════════════════

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'user', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE bot_status AS ENUM ('stopped', 'starting', 'running', 'error');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE memory_type AS ENUM ('none', 'short_term', 'long_term', 'hybrid');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE knowledge_status AS ENUM ('pending', 'downloading', 'parsing', 'indexing', 'ready', 'error');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE message_role AS ENUM ('system', 'user', 'assistant', 'tool');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- Users
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    max_bots INTEGER DEFAULT 10,
    telegram_id VARCHAR(100),
    avatar_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ─────────────────────────────────────────────────────────────────────────────
-- Bots
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_public BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT false,
    
    -- Model
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    
    -- Generation Parameters
    temperature DECIMAL(4,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2048,
    top_p DECIMAL(4,2),
    frequency_penalty DECIMAL(4,2),
    presence_penalty DECIMAL(4,2),
    
    -- Prompt
    system_prompt TEXT NOT NULL,
    
    -- Memory
    memory_type VARCHAR(50) DEFAULT 'short_term',
    memory_config JSONB DEFAULT '{}',
    tools_enabled BOOLEAN DEFAULT false,
    
    -- Telegram
    telegram_enabled BOOLEAN DEFAULT false,
    telegram_token VARCHAR(255),
    telegram_bot_name VARCHAR(100),
    telegram_allowed_chats TEXT[],
    
    -- Webhook
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'stopped',
    last_error TEXT,
    
    -- Statistics
    total_messages INTEGER DEFAULT 0,
    total_tokens_used BIGINT DEFAULT 0,
    total_cost DECIMAL(12,2) DEFAULT 0,
    
    -- Branding
    avatar_url VARCHAR(500),
    welcome_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_started TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_bots_slug ON bots(slug);
CREATE INDEX IF NOT EXISTS idx_bots_owner ON bots(owner_id);
CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status);
CREATE INDEX IF NOT EXISTS idx_bots_provider ON bots(provider);
CREATE INDEX IF NOT EXISTS idx_bots_created ON bots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bots_search ON bots USING gin(name gin_trgm_ops);

-- ─────────────────────────────────────────────────────────────────────────────
-- Bot Tools
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    tool_type VARCHAR(50) NOT NULL,
    config JSONB DEFAULT '{}',
    definition JSONB,
    is_enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(bot_id, tool_name)
);

CREATE INDEX IF NOT EXISTS idx_bot_tools_bot ON bot_tools(bot_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sessions
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    session_type VARCHAR(50) DEFAULT 'telegram',
    
    -- User info
    user_name VARCHAR(255),
    user_id VARCHAR(255),
    user_email VARCHAR(255),
    user_telegram_id VARCHAR(100),
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_starred BOOLEAN DEFAULT false,
    
    -- Statistics
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    -- Context
    context_snapshot TEXT,
    last_context_update TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_sessions_bot ON sessions(bot_id);
CREATE INDEX IF NOT EXISTS idx_sessions_external ON sessions(external_id) WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active, last_message_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_sessions_bot_active ON sessions(bot_id, is_active) WHERE is_active = true;

-- ─────────────────────────────────────────────────────────────────────────────
-- Messages
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    name VARCHAR(100),
    
    -- Model info
    model VARCHAR(100),
    provider VARCHAR(50),
    
    -- Token usage
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER GENERATED ALWAYS AS (COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) STORED,
    estimated_cost DECIMAL(10,6),
    
    -- Performance
    latency_ms INTEGER,
    first_token_ms INTEGER,
    
    -- Tool calls
    tool_calls JSONB,
    tool_result JSONB,
    
    -- Source
    source VARCHAR(50) DEFAULT 'telegram',
    
    -- Feedback
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    rating_reason TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_rating ON messages(rating) WHERE rating IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- Knowledge Sources
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    source_type VARCHAR(50) NOT NULL,
    
    -- File info
    file_name VARCHAR(500),
    file_path VARCHAR(1000),
    file_size BIGINT,
    mime_type VARCHAR(100),
    
    -- URL
    url VARCHAR(2000),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    -- Progress
    total_chunks INTEGER DEFAULT 0,
    indexed_chunks INTEGER DEFAULT 0,
    
    -- Configuration
    chunk_size INTEGER DEFAULT 500,
    chunk_overlap INTEGER DEFAULT 50,
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    
    -- Access
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    indexed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_bot ON knowledge_sources(bot_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_status ON knowledge_sources(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_created ON knowledge_sources(created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Knowledge Chunks (with vector embeddings)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Embeddings
    embedding VECTOR(1536),
    vector_id VARCHAR(100),
    
    -- Stats
    token_count INTEGER,
    char_count INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source ON knowledge_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_token_count ON knowledge_chunks(token_count) WHERE token_count IS NOT NULL;

-- Vector similarity search index (1536 dims for ada-002)
-- Uncomment for production with proper embedding dimensions:
-- CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding ON knowledge_chunks 
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─────────────────────────────────────────────────────────────────────────────
-- API Keys (for external access)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    
    permissions JSONB DEFAULT '["read"]',
    rate_limit INTEGER DEFAULT 60,
    
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- ═══════════════════════════════════════════════════════════════════════════════
-- FUNCTIONS & TRIGGERS
-- ═══════════════════════════════════════════════════════════════════════════════

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER bots_updated_at BEFORE UPDATE ON bots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER knowledge_sources_updated_at BEFORE UPDATE ON knowledge_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update message_count and total_tokens on sessions
CREATE OR REPLACE FUNCTION update_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE sessions 
        SET message_count = message_count + 1,
            total_tokens = total_tokens + COALESCE(NEW.total_tokens, 0),
            last_message_at = NOW()
        WHERE id = NEW.session_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE sessions 
        SET message_count = message_count - 1,
            total_tokens = total_tokens - COALESCE(OLD.total_tokens, 0)
        WHERE id = OLD.session_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_session_stats
    AFTER INSERT OR DELETE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_session_stats();

-- Update bot total_messages and total_tokens
CREATE OR REPLACE FUNCTION update_bot_stats()
RETURNS TRIGGER AS $$
DECLARE
    v_bot_id UUID;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_bot_id := (SELECT bot_id FROM sessions WHERE id = NEW.session_id);
        UPDATE bots 
        SET total_messages = total_messages + 1,
            total_tokens_used = total_tokens_used + COALESCE(NEW.total_tokens, 0)
        WHERE id = v_bot_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_bot_stats
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION update_bot_stats();

-- Soft delete bots
CREATE OR REPLACE FUNCTION soft_delete_bot()
RETURNS TRIGGER AS $$
BEGIN
    NEW.deleted_at = NOW();
    NEW.is_active = false;
    NEW.status = 'stopped';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════════
-- SEED DATA
-- ═══════════════════════════════════════════════════════════════════════════════

-- Create default admin user (password: admin123)
-- Hash generated with: bcrypt.hashpw(b'admin123', bcrypt.gensalt())
INSERT INTO users (email, username, password_hash, role, full_name)
VALUES (
    'admin@example.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4bMxOVJLpS3MqJGe',
    'admin',
    'System Administrator'
) ON CONFLICT (email) DO NOTHING;

-- Create sample bot templates
INSERT INTO bots (name, slug, owner_id, provider, model_name, system_prompt, description)
SELECT 
    'Assistant',
    'assistant',
    id,
    'openai',
    'gpt-4',
    'You are a helpful, friendly, and knowledgeable AI assistant. Provide accurate and concise responses.',
    'Default AI assistant bot'
FROM users WHERE email = 'admin@example.com'
ON CONFLICT (slug) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aibot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aibot;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO aibot;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO aibot;

-- Grant to public for extensions
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;

-- ═══════════════════════════════════════════════════════════════════════════════
-- COMMENTS
-- ═══════════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE users IS 'Platform users with RBAC';
COMMENT ON TABLE bots IS 'AI bot configurations';
COMMENT ON TABLE bot_tools IS 'Bot extensions and integrations';
COMMENT ON TABLE sessions IS 'Chat sessions/threads';
COMMENT ON TABLE messages IS 'Individual chat messages';
COMMENT ON TABLE knowledge_sources IS 'Knowledge base sources (files, URLs)';
COMMENT ON TABLE knowledge_chunks IS 'Indexed content chunks with embeddings';
COMMENT ON TABLE api_keys IS 'External API access keys';

COMMENT ON COLUMN bots.system_prompt IS 'Main system prompt for the bot';
COMMENT ON COLUMN bots.memory_type IS 'Memory strategy: none, short_term, long_term, hybrid';
COMMENT ON COLUMN messages.embedding IS 'Vector embedding for semantic search';
