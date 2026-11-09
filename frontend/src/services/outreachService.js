import api from './api';

export const visitorService = {
  list: (params) => api.get('/visitors/', { params }),
  summary: () => api.get('/visitors/summary'),
  get: (id) => api.get(`/visitors/${id}`),
  create: (payload) => api.post('/visitors/', payload),
  update: (id, payload) => api.put(`/visitors/${id}`, payload),
  remove: (id) => api.delete(`/visitors/${id}`),
  contacted: (id, notes) => api.post(`/visitors/${id}/contacted`, { notes }),
  convert: (id) => api.post(`/visitors/${id}/convert`),
};

export const prayerService = {
  list: (params) => api.get('/prayer-requests/', { params }),
  create: (payload) => api.post('/prayer-requests/', payload),
  update: (id, payload) => api.put(`/prayer-requests/${id}`, payload),
  prayed: (id) => api.post(`/prayer-requests/${id}/prayed`),
  remove: (id) => api.delete(`/prayer-requests/${id}`),
};

export const pledgeService = {
  campaigns: () => api.get('/pledges/campaigns'),
  campaign: (id) => api.get(`/pledges/campaigns/${id}`),
  createCampaign: (payload) => api.post('/pledges/campaigns', payload),
  updateCampaign: (id, payload) => api.put(`/pledges/campaigns/${id}`, payload),
  addPledge: (campaignId, payload) => api.post(`/pledges/campaigns/${campaignId}/pledges`, payload),
  recordPayment: (pledgeId, payload) => api.post(`/pledges/${pledgeId}/payments`, payload),
  removePledge: (pledgeId) => api.delete(`/pledges/${pledgeId}`),
};
