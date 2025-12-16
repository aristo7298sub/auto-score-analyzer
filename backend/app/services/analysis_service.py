from typing import List, Tuple, Dict, Any
from app.models.score import StudentScore, ScoreAnalysis
from app.core.config import settings
from openai import AsyncAzureOpenAI
import json
import asyncio

class AnalysisService:
    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, int]:
        """Extract OpenAI usage fields in a defensive way."""
        usage = getattr(response, "usage", None)
        if not usage:
            return {"prompt_tokens": 0, "completion_tokens": 0}

        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        return {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}

    @staticmethod
    async def analyze_score(score: StudentScore, one_shot_text: str | None = None) -> Tuple[ScoreAnalysis, Dict[str, int]]:
        """分析学生成绩"""
        try:
            # 初始化Azure OpenAI客户端
            client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )

            # 构建提示信息 - 只列出学生的薄弱知识点
            weak_points = [item.question_name for item in score.scores]
            
            prompt = f"""
学生姓名：{score.student_name}
总分：{score.total_score}分

该学生在以下知识点存在薄弱环节：
{', '.join(weak_points)}

请针对这些薄弱知识点，生成一段完整的成绩分析和改进建议。
要求：
1. 直接输出分析文本，不要分段标题
2. 以"从知识点方面"开头
3. 分析要具体、有针对性
4. 包含改进建议和练习方法
5. 语气要专业但亲切
"""
            
            # 用于返回的扣分汇总（按类别）
            deduction_by_category = {}
            for item in score.scores:
                if item.category not in deduction_by_category:
                    deduction_by_category[item.category] = []
                deduction_by_category[item.category].append({
                    "题目": item.question_name,
                    "扣分项": item.deduction
                })

            system_content = (
                "你是一位专业的小学数学教育分析专家。请根据学生的薄弱知识点，生成一段完整的成绩分析文本。\n\n"
                "参考格式示例：从知识点方面，小朋友能够基本掌握，但是在以下方面还需要继续加强：除法算理的运用不够灵活，根据余数和除数求最小、最大的被除数，可以针对性练习，回顾这个专题的练习，同时加强计算；轴对称图形观察图形的细致性还要提高；长度单位的换算和比较，不够熟练，假期要加强练习；英文表述的倍数关系不够熟练，建议多总结句型，针对性练习；归一问题读题不够透彻，很容易找不到那个单一的量，建议在读题的基础上，善于做一些标记、图来帮助分析；单位换算还需要继续练习；对于长度单位、面积单位的感知还不够熟悉，平时要在日常生活中多多留心，从生活中身边的例子出发，加深对于单位概念的理解和熟练度；混合运算的变形不够熟练，建议做一些标记、简单的提示词来帮助梳理思路；计算面积会忘记统一单位，还是要多总结做题方法、题型。\n\n"
                "注意：\n"
                "1. 直接输出一段完整的分析文本\n"
                "2. 不要使用分段标题或编号\n"
                "3. 以分号或顿号连接各个知识点\n"
                "4. 既要指出问题，也要给出具体的改进建议"
            )

            if one_shot_text and one_shot_text.strip():
                system_content += (
                    "\n\n以下为用户提供的一次参考案例（one-shot）。请学习其写作风格、长度与语气，但不要照搬内容：\n"
                    f"{one_shot_text.strip()}"
                )

            # 调用Azure OpenAI API
            response = await client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )

            usage = AnalysisService._extract_usage(response)

            # 获取AI生成的完整分析文本
            analysis_text = response.choices[0].message.content.strip()

            # 返回分析结果
            return ScoreAnalysis(
                student_name=score.student_name,
                deduction_summary=deduction_by_category,
                analysis=analysis_text,
                suggestions=[]  # 不再单独分离建议，全部在analysis中
            ), usage
        except Exception as e:
            raise Exception(f"分析学生 {score.student_name} 的成绩时出错: {str(e)}")
    
    @staticmethod
    async def analyze_scores_batch(
        scores: List[StudentScore],
        max_concurrent: int = 50,
        one_shot_text: str | None = None,
    ) -> Tuple[List[StudentScore], Dict[str, int]]:
        """
        批量分析学生成绩，支持并发处理
        
        Args:
            scores: 学生成绩列表
            max_concurrent: 最大并发数，默认50
            
        Returns:
            包含分析结果的学生成绩列表
        """
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(score: StudentScore) -> Tuple[StudentScore, Dict[str, int]]:
            """使用信号量控制的分析函数"""
            async with semaphore:
                try:
                    analysis, usage = await AnalysisService.analyze_score(score, one_shot_text=one_shot_text)
                    # 将分析结果添加到原始score对象中
                    score.analysis = analysis.analysis
                    score.suggestions = analysis.suggestions
                    return score, usage
                except Exception as e:
                    # 如果分析失败，记录错误但不中断整个流程
                    print(f"分析学生 {score.student_name} 时出错: {str(e)}")
                    score.analysis = f"分析失败: {str(e)}"
                    score.suggestions = []
                    return score, {"prompt_tokens": 0, "completion_tokens": 0}
        
        # 并发执行所有分析任务
        tasks = [analyze_with_semaphore(score) for score in scores]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        analyzed: List[StudentScore] = []
        total_prompt = 0
        total_completion = 0

        for item in results:
            if isinstance(item, Exception):
                continue
            score, usage = item
            analyzed.append(score)
            total_prompt += int((usage or {}).get("prompt_tokens", 0) or 0)
            total_completion += int((usage or {}).get("completion_tokens", 0) or 0)

        return analyzed, {"prompt_tokens": total_prompt, "completion_tokens": total_completion}