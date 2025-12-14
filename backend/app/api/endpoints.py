from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body, Depends, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel
import os
import logging
import tempfile
import io
from pathlib import Path
from urllib.parse import quote
from datetime import datetime
from app.services.file_service import FileService
from app.models.score import StudentScore, ScoreResponse
from app.services.analysis_service import AnalysisService
from app.services.storage_service import StorageService
from app.services.file_storage_service import file_storage
from app.services.export_service import ExportService
from app.services.visualization_service import VisualizationService
from app.core.database import get_db
from app.core.security import get_current_user, check_quota
from app.models.user import User, AnalysisLog, QuotaTransaction, ScoreFile
import pandas as pd
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    - 检查用户配额
    - 记录上传和分析日志
    - 扣除配额
    """
    start_time = datetime.utcnow()
    analysis_log = None
    
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
            
            # 创建临时文件用于处理（因为pandas/docx需要文件路径）
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
                temp_file.write(content)
                file_path = temp_file.name
            logger.info(f"创建临时文件: {file_path}")
            
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
        
        try:
            # 根据文件类型处理
            logger.info("开始处理文件内容")
            if file.filename.endswith('.xlsx'):
                logger.info("处理Excel文件")
                student_scores = await FileService.process_excel(file_path)
            elif file.filename.endswith('.docx'):
                logger.info("处理Word文件")
                student_scores = await FileService.process_word(file_path)
            elif file.filename.endswith('.pptx'):
                logger.info("处理PPT文件")
                student_scores = await FileService.process_ppt(file_path)
            
            if not student_scores:
                logger.error("未能从文件中提取到有效的成绩数据")
                raise HTTPException(status_code=400, detail="未能从文件中提取到有效的成绩数据")
            
            student_count = len(student_scores)
            logger.info(f"✅ 数据解析完成！成功提取到 {student_count} 个学生的成绩数据")
            
            # 检查配额（1个学生 = 1配额）
            quota_cost = student_count
            if not check_quota(current_user, quota_cost):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"配额不足。需要 {quota_cost} 配额，当前余额 {current_user.quota_balance}"
                )
            
            # 创建分析日志
            analysis_log = AnalysisLog(
                user_id=current_user.id,
                filename=file.filename,
                file_type=Path(file.filename).suffix,
                student_count=student_count,
                quota_cost=quota_cost,
                status="processing"
            )
            db.add(analysis_log)
            db.commit()
            db.refresh(analysis_log)
            
            # 使用批量并发分析成绩
            logger.info(f"🔍 开始智能分析 {student_count} 名学生的成绩（最多50个并发）...")
            
            student_scores = await AnalysisService.analyze_scores_batch(student_scores, max_concurrent=50)
            
            logger.info(f"✅ 成绩分析完成！已为 {student_count} 名学生生成个性化分析报告")
            
            # 保存成绩数据
            logger.info("💾 保存成绩数据...")
            storage_service.save_scores(student_scores)
            
            # 扣除配额（仅普通用户）
            if not current_user.is_vip:
                current_user.quota_balance -= quota_cost
            current_user.quota_used += quota_cost
            
            # 记录配额交易
            quota_transaction = QuotaTransaction(
                user_id=current_user.id,
                transaction_type="analysis_cost",
                amount=-quota_cost,
                balance_after=current_user.quota_balance,
                description=f"分析文件: {file.filename}"
            )
            db.add(quota_transaction)
            
            # 更新分析日志状态
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            analysis_log.status = "success"
            analysis_log.processing_time = processing_time
            
            # 保存ScoreFile记录（包含完整的分析结果JSON）
            import json
            analysis_result_json = json.dumps([score.dict() for score in student_scores], ensure_ascii=False)
            
            score_file = ScoreFile(
                user_id=current_user.id,
                filename=file.filename,
                file_size=len(content),
                file_type=Path(file.filename).suffix.lstrip('.'),  # 去掉开头的点
                student_count=student_count,
                file_url=file_url,
                analysis_completed=True,
                analysis_result=analysis_result_json,
                analyzed_at=datetime.utcnow()
            )
            db.add(score_file)
            
            db.commit()
            
            logger.info("🎉 文件处理完成")
            
            response_data = ScoreResponse(
                success=True,
                message="文件处理成功",
                data=student_scores,
                original_filename=file.filename,
                processing_info={
                    "student_count": student_count,
                    "analyzed_count": student_count,
                    "quota_cost": quota_cost,
                    "quota_remaining": current_user.quota_balance,
                    "processing_time": processing_time,
                    "stages_completed": ["upload", "parse", "analyze", "save"]
                }
            )
            
            logger.info(f"📤 准备返回响应 - success: {response_data.success}")
            logger.info(f"📤 响应中的学生数量: {len(response_data.data) if response_data.data else 0}")
            logger.info(f"📤 响应processing_info: {response_data.processing_info}")
            
            return response_data

        except HTTPException as he:
            # Propagate expected HTTP errors (e.g. quota insufficient) without masking them as 500.
            logger.error(f"❌ HTTP异常: {he.status_code} - {he.detail}")
            raise he

        except Exception as e:
            logger.error(f"❌ 处理文件失败: {str(e)}")
            logger.error(f"❌ 错误类型: {type(e).__name__}")
            logger.error(f"❌ 错误详情: {repr(e)}")
            import traceback
            logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
            
            # 记录失败日志
            if analysis_log:
                # Make sure the session is usable even if an earlier commit failed.
                try:
                    db.rollback()
                except Exception:
                    pass
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                analysis_log.status = "failed"
                analysis_log.error_message = str(e)
                analysis_log.processing_time = processing_time
                try:
                    db.commit()
                except Exception:
                    db.rollback()
            
            raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")
        
        finally:
            # 清理临时文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info("临时文件清理完成")
            except Exception as e:
                logger.error(f"清理临时文件失败: {str(e)}")
    
    except HTTPException as he:
        logger.error(f"❌ HTTP异常: {he.status_code} - {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ 上传处理过程中发生错误: {str(e)}")
        logger.error(f"❌ 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

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