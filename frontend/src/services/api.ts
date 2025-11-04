import axios from 'axios';
import { ScoreResponse, StudentScore } from '../types/score';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const uploadFile = async (file: File): Promise<ScoreResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<ScoreResponse>('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const getStudentScore = async (studentName: string): Promise<ScoreResponse> => {
    const response = await api.get<ScoreResponse>(`/student/${studentName}`);
    return response.data;
};

export const exportScores = async (format: string, scores: StudentScore[], originalFilename: string = ""): Promise<Blob> => {
    const response = await api.post(`/export/${format}`, {
        scores,
        original_filename: originalFilename
    }, {
        responseType: 'blob',
    });
    return response.data;
}; 