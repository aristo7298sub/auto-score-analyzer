import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import List, Dict
import os
import tempfile
from pathlib import Path
from app.models.score import StudentScore
from app.services.storage_service import StorageService
from app.services.file_storage_service import file_storage
from app.core.config import settings

class VisualizationService:
    def __init__(self):
        self.storage_service = StorageService()
        # 仅本地模式时创建目录
        if settings.STORAGE_TYPE == "local":
            self.charts_dir = "static/charts"
            os.makedirs(self.charts_dir, exist_ok=True)

    def _prepare_data(self) -> pd.DataFrame:
        """准备可视化数据"""
        scores = self.storage_service.get_all_scores()
        if not scores:
            raise ValueError("没有可用的成绩数据")

        # 转换数据为DataFrame格式
        data = []
        for score in scores:
            for item in score.scores:
                data.append({
                    "学生姓名": score.student_name,
                    "题目名称": item.question_name,
                    "题目类型": item.category,
                    "扣分": item.deduction
                })
        return pd.DataFrame(data)
    
    async def _save_chart(self, filename: str) -> str:
        """保存图表到存储服务"""
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_path = temp_file.name
            plt.savefig(temp_path, dpi=100, bbox_inches='tight')
            plt.close()
        
        try:
            # 读取文件内容
            with open(temp_path, "rb") as f:
                file_content = f.read()
            
            # 保存到存储服务
            file_url = await file_storage.save_file(
                file_content=file_content,
                filename=filename,
                file_type="chart",
                content_type="image/png"
            )
            
            return file_url
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def generate_score_distribution(self) -> str:
        """生成成绩分布柱状图"""
        df = self._prepare_data()
        
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x="学生姓名", y="扣分", hue="题目类型")
        plt.title("学生成绩分布")
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return await self._save_chart("score_distribution.png")

    async def generate_category_pie(self) -> str:
        """生成题目类型分布饼图"""
        df = self._prepare_data()
        
        plt.figure(figsize=(10, 10))
        category_sum = df.groupby("题目类型")["扣分"].sum()
        plt.pie(category_sum, labels=category_sum.index, autopct='%1.1f%%')
        plt.title("题目类型扣分分布")
        
        return await self._save_chart("category_pie.png")

    async def generate_student_comparison(self) -> str:
        """生成学生成绩对比折线图"""
        df = self._prepare_data()
        
        plt.figure(figsize=(12, 6))
        pivot_df = df.pivot(index="学生姓名", columns="题目类型", values="扣分")
        pivot_df.plot(kind='line', marker='o')
        plt.title("学生成绩对比")
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return await self._save_chart("student_comparison.png")

    async def generate_question_heatmap(self) -> str:
        """生成题目扣分热力图"""
        df = self._prepare_data()
        
        plt.figure(figsize=(12, 8))
        pivot_df = df.pivot(index="学生姓名", columns="题目名称", values="扣分")
        sns.heatmap(pivot_df, annot=True, fmt='.1f', cmap='YlOrRd')
        plt.title("题目扣分热力图")
        plt.tight_layout()
        
        return await self._save_chart("question_heatmap.png")

    async def get_all_charts(self) -> Dict[str, str]:
        """获取所有图表"""
        return {
            "score_distribution": await self.generate_score_distribution(),
            "category_pie": await self.generate_category_pie(),
            "student_comparison": await self.generate_student_comparison(),
            "question_heatmap": await self.generate_question_heatmap()
        }
        return {
            "score_distribution": self.generate_score_distribution(),
            "category_pie": self.generate_category_pie(),
            "student_comparison": self.generate_student_comparison(),
            "question_heatmap": self.generate_question_heatmap()
        } 