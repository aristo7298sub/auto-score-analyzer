#!/bin/bash
# 容器启动脚本 - 自动初始化数据库和管理员账号

set -e

echo "=========================================="
echo "AI成绩分析平台 - 容器启动"
echo "=========================================="

# 检查数据库文件是否存在
DB_PATH="${DATABASE_URL:-sqlite:////mnt/database/score_analyzer.db}"
DB_FILE=$(echo $DB_PATH | sed 's/sqlite:\/\/\///')

echo "数据库路径: $DB_FILE"

# 如果是首次启动（数据库文件不存在），初始化管理员账号
if [ ! -f "$DB_FILE" ]; then
    echo "检测到首次启动，正在初始化数据库和管理员账号..."
    python scripts/init_admin.py
else
    echo "数据库已存在，跳过初始化"
fi

# 启动应用
echo "启动应用服务..."
exec python run.py
