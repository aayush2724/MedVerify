import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
});

// Auth token injection
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export const certificateAPI = {
  verify: (formData, onUploadProgress) =>
    api.post('/api/certificates/verify', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    }),
  verifyAsync: (formData) =>
    api.post('/api/certificates/verify-async', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  pollStatus: (taskId) =>
    api.get(`/api/certificates/verify-async/${taskId}/status`),
  getAll: (params) => api.get('/api/certificates', { params }),
  getById: (id) => api.get(`/api/certificates/${id}`),
  getStats: () => api.get('/api/certificates/stats'),
  exportReport: (id) => api.get(`/api/certificates/${id}/export`),
};

export const authAPI = {
  login: (data) => api.post('/api/auth/login', data),
  register: (data) => api.post('/api/auth/register', data),
  me: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout'),
};

export const adminAPI = {
  getThresholds: () => api.get('/api/admin/thresholds'),
  updateThresholds: (data) => api.put('/api/admin/thresholds', data),
  getStats: () => api.get('/api/admin/stats'),
  getAuditLogs: (params) => api.get('/api/admin/audit-logs', { params }),
  getRecords: (params) => api.get('/api/admin/records', { params }),
};

export const verifyCertificate = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('certificate', file);
  return certificateAPI.verifyAsync(formData, onUploadProgress);
};

export const getTaskStatus = (taskId) => certificateAPI.pollStatus(taskId);
export const getRecords = (params) => certificateAPI.getAll(params);
export const getRecord = (id) => certificateAPI.getById(id);
export const login = (email, password) => authAPI.login({ email, password });

export default api;
