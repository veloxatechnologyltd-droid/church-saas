import api from './api';

export const attendanceService = {
  getSessions: (params) => api.get('/attendance/sessions', { params }),
  getSessionById: (id) => api.get(`/attendance/sessions/${id}`),
  createSession: (payload) => api.post('/attendance/sessions', payload),
  markAttendance: (sessionId, payload) => api.post(`/attendance/sessions/${sessionId}/mark`, payload),
  getMemberHistory: (memberId) => api.get(`/attendance/member/${memberId}`),
  getSummary: () => api.get('/attendance/summary'),
  setCheckin: (sessionId, open) => api.post(`/attendance/sessions/${sessionId}/checkin`, { open }),
};
