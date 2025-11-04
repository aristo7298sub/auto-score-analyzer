export interface ScoreItem {
    question_name: string;
    deduction: number;
    category: string;
}

export interface StudentScore {
    student_name: string;
    scores: ScoreItem[];
    total_score: number;
    analysis?: string;
    suggestions?: string[];
}

export interface ScoreAnalysis {
    student_name: string;
    deduction_summary: Record<string, number>;
    analysis: string;
    suggestions: string[];
}

export interface ScoreResponse {
    success: boolean;
    message: string;
    data?: StudentScore[];
    original_filename?: string;  // 原始文件名
} 