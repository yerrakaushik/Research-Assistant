import axios from 'axios';

const API_BASE = 'http://localhost:8000';

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

// Research
export const runResearch = (topic) => api.post('/api/research', { topic });
export const streamResearch = (topic, token) => {
  const url = `http://localhost:8000/api/research/stream?topic=${encodeURIComponent(topic)}`;
  return new EventSource(url + `&token=${encodeURIComponent(token)}`);
};
export const getHistory = () => api.get('/api/history');
export const getBlueprint = (id) => api.get(`/api/blueprint/${id}`);
export const deleteBlueprint = (id) => api.delete(`/api/blueprint/${id}`);

export default api;
