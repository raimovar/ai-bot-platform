import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import api from "../api/client";

export default function Dashboard() {
  const { data: bots } = useQuery({
    queryKey: ["bots"],
    queryFn: () => api.get("/bots").then((r) => r.data),
  });

  const stats = {
    total: bots?.total || 0,
    running: bots?.items?.filter((b: any) => b.status === "running").length || 0,
    stopped: bots?.items?.filter((b: any) => b.status === "stopped").length || 0,
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-3xl font-bold text-blue-600">{stats.total}</div>
          <div className="text-gray-600">Всего ботов</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-3xl font-bold text-green-600">{stats.running}</div>
          <div className="text-gray-600">Запущено</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-3xl font-bold text-gray-600">{stats.stopped}</div>
          <div className="text-gray-600">Остановлено</div>
        </div>
      </div>
      <Link
        to="/bots/new"
        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        + Создать бота
      </Link>
    </div>
  );
}
