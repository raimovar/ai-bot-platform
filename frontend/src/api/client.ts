import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;

// API functions
export const auth = {
  login: (username: string, password: string) =>
    api.post("/users/auth/login", { username, password }),
  register: (data: any) => api.post("/users/auth/register", data),
};

export const bots = {
  list: (params?: any) => api.get("/bots", { params }),
  get: (id: string) => api.get(`/bots/${id}`),
  create: (data: any) => api.post("/bots", data),
  update: (id: string, data: any) => api.patch(`/bots/${id}`, data),
  delete: (id: string) => api.delete(`/bots/${id}`),
  start: (id: string) => api.post(`/bots/${id}/start`),
  stop: (id: string) => api.post(`/bots/${id}/stop`),
};

export const sessions = {
  list: (params?: any) => api.get("/sessions", { params }),
  get: (id: string) => api.get(`/sessions/${id}`),
  messages: (id: string, params?: any) =>
    api.get(`/sessions/${id}/messages`, { params }),
};

export const knowledge = {
  list: (params?: any) => api.get("/knowledge", { params }),
  upload: (botId: string, formData: FormData) =>
    api.post(`/knowledge/upload?bot_id=${botId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
};
