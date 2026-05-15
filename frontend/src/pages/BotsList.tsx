import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import api from "../api/client";
import toast from "react-hot-toast";

export default function BotsList() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["bots"],
    queryFn: () => api.get("/bots").then((r) => r.data),
  });

  const startBot = useMutation({
    mutationFn: (id: string) => api.post(`/bots/${id}/start`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      toast.success("Бот запущен");
    },
    onError: () => toast.error("Ошибка запуска"),
  });

  const stopBot = useMutation({
    mutationFn: (id: string) => api.post(`/bots/${id}/stop`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      toast.success("Бот остановлен");
    },
  });

  const deleteBot = useMutation({
    mutationFn: (id: string) => api.delete(`/bots/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      toast.success("Бот удалён");
    },
  });

  if (isLoading) return <div>Загрузка...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Боты</h1>
        <Link
          to="/bots/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Новый бот
        </Link>
      </div>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Название</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Модель</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data?.items?.map((bot: any) => (
              <tr key={bot.id}>
                <td className="px-6 py-4">
                  <Link to={`/bots/${bot.id}`} className="text-blue-600 hover:underline">
                    {bot.name}
                  </Link>
                </td>
                <td className="px-6 py-4 text-gray-600">{bot.model_name}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    bot.status === "running" ? "bg-green-100 text-green-800" :
                    bot.status === "error" ? "bg-red-100 text-red-800" :
                    "bg-gray-100 text-gray-800"
                  }`}>
                    {bot.status}
                  </span>
                </td>
                <td className="px-6 py-4 space-x-2">
                  <Link
                    to={`/bots/${bot.id}/chat`}
                    className="text-blue-600 hover:underline text-sm"
                  >
                    Чат
                  </Link>
                  {bot.status === "running" ? (
                    <button
                      onClick={() => stopBot.mutate(bot.id)}
                      className="text-yellow-600 hover:underline text-sm"
                    >
                      Стоп
                    </button>
                  ) : (
                    <button
                      onClick={() => startBot.mutate(bot.id)}
                      className="text-green-600 hover:underline text-sm"
                    >
                      Старт
                    </button>
                  )}
                  <button
                    onClick={() => deleteBot.mutate(bot.id)}
                    className="text-red-600 hover:underline text-sm"
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
