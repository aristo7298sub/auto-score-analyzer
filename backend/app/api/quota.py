"""
配额管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from ..core.database import get_db
from ..core.security import get_current_user, get_current_admin_user, check_quota
from ..models.user import User, QuotaTransaction
from ..schemas import QuotaTransactionInfo, AdminAddQuota

router = APIRouter(prefix="/quota", tags=["配额管理"])


@router.get("/balance")
async def get_quota_balance(current_user: User = Depends(get_current_user)):
    """
    获取当前用户的配额余额
    """
    return {
        "quota_balance": current_user.quota_balance,
        "quota_used": current_user.quota_used,
        "is_vip": current_user.is_vip,
        "has_unlimited": current_user.is_vip
    }


@router.post("/check")
async def check_user_quota(
    cost: int = 1,
    current_user: User = Depends(get_current_user)
):
    """
    检查用户配额是否足够
    - VIP用户无限配额
    - 普通用户检查余额
    """
    has_quota = check_quota(current_user, cost)
    
    return {
        "has_quota": has_quota,
        "quota_balance": current_user.quota_balance,
        "is_vip": current_user.is_vip,
        "required": cost
    }


@router.get("/transactions", response_model=List[QuotaTransactionInfo])
async def get_quota_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取配额交易记录
    - 分页查询
    - 按时间倒序
    """
    transactions = (
        db.query(QuotaTransaction)
        .filter(QuotaTransaction.user_id == current_user.id)
        .order_by(desc(QuotaTransaction.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return [QuotaTransactionInfo.from_orm(t) for t in transactions]


@router.post("/admin/add", dependencies=[Depends(get_current_admin_user)])
async def admin_add_quota(
    data: AdminAddQuota,
    db: Session = Depends(get_db)
):
    """
    管理员添加配额
    - 仅管理员可用
    - 记录配额交易
    """
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户配额
    user.quota_balance += data.amount
    
    # 记录交易
    transaction = QuotaTransaction(
        user_id=user.id,
        transaction_type="admin_add",
        amount=data.amount,
        balance_after=user.quota_balance,
        description=data.description
    )
    db.add(transaction)
    db.commit()
    db.refresh(user)
    
    return {
        "message": "配额添加成功",
        "user_id": user.id,
        "username": user.username,
        "new_balance": user.quota_balance
    }


@router.get("/referral/code")
async def get_referral_code(current_user: User = Depends(get_current_user)):
    """
    获取用户的引荐码
    """
    return {
        "referral_code": current_user.referral_code,
        "referral_count": current_user.referral_count,
        "bonus_per_referral": 5
    }


@router.get("/referral/stats")
async def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取引荐统计信息
    """
    # 查询通过此用户引荐码注册的用户
    referred_users = db.query(User).filter(User.referred_by == current_user.id).all()
    
    return {
        "referral_code": current_user.referral_code,
        "total_referrals": current_user.referral_count,
        "total_bonus_earned": current_user.referral_count * 5,
        "referred_users": [
            {
                "username": u.username,
                "registered_at": u.created_at
            }
            for u in referred_users
        ]
    }
