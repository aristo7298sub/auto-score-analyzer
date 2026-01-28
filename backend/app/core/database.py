"""数据库配置和连接管理"""

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# 数据库URL配置
# 通过 Settings 读取，确保 backend/.env 生效
DATABASE_URL = settings.DATABASE_URL


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


def ensure_schema_compatibility() -> None:
    """Best-effort schema patching for backward compatibility.

    The project historically relied on create_all and manual DB setup across environments.
    To avoid breaking existing DBs when introducing small additive columns, we patch them
    at startup if missing.

    This is intentionally minimal and only covers additive, non-breaking columns.
    """

    try:
        insp = inspect(engine)
        dialect = getattr(engine.dialect, "name", "")
        if 'users' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('users')}
            if 'vip_expires_at' not in cols:
                with engine.begin() as conn:
                    vip_col_type = 'TIMESTAMPTZ' if dialect == 'postgresql' else 'TIMESTAMP'
                    conn.execute(text(f'ALTER TABLE users ADD COLUMN vip_expires_at {vip_col_type} NULL'))

            # Email verification fields (stage-1 auth)
            if 'email_verified_at' not in cols:
                with engine.begin() as conn:
                    try:
                        verified_at_type = 'TIMESTAMPTZ' if dialect == 'postgresql' else 'TIMESTAMP'
                        conn.execute(text(f'ALTER TABLE users ADD COLUMN email_verified_at {verified_at_type} NULL'))
                    except Exception:
                        pass

            if 'email_verified' not in cols:
                with engine.begin() as conn:
                    try:
                        # SQLite accepts 0/1 for booleans; Postgres expects TRUE/FALSE.
                        default_expr = "0" if dialect == "sqlite" else "FALSE"
                        conn.execute(text(f'ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT {default_expr}'))
                        # Best-effort backfill: if the DB already had email_verified_at, keep semantics consistent.
                        try:
                            conn.execute(text('UPDATE users SET email_verified = TRUE WHERE email_verified_at IS NOT NULL'))
                        except Exception:
                            pass
                    except Exception:
                        pass

        if 'analysis_logs' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('analysis_logs')}
            to_add = []
            if 'prompt_tokens' not in cols:
                to_add.append(('prompt_tokens', 'INTEGER', '0'))
            if 'completion_tokens' not in cols:
                to_add.append(('completion_tokens', 'INTEGER', '0'))

            if to_add:
                with engine.begin() as conn:
                    for name, col_type, default in to_add:
                        try:
                            conn.execute(text(f'ALTER TABLE analysis_logs ADD COLUMN {name} {col_type} DEFAULT {default}'))
                        except Exception:
                            pass
    except Exception:
        # Do not block app startup; environments that manage schema via Alembic can ignore this.
        pass

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
