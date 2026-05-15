-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables (handled by SQLAlchemy, but useful for reference)
-- Users table
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Bots table
CREATE TABLE IF NOT EXISTS bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_public BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT false,
    
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    temperature DECIMAL(4,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2048,
    top_p DECIMAL(4,2),
    frequency_penalty DECIMAL(4,2),
    presence_penalty DECIMAL(4,2),
    
    system_prompt TEXT NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'short_term',
    memory_config JSONB DEFAULT '{}',
    tools_enabled BOOLEAN DEFAULT false,
    
    telegram_enabled BOOLEAN DEFAULT false,
    telegram_token VARCHAR(255),
    telegram_bot_name VARCHAR(100),
    telegram_allowed_chats TEXT[],
    
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),
    
    status VARCHAR(50) DEFAULT 'stopped',
    last_error TEXT,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    
    avatar_url VARCHAR(500),
    welcome_message TEXT,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_started TIMESTAMP
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    session_type VARCHAR(50) DEFAULT 'telegram',
    user_name VARCHAR(255),
    user_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    context_snapshot VARCHAR(10000),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    name VARCHAR(100),
    model VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms INTEGER,
    tool_calls JSONB,
    tool_result JSONB,
    source VARCHAR(50) DEFAULT 'telegram',
    metadata JSONB DEFAULT '{}',
    rating INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge sources
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(500),
    file_path VARCHAR(500),
    file_size INTEGER,
    mime_type VARCHAR(100),
    url VARCHAR(2000),
    status VARCHAR(50) DEFAULT 'pending',
    total_chunks INTEGER DEFAULT 0,
    indexed_chunks INTEGER DEFAULT 0,
    chunk_size INTEGER DEFAULT 500,
    chunk_overlap INTEGER DEFAULT 50,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    indexed_at TIMESTAMP
);

-- Knowledge chunks with vector embeddings
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding JSONB,
    vector_id VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bot tools
CREATE TABLE IF NOT EXISTS bot_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    tool_type VARCHAR(50) NOT NULL,
    config JSONB DEFAULT '{}',
    definition JSONB,
    is_enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(bot_id, tool_name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bots_slug ON bots(slug);
CREATE INDEX IF NOT EXISTS idx_bots_owner ON bots(owner_id);
CREATE INDEX IF NOT EXISTS idx_sessions_bot ON sessions(bot_id);
CREATE INDEX IF NOT EXISTS idx_sessions_external ON sessions(external_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source ON knowledge_chunks(source_id);

-- Create admin user (password: admin123)
INSERT INTO users (email, username, password_hash, role)
VALUES ('admin@example.com', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4bMxOVJLpS3MqJGe', 'admin')
ON CONFLICT (email) DO NOTHING;
