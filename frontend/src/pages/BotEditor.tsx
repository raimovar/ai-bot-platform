// Bot Editor Page

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Save, Play, Square, Plus, Trash2 } from 'lucide-react';
import api from '../api/client';
import Input from '../components/Input';
import Select from '../components/Select';
import Textarea from '../components/Textarea';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';
import type { Bot } from '../types';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'ollama', label: 'Ollama (Local)' },
  { value: 'lmstudio', label: 'LM Studio' },
];

const MODELS: Record<string, { value: string; label: string }[]> = {
  openai: [
    { value: 'gpt-4-turbo-preview', label: 'GPT-4 Turbo' },
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  ],
  anthropic: [
    { value: 'claude-3-opus', label: 'Claude 3 Opus' },
    { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
    { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
  ],
  ollama: [
    { value: 'llama2', label: 'Llama 2' },
    { value: 'mistral', label: 'Mistral' },
    { value: 'codellama', label: 'Code Llama' },
  ],
  lmstudio: [
    { value: 'local', label: 'Local Model' },
  ],
};

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
    }
  }, [bot, isNew]);

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

  const availableModels = MODELS[form.provider || 'openai'] || MODELS.openai;

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

        {/* Model Configuration */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Model Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Provider"
              value={form.provider || 'openai'}
              onChange={(e) => {
                updateField('provider', e.target.value);
                updateField('model_name', MODELS[e.target.value]?.[0]?.value || '');
              }}
              options={PROVIDERS}
            />
            <Select
              label="Model"
              value={form.model_name || ''}
              onChange={(e) => updateField('model_name', e.target.value)}
              options={availableModels}
            />
            <Input
              label="Temperature"
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={form.temperature || 0.7}
              onChange={(e) => updateField('temperature', parseFloat(e.target.value))}
              helper="Lower = more focused, Higher = more creative"
            />
            <Input
              label="Max Tokens"
              type="number"
              min="1"
              max="32000"
              value={form.max_tokens || 2048}
              onChange={(e) => updateField('max_tokens', parseInt(e.target.value))}
            />
            <Input
              label="Top P"
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={form.top_p || 1}
              onChange={(e) => updateField('top_p', parseFloat(e.target.value))}
            />
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
