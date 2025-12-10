from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import engine, Base
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
    yield
    # 关闭时的清理操作（如果需要）


app = FastAPI(
    title="Auto Score Analyzer",
    description="智能成绩分析系统 - 支持多用户认证、配额管理和引荐系统",
    version="2.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体域名
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