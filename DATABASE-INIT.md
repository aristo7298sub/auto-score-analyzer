# 数据库初始化指南

## 问题说明

配置 Azure Files 持久存储后，数据库文件是全新的，之前的用户数据已丢失。

## 解决方案

### 自动初始化（推荐）

容器启动时会自动检测并初始化：

1. **自动创建数据库表**
2. **自动创建管理员账号**（如果是首次启动）
   - 用户名: `aristo7298`
   - 密码: `aristo7298`
   - 配额: 10000
   - 权限: 管理员

### 手动初始化（本地测试）

如果需要在本地运行初始化脚本：

```bash
cd backend
python scripts/init_admin.py
```

### 自定义管理员账号

通过环境变量自定义：

```bash
# 设置环境变量
export ADMIN_USERNAME=your_username
export ADMIN_PASSWORD=your_password
export ADMIN_EMAIL=your_email@example.com

# 运行初始化
python scripts/init_admin.py
```

### Container App 环境变量

在 Azure Container App 中设置：

```bash
az containerapp update \
  --name ca-score-analyzer-backend \
  --resource-group auto-score-analyzer-dev \
  --set-env-vars \
    ADMIN_USERNAME=your_username \
    ADMIN_PASSWORD=your_password \
    ADMIN_EMAIL=your_email@example.com
```

## 默认管理员凭据

**⚠️ 生产环境请务必修改默认密码！**

- URL: https://xscore-app.com
- 用户名: `aristo7298`
- 密码: `aristo7298`
- 配额: 10000
- 引荐码: 自动生成

## 重置数据库

如果需要完全重置数据库：

### 方法 1: 删除 Azure Files 中的数据库文件

```bash
# 列出文件
az storage file list \
  --share-name database \
  --account-name autoscoreanalyzerstorage

# 删除数据库文件
az storage file delete \
  --share-name database \
  --path score_analyzer.db \
  --account-name autoscoreanalyzerstorage
```

### 方法 2: 重启 Container App

删除文件后重启容器，会自动重新初始化：

```bash
az containerapp revision restart \
  --name ca-score-analyzer-backend \
  --resource-group auto-score-analyzer-dev \
  --revision <revision-name>
```

## 验证

登录后检查：

1. 能否正常登录
2. 配额显示是否正确
3. 管理员权限是否生效
4. 引荐码是否生成

## 安全建议

1. ✅ 首次登录后立即修改密码
2. ✅ 生产环境使用强密码
3. ✅ 定期备份数据库文件
4. ✅ 启用 Azure Files 的软删除功能
