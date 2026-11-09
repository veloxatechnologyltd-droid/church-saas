import api, { downloadFile } from './api';

export const churchService = {
  get: () => api.get('/church'),
  update: (payload) => api.put('/church', payload),
  uploadLogo: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/church/logo', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  completeOnboarding: () => api.post('/church/onboarding/complete'),
  usage: () => api.get('/church/usage'),
  exportData: (dataset, format) => downloadFile(`/church/export/${dataset}`, `${dataset}.${format}`, { format }),
};

export const branchService = {
  list: () => api.get('/branches'),
  create: (payload) => api.post('/branches', payload),
  update: (id, payload) => api.put(`/branches/${id}`, payload),
  makeMain: (id) => api.post(`/branches/${id}/make-main`),
  remove: (id) => api.delete(`/branches/${id}`),
};

export const teamService = {
  list: () => api.get('/team'),
  update: (membershipId, payload) => api.put(`/team/${membershipId}`, payload),
  invitations: () => api.get('/invitations/'),
  invite: (payload) => api.post('/invitations/', payload),
  revokeInvitation: (id) => api.delete(`/invitations/${id}`),
};

export const billingService = {
  plans: () => api.get('/billing/plans'),
  subscription: () => api.get('/billing/subscription'),
  checkout: (payload) => api.post('/billing/checkout', payload),
  invoices: () => api.get('/billing/invoices'),
  cancel: () => api.post('/billing/cancel'),
  fakeComplete: (invoiceId) => api.post(`/billing/fake/complete/${invoiceId}`),
  smsCredits: () => api.get('/sms-credits'),
  smsPacks: () => api.get('/sms-credits/packs'),
  purchaseSms: (packCode) => api.post('/sms-credits/purchase', { pack_code: packCode }),
};

export const platformService = {
  stats: () => api.get('/platform/stats'),
  churches: (params) => api.get('/platform/churches', { params }),
  church: (id) => api.get(`/platform/churches/${id}`),
  suspend: (id, reason) => api.post(`/platform/churches/${id}/suspend`, { reason }),
  reactivate: (id) => api.post(`/platform/churches/${id}/reactivate`),
  changePlan: (id, payload) => api.put(`/platform/churches/${id}/plan`, payload),
  grantSms: (id, payload) => api.post(`/platform/churches/${id}/sms-credits`, payload),
  impersonate: (id) => api.post(`/platform/churches/${id}/impersonate`),
  events: (params) => api.get('/platform/events', { params }),
  markInvoicePaid: (invoiceId) => api.post(`/platform/invoices/${invoiceId}/mark-paid`),
};

export const publicService = {
  church: (slug) => api.get(`/public/churches/${slug}`),
  submitVisitor: (slug, payload) => api.post(`/public/churches/${slug}/visitors`, payload),
  submitPrayer: (slug, payload) => api.post(`/public/churches/${slug}/prayer-requests`, payload),
  checkinInfo: (code) => api.get(`/public/checkin/${code}`),
  checkin: (code, phone) => api.post(`/public/checkin/${code}`, { phone }),
};
