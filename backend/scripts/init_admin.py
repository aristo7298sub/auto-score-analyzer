"""
创建管理员账号脚本
用于初始化数据库和创建第一个管理员用户
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash, generate_referral_code

def init_database():
    """初始化数据库表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建成功")

def create_admin(username: str, password: str, email: str = None):
    """创建管理员账号"""
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"✗ 用户 {username} 已存在")
            return False
        
        # 创建管理员用户
        admin_user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            referral_code=generate_referral_code(),
            quota_balance=10000,  # 管理员初始配额
            is_admin=True,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"\n✓ 管理员账号创建成功！")
        print(f"  用户名: {username}")
        print(f"  邮箱: {email or '未设置'}")
        print(f"  配额: {admin_user.quota_balance}")
        print(f"  引荐码: {admin_user.referral_code}")
        print(f"  管理员: 是")
        
        return True
    except Exception as e:
        print(f"✗ 创建失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("AI成绩分析平台 - 管理员账号初始化")
    print("=" * 50)
    
    # 初始化数据库
    init_database()
    
    # 从环境变量或使用默认值创建管理员
    admin_username = os.getenv("ADMIN_USERNAME", "aristo7298")
    admin_password = os.getenv("ADMIN_PASSWORD", "aristo7298")  # 生产环境请使用强密码！
    admin_email = os.getenv("ADMIN_EMAIL", "aristo7298@example.com")
    
    print(f"\n正在创建管理员账号: {admin_username}")
    success = create_admin(admin_username, admin_password, admin_email)
    
    if success:
        print("\n✓ 初始化完成！现在可以使用以下凭据登录：")
        print(f"  URL: https://xscore-app.com")
        print(f"  用户名: {admin_username}")
        print(f"  密码: {admin_password}")
        print("\n⚠️  请在首次登录后立即修改密码！")
    else:
        print("\n✗ 初始化失败")
        sys.exit(1)
