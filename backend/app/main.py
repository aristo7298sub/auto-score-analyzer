from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import os

from app.core.database import engine, Base, ensure_schema_compatibility
from app.core.config import settings
from app.api import router as api_router
from app.api.auth import router as auth_router
from app.api.quota import router as quota_router
from app.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - 启动时创建数据库表
    - 关闭时清理资源
    """
    # 启动时创建所有数据库表
    Base.metadata.create_all(bind=engine)
    # 兼容性补齐（best-effort）
    ensure_schema_compatibility()
    yield
    # 关闭时的清理操作（如果需要）


app = FastAPI(
    title="Auto Score Analyzer",
    description="智能成绩分析系统 - 支持多用户认证、配额管理和引荐系统",
    version="2.0.2",
    lifespan=lifespan
)

# 配置CORS
# - 默认兼容本地 Vite(5173/3000) 与生产域名
# - 如需覆盖，请在环境变量/ backend/.env 中设置：CORS_ORIGINS="https://a.com,http://localhost:3000"
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "https://xscore-app.com",
    "https://www.xscore-app.com",
    "https://ca-score-analyzer-frontend.blackwave-bc3cb801.eastasia.azurecontainerapps.io",
]

def _parse_cors_origins(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []

    parts: list[str]
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                parts = [str(x) for x in data]
            else:
                parts = [raw]
        except Exception:
            parts = [raw]
    else:
        parts = raw.split(",")

    cleaned: list[str] = []
    for item in parts:
        origin = str(item).strip()
        origin = origin.strip('"\'')
        origin = origin.strip()
        if origin:
            cleaned.append(origin)

    return cleaned


raw_cors_origins = os.getenv("CORS_ORIGINS") or (settings.CORS_ORIGINS or "")
origins = _parse_cors_origins(raw_cors_origins) or default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api", tags=["认证"])
app.include_router(quota_router, prefix="/api", tags=["配额"])
app.include_router(admin_router, prefix="/api", tags=["管理员"])
app.include_router(api_router, prefix="/api", tags=["成绩分析"])

@app.get("/")
async def root():
    return {
        "message": "欢迎使用 Auto Score Analyzer",
        "version": "2.0.2",
        "features": [
            "用户认证系统",
            "配额管理",
            "引荐系统",
            "管理员后台",
            "智能成绩分析"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "auto-score-analyzer",
        "version": "2.0.2"
    } 
