"""
数据库迁移脚本 - 添加 file_size 列到 score_files 表
"""
import sqlite3
import os
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / "score_analyzer.db"

def migrate():
    """执行数据库迁移"""
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(score_files)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'file_size' in columns:
            print("✅ file_size 列已存在,无需迁移")
            return
        
        # 添加 file_size 列
        print("🔄 开始添加 file_size 列...")
        cursor.execute("""
            ALTER TABLE score_files 
            ADD COLUMN file_size INTEGER
        """)
        
        conn.commit()
        print("✅ 成功添加 file_size 列到 score_files 表")
        
        # 验证
        cursor.execute("PRAGMA table_info(score_files)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 当前列: {', '.join(columns)}")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
