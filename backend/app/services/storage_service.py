import json
import os
from typing import List, Optional
from app.models.score import StudentScore

class StorageService:
    def __init__(self):
        self.storage_file = "data/student_scores.json"
        self._ensure_storage_exists()
        self._scores: List[StudentScore] = self._load_scores()

    def _ensure_storage_exists(self):
        """确保存储目录和文件存在"""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load_scores(self) -> List[StudentScore]:
        """从文件加载成绩数据"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [StudentScore(**score) for score in data]
        except Exception:
            return []

    def _save_scores(self):
        """保存成绩数据到文件"""
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump([score.dict() for score in self._scores], f, ensure_ascii=False, indent=2)

    def save_scores(self, scores: List[StudentScore]):
        """保存新的成绩数据"""
        self._scores = scores
        self._save_scores()

    def get_student_score(self, student_name: str) -> Optional[StudentScore]:
        """根据学生姓名查询成绩"""
        student_name = student_name.strip()
        for score in self._scores:
            if score.student_name == student_name:
                return score
        return None

    def get_all_scores(self) -> List[StudentScore]:
        """获取所有学生成绩"""
        return self._scores

    def search_students(self, keyword: str) -> List[StudentScore]:
        """根据关键词搜索学生成绩"""
        keyword = keyword.strip().lower()
        return [
            score for score in self._scores
            if keyword in score.student_name.lower()
        ] 