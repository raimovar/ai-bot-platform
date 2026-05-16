// Dashboard Page

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Bot, MessageSquare, Zap, Clock, TrendingUp, Plus } from 'lucide-react';
import api from '../api/client';
import { useAuthStore } from '../stores/authStore';

export default function Dashboard() {
  const { isAuthenticated } = useAuthStore();

  // Fetch bots
  const { data: botsData } = useQuery({
    queryKey: ['bots'],
    queryFn: () => api.get('/bots/').then((r) => r.data),
    enabled: isAuthenticated,
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['bot-stats'],
    queryFn: () => api.get('/bots/stats/overview').then((r) => r.data),
    enabled: isAuthenticated,
  });

  const bots = botsData?.items || [];
  
  const runningBots = bots.filter((b: any) => b.status === 'running');
  const recentBots = [...bots]
    .sort((a: any, b: any) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Welcome back! Here's what's happening.</p>
        </div>
        <Link
          to="/bots/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Bot
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100">Total Bots</p>
              <p className="text-3xl font-bold mt-1">{stats?.total_bots || 0}</p>
            </div>
            <Bot className="w-10 h-10 text-blue-200" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100">Running</p>
              <p className="text-3xl font-bold mt-1">{stats?.running_bots || 0}</p>
            </div>
            <Zap className="w-10 h-10 text-green-200" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100">Total Messages</p>
              <p className="text-3xl font-bold mt-1">{stats?.total_messages?.toLocaleString() || 0}</p>
            </div>
            <MessageSquare className="w-10 h-10 text-purple-200" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-100">Tokens Used</p>
              <p className="text-3xl font-bold mt-1">
                {((stats?.total_tokens || 0) / 1000000).toFixed(1)}M
              </p>
            </div>
            <TrendingUp className="w-10 h-10 text-orange-200" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Running Bots */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Active Bots</h2>
            <Link to="/bots" className="text-sm text-blue-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {runningBots.length > 0 ? (
              runningBots.slice(0, 5).map((bot: any) => (
                <Link
                  key={bot.id}
                  to={`/bots/${bot.id}/chat`}
                  className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center text-white font-bold">
                    {bot.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{bot.name}</p>
                    <p className="text-sm text-gray-500">{bot.model_name}</p>
                  </div>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                    Online
                  </span>
                </Link>
              ))
            ) : (
              <div className="px-5 py-8 text-center text-gray-500">
                <Zap className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p>No active bots</p>
                <Link to="/bots/new" className="text-blue-600 hover:underline text-sm">
                  Create one now
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Recent Bots */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Bots</h2>
            <Link to="/bots" className="text-sm text-blue-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recentBots.length > 0 ? (
              recentBots.map((bot: any) => (
                <Link
                  key={bot.id}
                  to={`/bots/${bot.id}`}
                  className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                    {bot.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{bot.name}</p>
                    <p className="text-sm text-gray-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Updated {new Date(bot.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    bot.status === 'running' ? 'bg-green-100 text-green-800' :
                    bot.status === 'error' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {bot.status}
                  </span>
                </Link>
              ))
            ) : (
              <div className="px-5 py-8 text-center text-gray-500">
                <Bot className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p>No bots yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
