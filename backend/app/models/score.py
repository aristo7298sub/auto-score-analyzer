import math

from pydantic import BaseModel, field_validator, model_validator
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

    @field_validator('total_score', mode='before')
    @classmethod
    def _coerce_total_score(cls, v):
        # Allow None/blank/NaN/Inf and repair later in model_validator.
        if v is None or v == "":
            return float('nan')

        if isinstance(v, float):
            return v

        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                return float('nan')

        try:
            return float(v)
        except Exception:
            return float('nan')

    @model_validator(mode='after')
    def _fill_total_score_from_deductions(self):
        # If total_score is missing/invalid, compute it from deductions.
        if isinstance(self.total_score, float) and math.isfinite(self.total_score):
            return self

        full_score = 100.0
        total_deduction = sum(float(i.deduction or 0.0) for i in (self.scores or []))
        computed = full_score - total_deduction
        if not math.isfinite(computed):
            computed = 0.0
        self.total_score = max(0.0, min(full_score, float(computed)))
        return self

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