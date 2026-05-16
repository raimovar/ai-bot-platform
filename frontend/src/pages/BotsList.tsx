// Bots List Page

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Bot as BotIcon } from 'lucide-react';
import api from '../api/client';
import BotCard from '../components/BotCard';
import EmptyState from '../components/EmptyState';
import LoadingSpinner from '../components/LoadingSpinner';
import ConfirmDialog from '../components/ConfirmDialog';
import toast from 'react-hot-toast';

export default function BotsList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch bots
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['bots'],
    queryFn: () => api.get('/bots/').then((r) => r.data),
  });

  // Mutations
  const startBot = useMutation({
    mutationFn: (id: string) => api.post(`/bots/${id}/start`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] });
      toast.success('Bot started');
    },
    onError: () => toast.error('Failed to start bot'),
  });

  const stopBot = useMutation({
    mutationFn: (id: string) => api.post(`/bots/${id}/stop`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] });
      toast.success('Bot stopped');
    },
    onError: () => toast.error('Failed to stop bot'),
  });

  const deleteBot = useMutation({
    mutationFn: (id: string) => api.delete(`/bots/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] });
      setDeleteId(null);
      toast.success('Bot deleted');
    },
    onError: () => toast.error('Failed to delete bot'),
  });

  // Filter bots by search
  const filteredBots = data?.items?.filter((bot: any) => 
    bot.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    bot.model_name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // Stats
  const stats = {
    total: data?.total || 0,
    running: data?.items?.filter((b: any) => b.status === 'running').length || 0,
    stopped: data?.items?.filter((b: any) => b.status === 'stopped').length || 0,
  };

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error loading bots</p>
        <button onClick={() => refetch()} className="text-blue-600 hover:underline mt-2">
          Try again
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Bots</h1>
          <p className="text-gray-500 mt-1">
            Create and manage your AI assistants
          </p>
        </div>
        <Link
          to="/bots/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Bot
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
          <div className="text-sm text-gray-500">Total Bots</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-green-600">{stats.running}</div>
          <div className="text-sm text-gray-500">Running</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-600">{stats.stopped}</div>
          <div className="text-sm text-gray-500">Stopped</div>
        </div>
      </div>

      {/* Search */}
      {data?.total > 0 && (
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search bots..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>
      )}

      {/* Bots Grid */}
      {isLoading ? (
        <LoadingSpinner />
      ) : filteredBots.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredBots.map((bot: any) => (
            <BotCard
              key={bot.id}
              bot={bot}
              onStart={(id) => startBot.mutate(id)}
              onStop={(id) => stopBot.mutate(id)}
              onDelete={(id) => setDeleteId(id)}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<BotIcon className="w-8 h-8" />}
          title={searchQuery ? 'No bots found' : 'No bots yet'}
          description={
            searchQuery 
              ? 'Try a different search term'
              : 'Create your first AI bot to get started'
          }
          action={
            !searchQuery
              ? {
                  label: 'Create Bot',
                  onClick: () => navigate('/bots/new'),
                }
              : undefined
          }
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={() => deleteId && deleteBot.mutate(deleteId)}
        title="Delete Bot"
        message="Are you sure you want to delete this bot? This action cannot be undone and all associated data will be permanently removed."
        confirmText="Delete"
        variant="danger"
        isLoading={deleteBot.isPending}
      />
    </div>
  );
}
