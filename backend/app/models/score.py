from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class ScoreItem(BaseModel):
    """单个成绩项"""
    question_name: str
    deduction: float
    category: str

class StudentScore(BaseModel):
    """学生成绩"""
    student_name: str
    scores: List[ScoreItem]
    total_score: float
    analysis: Optional[str] = None
    suggestions: Optional[List[str]] = None

class ScoreAnalysis(BaseModel):
    """成绩分析"""
    student_name: str
    deduction_summary: dict
    analysis: str
    suggestions: List[str]

class ScoreResponse(BaseModel):
    """API响应"""
    success: bool
    message: str
    data: Optional[List[StudentScore]] = None
    original_filename: Optional[str] = None  # 原始文件名
    processing_info: Optional[Dict[str, Any]] = None  # 处理信息（学生数量、处理阶段等） 