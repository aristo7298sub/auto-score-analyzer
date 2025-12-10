# 后端API文档

## 认证系统测试通过 ✅

### 已实现功能

#### 1. 用户认证 (`/api/auth`)
- ✅ `POST /api/auth/register` - 用户注册
  - 支持引荐码
  - 新用户获得10配额（使用引荐码+5）
  - 引荐人获得5配额奖励
- ✅ `POST /api/auth/login` - 用户登录
  - 返回JWT token（7天有效期）
- ✅ `GET /api/auth/me` - 获取当前用户信息（需认证）
- ✅ `POST /api/auth/logout` - 用户登出

#### 2. 配额管理 (`/api/quota`)
- ✅ `GET /api/quota/balance` - 查询配额余额（需认证）
- ✅ `POST /api/quota/check` - 检查配额是否足够（需认证）
- ✅ `GET /api/quota/transactions` - 获取配额交易记录（需认证）
- ✅ `POST /api/quota/admin/add` - 管理员添加配额（需管理员权限）
- ✅ `GET /api/quota/referral/code` - 获取引荐码（需认证）
- ✅ `GET /api/quota/referral/stats` - 获取引荐统计（需认证）

#### 3. 管理员功能 (`/api/admin`)
- ✅ `GET /api/admin/users` - 获取所有用户列表（需管理员权限）
- ✅ `POST /api/admin/users/set-vip` - 设置VIP状态（需管理员权限）
- ✅ `POST /api/admin/users/{user_id}/toggle-active` - 启用/禁用账号（需管理员权限）
- ✅ `GET /api/admin/stats` - 获取系统统计数据（需管理员权限）
- ✅ `GET /api/admin/logs` - 获取所有分析日志（需管理员权限）
- ✅ `GET /api/admin/users/{user_id}/logs` - 获取用户分析日志（需管理员权限）

#### 4. 成绩分析 (`/api`)
- ✅ `POST /api/upload` - 上传成绩文件（需认证，扣除配额）
  - 自动检查配额（1学生=1配额）
  - VIP用户无限配额
  - 记录分析日志和文件
- ✅ `GET /api/student/{student_name}` - 查询学生成绩
- ✅ `GET /api/search` - 搜索学生
- ✅ `POST /api/export/{format}` - 导出成绩（xlsx/docx）
- ✅ `GET /api/charts` - 获取所有图表
- ✅ `GET /api/charts/{chart_type}` - 获取特定图表

### 数据模型

#### User（用户）
- `id` - 用户ID
- `username` - 用户名（唯一）
- `email` - 邮箱（唯一）
- `hashed_password` - 密码哈希
- `is_active` - 账号是否激活
- `is_vip` - VIP状态（无限配额）
- `is_admin` - 管理员权限
- `quota_balance` - 配额余额
- `quota_used` - 已使用配额
- `referral_code` - 引荐码（唯一）
- `referred_by` - 被谁引荐（用户ID）
- `referral_count` - 成功引荐人数
- `created_at` - 注册时间
- `last_login` - 最后登录时间

#### QuotaTransaction（配额交易）
- `id` - 交易ID
- `user_id` - 用户ID
- `transaction_type` - 交易类型
  - `register` - 注册奖励
  - `referral` - 引荐奖励
  - `admin_add` - 管理员添加
  - `analysis_cost` - 分析消耗
  - `refund` - 退款
- `amount` - 金额（正数增加，负数扣除）
- `balance_after` - 交易后余额
- `description` - 描述
- `created_at` - 交易时间

#### AnalysisLog（分析日志）
- `id` - 日志ID
- `user_id` - 用户ID
- `filename` - 文件名
- `file_type` - 文件类型（xlsx/docx/pptx）
- `student_count` - 学生数量
- `status` - 状态（success/failed/processing）
- `error_message` - 错误信息
- `quota_cost` - 配额消耗
- `processing_time` - 处理时间（秒）
- `created_at` - 创建时间

#### ScoreFile（成绩文件）
- `id` - 文件ID
- `user_id` - 用户ID
- `filename` - 文件名
- `file_size` - 文件大小（字节）
- `storage_url` - 存储URL
- `file_type` - 文件类型
- `student_count` - 学生数量
- `analysis_completed` - 是否完成分析
- `uploaded_at` - 上传时间
- `analyzed_at` - 分析时间

### 测试结果

```bash
# 基础认证测试
✅ 用户注册 - 201 Created
✅ 用户登录 - 200 OK
✅ 获取用户信息 - 200 OK
✅ 查询配额 - 200 OK
✅ 获取引荐码 - 200 OK
✅ 使用引荐码注册 - 201 Created
✅ 引荐奖励正确发放
```

### 配置

#### 环境变量
```bash
# 数据库
DATABASE_URL=sqlite:///./score_analyzer.db  # 默认SQLite

# JWT
SECRET_KEY=your-secret-key-here  # 从环境变量读取
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Storage（可选）
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
```

### 下一步

现在后端已完成，需要开始前端开发：
1. 安装React Router和状态管理库（Zustand）
2. 实现登录/注册页面
3. 实现主应用布局和路由
4. 实现Morandi配色主题系统
5. 实现国际化（中英文切换）
