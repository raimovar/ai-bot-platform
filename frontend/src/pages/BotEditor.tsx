// Bot Editor Page

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Save, Play, Square } from 'lucide-react';
import api from '../api/client';
import Input from '../components/Input';
import Select from '../components/Select';
import Textarea from '../components/Textarea';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';
import type { Bot } from '../types';

// Provider and Model Configuration
// Comprehensive list inspired by Hermes Agent

export interface ModelOption {
  value: string;
  label: string;
  description?: string;
}

export interface ProviderOption {
  value: string;
  label: string;
  icon?: string;
  baseURL?: string;
  models: ModelOption[];
}

// Extended Provider List (inspired by Hermes)
export const PROVIDERS: ProviderOption[] = [
  // === OpenAI Compatible ===
  {
    value: 'openai',
    label: 'OpenAI',
    icon: '🤖',
    baseURL: 'https://api.openai.com/v1',
    models: [
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo', description: 'Most capable, fastest' },
      { value: 'gpt-4-turbo-2024-04-09', label: 'GPT-4 Turbo (Apr 2024)' },
      { value: 'gpt-4', label: 'GPT-4', description: 'Strong reasoning' },
      { value: 'gpt-4-32k', label: 'GPT-4 32K' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', description: 'Fast & affordable' },
    ],
  },
  {
    value: 'azure-openai',
    label: 'Azure OpenAI',
    icon: '☁️',
    models: [
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'gpt-4', label: 'GPT-4' },
      { value: 'gpt-35-turbo', label: 'GPT-3.5 Turbo' },
    ],
  },
  
  // === Anthropic ===
  {
    value: 'anthropic',
    label: 'Anthropic (Claude)',
    icon: '🧠',
    baseURL: 'https://api.anthropic.com/v1',
    models: [
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet', description: 'Best balance' },
      { value: 'claude-3-5-sonnet-latest', label: 'Claude 3.5 Sonnet (Latest)' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus', description: 'Most capable' },
      { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku', description: 'Fastest & cheapest' },
    ],
  },
  
  // === Google ===
  {
    value: 'google',
    label: 'Google (Gemini)',
    icon: '✨',
    baseURL: 'https://generativelanguage.googleapis.com/v1beta',
    models: [
      { value: 'gemini-2.0-flash-exp', label: 'Gemini 2.0 Flash', description: 'Fast & versatile' },
      { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
      { value: 'gemini-1.5-flash-8b', label: 'Gemini 1.5 Flash 8B', description: 'Ultra fast' },
      { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro', description: 'Large context' },
      { value: 'gemini-1.5-pro-latest', label: 'Gemini 1.5 Pro (Latest)' },
      { value: 'gemini-1.0-pro', label: 'Gemini 1.0 Pro' },
    ],
  },
  
  // === Mistral ===
  {
    value: 'mistral',
    label: 'Mistral AI',
    icon: '🌬️',
    baseURL: 'https://api.mistral.ai/v1',
    models: [
      { value: 'mistral-large-latest', label: 'Mistral Large', description: 'Flagship model' },
      { value: 'mistral-small-latest', label: 'Mistral Small', description: 'Fast & efficient' },
      { value: 'mistral-nemo', label: 'Mistral Nemo', description: 'Balanced performance' },
      { value: 'codestral', label: 'Codestral', description: 'Code-specialized' },
    ],
  },
  
  // === Cohere ===
  {
    value: 'cohere',
    label: 'Cohere',
    icon: '🌊',
    baseURL: 'https://api.cohere.ai/v1',
    models: [
      { value: 'command-r-plus', label: 'Command R+', description: 'Best for RAG' },
      { value: 'command-r', label: 'Command R' },
      { value: 'command', label: 'Command' },
    ],
  },
  
  // === Groq ===
  {
    value: 'groq',
    label: 'Groq',
    icon: '⚡',
    baseURL: 'https://api.groq.com/openai/v1',
    models: [
      { value: 'llama-3.1-70b-versatile', label: 'Llama 3.1 70B', description: 'Fast inference' },
      { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B', description: 'Very fast' },
      { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
    ],
  },
  
  // === Perplexity ===
  {
    value: 'perplexity',
    label: 'Perplexity',
    icon: '🔍',
    baseURL: 'https://api.perplexity.ai',
    models: [
      { value: 'llama-3.1-sonar-large-128k-online', label: 'Sonar Large Online', description: 'Web search' },
      { value: 'llama-3.1-sonar-huge-128k-online', label: 'Sonar Huge Online', description: 'Best web search' },
      { value: 'llama-3.1-sonar-large-128k', label: 'Sonar Large' },
      { value: 'llama-3.1-sonar-small-128k', label: 'Sonar Small' },
    ],
  },
  
  // === DeepSeek ===
  {
    value: 'deepseek',
    label: 'DeepSeek',
    icon: '🔭',
    baseURL: 'https://api.deepseek.com/v1',
    models: [
      { value: 'deepseek-chat', label: 'DeepSeek Chat', description: 'General purpose' },
      { value: 'deepseek-coder', label: 'DeepSeek Coder', description: 'Code-specialized' },
      { value: 'deepseek-reasoner', label: 'DeepSeek R1', description: 'Advanced reasoning' },
    ],
  },
  
  // === Local / Self-hosted ===
  {
    value: 'ollama',
    label: 'Ollama (Local)',
    icon: '🖥️',
    baseURL: 'http://localhost:11434/v1',
    models: [
      { value: 'llama3.2', label: 'Llama 3.2', description: 'Latest Llama' },
      { value: 'llama3.2:1b', label: 'Llama 3.2 1B', description: 'Lightweight' },
      { value: 'llama3.1', label: 'Llama 3.1' },
      { value: 'llama3', label: 'Llama 3' },
      { value: 'llama2', label: 'Llama 2' },
      { value: 'mistral', label: 'Mistral' },
      { value: 'mixtral', label: 'Mixtral' },
      { value: 'codellama', label: 'Code Llama' },
      { value: 'phi3', label: 'Phi-3' },
      { value: 'qwen2.5', label: 'Qwen 2.5' },
      { value: 'gemma2', label: 'Gemma 2' },
    ],
  },
  {
    value: 'lmstudio',
    label: 'LM Studio (Local)',
    icon: '📚',
    baseURL: 'http://localhost:1234/v1',
    models: [
      { value: 'local', label: 'Local Model (auto-detect)', description: 'Uses loaded model' },
    ],
  },
  {
    value: 'textgen-webui',
    label: 'textgen-webui (Local)',
    icon: '🎛️',
    baseURL: 'http://localhost:5000/v1',
    models: [
      { value: 'local', label: 'Local Model (auto-detect)' },
    ],
  },
  {
    value: 'aphrodite',
    label: 'Aphrodite (Local)',
    icon: '🏹',
    baseURL: 'http://localhost:22488/v1',
    models: [
      { value: 'local', label: 'Local Model (auto-detect)' },
    ],
  },
  
  // === OpenRouter (aggregates many providers) ===
  {
    value: 'openrouter',
    label: 'OpenRouter',
    icon: '🛣️',
    baseURL: 'https://openrouter.ai/api/v1',
    models: [
      { value: 'anthropic/claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' },
      { value: 'openai/gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'google/gemini-pro-1.5', label: 'Gemini Pro 1.5' },
      { value: 'anthropic/claude-3-haiku', label: 'Claude 3 Haiku' },
      { value: 'meta-llama/llama-3-8b-instruct', label: 'Llama 3 8B' },
      { value: 'mistralai/mistral-7b-instruct', label: 'Mistral 7B' },
    ],
  },
  
  // === Together AI ===
  {
    value: 'together',
    label: 'Together AI',
    icon: '🤝',
    baseURL: 'https://api.together.xyz/v1',
    models: [
      { value: 'meta-llama/Llama-3-70b-chat-hf', label: 'Llama 3 70B' },
      { value: 'meta-llama/Llama-3-8b-chat-hf', label: 'Llama 3 8B' },
      { value: 'mistralai/Mixtral-8x22B-Instruct-v0.1', label: 'Mixtral 8x22B' },
      { value: 'Qwen/Qwen2-72B-Instruct', label: 'Qwen 2 72B' },
    ],
  },
  
  // === Fireworks AI ===
  {
    value: 'fireworks',
    label: 'Fireworks AI',
    icon: '🎆',
    baseURL: 'https://api.fireworks.ai/inference/v1',
    models: [
      { value: 'accounts/fireworks/models/llama-v3p1-70b-instruct', label: 'Llama 3.1 70B' },
      { value: 'accounts/fireworks/models/llama-v3p1-8b-instruct', label: 'Llama 3.1 8B' },
      { value: 'accounts/fireworks/models/mixtral-8x22b-instruct', label: 'Mixtral 8x22B' },
    ],
  },
  
  // === Novita AI ===
  {
    value: 'novita',
    label: 'Novita AI',
    icon: '🌟',
    baseURL: 'https://api.novita.ai/v1',
    models: [
      { value: 'meta-llama/llama-3.1-70b-instruct', label: 'Llama 3.1 70B' },
      { value: 'meta-llama/llama-3.1-8b-instruct', label: 'Llama 3.1 8B' },
      { value: 'deepseek-ai/deepseek-v3', label: 'DeepSeek V3' },
      { value: 'deepseek-ai/deepseek-r1', label: 'DeepSeek R1' },
    ],
  },
  
  // === Hyperbolic ===
  {
    value: 'hyperbolic',
    label: 'Hyperbolic',
    icon: '🔗',
    baseURL: 'https://api.hyperbolic.xyz/v1',
    models: [
      { value: 'meta-llama/Llama-3.1-70B-Instruct', label: 'Llama 3.1 70B' },
      { value: 'meta-llama/Llama-3.1-8B-Instruct', label: 'Llama 3.1 8B' },
      { value: 'Qwen/Qwen2.5-72B-Instruct', label: 'Qwen 2.5 72B' },
    ],
  },
  
  // === Custom / Generic ===
  {
    value: 'custom',
    label: 'Custom Provider',
    icon: '⚙️',
    models: [
      { value: 'custom-model', label: 'Custom Model', description: 'Specify model name' },
    ],
  },
];

// Helper to get provider by value
export const getProvider = (value: string): ProviderOption | undefined => {
  return PROVIDERS.find(p => p.value === value);
};

// Helper to get models for provider
export const getModelsForProvider = (providerValue: string): ModelOption[] => {
  const provider = getProvider(providerValue);
  return provider?.models || [];
};

// Default presets for generation parameters
export const TEMPERATURE_PRESETS = [
  { value: 'auto', label: 'Auto', description: 'Use model defaults' },
  { value: '0.0', label: 'Precise (0.0)', description: 'Deterministic, factual' },
  { value: '0.3', label: 'Focused (0.3)', description: 'Balanced' },
  { value: '0.5', label: 'Balanced (0.5)', description: 'Creative yet focused' },
  { value: '0.7', label: 'Creative (0.7)', description: 'Default creative' },
  { value: '1.0', label: 'Creative+ (1.0)', description: 'Maximum creativity' },
  { value: '1.5', label: 'Wild (1.5)', description: 'High randomness' },
  { value: 'custom', label: 'Custom value', description: 'Enter specific value' },
];

export const MAX_TOKENS_PRESETS = [
  { value: 'auto', label: 'Auto', description: 'Use model defaults' },
  { value: '256', label: 'Short (256)', description: 'Brief responses' },
  { value: '512', label: 'Medium (512)', description: 'Standard response' },
  { value: '1024', label: 'Long (1024)', description: 'Detailed response' },
  { value: '2048', label: 'Extended (2048)', description: 'Long-form content' },
  { value: '4096', label: 'Full (4096)', description: 'Extended content' },
  { value: '8192', label: 'Max (8192)', description: 'Maximum length' },
  { value: 'custom', label: 'Custom value', description: 'Enter specific value' },
];

export const TOP_P_PRESETS = [
  { value: 'auto', label: 'Auto', description: 'Use model defaults' },
  { value: '0.0', label: 'Narrow (0.0)', description: 'Most deterministic' },
  { value: '0.5', label: 'Focused (0.5)', description: 'Focused sampling' },
  { value: '0.8', label: 'Balanced (0.8)', description: 'Good balance' },
  { value: '0.9', label: 'Diverse (0.9)', description: 'More diverse' },
  { value: '0.95', label: 'Diverse+ (0.95)', description: 'High diversity' },
  { value: '1.0', label: 'Full (1.0)', description: 'Sample from all' },
  { value: 'custom', label: 'Custom value', description: 'Enter specific value' },
];

const MEMORY_TYPES = [
  { value: 'none', label: 'No Memory' },
  { value: 'short_term', label: 'Short-term (Rolling window)' },
  { value: 'long_term', label: 'Long-term (Vector store)' },
  { value: 'hybrid', label: 'Hybrid (Both)' },
];

export default function BotEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id;

  // Fetch bot if editing
  const { data: bot, isLoading } = useQuery({
    queryKey: ['bot', id],
    queryFn: () => api.get(`/bots/${id}`).then((r) => r.data),
    enabled: !isNew,
  });

  // Form state
  const [form, setForm] = useState<Partial<Bot>>({
    name: '',
    slug: '',
    description: '',
    provider: 'openai',
    model_name: 'gpt-4-turbo-preview',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1,
    system_prompt: 'You are a helpful AI assistant.',
    memory_type: 'short_term',
    memory_config: { window_size: 10 },
    telegram_enabled: false,
  });

  // Extended form state for model config
  const [modelConfig, setModelConfig] = useState({
    temperature_preset: '0.7',
    temperature_custom: 0.7,
    max_tokens_preset: '2048',
    max_tokens_custom: 2048,
    top_p_preset: '1.0',
    top_p_custom: 1.0,
  });

  // Update form when bot loads
  useEffect(() => {
    if (bot && !isNew) {
      setForm({
        name: bot.name,
        slug: bot.slug,
        description: bot.description,
        provider: bot.provider,
        model_name: bot.model_name,
        temperature: bot.temperature,
        max_tokens: bot.max_tokens,
        top_p: bot.top_p,
        system_prompt: bot.system_prompt,
        memory_type: bot.memory_type,
        memory_config: bot.memory_config,
        telegram_enabled: bot.telegram_enabled,
      });
      // Parse existing values into presets
      const tempPreset = TEMPERATURE_PRESETS.find(p => p.value === String(bot.temperature));
      const tokensPreset = MAX_TOKENS_PRESETS.find(p => p.value === String(bot.max_tokens));
      const topPPreset = TOP_P_PRESETS.find(p => p.value === String(bot.top_p));
      setModelConfig({
        temperature_preset: tempPreset ? String(bot.temperature) : 'custom',
        temperature_custom: bot.temperature,
        max_tokens_preset: tokensPreset ? String(bot.max_tokens) : 'custom',
        max_tokens_custom: bot.max_tokens,
        top_p_preset: topPPreset ? String(bot.top_p) : 'custom',
        top_p_custom: bot.top_p,
      });
    }
  }, [bot, isNew]);

  // Get current provider info
  const availableModels = getModelsForProvider(form.provider || 'openai');

  // Mutations
  const createBot = useMutation({
    mutationFn: (data: any) => api.post('/bots', data),
    onSuccess: (response) => {
      toast.success('Bot created!');
      navigate(`/bots/${response.data.id}`);
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || 'Failed to create bot'),
  });

  const updateBot = useMutation({
    mutationFn: (data: any) => api.patch(`/bots/${id}`, data),
    onSuccess: () => {
      toast.success('Saved!');
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || 'Failed to save'),
  });

  const startBot = useMutation({
    mutationFn: () => api.post(`/bots/${id}/start`),
    onSuccess: () => toast.success('Bot started!'),
    onError: () => toast.error('Failed to start bot'),
  });

  const stopBot = useMutation({
    mutationFn: () => api.post(`/bots/${id}/stop`),
    onSuccess: () => toast.success('Bot stopped'),
    onError: () => toast.error('Failed to stop bot'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isNew) {
      createBot.mutate(form);
    } else {
      updateBot.mutate(form);
    }
  };

  const updateField = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  if (!isNew && isLoading) {
    return <LoadingSpinner />;
  }

  

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          to="/bots"
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isNew ? 'Create New Bot' : `Edit: ${bot?.name}`}
          </h1>
          <p className="text-gray-500">
            {isNew ? 'Configure your AI assistant' : 'Update bot settings'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Bot Name"
              value={form.name || ''}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="My Awesome Bot"
              required
            />
            <Input
              label="Slug (URL)"
              value={form.slug || ''}
              onChange={(e) => updateField('slug', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
              placeholder="my-awesome-bot"
              helper="Used in URLs and Telegram handle"
            />
            <div className="md:col-span-2">
              <Textarea
                label="Description"
                value={form.description || ''}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="What does this bot do?"
                rows={2}
              />
            </div>
          </div>
        </div>

// Model Configuration Section
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Model Configuration</h2>
          
          {/* Step 1: Provider Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Step 1: Select Provider
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
              {PROVIDERS.map((provider) => (
                <button
                  key={provider.value}
                  type="button"
                  onClick={() => {
                    updateField('provider', provider.value);
                    updateField('model_name', provider.models[0]?.value || '');
                  }}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    form.provider === provider.value
                      ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{provider.icon || '🔗'}</span>
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {provider.label}
                    </span>
                  </div>
                </button>
              ))}
            </div>
            {form.provider === 'custom' && (
              <div className="mt-3">
                <Input
                  label="Custom Base URL"
                  value={(form as any).config?.custom_base_url || ''}
                  onChange={(e) => updateField('config', { ...(form as any).config || {}, custom_base_url: e.target.value })}
                  placeholder="https://api.example.com/v1"
                />
              </div>
            )}
          </div>

          {/* Step 2: Model Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Step 2: Select Model
            </label>
            <div className="space-y-2 max-h-60 overflow-y-auto border border-gray-200 rounded-lg p-3">
              {availableModels.map((model) => (
                <label
                  key={model.value}
                  className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                    form.model_name === model.value
                      ? 'bg-blue-50 border border-blue-200'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="model_selection"
                    value={model.value}
                    checked={form.model_name === model.value}
                    onChange={(e) => updateField('model_name', e.target.value)}
                    className="mt-1"
                  />
                  <div>
                    <div className="font-medium text-gray-900">{model.label}</div>
                    {model.description && (
                      <div className="text-sm text-gray-500">{model.description}</div>
                    )}
                  </div>
                </label>
              ))}
            </div>
            {form.provider === 'custom' && (
              <div className="mt-3">
                <Input
                  label="Custom Model Name"
                  value={form.model_name === 'custom-model' ? '' : form.model_name || ''}
                  onChange={(e) => updateField('model_name', e.target.value)}
                  placeholder="e.g., gpt-4-turbo, claude-3-opus"
                />
              </div>
            )}
          </div>

          {/* Step 3: Generation Parameters with Presets */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Step 3: Generation Parameters
            </label>
            
            {/* Temperature */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Temperature <span className="text-gray-400">(creativity)</span>
                </label>
                <select
                  value={modelConfig.temperature_preset}
                  onChange={(e) => {
                    const val = e.target.value;
                    setModelConfig(prev => ({
                      ...prev,
                      temperature_preset: val,
                      temperature: val === 'auto' ? 0.7 : val === 'custom' ? prev.temperature_custom : parseFloat(val)
                    }));
                    if (val !== 'auto' && val !== 'custom') {
                      updateField('temperature', parseFloat(val));
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {TEMPERATURE_PRESETS.map(p => (
                    <option key={p.value} value={p.value}>
                      {p.label} {p.description ? `- ${p.description}` : ''}
                    </option>
                  ))}
                </select>
                {modelConfig.temperature_preset === 'custom' && (
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={modelConfig.temperature_custom}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setModelConfig(prev => ({ ...prev, temperature_custom: val }));
                      updateField('temperature', val);
                    }}
                    className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    placeholder="0.0 - 2.0"
                  />
                )}
              </div>

              {/* Max Tokens */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Max Tokens <span className="text-gray-400">(response length)</span>
                </label>
                <select
                  value={modelConfig.max_tokens_preset}
                  onChange={(e) => {
                    const val = e.target.value;
                    setModelConfig(prev => ({
                      ...prev,
                      max_tokens_preset: val,
                      max_tokens: val === 'auto' ? 2048 : val === 'custom' ? prev.max_tokens_custom : parseInt(val)
                    }));
                    if (val !== 'auto' && val !== 'custom') {
                      updateField('max_tokens', parseInt(val));
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {MAX_TOKENS_PRESETS.map(p => (
                    <option key={p.value} value={p.value}>
                      {p.label} {p.description ? `- ${p.description}` : ''}
                    </option>
                  ))}
                </select>
                {modelConfig.max_tokens_preset === 'custom' && (
                  <input
                    type="number"
                    min="1"
                    max="32000"
                    value={modelConfig.max_tokens_custom}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setModelConfig(prev => ({ ...prev, max_tokens_custom: val }));
                      updateField('max_tokens', val);
                    }}
                    className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    placeholder="1 - 32000"
                  />
                )}
              </div>

              {/* Top P */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Top P <span className="text-gray-400">(nucleus sampling)</span>
                </label>
                <select
                  value={modelConfig.top_p_preset}
                  onChange={(e) => {
                    const val = e.target.value;
                    setModelConfig(prev => ({
                      ...prev,
                      top_p_preset: val,
                      top_p: val === 'auto' ? 1.0 : val === 'custom' ? prev.top_p_custom : parseFloat(val)
                    }));
                    if (val !== 'auto' && val !== 'custom') {
                      updateField('top_p', parseFloat(val));
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {TOP_P_PRESETS.map(p => (
                    <option key={p.value} value={p.value}>
                      {p.label} {p.description ? `- ${p.description}` : ''}
                    </option>
                  ))}
                </select>
                {modelConfig.top_p_preset === 'custom' && (
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={modelConfig.top_p_custom}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setModelConfig(prev => ({ ...prev, top_p_custom: val }));
                      updateField('top_p', val);
                    }}
                    className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    placeholder="0.0 - 1.0"
                  />
                )}
              </div>
            </div>
            
            <p className="text-xs text-gray-400 mt-2">
              <strong>Tips:</strong> Temperature controls creativity (0=factual, 1=creative). 
              Max Tokens limits response length. Top P controls diversity of token selection.
            </p>
          </div>
        </div>

        {/* System Prompt */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">System Prompt</h2>
          <Textarea
            label=""
            value={form.system_prompt || ''}
            onChange={(e) => updateField('system_prompt', e.target.value)}
            placeholder="You are a helpful AI assistant..."
            rows={8}
            required
          />
          <p className="mt-2 text-sm text-gray-500">
            Define how your bot should behave. Be specific about its personality, knowledge, and capabilities.
          </p>
        </div>

        {/* Memory */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Memory Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Memory Type"
              value={form.memory_type || 'short_term'}
              onChange={(e) => updateField('memory_type', e.target.value)}
              options={MEMORY_TYPES}
            />
            {form.memory_type !== 'none' && (
              <Input
                label="Context Window"
                type="number"
                min="1"
                max="50"
                value={(form.memory_config as any)?.window_size || 10}
                onChange={(e) => updateField('memory_config', { 
                  ...form.memory_config, 
                  window_size: parseInt(e.target.value) 
                })}
                helper="Number of recent messages to remember"
              />
            )}
          </div>
        </div>

        {/* Telegram */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Telegram Integration</h2>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.telegram_enabled || false}
              onChange={(e) => updateField('telegram_enabled', e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-gray-700">Enable Telegram Bot</span>
          </label>
          {form.telegram_enabled && (
            <p className="mt-2 text-sm text-gray-500">
              Add your Telegram bot token in the bot settings after creation.
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4">
          <div className="flex gap-3">
            <Button type="submit" isLoading={createBot.isPending || updateBot.isPending}>
              <Save className="w-4 h-4" />
              {isNew ? 'Create Bot' : 'Save Changes'}
            </Button>
            {!isNew && (
              <>
                {bot?.status === 'running' ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => stopBot.mutate()}
                    isLoading={stopBot.isPending}
                  >
                    <Square className="w-4 h-4" />
                    Stop
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => startBot.mutate()}
                    isLoading={startBot.isPending}
                  >
                    <Play className="w-4 h-4" />
                    Start
                  </Button>
                )}
              </>
            )}
          </div>
          <Button
            type="button"
            variant="ghost"
            onClick={() => navigate('/bots')}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
