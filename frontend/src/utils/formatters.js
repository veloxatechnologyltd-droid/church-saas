export const formatCurrency = (amount, currency = 'GHS') => {
  try {
    return new Intl.NumberFormat('en-GH', { style: 'currency', currency }).format(Number(amount || 0));
  } catch {
    return `${currency} ${Number(amount || 0).toFixed(2)}`;
  }
};

export const formatDate = (value) => {
  if (!value) return '-';
  return new Intl.DateTimeFormat('en-GH', { dateStyle: 'medium' }).format(new Date(value));
};

export const formatDateTime = (value) => {
  if (!value) return '-';
  return new Intl.DateTimeFormat('en-GH', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
};

export const todayISO = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};

// Extracts a readable message from an axios error (string detail, {code,message} detail, or 422 list).
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail;
  if (!detail) return error?.message && !error.response ? 'Cannot reach the server. Check your connection.' : fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || String(d)).join('; ');
  if (detail.message) return detail.message;
  return fallback;
}
