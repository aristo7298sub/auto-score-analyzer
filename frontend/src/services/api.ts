import { apiClient } from './apiClient';
import { ScoreResponse, StudentScore } from '../types/score';
import axios from 'axios';
import { useAuthStore } from '../store/authStore';

export const uploadFile = async (file: File): Promise<ScoreResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<ScoreResponse>('/api/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const getStudentScore = async (studentName: string): Promise<ScoreResponse> => {
    const response = await apiClient.get<ScoreResponse>(`/api/student/${studentName}`);
    return response.data;
};

export const exportScores = async (format: string, scores: StudentScore[], originalFilename: string = ""): Promise<Blob> => {
    const response = await apiClient.post(`/api/export/${format}`, {
        scores,
        original_filename: originalFilename
    }, {
        responseType: 'blob',
    });
    return response.data;
};

// ==================== 历史记录相关 API ====================

export interface HistoryFile {
    id: number;
    filename: string;
    file_type: string;
    file_size: number;
    student_count: number;
    analysis_completed: boolean;
    uploaded_at: string;
    analyzed_at: string | null;
}

export interface HistoryResponse {
    success: boolean;
    data: HistoryFile[];
    pagination: {
        page: number;
        page_size: number;
        total: number;
        total_pages: number;
    };
}

export interface FileDetailResponse {
    success: boolean;
    data: {
        id: number;
        filename: string;
        file_type: string;
        file_size: number;
        file_url: string;
        student_count: number;
        analysis_completed: boolean;
        uploaded_at: string;
        analyzed_at: string | null;
        students: StudentScore[];
    };
}

// 创建一个独立的 axios 实例用于历史记录，避免被长时间的上传请求阻塞
// 使用更短的超时时间，并通过 HTTP/1.1 pipeline 优化
const historyApiClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 10000, // 10秒超时，快速失败
    headers: {
        'Content-Type': 'application/json',
        'Connection': 'keep-alive',
    },
    // 禁用请求队列，确保请求立即发送
    maxRedirects: 0,
});

// 添加认证拦截器 - 直接使用 useAuthStore 确保与主客户端一致
historyApiClient.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().token;
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 响应拦截器 - 处理401错误
historyApiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            useAuthStore.getState().logout();
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export const getHistoryFiles = async (page: number = 1, pageSize: number = 10): Promise<HistoryResponse> => {
    const response = await historyApiClient.get<HistoryResponse>('/api/files', {
        params: { page, page_size: pageSize }
    });
    return response.data;
};

export const getFileDetail = async (fileId: number): Promise<FileDetailResponse> => {
    const response = await historyApiClient.get<FileDetailResponse>(`/api/files/${fileId}`);
    return response.data;
};

export const deleteFile = async (fileId: number): Promise<{ success: boolean; message: string }> => {
    const response = await historyApiClient.delete(`/api/files/${fileId}`);
    return response.data;
};

export const batchDeleteFiles = async (fileIds: number[]): Promise<{ 
    success: boolean; 
    message: string;
    deleted_count: number;
    failed_ids: number[];
}> => {
    const response = await historyApiClient.post('/api/files/batch-delete', { file_ids: fileIds });
    return response.data;
}; 