import axios from 'axios';
import { useAuthStore } from '../store/authStore';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: API_BASE_URL });

// Public pages that must never bounce to /login on a 401.
const PUBLIC_PREFIXES = ['/login', '/signup', '/pricing', '/welcome/', '/pray/', '/checkin/', '/forgot-password', '/reset-password', '/accept-invite'];

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    const code = detail && typeof detail === 'object' ? detail.code : null;
    const store = useAuthStore.getState();

    if (status === 401 && store.token) {
      store.logout();
      const path = window.location.pathname;
      if (path !== '/' && !PUBLIC_PREFIXES.some((prefix) => path.startsWith(prefix))) {
        window.location.href = '/login';
      }
    } else if (status === 402 && code === 'subscription_required') {
      store.setBillingNotice({ code, message: detail.message });
    } else if (status === 403 && code === 'church_suspended') {
      store.setSuspension({ message: detail.message });
    }
    return Promise.reject(error);
  }
);

// Download a protected file (CSV/XLSX export) and save it with the given name.
export async function downloadFile(url, filename, params) {
  const response = await api.get(url, { params, responseType: 'blob' });
  const disposition = response.headers?.['content-disposition'] || '';
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  const href = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = href;
  link.download = match?.[1] || filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

export default api;
