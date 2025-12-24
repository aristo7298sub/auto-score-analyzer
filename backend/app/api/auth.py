"""
认证相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from datetime import timedelta
import hashlib
import secrets
import logging

from ..core.database import get_db
from ..core.config import settings
from ..core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    generate_referral_code,
    SECRET_KEY,
)
from ..models.user import User, QuotaTransaction, EmailCode
from ..schemas import (
    UserRegister,
    UserLogin,
    Token,
    UserInfo,
    SendVerificationCodeRequest,
    SendLoginCodeRequest,
    EmailLoginRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
)

from ..services.email_service import EmailMessage, EmailSendError, send_email

logger = logging.getLogger(__name__)

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
    
    # 邮箱必须唯一
    email = str(user_data.email).strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # Verify email code (purpose=verify) before creating the account.
    now = datetime.utcnow()
    code = (user_data.email_code or "").strip()
    row = (
        db.query(EmailCode)
        .filter(
            EmailCode.email == email,
            EmailCode.purpose == "verify",
            EmailCode.used_at.is_(None),
        )
        .order_by(EmailCode.id.desc())
        .first()
    )
    if not row or row.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")
    if int(row.attempts or 0) >= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    expected = _hash_email_code(email=email, purpose="verify", code=code)
    if expected != row.code_hash:
        row.attempts = int(row.attempts or 0) + 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    # Mark code as used (single-use)
    row.used_at = now
    
    try:
        # 创建新用户
        new_user = User(
            username=user_data.username,
            email=email,
            email_verified=True,
            email_verified_at=now,
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
    # Accept username OR email
    identifier = (credentials.username or "").strip()
    if "@" in identifier:
        user = db.query(User).filter(User.email == identifier.lower()).first()
    else:
        user = db.query(User).filter(User.username == identifier).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名/邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    # Stage-1 constraint: if the account has an email set but it's not verified, deny password login.
    # (Legacy users with no email remain login-able until email verification rollout completes.)
    if getattr(user, "email", None) and not bool(getattr(user, "email_verified", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邮箱未验证，请先完成邮箱验证后再登录",
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


def _hash_email_code(*, email: str, purpose: str, code: str) -> str:
    # Stable hash (not reversible). Uses SECRET_KEY as a pepper.
    raw = f"{email}|{purpose}|{code}|{SECRET_KEY}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _generate_6_digit_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _client_ip(request: Request | None) -> str | None:
    try:
        return request.client.host if request and request.client else None
    except Exception:
        return None


@router.post("/email/send-login-code")
async def send_login_code(
    payload: SendLoginCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send login code to email (generic response; does not reveal whether email exists)."""
    email = str(payload.email).strip().lower()
    purpose = "login"
    now = datetime.utcnow()
    ip = _client_ip(request)

    # Cooldown: per email+purpose, 60 seconds
    cooldown_seconds = 60
    try:
        recent = (
            db.query(EmailCode)
            .filter(EmailCode.email == email, EmailCode.purpose == purpose)
            .order_by(EmailCode.id.desc())
            .first()
        )
        if recent and getattr(recent, "created_at", None):
            try:
                if (now - recent.created_at).total_seconds() < cooldown_seconds:
                    return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}
            except Exception:
                pass
    except Exception:
        pass

    # Do not reveal existence: only send/store if user exists, but return same message regardless.
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}

    code = _generate_6_digit_code()
    expires_at = now + timedelta(minutes=10)
    row = EmailCode(
        email=email,
        purpose=purpose,
        code_hash=_hash_email_code(email=email, purpose=purpose, code=code),
        attempts=0,
        used_at=None,
        expires_at=expires_at,
        ip=ip,
    )
    db.add(row)
    db.commit()

    try:
        send_email(
            EmailMessage(
                to_email=email,
                subject="登录验证码",
                text_body=f"你的登录验证码是：{code}\n\n有效期 10 分钟。若非本人操作请忽略。",
            )
        )
    except EmailSendError as exc:
        logger.exception("Failed to send login code email (provider=%s)", getattr(settings, "EMAIL_PROVIDER", None))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="验证码发送失败，请稍后再试") from exc

    return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}


@router.post("/email/login", response_model=Token)
async def email_login(payload: EmailLoginRequest, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    code = (payload.code or "").strip()
    now = datetime.utcnow()

    # Fetch newest unexpired, unused code.
    row = (
        db.query(EmailCode)
        .filter(
            EmailCode.email == email,
            EmailCode.purpose == "login",
            EmailCode.used_at.is_(None),
        )
        .order_by(EmailCode.id.desc())
        .first()
    )
    if not row or row.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    if int(row.attempts or 0) >= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    expected = _hash_email_code(email=email, purpose="login", code=code)
    if expected != row.code_hash:
        row.attempts = int(row.attempts or 0) + 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    # Mark used
    row.used_at = now

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录失败")

    # Successful email login implies email ownership; mark verified.
    if not bool(getattr(user, "email_verified", False)):
        user.email_verified = True
        user.email_verified_at = now

    # Update last login
    user.last_login = now
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, user=UserInfo.from_orm(user))


