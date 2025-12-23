import math

from pydantic import BaseModel, field_validator
from typing import List, Dict, Optional, Any

class ScoreItem(BaseModel):
    """单个成绩项"""
    question_name: str
    deduction: float
    category: str

    @field_validator('deduction', mode='before')
    @classmethod
    def _coerce_deduction(cls, v):
        # Universal parsing may output None/blank/NaN/Inf; treat as 0 to keep response schema stable.
        if v is None or v == "":
            return 0.0

        if isinstance(v, float):
            return v if math.isfinite(v) else 0.0

        # Strings like "nan" / "inf" sometimes leak from Excel/Pandas conversions.
        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                return 0.0

        try:
            f = float(v)
            return f if math.isfinite(f) else 0.0
        except Exception:
            return 0.0

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