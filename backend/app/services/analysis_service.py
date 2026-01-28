from typing import List, Tuple, Dict, Any
import math
from app.models.score import StudentScore, ScoreAnalysis
from app.core.config import settings
import asyncio

from app.services.azure_openai_responses_client import AzureOpenAIResponsesClient

class AnalysisService:
    SYSTEM_ROLE_INSTRUCTION = (
        "你是一位专业的小学学科教育分析专家。请根据学生的薄弱知识点与扣分情况，生成一段完整的成绩分析和改进建议，要鼓励与建议并存。\n\n"
    )

    SYSTEM_NOTES = (
        "注意：\n"
        "1. 直接输出一段完整的分析文本\n"
        "2. 不要使用分段标题或编号\n"
        "3. 以分号或顿号连接各个知识点\n"
        "4. 既要指出问题，也要给出具体的改进建议"
    )

    DEFAULT_REFERENCE_EXAMPLE = (
        "从知识点方面，小朋友能够基本掌握，但是在以下方面还需要继续加强：除法算理的运用不够灵活，根据余数和除数求最小、最大的被除数，可以针对性练习，回顾这个专题的练习，同时加强计算；轴对称图形观察图形的细致性还要提高；长度单位的换算和比较，不够熟练，假期要加强练习；英文表述的倍数关系不够熟练，建议多总结句型，针对性练习；归一问题读题不够透彻，很容易找不到那个单一的量，建议在读题的基础上，善于做一些标记、图来帮助分析；单位换算还需要继续练习；对于长度单位、面积单位的感知还不够熟悉，平时要在日常生活中多多留心，从生活中身边的例子出发，加深对于单位概念的理解和熟练度；混合运算的变形不够熟练，建议做一些标记、简单的提示词来帮助梳理思路；计算面积会忘记统一单位，还是要多总结做题方法、题型。"
    )

    @staticmethod
    def _build_system_prompt(one_shot_text: str | None = None) -> str:
        reference_example = (
            one_shot_text.strip()
            if one_shot_text and one_shot_text.strip()
            else AnalysisService.DEFAULT_REFERENCE_EXAMPLE
        )

        return (
            AnalysisService.SYSTEM_ROLE_INSTRUCTION
            + "以下是参考示例，请你只学习风格，不要照搬，示例中的学科不具备参考价值，请你尊重用户真实提供的题目和学科描述。\n"
            + f"参考格式示例：{reference_example}\n\n"
            + AnalysisService.SYSTEM_NOTES
        )

    @staticmethod
    def _resolve_responses_url() -> str:
        if settings.AZURE_OPENAI_RESPONSES_URL and settings.AZURE_OPENAI_RESPONSES_URL.strip():
            return settings.AZURE_OPENAI_RESPONSES_URL.strip()

        if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_ENDPOINT.strip():
            raise ValueError("AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_RESPONSES_URL must be set")

        endpoint = settings.AZURE_OPENAI_ENDPOINT.strip().rstrip("/")
        # If user provided https://.../openai/v1 already, normalize.
        if endpoint.endswith("/openai/v1"):
            return f"{endpoint}/responses"
        if endpoint.endswith("/openai/v1/responses"):
            return endpoint
        return f"{endpoint}/openai/v1/responses"

    @staticmethod
    def _resolve_analysis_model() -> str:
        # New preferred knob for /responses.
        if settings.ANALYSIS_MODEL and settings.ANALYSIS_MODEL.strip():
            return settings.ANALYSIS_MODEL.strip()
        # Backward compatibility with older chat.completions path.
        if settings.AZURE_OPENAI_DEPLOYMENT_NAME and settings.AZURE_OPENAI_DEPLOYMENT_NAME.strip():
            return settings.AZURE_OPENAI_DEPLOYMENT_NAME.strip()
        raise ValueError("ANALYSIS_MODEL (or AZURE_OPENAI_DEPLOYMENT_NAME) must be set")

    @staticmethod
    async def analyze_score(score: StudentScore, one_shot_text: str | None = None) -> Tuple[ScoreAnalysis, Dict[str, int]]:
        """分析学生成绩"""
        try:
            if not settings.AZURE_OPENAI_API_KEY:
                raise ValueError("AZURE_OPENAI_API_KEY must be set")

            client = AzureOpenAIResponsesClient(
                responses_url=AnalysisService._resolve_responses_url(),
                api_key=settings.AZURE_OPENAI_API_KEY,
                fallback_responses_url=(settings.AZURE_OPENAI_RESPONSES_URL_2 or None),
                fallback_api_key=(settings.AZURE_OPENAI_API_KEY_2 or None),
                timeout_seconds=float(settings.OPENAI_REQUEST_TIMEOUT_SECONDS or 600.0),
            )

            # User prompt: directly list original Excel questions and their deduction.
            # Only include deducted items (deduction > 0) to keep prompt focused and reduce token usage.
            deducted_items = []
            for item in (score.scores or []):
                try:
                    d = float(getattr(item, "deduction", 0.0) or 0.0)
                    if not math.isfinite(d):
                        d = 0.0
                except Exception:
                    d = 0.0

                if d > 0:
                    deducted_items.append((item, d))

            lines: list[str] = []
            lines.append(f"学生姓名：{score.student_name}")
            lines.append(f"总分：{score.total_score}分")
            lines.append("")

            if not deducted_items:
                lines.append("扣分情况：本次未识别到明确扣分项（可能表示各题目未扣分，或原始文件未标记扣分）。")
                lines.append("请基于学生总分与整体表现给出鼓励性评价，并给出保持优势与巩固复习的建议。")
            else:
                lines.append("扣分明细（按原始题目逐条列出）：")
                for idx, (item, d) in enumerate(deducted_items, start=1):
                    q = (getattr(item, "question_name", "") or "").strip() or "（未命名题目）"
                    cat = (getattr(item, "category", "") or "").strip()
                    # category is optional hint; keep it only when it adds extra information
                    if cat and cat != q:
                        lines.append(f"{idx}. 题目：{q}；扣分：{d}分；知识点/题型：{cat}")
                    else:
                        lines.append(f"{idx}. 题目：{q}；扣分：{d}分")

            prompt = "\n".join(lines) + "\n"

            # Call AOAI via /responses; fallback resource will be used automatically on recoverable errors.

            # Return deduction summary keyed by category (as before), but only include deducted items.
            deduction_by_category: dict[str, list[dict[str, Any]]] = {}
            for item, d in deducted_items:
                cat = (getattr(item, "category", "") or "").strip() or "（未分类）"
                deduction_by_category.setdefault(cat, []).append({
                    "题目": (getattr(item, "question_name", "") or "").strip() or "（未命名题目）",
                    "扣分项": d,
                })

            system_content = AnalysisService._build_system_prompt(one_shot_text=one_shot_text)

            result = await client.create_text_response(
                model=AnalysisService._resolve_analysis_model(),
                fallback_model=(settings.ANALYSIS_MODEL_2.strip() if settings.ANALYSIS_MODEL_2 else None),
                system_prompt=system_content,
                user_prompt=prompt,
                temperature=float(settings.ANALYSIS_TEMPERATURE or 0.5),
            )

            # Backward compatible keys used across the codebase.
            usage = {
                "prompt_tokens": int(result.usage.input_tokens or 0),
                "completion_tokens": int(result.usage.output_tokens or 0),
            }

            analysis_text = (result.text or "").strip()
            if not analysis_text:
                analysis_text = "（模型未返回有效文本）"

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