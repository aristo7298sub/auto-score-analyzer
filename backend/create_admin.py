"""
创建管理员账号脚本
用法: python create_admin.py
"""
import sys
import os
from getpass import getpass

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import get_password_hash
import uuid

def generate_referral_code():
    """生成唯一的引荐码"""
    return str(uuid.uuid4())[:8].upper()

def create_admin():
    print("=" * 50)
    print("创建管理员账号")
    print("=" * 50)
    
    # 获取用户输入
    username = "aristo7298"
    email = input("请输入邮箱地址: ").strip()
    
    if not email:
        print("❌ 邮箱不能为空")
        return
    
    password = getpass("请输入密码: ")
    password_confirm = getpass("请再次输入密码: ")
    
    if password != password_confirm:
        print("❌ 两次密码不一致")
        return
    
    if len(password) < 6:
        print("❌ 密码长度至少6个字符")
        return
    
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"⚠️  用户 {username} 已存在")
            choice = input("是否将其设置为管理员? (y/n): ").strip().lower()
            if choice == 'y':
                existing_user.is_admin = True
                db.commit()
                print(f"✅ 用户 {username} 已设置为管理员")
            return
        
        # 创建新用户
        hashed_password = get_password_hash(password)
        referral_code = generate_referral_code()
        
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=True,  # 设置为管理员
            is_active=True,
            is_vip=True,  # 管理员默认开通VIP
            quota_balance=10000,  # 给予初始配额
            referral_code=referral_code,
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print("\n" + "=" * 50)
        print("✅ 管理员账号创建成功！")
        print("=" * 50)
        print(f"用户名: {new_user.username}")
        print(f"邮箱: {new_user.email}")
        print(f"管理员: {'是' if new_user.is_admin else '否'}")
        print(f"VIP: {'是' if new_user.is_vip else '否'}")
        print(f"配额余额: {new_user.quota_balance}")
        print(f"引荐码: {new_user.referral_code}")
        print("=" * 50)
        print("\n现在可以使用以下信息登录:")
        print(f"  用户名: {username}")
        print(f"  密码: ********")
        print(f"\n访问管理后台: http://localhost:3000/admin")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建失败: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
