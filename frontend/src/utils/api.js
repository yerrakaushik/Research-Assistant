import axios from 'axios';

// Reads from .env (dev) or .env.production (build) — never hardcoded
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auth
export const register = (data) => api.post('/api/auth/register', data);
export const login = (data) => api.post('/api/auth/login', data);
export const guestLogin = () => api.post('/api/auth/guest');

// Research
export const runResearch = (topic) => api.post('/api/research', { topic });
export const streamResearch = (topic, token) => {
  const url = `${API_BASE}/api/research/stream?topic=${encodeURIComponent(topic)}`;
  return new EventSource(url + `&token=${encodeURIComponent(token)}`);
};
export const getHistory = () => api.get('/api/history');
export const getBlueprint = (id) => api.get(`/api/blueprint/${id}`);
export const deleteBlueprint = (id) => api.delete(`/api/blueprint/${id}`);

export default api;
