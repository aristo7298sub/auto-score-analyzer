"""
Schemas模块初始化
"""
from .user_schemas import (
    UserRegister,
    UserLogin,
    Token,
    UserInfo,
    QuotaTransactionInfo,
    QuotaConsumptionSummary,
    QuotaConsumptionResponse,
    AnalysisLogInfo,
    AdminUserListItem,
    AdminAddQuota,
    AdminSetVIP,
    AdminStats,
    AdminQuotaUsageItem,
    AdminQuotaTaskItem,
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "Token",
    "UserInfo",
    "QuotaTransactionInfo",
    "QuotaConsumptionSummary",
    "QuotaConsumptionResponse",
    "AnalysisLogInfo",
    "AdminUserListItem",
    "AdminAddQuota",
    "AdminSetVIP",
    "AdminStats",
    "AdminQuotaUsageItem",
    "AdminQuotaTaskItem",
]
