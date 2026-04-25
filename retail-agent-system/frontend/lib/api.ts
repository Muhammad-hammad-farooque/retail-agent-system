import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (username: string, password: string) => {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);
  return api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

export const register = (data: {
  username: string;
  email: string;
  password: string;
  role?: string;
}) => api.post('/auth/register', data);

export const getMe = () => api.get('/auth/me');

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getKpis = () => api.get('/dashboard/kpis');

// ── Inventory ─────────────────────────────────────────────────────────────────
export const getProducts = (params?: { skip?: number; limit?: number; category?: string }) =>
  api.get('/inventory/products', { params });

export const getCriticalStock = () => api.get('/inventory/critical');

export const addProduct = (data: object) => api.post('/inventory/products', data);

export const updateProduct = (id: number, data: object) =>
  api.patch(`/inventory/products/${id}`, data);

// ── Accounting ────────────────────────────────────────────────────────────────
export const getInvoices = (params?: {
  status?: string;
  start_date?: string;
  end_date?: string;
}) => api.get('/accounting/invoices', { params });

export const getAccountingSummary = () => api.get('/accounting/summary');

// ── Agent ─────────────────────────────────────────────────────────────────────
export const runAgentTask = (query: string) =>
  api.post('/agent/task', { query });

export default api;
