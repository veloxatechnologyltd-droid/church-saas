import api from './api';

export const pastoralService = {
  getAll: (params) => api.get('/pastoral/', { params }),
  getSummary: () => api.get('/pastoral/summary'),
  getAttendanceRisks: (params) => api.get('/pastoral/attendance-risks', { params }),
  getAssignees: () => api.get('/pastoral/assignees'),
  create: (payload) => api.post('/pastoral/', payload),
  update: (id, payload) => api.put(`/pastoral/${id}`, payload),
};
