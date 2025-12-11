import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { StudentScore } from '../types/score';

export interface FileGroup {
    id: string;
    filename: string;
    scores: StudentScore[];
    uploadTime: string;
    status: 'uploading' | 'analyzing' | 'complete' | 'error';
    statusMessage?: string;
    studentCount?: number;
    quotaCost?: number;
}

interface ScoreState {
    // 当前文件的成绩数据
    currentScores: StudentScore[] | null;
    currentFilename: string | null;
    currentProcessingInfo: any | null;
    
    // 文件组列表（包含上传中的文件）
    fileGroups: FileGroup[];
    activeFileId: string;
    
    // 操作方法
    setScores: (scores: StudentScore[], filename: string, processingInfo?: any) => void;
    clearScores: () => void;
    setFileGroups: (groups: FileGroup[] | ((prev: FileGroup[]) => FileGroup[])) => void;
    setActiveFileId: (fileId: string) => void;
}

export const useScoreStore = create<ScoreState>()(
    persist(
        (set) => ({
            currentScores: null,
            currentFilename: null,
            currentProcessingInfo: null,
            fileGroups: [],
            activeFileId: '',

            setScores: (scores, filename, processingInfo) =>
                set({
                    currentScores: scores,
                    currentFilename: filename,
                    currentProcessingInfo: processingInfo,
                }),

            clearScores: () =>
                set({
                    currentScores: null,
                    currentFilename: null,
                    currentProcessingInfo: null,
                    fileGroups: [],
                    activeFileId: '',
                }),

            setFileGroups: (groups) => 
                set((state) => ({
                    fileGroups: typeof groups === 'function' ? groups(state.fileGroups) : groups
                })),

            setActiveFileId: (fileId) => set({ activeFileId: fileId }),
        }),
        {
            name: 'score-storage', // localStorage key
        }
    )
);
