import uvicorn
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash, generate_referral_code

def init_database():
    """初始化数据库和管理员账号"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✓ 数据库表已创建")
        
        # 检查是否需要创建管理员
        db = SessionLocal()
        try:
            admin_count = db.query(User).filter(User.is_admin == True).count()
            if admin_count == 0:
                print("检测到首次启动，创建管理员账号...")
                admin_user = User(
                    username=os.getenv("ADMIN_USERNAME", "aristo7298"),
                    email=os.getenv("ADMIN_EMAIL", "aristo7298@example.com"),
                    hashed_password=get_password_hash(os.getenv("ADMIN_PASSWORD", "aristo7298")),
                    referral_code=generate_referral_code(),
                    quota_balance=10000,
                    is_admin=True,
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                print(f"✓ 管理员账号已创建: {admin_user.username}")
            else:
                print(f"✓ 数据库已初始化 ({admin_count} 个管理员)")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠ 数据库初始化警告: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("AI成绩分析平台 - 启动")
    print("=" * 50)
    
    # 初始化数据库
    init_database()
    
    # 启动应用
    print("\n启动 FastAPI 服务...")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    ) 