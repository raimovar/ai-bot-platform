import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import toast from "react-hot-toast";

export default function Login() {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isRegister) {
        await api.post("/users/auth/register", form);
        toast.success("Регистрация успешна!");
      }
      const response = await api.post("/users/auth/login", {
        username: form.username,
        password: form.password,
      });
      localStorage.setItem("token", response.data.access_token);
      navigate("/");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Ошибка");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">
          {isRegister ? "Регистрация" : "Вход"}
        </h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <input
              type="email"
              placeholder="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          )}
          <input
            type="text"
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg"
            required
          />
          <button
            type="submit"
            className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {isRegister ? "Зарегистрироваться" : "Войти"}
          </button>
        </form>
        <button
          onClick={() => setIsRegister(!isRegister)}
          className="w-full mt-4 text-blue-600 hover:underline"
        >
          {isRegister ? "Уже есть аккаунт? Войти" : "Нет аккаунта? Регистрация"}
        </button>
      </div>
    </div>
  );
}
