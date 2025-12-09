from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router

app = FastAPI(title="学生成绩分析系统")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "欢迎使用学生成绩分析系统"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "auto-score-analyzer",
        "version": "1.0.0"
    } 