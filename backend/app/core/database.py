"""数据库配置和连接管理"""

import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# 数据库URL配置
# 容器环境中，确保SQLite文件存储在有写权限的目录
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/score_analyzer.db")


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")

# 创建数据库引擎
engine_kwargs = {
    "pool_pre_ping": True,
}

if _is_sqlite(DATABASE_URL):
    engine_kwargs.update(
        {
            "connect_args": {"check_same_thread": False},
            # Avoid reusing a bad connection/transaction in SQLite.
            "poolclass": NullPool,
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 依赖注入：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Ensure failed transactions don't poison the next operation.
        db.rollback()
        raise
    finally:
        db.close()
