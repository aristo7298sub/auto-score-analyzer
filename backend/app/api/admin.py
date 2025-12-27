"""
管理员API端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
    AnalysisLogInfo,
    AdminQuotaUsageItem,
    AdminQuotaTaskItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.get("/users", response_model=List[AdminUserListItem])
async def get_all_users(
    limit: int = 100,
    offset: int = 0,
    search: str = None,
    time_range: str = Query("7d", description="1d | 7d | 30d | custom"),
    start_at: datetime = None,
    end_at: datetime = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取所有用户列表
    - 仅管理员可用
    - 支持搜索和分页
    """
    # Resolve time window
    now = end_at or datetime.utcnow()
    tr = (time_range or "7d").strip().lower()
    if tr == "1d":
        start = now - timedelta(days=1)
    elif tr == "7d":
        start = now - timedelta(days=7)
    elif tr in ("30d", "1m", "month"):
        start = now - timedelta(days=30)
    elif tr == "custom":
        if not start_at:
            raise HTTPException(status_code=400, detail="custom 时间范围需要提供 start_at")
        start = start_at
    else:
        raise HTTPException(status_code=400, detail="time_range 仅支持 1d / 7d / 30d / custom")

    query = db.query(User)
    
    # 搜索功能
    if search:
        query = query.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )
    
    # Aggregations (range-based)
    analysis_agg = (
        db.query(
            AnalysisLog.user_id.label("user_id"),
            func.coalesce(func.sum(AnalysisLog.quota_cost), 0).label("range_quota_used"),
            func.coalesce(func.sum(getattr(AnalysisLog, "prompt_tokens", 0)), 0).label("range_prompt_tokens"),
            func.coalesce(func.sum(getattr(AnalysisLog, "completion_tokens", 0)), 0).label("range_completion_tokens"),
        )
        .filter(AnalysisLog.created_at >= start)
        .filter(AnalysisLog.created_at <= now)
        .filter(AnalysisLog.status == "success")
        .group_by(AnalysisLog.user_id)
        .subquery()
    )

    referral_agg = (
        db.query(
            User.referred_by.label("user_id"),
            func.count(User.id).label("range_referral_count"),
        )
        .filter(User.referred_by.isnot(None))
        .filter(User.created_at >= start)
        .filter(User.created_at <= now)
        .group_by(User.referred_by)
        .subquery()
    )

    rows = (
        query
        .outerjoin(analysis_agg, analysis_agg.c.user_id == User.id)
        .outerjoin(referral_agg, referral_agg.c.user_id == User.id)
        .add_columns(
            func.coalesce(analysis_agg.c.range_quota_used, 0),
            func.coalesce(referral_agg.c.range_referral_count, 0),
            func.coalesce(analysis_agg.c.range_prompt_tokens, 0),
            func.coalesce(analysis_agg.c.range_completion_tokens, 0),
        )
        .order_by(desc(User.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    items: List[AdminUserListItem] = []
    for u, rq, rr, rp, rc in rows:
        base = AdminUserListItem.model_validate(u).model_dump()
        base.update(
            {
                "range_quota_used": int(rq or 0),
                "range_referral_count": int(rr or 0),
                "range_prompt_tokens": int(rp or 0),
                "range_completion_tokens": int(rc or 0),
            }
        )
        items.append(AdminUserListItem(**base))

    return items


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
    
    # 设置/取消 VIP
    if data.is_vip:
        # 默认 30 天；仅支持 30 的倍数
        days = data.days if data.days is not None else 30
        if days <= 0 or days % 30 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VIP天数必须为正数且为30的倍数"
            )

        user.is_vip = True
        user.vip_expires_at = datetime.utcnow() + timedelta(days=days)
    else:
        user.is_vip = False
        user.vip_expires_at = None
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"用户VIP状态已更新",
        "user_id": user.id,
        "username": user.username,
        "is_vip": user.is_vip,
        "vip_expires_at": user.vip_expires_at,
    }


@router.get("/quota/usage", response_model=List[AdminQuotaUsageItem])
async def get_quota_usage_by_month(
    month: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """按月统计每个用户的配额消耗（按消耗从高到低）"""

    # month: YYYY-MM
    if month:
        try:
            year_str, month_str = month.split("-", 1)
            year = int(year_str)
            month_num = int(month_str)
            start = datetime(year, month_num, 1)
        except Exception as e:
            raise HTTPException(status_code=400, detail="month 参数格式应为 YYYY-MM") from e
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)

    # 下月起始
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    rows = (
        db.query(
            User.id.label("user_id"),
            User.username,
            User.email,
            func.coalesce(func.sum(AnalysisLog.quota_cost), 0).label("total_quota_cost"),
            func.count(AnalysisLog.id).label("task_count"),
        )
        .select_from(AnalysisLog)
        .join(User, User.id == AnalysisLog.user_id)
        .filter(AnalysisLog.created_at >= start)
        .filter(AnalysisLog.created_at < end)
        .filter(AnalysisLog.status == "success")
        .group_by(User.id, User.username, User.email)
        .order_by(desc(func.coalesce(func.sum(AnalysisLog.quota_cost), 0)))
        .all()
    )

    return [
        AdminQuotaUsageItem(
            user_id=r.user_id,
            username=r.username,
            email=r.email,
            total_quota_cost=int(r.total_quota_cost or 0),
            task_count=int(r.task_count or 0),
        )
        for r in rows
    ]


@router.get("/quota/tasks", response_model=List[AdminQuotaTaskItem])
async def get_quota_tasks_by_month(
    month: str = None,
    user_id: int = None,
    limit: int = 200,
    offset: int = 0,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """按月获取配额消耗明细（任务维度），可按用户筛选"""

    if month:
        try:
            year_str, month_str = month.split("-", 1)
            year = int(year_str)
            month_num = int(month_str)
            start = datetime(year, month_num, 1)
        except Exception as e:
            raise HTTPException(status_code=400, detail="month 参数格式应为 YYYY-MM") from e
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)

    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    query = (
        db.query(AnalysisLog, User.username)
        .join(User, User.id == AnalysisLog.user_id)
        .filter(AnalysisLog.created_at >= start)
        .filter(AnalysisLog.created_at < end)
        .order_by(desc(AnalysisLog.created_at))
    )

    if user_id:
        query = query.filter(AnalysisLog.user_id == user_id)

    logs = query.limit(limit).offset(offset).all()

    return [
        AdminQuotaTaskItem(
            id=log.id,
            user_id=log.user_id,
            username=username,
            filename=log.filename,
            student_count=log.student_count,
            quota_cost=log.quota_cost,
            status=log.status,
            created_at=log.created_at,
        )
        for log, username in logs
    ]


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

    # 总 tokens 消耗（全平台，成功任务）
    total_prompt_tokens = (
        db.query(func.coalesce(func.sum(getattr(AnalysisLog, "prompt_tokens", 0)), 0))
        .filter(AnalysisLog.status == "success")
        .scalar()
        or 0
    )
    total_completion_tokens = (
        db.query(func.coalesce(func.sum(getattr(AnalysisLog, "completion_tokens", 0)), 0))
        .filter(AnalysisLog.status == "success")
        .scalar()
        or 0
    )
    
    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        vip_users=vip_users,
        total_analyses=total_analyses,
        success_analyses=success_analyses,
        failed_analyses=failed_analyses,
        total_quota_used=total_quota_used,
        total_prompt_tokens=int(total_prompt_tokens),
        total_completion_tokens=int(total_completion_tokens),
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
    # Join User so admin UI can display username.
    query = db.query(AnalysisLog, User.username).join(User, User.id == AnalysisLog.user_id)
    
    if status_filter:
        query = query.filter(AnalysisLog.status == status_filter)

    if user_id:
        query = query.filter(AnalysisLog.user_id == user_id)

    rows = (
        query
        .order_by(desc(AnalysisLog.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    items: List[AnalysisLogInfo] = []
    for log, username in rows:
        base = AnalysisLogInfo.model_validate(log).model_dump()
        base["username"] = username
        items.append(AnalysisLogInfo(**base))

    return items


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

    items: List[AnalysisLogInfo] = []
    for log in logs:
        base = AnalysisLogInfo.model_validate(log).model_dump()
        base["username"] = user.username
        items.append(AnalysisLogInfo(**base))

    return items
