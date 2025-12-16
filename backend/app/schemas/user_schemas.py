"""
用户相关的Schema定义
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


# 用户注册
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None  # 邮箱改为可选
    password: str = Field(..., min_length=6, max_length=100)
    referral_code: Optional[str] = None  # 引荐码


# 用户登录
class UserLogin(BaseModel):
    username: str
    password: str


# Token响应
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


# 用户信息
class UserInfo(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    is_vip: bool
    vip_expires_at: Optional[datetime] = None
    is_admin: bool
    quota_balance: int
    quota_used: int
    referral_code: Optional[str] = None
    referral_count: int
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


# 配额交易记录
class QuotaTransactionInfo(BaseModel):
    id: int
    transaction_type: str
    amount: int
    balance_after: int
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class QuotaConsumptionSummary(BaseModel):
    start_at: datetime
    end_at: datetime
    task_count: int
    total_consumed: int


class QuotaConsumptionResponse(BaseModel):
    items: list[QuotaTransactionInfo]
    summary: QuotaConsumptionSummary


# 分析日志
class AnalysisLogInfo(BaseModel):
    id: int
    filename: str
    file_type: str
    student_count: int
    status: str
    error_message: Optional[str]
    quota_cost: int
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    processing_time: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# 管理员：用户列表项
class AdminUserListItem(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    is_vip: bool
    vip_expires_at: Optional[datetime] = None
    is_admin: bool
    is_active: bool
    quota_balance: int
    quota_used: int
    referral_count: int

    # Range metrics (computed by admin API based on selected time window)
    range_quota_used: int = 0
    range_referral_count: int = 0
    range_prompt_tokens: int = 0
    range_completion_tokens: int = 0
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


# 管理员：添加配额
class AdminAddQuota(BaseModel):
    user_id: int
    amount: int = Field(..., gt=0)
    description: Optional[str] = "管理员手动添加"


# 管理员：设置VIP
class AdminSetVIP(BaseModel):
    user_id: int
    is_vip: bool
    days: Optional[int] = None


# 管理员：按月配额消耗统计（用户维度）
class AdminQuotaUsageItem(BaseModel):
    user_id: int
    username: str
    email: Optional[EmailStr] = None
    total_quota_cost: int
    task_count: int


# 管理员：配额消耗明细（任务维度）
class AdminQuotaTaskItem(BaseModel):
    id: int
    user_id: int
    username: str
    filename: str
    student_count: int
    quota_cost: int
    status: str
    created_at: datetime


# 管理员：统计数据
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    vip_users: int
    total_analyses: int
    success_analyses: int
    failed_analyses: int
    total_quota_used: int
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
