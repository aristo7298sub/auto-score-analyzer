"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # 用户类型
    is_active = Column(Boolean, default=True)
    is_vip = Column(Boolean, default=False)  # VIP用户无限配额
    vip_expires_at = Column(DateTime(timezone=True), nullable=True)  # VIP到期时间（为空表示永久/未设置）
    is_admin = Column(Boolean, default=False)  # 管理员权限
    
    # 配额
    quota_balance = Column(Integer, default=0)  # 新用户默认0配额（如通过邀请码注册可获得奖励）
    quota_used = Column(Integer, default=0)  # 已使用配额
    
    # 引荐相关
    referral_code = Column(String(20), unique=True, index=True, nullable=False)  # 自己的引荐码
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 被谁引荐（用户ID）
    referral_count = Column(Integer, default=0)  # 成功引荐人数
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    quotas = relationship("QuotaTransaction", back_populates="user", cascade="all, delete-orphan")
    analysis_logs = relationship("AnalysisLog", back_populates="user", cascade="all, delete-orphan")
    score_files = relationship("ScoreFile", back_populates="user", cascade="all, delete-orphan")


class QuotaTransaction(Base):
    """配额交易记录"""
    __tablename__ = "quota_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # 交易类型：register, referral, referral_bonus, admin_add, analysis_cost, refund
    transaction_type = Column(String(20), nullable=False)
    amount = Column(Integer, nullable=False)  # 正数为增加，负数为扣除
    balance_after = Column(Integer, nullable=False)  # 交易后余额
    
    # 描述信息
    description = Column(String(255), nullable=True)
    related_user_id = Column(Integer, nullable=True)  # 关联用户（如引荐人）
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="quotas")


class AnalysisLog(Base):
    """分析请求日志"""
    __tablename__ = "analysis_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # 文件信息
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # xlsx, docx, pptx
    student_count = Column(Integer, nullable=False)  # 学生数量
    
    # 请求状态
    status = Column(String(20), nullable=False, index=True)  # success, failed, processing
    error_message = Column(Text, nullable=True)  # 失败原因
    
    # 消耗配额
    quota_cost = Column(Integer, default=0)

    # Azure OpenAI token usage (aggregated per log)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    
    # 时间信息
    processing_time = Column(Float, nullable=True)  # 处理时间（秒）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="analysis_logs")


class ScoreFile(Base):
    """用户成绩文件记录"""
    __tablename__ = "score_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # 文件信息
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    file_url = Column(String(500), nullable=True)  # 云存储URL
    file_type = Column(String(20), nullable=False)
    
    # 分析结果
    student_count = Column(Integer, nullable=False)
    analysis_completed = Column(Boolean, default=False)
    analysis_result = Column(Text, nullable=True)  # JSON格式的完整分析结果
    
    # 时间戳
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    user = relationship("User", back_populates="score_files")
