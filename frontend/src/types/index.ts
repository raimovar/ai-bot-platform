// TypeScript types for the application

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  role: 'admin' | 'user' | 'viewer';
  is_active: boolean;
  max_bots: number;
  telegram_id?: string;
  created_at: string;
  last_login?: string;
}

export interface Bot {
  id: string;
  name: string;
  slug: string;
  description?: string;
  owner_id: string;
  is_public: boolean;
  is_active: boolean;
  
  // Model
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  
  // Prompt
  system_prompt: string;
  
  // Memory
  memory_type: string;
  memory_config: Record<string, any>;
  
  // Tools
  tools_enabled: boolean;
  tools: BotTool[];
  
  // Telegram
  telegram_enabled: boolean;
  telegram_bot_name?: string;
  
  // Status
  status: 'stopped' | 'starting' | 'running' | 'error';
  last_error?: string;
  total_messages: number;
  total_tokens_used: number;
  
  // Branding
  avatar_url?: string;
  welcome_message?: string;
  
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_started?: string;
}

export interface BotTool {
  id: string;
  tool_name: string;
  tool_type: string;
  config: Record<string, any>;
  definition?: Record<string, any>;
  is_enabled: boolean;
  priority: number;
}

export interface Session {
  id: string;
  bot_id: string;
  external_id?: string;
  session_type: string;
  user_name?: string;
  user_id?: string;
  is_active: boolean;
  message_count: number;
  total_tokens: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_message_at?: string;
  recent_messages: Message[];
}

export interface Message {
  id: string;
  session_id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  name?: string;
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  latency_ms?: number;
  tool_calls?: ToolCall[];
  tool_result?: Record<string, any>;
  source: string;
  metadata: Record<string, any>;
  rating?: number;
  created_at: string;
}

export interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

export interface KnowledgeSource {
  id: string;
  bot_id: string;
  name: string;
  description?: string;
  source_type: 'file' | 'url' | 'text' | 'api';
  file_name?: string;
  file_size?: number;
  mime_type?: string;
  url?: string;
  status: 'pending' | 'downloading' | 'parsing' | 'indexing' | 'ready' | 'error';
  total_chunks: number;
  indexed_chunks: number;
  error_message?: string;
  metadata: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  indexed_at?: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  response: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
  session: Session;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
}
