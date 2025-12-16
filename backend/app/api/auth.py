"""
认证相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from ..core.database import get_db
from ..core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    generate_referral_code,
)
from ..models.user import User, QuotaTransaction
from ..schemas import UserRegister, UserLogin, Token, UserInfo

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册
    - 检查用户名和邮箱是否已存在
    - 处理引荐码，给引荐人和新用户都加配额
    - 返回JWT token
    """
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用"
        )
    
    # 如果提供了邮箱，检查是否已存在
    if user_data.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
    
    try:
        # 创建新用户
        new_user = User(
            username=user_data.username,
            email=user_data.email,  # 可以为 None
            hashed_password=get_password_hash(user_data.password),
            referral_code=generate_referral_code(),
            quota_balance=0,  # 新用户默认0配额
        )

        # 处理引荐码
        referrer = None
        if user_data.referral_code:
            referrer = db.query(User).filter(User.referral_code == user_data.referral_code).first()
            if referrer:
                new_user.referred_by = referrer.id
                # 给引荐人增加配额和计数
                referrer_bonus = 30
                new_user_bonus = 20

                referrer.quota_balance += referrer_bonus
                referrer.referral_count += 1

                # 记录引荐人的配额交易
                referrer_transaction = QuotaTransaction(
                    user_id=referrer.id,
                    transaction_type="referral",
                    amount=referrer_bonus,
                    balance_after=referrer.quota_balance,
                    description=f"引荐用户 {user_data.username} 注册",
                    related_user_id=None,
                )
                db.add(referrer_transaction)

                # 给新用户额外配额
                new_user.quota_balance += new_user_bonus

                # 记录新用户的引荐奖励交易
                new_user_referral_tx = QuotaTransaction(
                    user_id=0,  # flush 后回填
                    transaction_type="referral_bonus",
                    amount=new_user_bonus,
                    balance_after=new_user.quota_balance,
                    description=f"使用邀请码获得奖励（来自 {referrer.username}）",
                    related_user_id=referrer.id,
                )

        db.add(new_user)
        db.flush()  # 获取 new_user.id

        # 回填引荐人交易关联用户（best-effort）
        if user_data.referral_code and referrer:
            try:
                referrer_transaction.related_user_id = new_user.id
            except Exception:
                pass

        # 回填新用户引荐奖励交易的 user_id（如果存在）
        if user_data.referral_code and referrer:
            # 在上面创建过 new_user_referral_tx
            try:
                new_user_referral_tx.user_id = new_user.id
                db.add(new_user_referral_tx)
            except Exception:
                pass

        # 记录新用户注册交易（默认0配额；如使用邀请码则另有 referral_bonus 记录）
        initial_transaction = QuotaTransaction(
            user_id=new_user.id,
            transaction_type="register",
            amount=0,
            balance_after=new_user.quota_balance,
            description="新用户注册（默认0配额）" + (" + 使用邀请码" if referrer else ""),
        )
        db.add(initial_transaction)

        db.commit()
        db.refresh(new_user)
    except IntegrityError as e:
        db.rollback()
        # 兜底：并发注册/唯一约束冲突等场景，转成 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="注册信息冲突，请检查用户名/邮箱是否已被使用") from e
    except Exception as e:
        db.rollback()
        raise
    
    # 生成JWT token
    access_token = create_access_token(data={"sub": new_user.username})
    
    return Token(
        access_token=access_token,
        user=UserInfo.from_orm(new_user)
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    - 验证用户名和密码
    - 更新最后登录时间
    - 返回JWT token
    """
    # 查找用户
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 更新最后登录时间
    try:
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
    except Exception as e:
        # 记录错误但允许登录继续（可能是数据库只读或锁定）
        print(f"Warning: Failed to update last_login: {e}")
        db.rollback()
    
    # 生成JWT token
    access_token = create_access_token(data={"sub": user.username})
    
    return Token(
        access_token=access_token,
        user=UserInfo.from_orm(user)
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    - 需要JWT token认证
    """
    return UserInfo.from_orm(current_user)


@router.post("/logout")
async def logout():
    """
    用户登出
    - JWT是无状态的，前端删除token即可
    - 这个端点主要用于记录登出日志（可选）
    """
    return {"message": "登出成功"}
