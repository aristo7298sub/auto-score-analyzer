# 数据库初始化与重置（当前架构）

本项目当前生产/演示环境使用 **PostgreSQL（云端）**，不再使用 “Azure Files 挂载 SQLite 文件” 的方案。

## Schema 初始化

- **本地开发（SQLite）**：应用启动时会自动创建表（并包含 best-effort 的 schema 兼容补齐逻辑）。
- **生产/演示（PostgreSQL）**：建议用迁移管理 schema；仓库已包含 Alembic 依赖。

如需手动执行迁移（可选）：

```bash
cd backend
alembic upgrade head
```

## 管理员设置

本项目不依赖“启动时自动创建默认管理员账号”。
管理员权限通过将用户的 `is_admin` 设置为 `true` 来授予，详见 [admin-guide.md](admin-guide.md)。

## 重置数据库（危险操作）

在 PostgreSQL 方案下，“重置数据库”通常意味着：
- 删除并重建数据库，或
- 清空 schema（drop schema / drop tables），再重新执行迁移。

具体操作方式取决于你使用的 PostgreSQL（Azure Database for PostgreSQL / 自建等），请在执行前确认备份策略。
