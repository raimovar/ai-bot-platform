import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "../api/client";

export default function BotChat() {
  const { id } = useParams();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: bot } = useQuery({
    queryKey: ["bot", id],
    queryFn: () => api.get(`/bots/${id}`).then((r) => r.data),
  });

  // Load session messages
  const { data: sessions } = useQuery({
    queryKey: ["sessions", id],
    queryFn: () =>
      api.get("/sessions", { params: { bot_id: id } }).then((r) => r.data),
  });

  useEffect(() => {
    if (sessions?.items?.length > 0) {
      const sessionId = sessions.items[0].id;
      api.get(`/sessions/${sessionId}/messages`).then((r) => {
        setMessages(r.data.items || []);
      });
    }
  }, [sessions]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    const userMessage = { role: "user", content: message };
    setMessages((prev) => [...prev, userMessage]);
    setMessage("");
    setIsLoading(true);

    try {
      const sessionId = sessions?.items?.[0]?.id;
      const response = await api.post("/sessions/chat", {
        bot_id: id,
        message,
        session_id: sessionId,
      });

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.data.response },
      ]);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow flex flex-col h-[600px]">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Чат с {bot?.name}</h2>
          <p className="text-sm text-gray-500">
            Модель: {bot?.model_name} | Статус: {bot?.status}
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              Начните разговор с ботом...
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[70%] px-4 py-2 rounded-lg ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 px-4 py-2 rounded-lg">
                <span className="animate-pulse">Печатает...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={sendMessage} className="p-4 border-t">
          <div className="flex space-x-4">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Введите сообщение..."
              className="flex-1 px-4 py-2 border rounded-lg"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !message.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
            >
              Отправить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
