// Bot Card component

import { Link } from 'react-router-dom';
import { Bot } from '../types';
import { Play, Square, Settings, Trash2, MessageSquare } from 'lucide-react';

interface BotCardProps {
  bot: Bot;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function BotCard({ bot, onStart, onStop, onDelete }: BotCardProps) {
  const statusColors = {
    running: 'bg-green-100 text-green-800',
    stopped: 'bg-gray-100 text-gray-800',
    starting: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
              {bot.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <Link 
                to={`/bots/${bot.id}`} 
                className="font-semibold text-gray-900 hover:text-blue-600 transition-colors"
              >
                {bot.name}
              </Link>
              <p className="text-sm text-gray-500">{bot.model_name}</p>
            </div>
          </div>
          <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[bot.status]}`}>
            {bot.status}
          </span>
        </div>
        
        {bot.description && (
          <p className="mt-3 text-sm text-gray-600 line-clamp-2">{bot.description}</p>
        )}
      </div>

      {/* Stats */}
      <div className="px-4 py-3 bg-gray-50 grid grid-cols-3 gap-4 text-center">
        <div>
          <p className="text-lg font-semibold text-gray-900">{bot.total_messages}</p>
          <p className="text-xs text-gray-500">Messages</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">
            {(bot.total_tokens_used / 1000).toFixed(1)}K
          </p>
          <p className="text-xs text-gray-500">Tokens</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">{bot.tools?.length || 0}</p>
          <p className="text-xs text-gray-500">Tools</p>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 flex items-center justify-between border-t border-gray-100">
        <div className="flex gap-1">
          <Link
            to={`/bots/${bot.id}/chat`}
            className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="Chat"
          >
            <MessageSquare className="w-4 h-4" />
          </Link>
          <Link
            to={`/bots/${bot.id}`}
            className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </Link>
        </div>
        
        <div className="flex gap-1">
          {bot.status === 'running' ? (
            <button
              onClick={() => onStop(bot.id)}
              className="p-2 text-gray-600 hover:text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
              title="Stop"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => onStart(bot.id)}
              className="p-2 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
              title="Start"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={() => onDelete(bot.id)}
            className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
