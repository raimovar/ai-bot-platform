import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import toast from "react-hot-toast";

export default function BotEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew = !id;

  const { data: bot, isLoading } = useQuery({
    queryKey: ["bot", id],
    queryFn: () => api.get(`/bots/${id}`).then((r) => r.data),
    enabled: !isNew,
  });

  const [form, setForm] = useState({
    name: "",
    provider: "openai",
    model_name: "gpt-4",
    temperature: 0.7,
    max_tokens: 2048,
    system_prompt: "You are a helpful AI assistant.",
    telegram_enabled: false,
  });

  // Update form when bot loads
  if (bot && !isNew && form.name === "") {
    setForm({
      name: bot.name,
      provider: bot.provider,
      model_name: bot.model_name,
      temperature: bot.temperature,
      max_tokens: bot.max_tokens,
      system_prompt: bot.system_prompt,
      telegram_enabled: bot.telegram_enabled,
    });
  }

  const createBot = useMutation({
    mutationFn: (data: any) => api.post("/bots", data),
    onSuccess: (response) => {
      toast.success("Бот создан!");
      navigate(`/bots/${response.data.id}`);
    },
    onError: () => toast.error("Ошибка создания"),
  });

  const updateBot = useMutation({
    mutationFn: (data: any) => api.patch(`/bots/${id}`, data),
    onSuccess: () => {
      toast.success("Сохранено!");
      queryClient.invalidateQueries({ queryKey: ["bot", id] });
    },
    onError: () => toast.error("Ошибка сохранения"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isNew) {
      createBot.mutate(form);
    } else {
      updateBot.mutate(form);
    }
  };

  if (!isNew && isLoading) return <div>Загрузка...</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">
        {isNew ? "Создание бота" : `Редактирование: ${bot?.name}`}
      </h1>
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Название</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full px-3 py-2 border rounded-lg"
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Провайдер</label>
            <select
              value={form.provider}
              onChange={(e) => setForm({ ...form, provider: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama (локально)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Модель</label>
            <input
              type="text"
              value={form.model_name}
              onChange={(e) => setForm({ ...form, model_name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="gpt-4"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Temperature</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={form.temperature}
              onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Max Tokens</label>
            <input
              type="number"
              min="1"
              max="32000"
              value={form.max_tokens}
              onChange={(e) => setForm({ ...form, max_tokens: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">System Prompt</label>
          <textarea
            value={form.system_prompt}
            onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            rows={6}
            className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
            required
          />
        </div>
        <div className="flex items-center">
          <input
            type="checkbox"
            id="telegram"
            checked={form.telegram_enabled}
            onChange={(e) => setForm({ ...form, telegram_enabled: e.target.checked })}
            className="mr-2"
          />
          <label htmlFor="telegram">Подключить Telegram</label>
        </div>
        <div className="flex space-x-4">
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {isNew ? "Создать" : "Сохранить"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/bots")}
            className="px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
}
