// Settings Page

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Save, Key, Bell, Shield, Palette, Plus, Trash2, Eye, EyeOff, Copy, Check } from 'lucide-react';
import api from '../api/client';
import { useAuthStore } from '../stores/authStore';
import Input from '../components/Input';
import Button from '../components/Button';
import toast from 'react-hot-toast';
import { PROVIDERS } from './BotEditor';

export default function Settings() {
  useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-1">
            {[
              { id: 'profile', label: 'Profile', icon: Palette },
              { id: 'api', label: 'API Keys', icon: Key },
              { id: 'security', label: 'Security', icon: Shield },
              { id: 'notifications', label: 'Notifications', icon: Bell },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && <ProfileSettings />}
          {activeTab === 'api' && <ApiKeysSettings />}
          {activeTab === 'security' && <SecuritySettings />}
          {activeTab === 'notifications' && <NotificationSettings />}
        </div>
      </div>
    </div>
  );
}

function ProfileSettings() {
  const { user, updateUser } = useAuthStore();
  const [form, setForm] = useState({
    username: user?.username || '',
    email: user?.email || '',
    full_name: user?.full_name || '',
  });

  const updateProfile = useMutation({
    mutationFn: (data: any) => api.patch('/users/auth/me', data),
    onSuccess: (response) => {
      updateUser(response.data);
      toast.success('Profile updated!');
    },
    onError: () => toast.error('Failed to update profile'),
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Profile Settings</h2>
      
      <div className="space-y-4">
        <Input
          label="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
        <Input
          label="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <Input
          label="Full Name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
        />
        
        <Button 
          onClick={() => updateProfile.mutate(form)}
          isLoading={updateProfile.isPending}
        >
          <Save className="w-4 h-4" />
          Save Changes
        </Button>
      </div>
    </div>
  );
}

function SecuritySettings() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const changePassword = useMutation({
    mutationFn: (data: any) => api.post('/users/auth/change-password', data),
    onSuccess: () => {
      toast.success('Password changed!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    },
    onError: () => toast.error('Failed to change password'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    changePassword.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Change Password</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Current Password"
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
        />
        <Input
          label="New Password"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          minLength={8}
        />
        <Input
          label="Confirm New Password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />
        
        <Button 
          type="submit"
          isLoading={changePassword.isPending}
        >
          <Shield className="w-4 h-4" />
          Change Password
        </Button>
      </form>
    </div>
  );
}

function ApiKeysSettings() {
  // Fetch user's provider API keys
  const { data: keysData, isLoading, refetch } = useQuery({
    queryKey: ['provider-keys'],
    queryFn: () => api.get('/users/provider-keys/').then(r => r.data),
  });

  const [form, setForm] = useState({
    provider: 'openai',
    api_key: '',
    base_url: '',
    label: '',
  });
  const [showKey, setShowKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const addKey = useMutation({
    mutationFn: (data: any) => api.post('/users/provider-keys/', data),
    onSuccess: () => {
      toast.success('API key added!');
      setForm({ provider: 'openai', api_key: '', base_url: '', label: '' });
      refetch();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to add key'),
  });

  const deleteKey = useMutation({
    mutationFn: (id: string) => api.delete(`/users/provider-keys/${id}`),
    onSuccess: () => {
      toast.success('API key deleted');
      refetch();
    },
    onError: () => toast.error('Failed to delete key'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.api_key.trim()) {
      toast.error('API key is required');
      return;
    }
    addKey.mutate({
      provider: form.provider,
      api_key: form.api_key,
      base_url: form.base_url || undefined,
      label: form.label || undefined,
    });
  };

  const selectedProvider = PROVIDERS.find(p => p.value === form.provider);
  const needsBaseUrl = ['ollama', 'lmstudio', 'textgen-webui', 'aphrodite', 'custom'].includes(form.provider);
  const isLocal = ['ollama', 'lmstudio', 'textgen-webui', 'aphrodite'].includes(form.provider);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(text);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Add New API Key */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Add Provider API Key</h2>
        <p className="text-gray-500 text-sm mb-4">
          Store your API keys securely. Keys are encrypted and only used when running bots.
        </p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Provider</label>
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
              {PROVIDERS.filter(p => p.value !== 'custom' || true).map((provider) => (
                <button
                  key={provider.value}
                  type="button"
                  onClick={() => setForm(f => ({ ...f, provider: provider.value, base_url: provider.baseURL || '' }))}
                  className={`p-2 rounded-lg border text-xs text-center transition-all ${
                    form.provider === provider.value
                      ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-base">{provider.icon}</div>
                  <div className="truncate mt-1">{provider.label.split(' ')[0]}</div>
                </button>
              ))}
            </div>
          </div>

          {/* API Key Input */}
          <div>
            <Input
              label="API Key"
              type="password"
              value={form.api_key}
              onChange={(e) => setForm(f => ({ ...f, api_key: e.target.value }))}
              placeholder={isLocal ? "Leave empty for local connection" : "sk-..."}
              required={!isLocal}
            />
          </div>

          {/* Base URL (for local/custom providers) */}
          {needsBaseUrl && (
            <div>
              <Input
                label={isLocal ? "Base URL (leave default for local)" : "Custom Base URL"}
                type="text"
                value={form.base_url}
                onChange={(e) => setForm(f => ({ ...f, base_url: e.target.value }))}
                placeholder={selectedProvider?.baseURL || 'https://api.example.com/v1'}
              />
            </div>
          )}

          {/* Optional Label */}
          <div>
            <Input
              label="Label (optional)"
              type="text"
              value={form.label}
              onChange={(e) => setForm(f => ({ ...f, label: e.target.value }))}
              placeholder="e.g., Production, Development, My Key"
            />
          </div>

          <Button type="submit" isLoading={addKey.isPending}>
            <Plus className="w-4 h-4" />
            Add API Key
          </Button>
        </form>
      </div>

      {/* Existing Keys */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Your API Keys</h2>
        
        {isLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : !keysData?.items?.length ? (
          <p className="text-gray-500 text-sm">No API keys added yet. Add one above to get started.</p>
        ) : (
          <div className="space-y-3">
            {keysData.items.map((key: any) => {
              const provider = PROVIDERS.find(p => p.value === key.provider);
              const maskedKey = key.api_key ? `${key.api_key.slice(0, 8)}${'•'.repeat(Math.max(0, key.api_key.length - 12))}${key.api_key.slice(-4)}` : '••••••••';
              
              return (
                <div key={key.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{provider?.icon || '🔑'}</span>
                    <div>
                      <div className="font-medium text-gray-900">
                        {provider?.label || key.provider}
                      </div>
                      <div className="text-sm text-gray-500 font-mono">
                        {showKey === key.id ? key.api_key : maskedKey}
                      </div>
                      {key.label && (
                        <div className="text-xs text-gray-400">{key.label}</div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowKey(showKey === key.id ? null : key.id)}
                      className="p-2 text-gray-400 hover:text-gray-600"
                      title={showKey === key.id ? 'Hide' : 'Show'}
                    >
                      {showKey === key.id ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => copyToClipboard(key.api_key)}
                      className="p-2 text-gray-400 hover:text-gray-600"
                      title="Copy"
                    >
                      {copiedKey === key.id ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => deleteKey.mutate(key.id)}
                      className="p-2 text-gray-400 hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function NotificationSettings() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Notification Preferences</h2>
      <p className="text-gray-500">
        Configure how you receive notifications.
      </p>
    </div>
  );
}
