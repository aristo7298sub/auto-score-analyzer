# AI成绩分析平台

基于 Azure OpenAI 的智能学生成绩分析系统，支持 Excel/Word/PPT 文件上传、AI 智能分析、个性化建议生成和报告导出。

## 🌍 环境模式（同一套代码，靠环境变量切换）

本仓库长期维护三种运行方式：

- **A. Local-All（纯本地，除 Azure OpenAI 外）**：本地 SQLite + 本地文件存储
- **B. Hybrid（本地代码 + 云端数据库）**：本地跑前后端，数据库（以及可选的文件存储）走云端
- **C. Cloud-All（纯云端）**：Azure Container Apps（生产/演示）

详细说明与发布模板见：
- [docs/README.md](docs/README.md)
- [docs/guides/environments.md](docs/guides/environments.md)
- [docs/guides/local-development.md](docs/guides/local-development.md)

## ✨ 核心功能

### 🎯 成绩分析
- **多格式支持**: 支持 .xlsx, .docx, .pptx 格式文件
- **智能解析**: 自动识别学生姓名、总分和扣分项
- **批量分析**: 并发处理多个学生成绩,最高支持50并发
- **AI建议**: 基于Azure OpenAI GPT-4生成个性化学习建议

### 👤 用户系统
- **账户管理**: 注册/登录/登出
- **配额系统**: 基于配额的使用计费(1学生=1配额)
- **VIP特权**: VIP用户无限配额
- **推荐奖励**: 推荐新用户获得配额奖励

### 📊 管理后台
- **用户管理**: VIP设置、账户启用/禁用、配额充值
- **数据统计**: 实时用户数、分析总数、配额消耗统计
- **分析日志**: 查看所有分析记录和状态
- **隐藏访问**: 仅通过 `/admin` 路径访问,不在导航显示

### 🎨 UI/UX
- **莫兰迪配色**: 柔和舒适的教育主题色调
- **响应式设计**: 完美适配桌面和移动设备
- **国际化**: 中英文切换支持
- **主题切换**: 明暗主题切换

### 📥 导出功能
- **Excel导出**: 包含详细分析数据的Excel表格
- **Word导出**: 格式化的分析报告文档

## 🚀 快速开始

### 前置要求

- Node.js 18+
- Python 3.11+
- Azure OpenAI API 访问权限

### 本地开发

#### 1. 克隆仓库

```bash
git clone https://github.com/aristo7298sub/auto-score-analyzer.git
cd auto-score-analyzer
```

#### 2. 配置环境变量

创建 `backend/.env` 文件（不要提交到 GitHub）：

- Local-All：参考模板 `backend/.env.local.example`
- Hybrid：参考模板 `backend/.env.clouddb.example`

```env
# Azure OpenAI 配置（必填）
AZURE_OPENAI_API_KEY=your-api-key

# 推荐（新架构）：Responses API + 模型分离
# - 直接使用 /openai/v1/responses
# - `PARSING_MODEL` / `ANALYSIS_MODEL` 填写 Azure OpenAI 的部署名（deployment name）
AZURE_OPENAI_RESPONSES_URL=https://your-resource.openai.azure.com/openai/v1/responses
PARSING_MODEL=o4-mini
PARSING_REASONING_EFFORT=high
ANALYSIS_MODEL=gpt-4.1-nano
ANALYSIS_TEMPERATURE=0.5

# 数据库
# Local-All 示例：
DATABASE_URL=sqlite:///./data/score_analyzer.db
# Hybrid 示例：
# DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME

# 存储配置(本地开发使用local)
STORAGE_TYPE=local

# 应用配置
DEBUG=True
HOST=0.0.0.0
PORT=8000
BACKEND_URL=http://localhost:8000
# 逗号分隔："http://localhost:3000,http://localhost:5173"
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
```

#### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端运行在 http://localhost:8000
API文档: http://localhost:8000/docs

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行端口以 Vite 输出为准（默认配置为 http://localhost:3000）。

#### 5. 设置管理员（可选）

管理员权限需要在数据库中将用户的 `is_admin` 设置为 `true`，详见 [docs/reference/admin-guide.md](docs/reference/admin-guide.md)。


### 生产部署

生产/演示环境使用 Azure Container Apps（不再使用 Azure VM）。

- 部署：见 [docs/guides/container-apps-deployment.md](docs/guides/container-apps-deployment.md)
- 自定义域名：见 [docs/guides/domain-setup.md](docs/guides/domain-setup.md)

