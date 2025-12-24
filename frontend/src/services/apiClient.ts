import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';

// 获取API基础URL
const getApiUrl = () => {
  const configured = import.meta.env.VITE_API_URL as string | undefined;

  // In local dev we prefer the Vite proxy (same-origin) to avoid CORS/preflight.
  // Production/preview builds should still use an explicit backend URL.
  if (import.meta.env.DEV) {
    if (!configured || configured === 'http://localhost:8000') {
      return '';
    }
  }

  return configured || 'http://localhost:8000';
};

// 创建axios实例
export const apiClient = axios.create({
  baseURL: getApiUrl(),
  timeout: 180000, // 3分钟超时,适应大批量学生分析
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token过期或无效，清除认证状态
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 认证API
export const authApi = {
  register: (data: { username: string; email: string; email_code: string; password: string; referral_code?: string }) =>
    apiClient.post('/api/auth/register', data),

  login: (data: { username: string; password: string }) =>
    apiClient.post('/api/auth/login', data),

  sendVerificationCode: (data: { email: string }) =>
    apiClient.post('/api/auth/email/send-verification-code', data),

  sendLoginCode: (data: { email: string }) =>
    apiClient.post('/api/auth/email/send-login-code', data),

  emailLogin: (data: { email: string; code: string }) =>
    apiClient.post('/api/auth/email/login', data),

  passwordResetRequest: (data: { email: string }) =>
    apiClient.post('/api/auth/password/reset/request', data),

  passwordResetConfirm: (data: { email: string; code: string; new_password: string }) =>
    apiClient.post('/api/auth/password/reset/confirm', data),
  
  getCurrentUser: () =>
    apiClient.get('/api/auth/me'),
  
  logout: () =>
    apiClient.post('/api/auth/logout'),
};

// 配额API
export const quotaApi = {
  getBalance: () =>
    apiClient.get('/api/quota/balance'),
  
  checkQuota: (cost: number) =>
    apiClient.post('/api/quota/check', { cost }),
  
  getTransactions: (limit = 50, offset = 0) =>
    apiClient.get('/api/quota/transactions', { params: { limit, offset } }),

  getConsumption: (
    limit = 50,
    offset = 0,
    timeRange: '1d' | '7d' | '30d' | 'custom' = '7d',
    startAt?: string,
    endAt?: string
  ) => apiClient.get('/api/quota/consumption', { params: { limit, offset, time_range: timeRange, start_at: startAt, end_at: endAt } }),
  
  getReferralCode: () =>
    apiClient.get('/api/quota/referral/code'),
  
  getReferralStats: () =>
    apiClient.get('/api/quota/referral/stats'),
};

// 管理员API
export const adminApi = {
  getUsers: (
    limit = 100,
    offset = 0,
    search?: string,
    timeRange: '1d' | '7d' | '30d' | 'custom' = '7d',
    startAt?: string,
    endAt?: string
  ) =>
    apiClient.get('/api/admin/users', { params: { limit, offset, search, time_range: timeRange, start_at: startAt, end_at: endAt } }),
  
  setVip: (userId: number, isVip: boolean, days?: number) =>
    apiClient.post('/api/admin/users/set-vip', { user_id: userId, is_vip: isVip, days }),
  
  toggleActive: (userId: number) =>
    apiClient.post(`/api/admin/users/${userId}/toggle-active`),
  
  getStats: () =>
    apiClient.get('/api/admin/stats'),
  
  getLogs: (limit = 100, offset = 0, statusFilter?: string, userId?: number) =>
    apiClient.get('/api/admin/logs', { params: { limit, offset, status_filter: statusFilter, user_id: userId } }),
  
  addQuota: (userId: number, amount: number, description?: string) =>
    apiClient.post('/api/quota/admin/add', { user_id: userId, amount, description }),

  deleteUser: (userId: number) =>
    apiClient.delete(`/api/admin/users/${userId}`),

  getQuotaUsage: (month: string) =>
    apiClient.get('/api/admin/quota/usage', { params: { month } }),

  getQuotaTasks: (month: string, userId?: number, limit: number = 200, offset: number = 0) =>
    apiClient.get('/api/admin/quota/tasks', { params: { month, user_id: userId, limit, offset } }),
};

// 成绩分析API
export const scoreApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  analyzeFile: (fileId: number, oneShotText?: string) =>
    apiClient.post(`/api/files/${fileId}/analyze`, { one_shot_text: oneShotText || '' }),

  parsePreview: (fileId: number) =>
    apiClient.post('/api/files/parse/preview', { file_id: fileId }),

  parseConfirm: (sessionId: string, mapping?: any) =>
    apiClient.post('/api/files/parse/confirm', { session_id: sessionId, mapping: mapping || null }),
  
  getStudent: (studentName: string) =>
    apiClient.get(`/api/student/${studentName}`),
  
  search: (keyword: string) =>
    apiClient.get('/api/search', { params: { keyword } }),
  
  export: (format: 'xlsx' | 'docx', scores: any[], originalFilename?: string) =>
    apiClient.post(`/api/export/${format}`, { scores, original_filename: originalFilename }, {
      responseType: 'blob',
    }),
  
  getCharts: () =>
    apiClient.get('/api/charts'),
  
  getChart: (chartType: string) =>
    apiClient.get(`/api/charts/${chartType}`),
};

export default apiClient;
