"""
添加 analysis_result 字段到 score_files 表
"""
import sqlite3
import sys
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / "score_analyzer.db"

def migrate():
    """添加 analysis_result 列"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(score_files)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'analysis_result' not in columns:
            print("添加 analysis_result 列...")
            cursor.execute("""
                ALTER TABLE score_files 
                ADD COLUMN analysis_result TEXT
            """)
            conn.commit()
            print("✅ analysis_result 列添加成功")
        else:
            print("ℹ️  analysis_result 列已存在，跳过")
        
        conn.close()
        print("\n✨ 数据库迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
