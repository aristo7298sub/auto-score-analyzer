from pydantic_settings import BaseSettings
from typing import Optional, Literal
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "学生成绩分析系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # 数据库配置
    # 默认使用相对路径：
    # - 本地运行（cd backend） => backend/data/score_analyzer.db
    # - 容器运行（WORKDIR=/app） => /app/data/score_analyzer.db
    DATABASE_URL: str = "sqlite:///./data/score_analyzer.db"
    
    # Azure OpenAI配置
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None

    # Azure OpenAI Responses API（阶段性：按 /openai/v1/responses 调用）
    # 推荐直接设置完整 URL："https://<resource>.openai.azure.com/openai/v1/responses"
    # 若未设置，则会根据 AZURE_OPENAI_ENDPOINT 推导。
    AZURE_OPENAI_RESPONSES_URL: Optional[str] = None

    # 解析/总结模型分离（纯配置）
    # 在 /responses API 下，直接填写请求 body 的 model 字段值。
    PARSING_MODEL: Optional[str] = None
    PARSING_REASONING_EFFORT: str = "high"

    ANALYSIS_MODEL: Optional[str] = None
    ANALYSIS_TEMPERATURE: float = 0.5

    OPENAI_REQUEST_TIMEOUT_SECONDS: float = 60.0
    
    # Azure Storage 配置
    STORAGE_TYPE: Literal["local", "azure"] = "local"
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None
    AZURE_STORAGE_BLOB_ENDPOINT: Optional[str] = None
    
    # Blob Container 名称
    AZURE_STORAGE_UPLOADS_CONTAINER: str = "uploads"
    AZURE_STORAGE_EXPORTS_CONTAINER: str = "exports"
    AZURE_STORAGE_CHARTS_CONTAINER: str = "charts"
    
    # 本地存储路径（仅当 STORAGE_TYPE=local 时使用）
    LOCAL_UPLOADS_DIR: str = "uploads"
    LOCAL_EXPORTS_DIR: str = "exports"
    LOCAL_CHARTS_DIR: str = "static/charts"
    LOCAL_DATA_DIR: str = "data"
    
    # 应用配置
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 前端配置（仅用于参考）
    BACKEND_URL: Optional[str] = None
    CORS_ORIGINS: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # Debug logging knobs
    # Whether to print the full request body sent to Azure OpenAI /responses.
    # WARNING: may contain student names and file preview content.
    LOG_AOAI_REQUEST_BODY: bool = False
    # Safety cap to avoid flooding logs; increase locally if you truly need full payload.
    LOG_AOAI_REQUEST_MAX_CHARS: int = 120000
    # Whether to print the AOAI returned output text (already extracted from response JSON).
    LOG_AOAI_RESPONSE_TEXT: bool = False
    
    class Config:
        # Load backend/.env no matter where the server is launched from.
        # Also allow a local override via a cwd ".env" if present.
        env_file = (
            str(Path(__file__).resolve().parents[2] / ".env"),
            ".env",
        )
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量

settings = Settings() 