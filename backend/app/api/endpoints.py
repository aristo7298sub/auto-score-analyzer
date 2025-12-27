from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body, Depends, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel
import os
import logging
import tempfile
import io
import math
import numbers
from pathlib import Path
from urllib.parse import quote, urlparse, unquote
from datetime import datetime
from app.core.time import utcnow
from app.models.score import StudentScore, ScoreResponse
from app.services.analysis_service import AnalysisService
from app.services.storage_service import StorageService
from app.services.file_storage_service import file_storage
from app.services.export_service import ExportService
from app.services.visualization_service import VisualizationService
from app.core.database import get_db
from app.core.security import get_current_user, check_quota
from app.models.user import User, AnalysisLog, QuotaTransaction, ScoreFile
from app.models.file_parse_session import FileParseSession
from app.services.universal_parsing_service import UniversalParsingService
import pandas as pd
import uuid
import json
from datetime import timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
parse_logger = logging.getLogger("app.services.universal_parsing_service")

router = APIRouter()
storage_service = StorageService()
export_service = ExportService()
visualization_service = VisualizationService()

# 本地模式时创建必要的目录
if file_storage.storage_type == "local":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    os.makedirs("static/charts", exist_ok=True)

@router.post("/upload", response_model=ScoreResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传成绩文件（需要认证）
    - 上传后自动使用“全能解析”完成解析（无需用户确认映射）
    - 不调用 Azure OpenAI（等待用户点击“一键AI分析”再触发）
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"用户 {current_user.username} 开始处理文件上传: {file.filename}")
        
        # 检查文件类型
        if not file.filename.endswith(('.xlsx', '.docx', '.pptx')):
            logger.error(f"不支持的文件格式: {file.filename}")
            raise HTTPException(status_code=400, detail="不支持的文件格式，仅支持 .xlsx, .docx, .pptx 格式")
        
        # 读取文件内容
        content = await file.read()
        
        # 保存上传的文件到存储服务
        logger.info(f"保存文件到存储: {file.filename}")
        try:
            # 保存到云存储或本地
            file_url = await file_storage.save_file(
                file_content=content,
                filename=file.filename,
                file_type="upload",
                content_type=file.content_type
            )
            logger.info(f"文件保存成功: {file_url}")

        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
        
        try:
            # 保存 ScoreFile 记录（稍后写入解析结果）
            score_file = ScoreFile(
                user_id=current_user.id,
                filename=file.filename,
                file_size=len(content),
                file_type=Path(file.filename).suffix.lstrip('.'),  # 去掉开头的点
                student_count=0,
                file_url=file_url,
                analysis_completed=False,
                analysis_result=None,
                analyzed_at=None,
            )
            db.add(score_file)
            db.commit()
            db.refresh(score_file)

            # 自动全能解析（无需用户确认映射）
            preview = UniversalParsingService.extract_preview(file_bytes=content, filename=file.filename)
            mapping_result = await UniversalParsingService.infer_mapping(
                file_type=preview.file_type,
                ir=preview.ir,
                preview=preview.preview,
            )
            student_scores = UniversalParsingService.parse_full(
                file_bytes=content,
                filename=file.filename,
                mapping=mapping_result.mapping,
            )

            _log_parsed_scores(
                student_scores,
                context=f"upload:file_id={score_file.id}:name={file.filename}",
                ir=preview.ir,
                preview=preview.preview,
            )

            if not student_scores:
                raise HTTPException(status_code=400, detail="未能从文件中提取到有效的成绩数据")

            students_payload = _json_sanitize([s.dict() for s in student_scores])

            score_file.student_count = len(student_scores)
            score_file.analysis_completed = False
            score_file.analyzed_at = None
            score_file.analysis_result = json.dumps(students_payload, ensure_ascii=False, allow_nan=False)
            db.commit()

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ScoreResponse(
                success=True,
                message="解析成功，请点击 AI 分析",
                data=students_payload,
                original_filename=file.filename,
                processing_info={
                    "file_id": score_file.id,
                    "student_count": score_file.student_count,
                    "quota_cost": 0,
                    "analysis_completed": False,
                    "processing_time": processing_time,
                    "stages_completed": ["upload", "save", "parse"],
                    "parse_usage": getattr(mapping_result, "usage", None),
                },
            )

        except HTTPException as he:
            logger.error(f"❌ HTTP异常: {he.status_code} - {he.detail}")
            raise he

        except Exception as e:
            logger.error(f"❌ 处理文件失败: {str(e)}")
            logger.error(f"❌ 错误类型: {type(e).__name__}")
            logger.error(f"❌ 错误详情: {repr(e)}")
            import traceback
            logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")

        finally:
            pass
    
    except HTTPException as he:
        logger.error(f"❌ HTTP异常: {he.status_code} - {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ 上传处理过程中发生错误: {str(e)}")
        logger.error(f"❌ 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzeFileRequest(BaseModel):
    one_shot_text: str | None = None


class ParsePreviewRequest(BaseModel):
    file_id: int


class ParseConfirmRequest(BaseModel):
    session_id: str
    mapping: Dict | None = None


def _extract_storage_key(file_url: str) -> str:
    if not file_url:
        return file_url

    # Azure Blob URL may contain URL-encoded blob name (e.g. Chinese chars/spaces).
    # We must decode it back to the original blob name, otherwise read/delete fails.
    try:
        parsed = urlparse(file_url)
        if parsed.scheme and parsed.netloc:
            tail = parsed.path.split('/')[-1]
        else:
            normalized = file_url.replace('\\', '/')
            tail = normalized.split('/')[-1]
    except Exception:
        normalized = file_url.replace('\\', '/')
        tail = normalized.split('/')[-1]

    return unquote(tail)


def _deep_merge_dict(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _json_sanitize(value):
    """Convert values to be JSON-compliant (replace NaN/Infinity with None).

    Starlette's JSONResponse uses json.dumps(..., allow_nan=False) so any NaN/Inf
    will crash the response serialization.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value

    # Handle native floats
    if isinstance(value, float):
        return value if math.isfinite(value) else None

    # Handle numpy/pandas numeric scalars (and other Real types)
    if isinstance(value, numbers.Real):
        try:
            f = float(value)
            return f if math.isfinite(f) else None
        except Exception:
            return None

    if isinstance(value, dict):
        return {k: _json_sanitize(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_sanitize(v) for v in value]

    return value


def _log_parsed_scores(
    student_scores: list,
    *,
    context: str,
    ir: dict | None = None,
    preview: dict | None = None,
    max_students: int = 80,
    max_items_per_student: int = 80,
):
    """Log parsed scores to help verify parsing correctness.

    Format intentionally mimics the earlier file_service logs to make it easy
    to eyeball correctness (per-student totals + per-knowledge-point deductions).
    """
    try:
        total_students = len(student_scores or [])
    except Exception:
        total_students = -1

    # Optional: Excel shape info from IR
    try:
        shape = (ir or {}).get("shape") if isinstance(ir, dict) else None
        if isinstance(shape, dict) and shape.get("rows") is not None and shape.get("cols") is not None:
            parse_logger.info("Excel文件读取成功，共 %s 行, %s 列", shape.get("rows"), shape.get("cols"))
    except Exception:
        pass

    parse_logger.info("✅ 解析结果摘要[%s]: students=%s", context, total_students)
    parse_logger.info("字段说明：知识点=category（用于汇总统计）；题目=question_name（更细的题目/描述，可能与知识点相同）")

    if not student_scores:
        return

    # Compute knowledge points (unique categories)
    try:
        all_categories: set[str] = set()
        for s in student_scores:
            items = getattr(s, "scores", None) if not isinstance(s, dict) else s.get("scores")
            if not items:
                continue
            for it in items:
                c = getattr(it, "category", None) if not isinstance(it, dict) else it.get("category")
                if isinstance(c, str) and c.strip():
                    all_categories.add(c.strip())
        if all_categories:
            parse_logger.info("识别到 %d 个知识点", len(all_categories))
    except Exception:
        pass

    students_to_log = student_scores[:max_students]
    for idx, s in enumerate(students_to_log, start=1):
        try:
            name = getattr(s, "student_name", None) or (s.get("student_name") if isinstance(s, dict) else None)
            total = getattr(s, "total_score", None) if not isinstance(s, dict) else s.get("total_score")
            items = getattr(s, "scores", None) if not isinstance(s, dict) else s.get("scores")
        except Exception:
            name, total, items = None, None, None

        parse_logger.info("处理学生: %s", name)
        parse_logger.info("%s 总分: %s", name, total)

        if not items:
            continue

        try:
            items_to_log = list(items)[:max_items_per_student]
        except Exception:
            items_to_log = []

        deducted_points = 0
        for it in items_to_log:
            try:
                q = getattr(it, "question_name", None) if not isinstance(it, dict) else it.get("question_name")
                d = getattr(it, "deduction", 0.0) if not isinstance(it, dict) else it.get("deduction", 0.0)
                c = getattr(it, "category", None) if not isinstance(it, dict) else it.get("category")
            except Exception:
                q, d, c = None, 0.0, None

            # Normalize for logging: NaN/Inf => 0
            try:
                d_val = float(d) if d is not None else 0.0
                if not math.isfinite(d_val):
                    d_val = 0.0
            except Exception:
                d_val = 0.0

            # Always print per-item detail (score/lose style). If no deduction, mark it explicitly.
            if d_val > 0:
                deducted_points += 1
                if abs(d_val - round(d_val)) < 1e-9:
                    parse_logger.info("%s 在知识点 '%s' 有扣%d分标记", name, c, int(round(d_val)))
                else:
                    parse_logger.info("%s 在知识点 '%s' 有扣分标记(扣%s分)", name, c, d_val)
            else:
                # Keep it compact but still visible
                parse_logger.info("%s | 知识点 '%s' | 题目 '%s' | 无扣分", name, c, q)

        parse_logger.info("成功添加 %s 的成绩记录，共 %d 个扣分知识点", name, deducted_points)

        try:
            if len(items) > max_items_per_student:
                parse_logger.info("... (items truncated: %d -> %d)", len(items), max_items_per_student)
        except Exception:
            pass

    if total_students > max_students:
        parse_logger.info("... (students truncated: %d -> %d)", total_students, max_students)


@router.post("/files/parse/preview")
async def parse_preview(
    request: ParsePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全能文件解析：预览（IR + AI mapping + preview samples）。"""
    file_record = db.query(ScoreFile).filter(
        ScoreFile.id == request.file_id,
        ScoreFile.user_id == current_user.id,
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not file_record.file_url:
        raise HTTPException(status_code=400, detail="文件缺少存储地址，无法解析")

    try:
        storage_key = _extract_storage_key(file_record.file_url)
        file_bytes = await file_storage.read_file(
            storage_key if file_storage.storage_type == "azure" else file_record.file_url,
            file_type="upload",
        )
    except Exception as e:
        logger.error(
            "读取文件失败: %s | storage_type=%s | file_url=%s | storage_key=%s",
            e,
            file_storage.storage_type,
            file_record.file_url,
            storage_key if 'storage_key' in locals() else None,
        )
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

    try:
        preview = UniversalParsingService.extract_preview(file_bytes=file_bytes, filename=file_record.filename)
        mapping_result = await UniversalParsingService.infer_mapping(
            file_type=preview.file_type,
            ir=preview.ir,
            preview=preview.preview,
        )
    except Exception as e:
        logger.error(f"生成解析预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成解析预览失败: {str(e)}")

    session_id = str(uuid.uuid4())
    expires_at = utcnow() + timedelta(minutes=10)

    session = FileParseSession(
        id=session_id,
        user_id=current_user.id,
        score_file_id=file_record.id,
        status="previewed",
        file_type=preview.file_type,
        ir_json=json.dumps(preview.ir, ensure_ascii=False),
        ai_mapping_json=json.dumps(mapping_result.mapping, ensure_ascii=False),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    return JSONResponse(
        {
            "success": True,
            "message": "解析预览生成成功",
            "data": {
                "session_id": session_id,
                "file_id": file_record.id,
                "file_type": preview.file_type,
                "confidence": mapping_result.confidence,
                "mapping": mapping_result.mapping,
                "errors": mapping_result.errors,
                "recommendations": mapping_result.recommendations,
                "ir": preview.ir,
                "preview": preview.preview,
                "usage": mapping_result.usage,
                "expires_at": expires_at.isoformat(),
            },
        }
    )


@router.post("/files/parse/confirm")
async def parse_confirm(
    request: ParseConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全能文件解析：确认映射并产出最终 StudentScore[]。"""
    session = db.query(FileParseSession).filter(
        FileParseSession.id == request.session_id,
        FileParseSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="解析会话不存在")
    if session.expires_at and session.expires_at < utcnow():
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="解析会话已过期，请重新预览")

    file_record = db.query(ScoreFile).filter(
        ScoreFile.id == session.score_file_id,
        ScoreFile.user_id == current_user.id,
    ).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not file_record.file_url:
        raise HTTPException(status_code=400, detail="文件缺少存储地址，无法解析")

    try:
        stored_mapping = json.loads(session.ai_mapping_json) if session.ai_mapping_json else {}
    except Exception:
        stored_mapping = {}

    override_mapping = request.mapping if isinstance(request.mapping, dict) else {}
    merged_mapping = _deep_merge_dict(stored_mapping, override_mapping)

    try:
        storage_key = _extract_storage_key(file_record.file_url)
        file_bytes = await file_storage.read_file(
            storage_key if file_storage.storage_type == "azure" else file_record.file_url,
            file_type="upload",
        )
        student_scores = UniversalParsingService.parse_full(
            file_bytes=file_bytes,
            filename=file_record.filename,
            mapping=merged_mapping,
        )

        _log_parsed_scores(
            student_scores,
            context=f"confirm:file_id={file_record.id}:name={file_record.filename}",
        )
    except Exception as e:
        logger.error(
            "确认解析失败: %s | storage_type=%s | file_url=%s | storage_key=%s",
            e,
            file_storage.storage_type,
            file_record.file_url,
            storage_key if 'storage_key' in locals() else None,
        )
        raise HTTPException(status_code=500, detail=f"确认解析失败: {str(e)}")

    if not student_scores:
        raise HTTPException(status_code=400, detail="未能从文件中提取到有效的成绩数据")

    students_payload = _json_sanitize([s.dict() for s in student_scores])

    file_record.student_count = len(student_scores)
    file_record.analysis_completed = False
    file_record.analyzed_at = None
    # Persist strict JSON (no NaN/Infinity)
    file_record.analysis_result = json.dumps(students_payload, ensure_ascii=False, allow_nan=False)

    session.status = "confirmed"
    session.confirmed_at = utcnow()

    db.commit()

    return JSONResponse(
        {
            "success": True,
            "message": "确认解析成功",
            "data": {
                "file_id": file_record.id,
                "student_count": file_record.student_count,
                "students": students_payload,
                "mapping": merged_mapping,
            },
        }
    )


@router.post("/files/{file_id}/analyze", response_model=ScoreResponse)
async def analyze_file(
    file_id: int,
    request: AnalyzeFileRequest = Body(default=AnalyzeFileRequest()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """对已上传解析的文件触发AI分析（需要认证）"""
    start_time = datetime.utcnow()

    # 查询文件记录
    file_record = db.query(ScoreFile).filter(
        ScoreFile.id == file_id,
        ScoreFile.user_id == current_user.id
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 已分析过则直接返回（幂等）
    import json
    if file_record.analysis_completed and file_record.analysis_result:
        try:
            students_data = json.loads(file_record.analysis_result)
        except Exception:
            students_data = []

        return ScoreResponse(
            success=True,
            message="文件已完成AI分析",
            data=[StudentScore(**s) for s in students_data],
            original_filename=file_record.filename,
            processing_info={
                "file_id": file_record.id,
                "student_count": file_record.student_count,
                "quota_cost": file_record.student_count,
                "quota_remaining": current_user.quota_balance,
                "analysis_completed": True,
                "processing_time": None,
                "stages_completed": ["upload", "parse", "analyze", "save"],
            },
        )

    if not file_record.analysis_result:
        raise HTTPException(status_code=400, detail="文件尚未完成解析，无法进行AI分析")

    # 解析保存的解析结果JSON
    try:
        students_data = json.loads(file_record.analysis_result)
    except Exception:
        students_data = []

    scores: List[StudentScore] = [StudentScore(**s) for s in (students_data or [])]
    if not scores:
        raise HTTPException(status_code=400, detail="未找到可分析的学生数据")

    student_count = len(scores)
    quota_cost = student_count
    if not check_quota(current_user, quota_cost):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"配额不足。需要 {quota_cost} 配额，当前余额 {current_user.quota_balance}",
        )

    analysis_log = AnalysisLog(
        user_id=current_user.id,
        filename=file_record.filename,
        file_type=file_record.file_type,
        student_count=student_count,
        quota_cost=quota_cost,
        status="processing",
    )
    db.add(analysis_log)
    db.commit()
    db.refresh(analysis_log)

    try:
        one_shot_text = (request.one_shot_text or "").strip() or None

        # 调用 AOAI 批量分析成绩
        analyzed_scores, usage = await AnalysisService.analyze_scores_batch(
            scores,
            max_concurrent=50,
            one_shot_text=one_shot_text,
        )

        # 扣除配额（仅普通用户）
        if not current_user.is_vip:
            current_user.quota_balance -= quota_cost
        current_user.quota_used += quota_cost

        quota_transaction = QuotaTransaction(
            user_id=current_user.id,
            transaction_type="analysis_cost",
            amount=-quota_cost,
            balance_after=current_user.quota_balance,
            description=f"分析文件: {file_record.filename}",
        )
        db.add(quota_transaction)

        # 更新分析日志
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        analysis_log.status = "success"
        analysis_log.processing_time = processing_time
        try:
            analysis_log.prompt_tokens = int((usage or {}).get("prompt_tokens", 0) or 0)
            analysis_log.completion_tokens = int((usage or {}).get("completion_tokens", 0) or 0)
        except Exception:
            pass

        # 更新ScoreFile记录
        file_record.analysis_completed = True
        file_record.analyzed_at = utcnow()
        file_record.analysis_result = json.dumps([s.dict() for s in analyzed_scores], ensure_ascii=False)

        db.commit()

        return ScoreResponse(
            success=True,
            message="AI分析完成",
            data=analyzed_scores,
            original_filename=file_record.filename,
            processing_info={
                "file_id": file_record.id,
                "student_count": student_count,
                "analyzed_count": student_count,
                "quota_cost": quota_cost,
                "quota_remaining": current_user.quota_balance,
                "processing_time": processing_time,
                "analysis_completed": True,
                "stages_completed": ["upload", "parse", "analyze", "save"],
            },
        )

    except HTTPException as he:
        # Best-effort: persist failure reason for admin logs.
        try:
            db.rollback()
        except Exception:
            pass
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        try:
            analysis_log.status = "failed"
            analysis_log.error_message = f"HTTPException {he.status_code}: {he.detail}"
            analysis_log.processing_time = processing_time
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        raise
    except Exception as e:
        logger.exception("AI分析失败: file_id=%s user_id=%s", file_record.id, current_user.id)
        try:
            db.rollback()
        except Exception:
            pass
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        try:
            analysis_log.status = "failed"
            analysis_log.error_message = f"{type(e).__name__}: {str(e)}"
            analysis_log.processing_time = processing_time
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

@router.get("/student/{student_name}", response_model=ScoreResponse)
async def get_student_score(student_name: str):
    """根据学生姓名查询成绩"""
    try:
        score = storage_service.get_student_score(student_name)
        if score:
            return ScoreResponse(
                success=True,
                message="查询成功",
                data=[score]
            )
        else:
            return ScoreResponse(
                success=False,
                message=f"未找到学生 {student_name} 的成绩记录"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=ScoreResponse)
async def search_students(keyword: str = Query(..., description="搜索关键词")):
    """根据关键词搜索学生成绩"""
    try:
        scores = storage_service.search_students(keyword)
        return ScoreResponse(
            success=True,
            message="搜索成功",
            data=scores
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/{format}")
async def export_scores(
    format: str,
    request: Dict = Body(...)
):
    """
    导出成绩数据 - 直接返回文件流
    
    Args:
        format: 导出格式 (xlsx 或 docx)
        request: 包含成绩列表和原始文件名的请求体
    """
    try:
        logger.info(f"收到导出请求，格式: {format}")
        logger.info(f"请求体类型: {type(request)}")
        logger.info(f"请求体内容: {request}")
        
        # 提取数据
        scores_data = request.get('scores', [])
        original_filename = request.get('original_filename', '')
        
        logger.info(f"scores 数量: {len(scores_data)}")
        
        # 将字典转换为 StudentScore 对象
        scores = []
        for score_dict in scores_data:
            try:
                scores.append(StudentScore(**score_dict))
            except Exception as e:
                logger.error(f"转换 StudentScore 失败: {e}, 数据: {score_dict}")
                raise
        
        # 生成文件名
        base_name = original_filename.rsplit('.', 1)[0] if original_filename else "成绩分析报告"
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        if format == "xlsx":
            filename = f"{base_name}-成绩分析_{timestamp}_{unique_id}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format == "docx":
            filename = f"{base_name}-成绩分析_{timestamp}_{unique_id}.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
        
        # 创建临时文件用于导出
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            temp_path = temp_file.name
        
        try:
            # 导出到临时文件
            if format == "xlsx":
                await export_service.export_to_excel(scores, temp_path, original_filename)
            else:
                await export_service.export_to_word(scores, temp_path, original_filename)
            
            # 读取文件内容
            with open(temp_path, "rb") as f:
                file_content = f.read()
            
            logger.info(f"导出文件生成成功: {filename}, 大小: {len(file_content)} bytes")
            
            # 同时保存到 Azure Storage（备份）
            try:
                file_url = await file_storage.save_file(
                    file_content=file_content,
                    filename=filename,
                    file_type="export",
                    content_type=media_type
                )
                logger.info(f"文件已备份到存储: {file_url}")
            except Exception as storage_error:
                logger.warning(f"存储备份失败（不影响下载）: {storage_error}")
            
            # 直接返回文件流给前端
            # 对文件名进行 URL 编码以支持中文
            encoded_filename = quote(filename.encode('utf-8'))
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename*=UTF-8\'\'{encoded_filename}',
                    "Content-Length": str(len(file_content))
                }
            )
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"导出失败: {str(e)}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.get("/charts", response_model=Dict[str, str])
async def get_charts():
    """获取所有图表"""
    try:
        charts = await visualization_service.get_all_charts()
        return charts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/charts/{chart_type}")
async def get_chart(chart_type: str):
    """获取指定类型的图表"""
    try:
        if chart_type == "score_distribution":
            file_url = await visualization_service.generate_score_distribution()
        elif chart_type == "category_pie":
            file_url = await visualization_service.generate_category_pie()
        elif chart_type == "student_comparison":
            file_url = await visualization_service.generate_student_comparison()
        elif chart_type == "question_heatmap":
            file_url = await visualization_service.generate_question_heatmap()
        else:
            raise HTTPException(status_code=400, detail="不支持的图表类型")
        
        # 返回图表 URL（可能是本地路径或 Azure Blob URL）
        return JSONResponse({
            "success": True,
            "chart_url": file_url,
            "chart_type": chart_type
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 历史记录相关 API ====================

@router.get("/files")
async def get_user_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的历史文件列表（分页）
    """
    try:
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询总数
        total = db.query(ScoreFile).filter(ScoreFile.user_id == current_user.id).count()
        
        # 查询文件列表（按上传时间倒序）
        files = db.query(ScoreFile).filter(
            ScoreFile.user_id == current_user.id
        ).order_by(
            ScoreFile.uploaded_at.desc()
        ).offset(offset).limit(page_size).all()
        
        # 格式化返回数据
        file_list = []
        for file in files:
            file_list.append({
                "id": file.id,
                "filename": file.filename,
                "file_type": file.file_type,
                "file_size": file.file_size,
                "student_count": file.student_count,
                "analysis_completed": file.analysis_completed,
                "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else None,
                "analyzed_at": file.analyzed_at.isoformat() if file.analyzed_at else None,
            })
        
        return JSONResponse({
            "success": True,
            "data": file_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        })
    except Exception as e:
        logger.error(f"获取历史文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史文件列表失败: {str(e)}")


@router.get("/files/{file_id}")
async def get_file_detail(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定文件的详细信息（包括学生成绩数据）
    """
    try:
        # 查询文件记录
        file_record = db.query(ScoreFile).filter(
            ScoreFile.id == file_id,
            ScoreFile.user_id == current_user.id
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 解析保存的分析结果JSON
        import json
        students_data = []
        if file_record.analysis_result:
            try:
                students_data = json.loads(file_record.analysis_result)
            except Exception as e:
                logger.warning(f"解析分析结果失败: {str(e)}")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": file_record.id,
                "filename": file_record.filename,
                "file_type": file_record.file_type,
                "file_size": file_record.file_size,
                "file_url": file_record.file_url,
                "student_count": file_record.student_count,
                "analysis_completed": file_record.analysis_completed,
                "students": students_data,
                "uploaded_at": file_record.uploaded_at.isoformat() if file_record.uploaded_at else None,
                "analyzed_at": file_record.analyzed_at.isoformat() if file_record.analyzed_at else None,
                # "students": []  # TODO: 添加学生成绩数据
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件详情失败: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除指定的历史文件记录
    """
    try:
        # 查询文件记录
        file_record = db.query(ScoreFile).filter(
            ScoreFile.id == file_id,
            ScoreFile.user_id == current_user.id
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除云存储中的文件（如果有）
        if file_record.file_url:
            try:
                # 从 URL 中提取 blob 名称
                blob_name = file_record.file_url.split('/')[-1] if '/' in file_record.file_url else file_record.file_url
                await file_storage.delete_file(blob_name, file_type="upload")
                logger.info(f"已删除云存储文件: {blob_name}")
            except Exception as e:
                logger.warning(f"删除云存储文件失败: {str(e)}")
        
        # 删除数据库记录
        db.delete(file_record)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "文件删除成功"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.post("/files/batch-delete")
async def batch_delete_files(
    file_ids: List[int] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量删除历史文件记录
    """
    try:
        deleted_count = 0
        failed_ids = []
        
        for file_id in file_ids:
            try:
                # 查询文件记录
                file_record = db.query(ScoreFile).filter(
                    ScoreFile.id == file_id,
                    ScoreFile.user_id == current_user.id
                ).first()
                
                if file_record:
                    # 删除云存储中的文件（如果有）
                    if file_record.file_url:
                        try:
                            # 从 URL 中提取 blob 名称
                            blob_name = file_record.file_url.split('/')[-1] if '/' in file_record.file_url else file_record.file_url
                            await file_storage.delete_file(blob_name, file_type="upload")
                            logger.info(f"已删除云存储文件: {blob_name}")
                        except Exception as e:
                            logger.warning(f"删除云存储文件失败: {str(e)}")
                    
                    # 删除数据库记录
                    db.delete(file_record)
                    deleted_count += 1
                else:
                    failed_ids.append(file_id)
            except Exception as e:
                logger.error(f"删除文件 {file_id} 失败: {str(e)}")
                failed_ids.append(file_id)
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"成功删除 {deleted_count} 个文件",
            "deleted_count": deleted_count,
            "failed_ids": failed_ids
        })
    except Exception as e:
        logger.error(f"批量删除文件失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除文件失败: {str(e)}") 