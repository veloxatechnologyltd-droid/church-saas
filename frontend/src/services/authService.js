import api from './api';

export const authService = {
  login: (payload) => api.post('/auth/login', payload),
  me: () => api.get('/auth/me'),
  churches: () => api.get('/auth/churches'),
  switchChurch: (churchId) => api.post('/auth/switch-church', { church_id: churchId }),
  changePassword: (payload) => api.post('/auth/change-password', payload),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (payload) => api.post('/auth/reset-password', payload),
  acceptInvite: (payload) => api.post('/invitations/accept', payload),
  signup: (payload) => api.post('/signup', payload),
  slugAvailable: (slug) => api.get('/signup/slug-available', { params: { slug } }),
};
