from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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
    version="2.0.0",
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
]

if settings.CORS_ORIGINS:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
else:
    origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
        "version": "2.0.0",
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
        "version": "2.0.0"
    } 
