"""
管理员API端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from datetime import datetime, timedelta

from ..core.database import get_db
from ..core.security import get_current_admin_user
from ..models.user import User, AnalysisLog, QuotaTransaction
from ..services.file_storage_service import file_storage
from ..schemas import (
    AdminUserListItem,
    AdminSetVIP,
    AdminStats,
    AnalysisLogInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.get("/users", response_model=List[AdminUserListItem])
async def get_all_users(
    limit: int = 100,
    offset: int = 0,
    search: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取所有用户列表
    - 仅管理员可用
    - 支持搜索和分页
    """
    query = db.query(User)
    
    # 搜索功能
    if search:
        query = query.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )
    
    users = (
        query
        .order_by(desc(User.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return [AdminUserListItem.from_orm(u) for u in users]


@router.post("/users/set-vip")
async def set_user_vip(
    data: AdminSetVIP,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    设置用户VIP状态
    - 仅管理员可用
    """
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.is_vip = data.is_vip
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"用户VIP状态已更新",
        "user_id": user.id,
        "username": user.username,
        "is_vip": user.is_vip
    }


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    启用/禁用用户账号
    - 仅管理员可用
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"用户已{'启用' if user.is_active else '禁用'}",
        "user_id": user.id,
        "username": user.username,
        "is_active": user.is_active
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    删除用户（及其关联数据）
    - 仅管理员可用
    - 防止删除自己
    - 清理 referred_by 引用以避免外键约束
    - 尝试删除该用户上传的文件（best-effort）
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录的管理员账号"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 解除其他用户对该用户的引用（避免删除时外键冲突）
    db.query(User).filter(User.referred_by == user_id).update({User.referred_by: None})

    # 如果该用户是被引荐用户，尽量回滚推荐人计数（best-effort）
    if user.referred_by:
        referrer = db.query(User).filter(User.id == user.referred_by).first()
        if referrer and (referrer.referral_count or 0) > 0:
            referrer.referral_count = max(0, (referrer.referral_count or 0) - 1)

    # 删除云存储中的上传文件（best-effort）
    try:
        # 先触发加载关系，避免删除后再访问
        score_files = list(getattr(user, "score_files", []) or [])
        for sf in score_files:
            if not getattr(sf, "file_url", None):
                continue
            try:
                blob_name = sf.file_url.split('/')[-1] if '/' in sf.file_url else sf.file_url
                await file_storage.delete_file(blob_name, file_type="upload")
            except Exception as e:
                logger.warning(f"删除用户文件失败 user_id={user_id} blob={getattr(sf, 'file_url', None)} err={e}")
    except Exception as e:
        logger.warning(f"枚举/删除用户文件失败 user_id={user_id} err={e}")

    username = user.username
    was_admin = user.is_admin
    was_vip = user.is_vip

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "用户删除成功",
        "user_id": user_id,
        "username": username,
        "was_admin": was_admin,
        "was_vip": was_vip,
    }


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取系统统计数据
    - 仅管理员可用
    """
    # 统计用户
    total_users = db.query(func.count(User.id)).scalar()
    
    # 活跃用户（最近30天登录过）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = (
        db.query(func.count(User.id))
        .filter(User.last_login >= thirty_days_ago)
        .scalar()
    )
    
    # VIP用户
    vip_users = db.query(func.count(User.id)).filter(User.is_vip == True).scalar()
    
    # 分析统计
    total_analyses = db.query(func.count(AnalysisLog.id)).scalar()
    success_analyses = (
        db.query(func.count(AnalysisLog.id))
        .filter(AnalysisLog.status == "success")
        .scalar()
    )
    failed_analyses = (
        db.query(func.count(AnalysisLog.id))
        .filter(AnalysisLog.status == "failed")
        .scalar()
    )
    
    # 总配额使用
    total_quota_used = db.query(func.sum(User.quota_used)).scalar() or 0
    
    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        vip_users=vip_users,
        total_analyses=total_analyses,
        success_analyses=success_analyses,
        failed_analyses=failed_analyses,
        total_quota_used=total_quota_used
    )


@router.get("/logs", response_model=List[AnalysisLogInfo])
async def get_analysis_logs(
    limit: int = 100,
    offset: int = 0,
    status_filter: str = None,
    user_id: int = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取所有分析日志
    - 仅管理员可用
    - 支持按状态和用户筛选
    """
    query = db.query(AnalysisLog)
    
    if status_filter:
        query = query.filter(AnalysisLog.status == status_filter)
    
    if user_id:
        query = query.filter(AnalysisLog.user_id == user_id)
    
    logs = (
        query
        .order_by(desc(AnalysisLog.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return [AnalysisLogInfo.from_orm(log) for log in logs]


@router.get("/users/{user_id}/logs", response_model=List[AnalysisLogInfo])
async def get_user_logs(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取特定用户的分析日志
    - 仅管理员可用
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    logs = (
        db.query(AnalysisLog)
        .filter(AnalysisLog.user_id == user_id)
        .order_by(desc(AnalysisLog.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return [AnalysisLogInfo.from_orm(log) for log in logs]
