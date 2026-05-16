import axios, { AxiosError } from "axios";
import { useAuthStore } from "../stores/authStore";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Axios request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const { token } = useAuthStore.getState();
    console.log('Axios interceptor - token:', token ? 'exists' : 'none');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.log('Axios interceptor - NO TOKEN, request will fail');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear auth
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ─────────────────────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────────────────────

export const auth = {
  login: (username: string, password: string) =>
    api.post("/users/auth/login", { username, password }),
  
  register: (data: {
    username: string;
    email: string;
    password: string;
  }) => api.post("/users/auth/register", data),
  
  me: () => api.get("/users/auth/me"),
  
  changePassword: (data: {
    current_password: string;
    new_password: string;
  }) => api.post("/users/auth/change-password", data),
};

// ─────────────────────────────────────────────────────────────
// Users API
// ─────────────────────────────────────────────────────────────

export const users = {
  list: (params?: {
    page?: number;
    page_size?: number;
    role?: string;
    search?: string;
  }) => api.get("/users/", { params }),
  
  get: (id: string) => api.get(`/users/${id}`),
  
  update: (id: string, data: any) => api.patch(`/users/${id}`, data),
  
  delete: (id: string) => api.delete(`/users/${id}`),
};

// ─────────────────────────────────────────────────────────────
// Bots API
// ─────────────────────────────────────────────────────────────

export const bots = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
  }) => api.get("/bots/", { params }),
  
  get: (id: string) => api.get(`/bots/${id}`),
  
  create: (data: any) => api.post("/bots/", data),
  
  update: (id: string, data: any) => api.patch(`/bots/${id}`, data),
  
  delete: (id: string) => api.delete(`/bots/${id}`),
  
  start: (id: string, telegramToken?: string) =>
    api.post(`/bots/${id}/start`, { telegram_token: telegramToken }),
  
  stop: (id: string) => api.post(`/bots/${id}/stop`),
  
  restart: (id: string) => api.post(`/bots/${id}/restart`),
  
  getConfig: (id: string) => api.get(`/bots/${id}/config`),
  
  stats: () => api.get("/bots/stats/overview"),
  
  // Tools
  addTool: (botId: string, data: any) =>
    api.post(`/bots/${botId}/tools`, data),
  
  updateTool: (botId: string, toolId: string, data: any) =>
    api.patch(`/bots/${botId}/tools/${toolId}`, data),
  
  deleteTool: (botId: string, toolId: string) =>
    api.delete(`/bots/${botId}/tools/${toolId}`),
};

// ─────────────────────────────────────────────────────────────
// Sessions API
// ─────────────────────────────────────────────────────────────

export const sessions = {
  list: (params?: {
    bot_id?: string;
    page?: number;
    page_size?: number;
    active_only?: boolean;
  }) => api.get("/sessions/", { params }),
  
  get: (id: string) => api.get(`/sessions/${id}`),
  
  create: (data: any) => api.post("/sessions/", data),
  
  update: (id: string, data: any) => api.patch(`/sessions/${id}`, data),
  
  delete: (id: string) => api.delete(`/sessions/${id}`),
  
  messages: (id: string, params?: {
    page?: number;
    page_size?: number;
    role?: string;
  }) => api.get(`/sessions/${id}/messages`, { params }),
  
  chat: (data: {
    bot_id: string;
    message: string;
    session_id?: string;
    external_id?: string;
    user_name?: string;
    user_id?: string;
  }) => api.post("/sessions/chat", data),
};

// ─────────────────────────────────────────────────────────────
// Messages API
// ─────────────────────────────────────────────────────────────

export const messages = {
  get: (id: string) => api.get(`/messages/${id}`),
  
  feedback: (id: string, rating: number) =>
    api.patch(`/messages/${id}/feedback`, { rating }),
  
  stats: (params?: { bot_id?: string }) =>
    api.get("/messages/stats/usage", { params }),
};

// ─────────────────────────────────────────────────────────────
// Knowledge Base API
// ─────────────────────────────────────────────────────────────

export const knowledge = {
  list: (params?: {
    bot_id?: string;
    page?: number;
    page_size?: number;
    status?: string;
  }) => api.get("/knowledge/", { params }),
  
  get: (id: string) => api.get(`/knowledge/${id}`),
  
  update: (id: string, data: any) => api.patch(`/knowledge/${id}`, data),
  
  delete: (id: string) => api.delete(`/knowledge/${id}`),
  
  upload: (
    botId: string,
    file: File,
    options?: {
      name?: string;
      description?: string;
      chunk_size?: number;
      chunk_overlap?: number;
    }
  ) => {
    const formData = new FormData();
    formData.append("file", file);
    if (options?.name) formData.append("name", options.name);
    if (options?.description) formData.append("description", options.description);
    
    const params = new URLSearchParams();
    params.append("bot_id", botId);
    if (options?.name) params.append("name", options.name);
    if (options?.description) params.append("description", options.description);
    if (options?.chunk_size) params.append("chunk_size", options.chunk_size.toString());
    if (options?.chunk_overlap) params.append("chunk_overlap", options.chunk_overlap.toString());
    
    return api.post(`/knowledge/upload?${params}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  
  search: (data: {
    query: string;
    limit?: number;
    source_ids?: string[];
  }) => api.post("/knowledge/search", data),
  
  chunks: (sourceId: string, params?: {
    page?: number;
    page_size?: number;
  }) => api.get(`/knowledge/${sourceId}/chunks`, { params }),
};

// ─────────────────────────────────────────────────────────────
// Webhooks API
// ─────────────────────────────────────────────────────────────

export const webhooks = {
  setTelegramWebhook: (botId: string, webhookUrl: string) =>
    api.post(`/webhooks/telegram/${botId}/set-webhook`, { webhook_url: webhookUrl }),
  
  deleteTelegramWebhook: (botId: string) =>
    api.delete(`/webhooks/telegram/${botId}/webhook`),
};

// Export default instance
export default api;