@router.post("/password/reset/request")
async def password_reset_request(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    """Request a password reset code (generic response)."""
    email = str(payload.email).strip().lower()
    purpose = "reset"
    now = datetime.utcnow()
    ip = _client_ip(request)

    # Cooldown: per email+purpose, 60 seconds
    cooldown_seconds = 60
    try:
        recent = (
            db.query(EmailCode)
            .filter(EmailCode.email == email, EmailCode.purpose == purpose)
            .order_by(EmailCode.id.desc())
            .first()
        )
        if recent and getattr(recent, "created_at", None):
            try:
                if (now - recent.created_at).total_seconds() < cooldown_seconds:
                    return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}
            except Exception:
                pass
    except Exception:
        pass

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}

    code = _generate_6_digit_code()
    expires_at = now + timedelta(minutes=10)
    row = EmailCode(
        email=email,
        purpose=purpose,
        code_hash=_hash_email_code(email=email, purpose=purpose, code=code),
        attempts=0,
        used_at=None,
        expires_at=expires_at,
        ip=ip,
    )
    db.add(row)
    db.commit()

    try:
        send_email(
            EmailMessage(
                to_email=email,
                subject="重置密码验证码",
                text_body=f"你的重置密码验证码是：{code}\n\n有效期 10 分钟。若非本人操作请忽略。",
            )
        )
    except EmailSendError:
        # Keep reset request generic (avoid account enumeration)
        logger.exception("Failed to send password reset email (provider=%s)", getattr(settings, "EMAIL_PROVIDER", None))
        return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}

    return {"message": "如果邮箱存在且可用，验证码已发送（请稍后查收）"}


@router.post("/email/send-verification-code")
async def send_verification_code(
    payload: SendVerificationCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send email verification code for registration.

    Generic response; does not reveal whether email is already registered.
    """
    email = str(payload.email).strip().lower()
    purpose = "verify"
    now = datetime.utcnow()
    ip = _client_ip(request)

    cooldown_seconds = 60
    try:
        recent = (
            db.query(EmailCode)
            .filter(EmailCode.email == email, EmailCode.purpose == purpose)
            .order_by(EmailCode.id.desc())
            .first()
        )
        if recent and getattr(recent, "created_at", None):
            try:
                if (now - recent.created_at).total_seconds() < cooldown_seconds:
                    return {"message": "如果邮箱可用，验证码已发送（请稍后查收）"}
            except Exception:
                pass
    except Exception:
        pass

    # If already registered, still return generic success.
    if db.query(User).filter(User.email == email).first():
        return {"message": "如果邮箱可用，验证码已发送（请稍后查收）"}

    code = _generate_6_digit_code()
    expires_at = now + timedelta(minutes=10)
    row = EmailCode(
        email=email,
        purpose=purpose,
        code_hash=_hash_email_code(email=email, purpose=purpose, code=code),
        attempts=0,
        used_at=None,
        expires_at=expires_at,
        ip=ip,
    )
    db.add(row)
    db.commit()

    try:
        send_email(
            EmailMessage(
                to_email=email,
                subject="注册验证码",
                text_body=f"你的注册验证码是：{code}\n\n有效期 10 分钟。若非本人操作请忽略。",
            )
        )
    except EmailSendError as exc:
        logger.exception("Failed to send verification email (provider=%s)", getattr(settings, "EMAIL_PROVIDER", None))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="验证码发送失败，请稍后再试") from exc

    return {"message": "如果邮箱可用，验证码已发送（请稍后查收）"}


@router.post("/password/reset/confirm")
async def password_reset_confirm(payload: PasswordResetConfirmRequest, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    code = (payload.code or "").strip()
    now = datetime.utcnow()

    row = (
        db.query(EmailCode)
        .filter(
            EmailCode.email == email,
            EmailCode.purpose == "reset",
            EmailCode.used_at.is_(None),
        )
        .order_by(EmailCode.id.desc())
        .first()
    )

    if not row or row.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")
    if int(row.attempts or 0) >= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    expected = _hash_email_code(email=email, purpose="reset", code=code)
    if expected != row.code_hash:
        row.attempts = int(row.attempts or 0) + 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        row.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="重置失败")

    # Update password
    user.hashed_password = get_password_hash(payload.new_password)
    user.email_verified = True
    user.email_verified_at = now

    row.used_at = now
    db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}


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
