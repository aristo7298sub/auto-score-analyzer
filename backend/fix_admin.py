"""
修复管理员账号的 referral_code
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User

def fix_admin_referral_code():
    db = SessionLocal()
    
    try:
        # 查找 aristo7298 用户
        user = db.query(User).filter(User.username == "aristo7298").first()
        
        if not user:
            print("❌ 未找到用户 aristo7298")
            return
        
        # 如果没有 referral_code，生成一个
        if not user.referral_code:
            user.referral_code = str(uuid.uuid4())[:8].upper()
            db.commit()
            print(f"✅ 已为用户 {user.username} 生成引荐码: {user.referral_code}")
        else:
            print(f"✅ 用户已有引荐码: {user.referral_code}")
            
    except Exception as e:
        db.rollback()
        print(f"❌ 修复失败: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_referral_code()