## 📦 项目结构

```
auto-score-analyzer/
├── backend/          # Python FastAPI 后端
├── frontend/         # React + TypeScript + Vite 前端
├── docs/             # 项目文档（入口见 docs/README.md）
├── docker-compose.yml
└── README.md
```

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI 0.104+
- **数据库**: SQLite (开发) / PostgreSQL (生产可选)
- **ORM**: SQLAlchemy
- **认证**: JWT + bcrypt
- **AI**: Azure OpenAI GPT-4
- **文件处理**: pandas, python-docx, python-pptx
- **存储**: 本地文件系统 / Azure Blob Storage

### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **UI组件**: Ant Design 5
- **状态管理**: Zustand
- **HTTP客户端**: Axios
- **国际化**: react-i18next
- **路由**: React Router 6

## 📝 API文档

启动后端后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要接口

#### 认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/email/send-verification-code` - 发送注册邮箱验证码（统一提示，不暴露邮箱是否存在）
- `POST /api/auth/password/reset/request` - 发起重置密码（统一提示，不暴露邮箱是否存在）
- `POST /api/auth/password/reset/confirm` - 使用验证码重置密码
- `POST /api/auth/email/bind/request` - 登录后绑定邮箱：发送绑定验证码
- `POST /api/auth/email/bind/confirm` - 登录后绑定邮箱：确认绑定
- `GET /api/auth/me` - 获取当前用户信息

说明：
- 注册必须提供邮箱与验证码（先调用 `POST /api/auth/email/send-verification-code` 获取验证码）。
- 当前日常登录方式为：用户名 + 密码（邮箱不作为登录标识）。

### 本地用 ACS 真发邮件验证码（可选，但推荐联调注册）

默认本地 `EMAIL_PROVIDER=dev` 会把验证码打印到后端日志。若你希望在本地开发时也能真正收到验证码邮件：

1) 在 Azure Portal 创建 **Azure Communication Services** 资源并启用 **Email** 功能。
2) 配置一个可用的发件人地址（Sender/From，需要在 ACS 中验证可用）。
3) 在 `backend/.env`（不要提交到 GitHub）中设置：

```env
EMAIL_PROVIDER=acs
ACS_EMAIL_CONNECTION_STRING=<your-acs-connection-string>
ACS_EMAIL_SENDER=<your-verified-sender-email>
EMAIL_LOG_CODES_IN_DEV=false
```

更详细步骤见 [docs/guides/local-development.md](docs/guides/local-development.md)。

#### 成绩分析
- `POST /api/upload` - 上传并分析成绩文件
- `GET /api/student/{name}` - 查询学生成绩
- `POST /api/export/{format}` - 导出分析报告

#### 配额管理
- `GET /api/quota/balance` - 查询配额余额
- `GET /api/quota/transactions` - 查询配额交易记录
- `GET /api/quota/referral/code` - 获取推荐码
- `GET /api/quota/referral/stats` - 查询推荐统计

#### 管理员
- `GET /api/admin/users` - 获取用户列表
- `POST /api/admin/users/set-vip` - 设置VIP
- `GET /api/admin/stats` - 获取系统统计
- `GET /api/admin/logs` - 获取分析日志

## 🔒 安全特性

- ✅ JWT Token 认证
- ✅ 密码 bcrypt 加密
- ✅ CORS 跨域保护
- ✅ SQL注入防护 (SQLAlchemy ORM)
- ✅ 文件类型验证
- ✅ 配额限制防滥用

## 🎯 使用流程

1. **注册账户**: 访问注册页面创建账户(邮箱可选)
2. **获取配额**: 新用户默认10配额,可通过推荐获得更多
3. **上传文件**: 支持 Excel/Word/PPT 格式的成绩文件
4. **智能分析**: 系统自动解析并调用AI生成个性化建议
5. **查看结果**: 实时查看分析结果和AI建议
6. **导出报告**: 导出Excel或Word格式的分析报告

## 🧪 开发相关

### 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 设置管理员

详见 [docs/reference/admin-guide.md](docs/reference/admin-guide.md)（包含 SQL 示例）。

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

### 代码格式化

```bash
# 后端
cd backend
black .
isort .

# 前端
cd frontend
npm run lint
npm run format
```

## 📄 许可证

MIT License

## 👨‍💻 作者

aristo7298sub

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📞 联系方式

如有问题或建议,请通过 GitHub Issues 联系。
