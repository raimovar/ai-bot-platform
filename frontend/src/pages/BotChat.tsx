// Bot Chat Page

import { useState, useRef, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Send, Bot as BotIcon, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react';
import api from '../api/client';
import toast from 'react-hot-toast';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string;
  tokens_used?: number;
  created_at: string;
}

export default function BotChat() {
  const { id } = useParams<{ id: string }>();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch bot info
  const { data: bot } = useQuery({
    queryKey: ['bot', id],
    queryFn: () => api.get(`/bots/${id}`).then((r) => r.data),
  });

  // Fetch sessions
  const { data: sessionsData, refetch: refetchSessions } = useQuery({
    queryKey: ['sessions', id],
    queryFn: () => api.get('/sessions', { params: { bot_id: id } }).then((r) => r.data),
  });

  // Load existing messages
  useEffect(() => {
    if (sessionsData?.items?.length > 0) {
      const sessionId = sessionsData.items[0].id;
      api.get(`/sessions/${sessionId}/messages`).then((r) => {
        const msgs = r.data.items || [];
        setMessages(msgs.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          model: m.model,
          tokens_used: m.input_tokens + m.output_tokens,
          created_at: m.created_at,
        })));
      });
    }
  }, [sessionsData]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Send message
  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const sentMessage = message;
    setMessage('');
    setIsLoading(true);

    try {
      const sessionId = sessionsData?.items?.[0]?.id;
      const response = await api.post('/sessions/chat', {
        bot_id: id,
        message: sentMessage,
        session_id: sessionId,
      });

      const assistantMessage: ChatMessage = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.response,
        model: response.data.model,
        tokens_used: response.data.tokens_used,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      refetchSessions();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to send message');
      // Remove user message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  // Rate message
  const rateMessage = async (messageId: string, rating: number) => {
    try {
      await api.patch(`/messages/${messageId}/feedback`, { rating });
      toast.success('Thanks for your feedback!');
    } catch {
      toast.error('Failed to rate message');
    }
  };

  // Clear chat
  const clearChat = async () => {
    if (!confirm('Clear all messages in this chat?')) return;
    setMessages([]);
  };

  // Format time
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <Link
            to="/bots"
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
              {bot?.name?.charAt(0).toUpperCase() || 'B'}
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">{bot?.name || 'Chat'}</h2>
              <p className="text-sm text-gray-500">
                {bot?.model_name} • {bot?.status === 'running' ? '🟢 Online' : '⚫ Offline'}
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={clearChat}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          title="Clear chat"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-white rounded-xl border border-gray-200 p-4 space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <BotIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>Start a conversation with {bot?.name}</p>
              <p className="text-sm mt-1">Send a message below to begin</p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>
              <div
                className={`px-4 py-3 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-md'
                    : msg.role === 'system'
                    ? 'bg-gray-100 text-gray-700 italic'
                    : 'bg-gray-100 text-gray-900 rounded-bl-md'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
              
              {/* Message meta */}
              <div className={`flex items-center gap-2 mt-1 text-xs text-gray-400 ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}>
                <span>{formatTime(msg.created_at)}</span>
                {msg.model && <span>• {msg.model}</span>}
                {msg.tokens_used && <span>• {msg.tokens_used} tokens</span>}
              </div>

              {/* Rating for assistant messages */}
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-1 mt-1 justify-start">
                  <button
                    onClick={() => rateMessage(msg.id, 1)}
                    className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                    title="Good response"
                  >
                    <ThumbsUp className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => rateMessage(msg.id, 1)}
                    className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                    title="Bad response"
                  >
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="flex gap-3">
        <textarea
          ref={inputRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              sendMessage(e);
            }
          }}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-500"
          rows={1}
          disabled={isLoading || bot?.status !== 'running'}
        />
        <button
          type="submit"
          disabled={!message.trim() || isLoading || bot?.status !== 'running'}
          className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {bot?.status !== 'running' && (
        <p className="text-center text-sm text-yellow-600 mt-2">
          Bot is not running. Start it to chat.
        </p>
      )}
    </div>
  );
}
