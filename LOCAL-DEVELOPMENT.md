# 本地开发环境快速启动指南

本项目支持三种长期维护的环境模式：

- **A. 纯本地（除 Azure OpenAI 外）**：数据库/文件存储都在本机
- **B. 本地开发 + 云端数据库（Hybrid）**：代码在本机跑，账号/配额/历史记录走云端 DB
- **C. 纯云端（Azure Container Apps）**：前后端都在 ACA

详情见 [ENVIRONMENTS.md](ENVIRONMENTS.md)。

## 📋 前提条件

- Python 3.11+
- Node.js 18+
- 已配置 `backend/.env` 文件（该文件不提交到 GitHub）

---

## 🚀 启动后端（FastAPI）

### 1. 进入后端目录并激活虚拟环境

```powershell
cd D:\Projects\2025\auto-score-analyzer\backend
.\venv\Scripts\Activate.ps1
```

### 2. 安装依赖（首次或更新后）

```powershell
pip install -r requirements.txt
```

### 3. 启动开发服务器

```powershell
python run.py
```

后端运行在：**http://localhost:8000**

- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 停止服务

按 `Ctrl+C`

---

## 🎨 启动前端（React + Vite）

### 1. 进入前端目录

```powershell
cd D:\Projects\2025\auto-score-analyzer\frontend
```

### 2. 安装依赖（首次或更新后）

```powershell
npm install
```

### 3. 启动开发服务器

```powershell
npm run dev
```

前端运行在：**http://localhost:5173**

> 注：本仓库默认 Vite 端口为 3000；请以终端输出的实际地址为准。

### 停止服务

按 `Ctrl+C`

---

## 🔄 开发工作流

### 选择环境模式

- **纯本地（推荐默认）**
	- 使用模板：`backend/.env.local.example`
	- 关键点：`DATABASE_URL=sqlite:...` + `STORAGE_TYPE=local`
	- 说明：除 Azure OpenAI 调用外，其它均本地

- **本地开发 + 云端数据库（Hybrid）**
	- 使用模板：`backend/.env.clouddb.example`
	- 关键点：`DATABASE_URL=postgresql+psycopg2://...`
	- 说明：会直接影响云端用户/配额/历史记录，请使用测试账号

### 场景1：修改后端代码

1. 激活虚拟环境：`.\venv\Scripts\Activate.ps1`
2. 修改 `backend/app/` 下的代码
3. 保存后自动重载（FastAPI的热重载）
4. 访问 http://localhost:8000/docs 测试API

### 场景2：修改前端代码

1. 确保前端dev server运行中
2. 修改 `frontend/src/` 下的代码
3. 保存后浏览器自动刷新（Vite的HMR）
4. 访问 http://localhost:5173 查看效果

### 场景3：同时开发前后端

打开两个终端：

**终端1（后端）：**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run.py
```

**终端2（前端）：**
```powershell
cd frontend
npm run dev
```

### 上云（Azure Container Apps）

本项目生产/演示环境使用 Azure Container Apps（非 Azure VM）。推荐流程：

1) 本地检查：
- 前端：`npm run build`
- 后端：`python -m compileall -q .`

2) 构建 + 发布：参考 [ENVIRONMENTS.md](ENVIRONMENTS.md) 的 Cloud-All 发布模板。

```powershell
# 在项目根目录
cd D:\Projects\2025\auto-score-analyzer

git add .
git commit -m "Your changes description"
git push
```

推送代码不会自动发布到生产环境；Cloud-All（Azure Container Apps）发布方式请参考 [ENVIRONMENTS.md](ENVIRONMENTS.md) 与 [CONTAINER-APPS-DEPLOYMENT.md](CONTAINER-APPS-DEPLOYMENT.md)。

---

## 🐳 本地Docker测试（可选）

如果想在本地测试Docker环境：

```powershell
# 在项目根目录
docker-compose up -d --build

# 访问
# http://localhost (前端)
# http://localhost/api (后端API)

# 停止
docker-compose down
```

---

## 📊 环境对比（简表）

| 模式 | 数据库 | 文件存储 | 运行位置 | 用途 |
|------|--------|----------|----------|------|
| **A. 纯本地** | 本地 SQLite | 本地目录 | 本机 | 日常开发/安全验证 |
| **B. Hybrid** | 云端 PostgreSQL | 本地（可选切云） | 本机 | 与线上账号/配额一致的联调 |
| **C. 纯云端** | 云端 PostgreSQL | Azure Blob | Azure Container Apps | 生产/演示 |

---

## ⚠️ 注意事项

### 环境变量

- **本地开发：** 使用 `backend/.env`
- **生产环境：** 使用 Azure Container Apps 注入的环境变量
- 两个文件**独立配置**，互不影响

#### 模型配置（全能解析 / AI 分析）

后端已支持“解析/分析模型分离”，并且**统一通过环境变量**配置：

- **解析（Preview/Confirm 里的 AI 推断映射）**：
	- `PARSING_MODEL`：建议填你的 Azure OpenAI **部署名（deployment name）**，例如 `o4-mini` 或你实际创建的部署名
	- `PARSING_REASONING_EFFORT`：`low|medium|high`（默认 `high`）

- **分析（一键 AI 分析）**：
	- `ANALYSIS_MODEL`：同样填部署名
	- `ANALYSIS_TEMPERATURE`：非推理模型可用（默认 `0.5`）

回退规则（为了本地更好用）：
- 如果你**没有配置** `PARSING_MODEL`，系统会自动回退使用 `ANALYSIS_MODEL`。

本地最小必配（能跑通 Preview/Confirm + Analyze）：
```env
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_RESPONSES_URL=https://<your-resource>.openai.azure.com/openai/v1/responses

# 推荐：直接填部署名（deployment name）
ANALYSIS_MODEL=<your-analysis-deployment>
PARSING_MODEL=<your-parsing-deployment>
```

PowerShell 临时设置（不写入文件，仅当前终端生效）：
```powershell
$env:AZURE_OPENAI_API_KEY = "<your-api-key>"
$env:AZURE_OPENAI_RESPONSES_URL = "https://<your-resource>.openai.azure.com/openai/v1/responses"
$env:PARSING_MODEL = "<your-parsing-deployment>"
$env:ANALYSIS_MODEL = "<your-analysis-deployment>"

python run.py
```

### 认证与邮箱（注册验证 / 忘记密码 / 绑定邮箱）

当前系统的日常登录方式为：**用户名 + 密码**（不使用“邮箱验证码登录”）。

邮箱仅用于以下场景：
- 注册邮箱验证码（防垃圾账号）
	- `POST /api/auth/email/send-verification-code`
	- `POST /api/auth/register`
- 忘记密码 / 重置密码（统一提示，不暴露邮箱是否存在）
	- `POST /api/auth/password/reset/request`
	- `POST /api/auth/password/reset/confirm`
- 登录后绑定邮箱（以及确认绑定）
	- `POST /api/auth/email/bind/request`
	- `POST /api/auth/email/bind/confirm`

安全策略（当前后端默认实现）：
- 验证码：6 位数字
- TTL：10 分钟
- 单次使用：成功后标记为已使用
- 错误次数限制：最多 5 次（超过后需要重新获取）
- 发送冷却：同一邮箱同一用途 60 秒内不会重复发送

开发环境注意：
- 邮件发送支持切换到 Azure Communication Services（ACS）。本地默认 `EMAIL_PROVIDER=dev` 会将验证码打印到后端日志；生产环境建议 `EMAIL_PROVIDER=acs` 并配置 `ACS_EMAIL_CONNECTION_STRING` / `ACS_EMAIL_SENDER`。
- 登录仅用户名+密码；邮箱不作为登录标识。

#### 本地启用 ACS（真发验证码邮件）

你可以在本地跑后端，但让验证码邮件通过 ACS 真正发出（推荐用于联调注册流程）。

1) 在 Azure Portal 创建资源
- 创建 **Azure Communication Services**（Communication Services）资源。
- 进入该资源的 **Email** 功能（Email / Email services）。

2) 配置发件人（Sender / From）
- 选择一种方式：
	- **Azure 托管域名（最快）**：使用 Azure 提供/托管的发件域名（适合开发联调）。
	- **自有域名（更正规）**：把你的域名接入并按提示配置 DNS（通常需要 SPF/DKIM 等记录）。
- 在 Email 配置里创建/选择一个可用的发件人地址（From），例如：
	- `no-reply@<primary-domain>`（自有域名）
	- 或 Azure 托管域名下的发件地址（以 Portal 实际显示为准）

3) 获取连接串（Connection String）
- 进入 Communication Services 资源的 **Keys**（密钥/连接字符串）页面。
- 复制 **Connection string**（不要提交到 GitHub）。

4) 在本地后端启用 ACS

在 `backend/.env`（不入库）中写入：

```env
# 邮件服务切换：dev | acs | disabled
EMAIL_PROVIDER=acs

# ACS Email（仅在 EMAIL_PROVIDER=acs 时必填）
ACS_EMAIL_CONNECTION_STRING=<your-acs-connection-string>
ACS_EMAIL_SENDER=<your-verified-sender-email>

# 建议本地关闭“把验证码打印到日志”（避免误用）
EMAIL_LOG_CODES_IN_DEV=false
```

5) 启动后端并验证
- 启动后端：`python run.py`
- 打开前端 `/register`：填写邮箱 → 点击“发送注册验证码” → 收到邮件 → 填写验证码完成注册。

常见问题排查：
- 若返回 500 且提示“验证码发送失败”：优先检查 `ACS_EMAIL_SENDER` 是否已在 ACS 中验证可用；连接串是否复制完整；以及 Email 功能是否已正确启用。
- 若邮件进入垃圾箱：自有域名方式需要正确配置 SPF/DKIM；开发期建议先用 Azure 托管域名联调。

### 端口占用

如果端口被占用：

```powershell
# 查找占用8000端口的进程
netstat -ano | findstr :8000

# 杀死进程（替换PID）
taskkill /PID <PID> /F
```

### 虚拟环境问题

如果虚拟环境损坏，重新创建：

```powershell
cd backend
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🎯 常用命令速查

```powershell
# 后端
cd backend
.\venv\Scripts\Activate.ps1         # 激活虚拟环境
python run.py                        # 启动后端
deactivate                           # 退出虚拟环境

# 前端
cd frontend
npm install                          # 安装依赖
npm run dev                          # 启动开发服务器
npm run build                        # 构建生产版本
npm run preview                      # 预览生产版本

# Git
git status                           # 查看状态
git add .                            # 添加所有更改
git commit -m "message"              # 提交
git push                             # 推送（触发自动部署）
git pull                             # 拉取最新代码

# Docker（本地测试）
docker-compose up -d --build         # 启动
docker-compose logs -f               # 查看日志
docker-compose ps                    # 查看状态
docker-compose down                  # 停止
```

---

## 🔧 故障排除

### 后端启动失败

1. 确认虚拟环境已激活（命令行前面有 `(venv)`）
2. 检查 `backend/.env` 文件是否存在
3. 检查Azure OpenAI配置是否正确
4. 重新安装依赖：`pip install -r requirements.txt`

### 前端启动失败

1. 删除 `node_modules` 和 `package-lock.json`
2. 重新安装：`npm install`
3. 清理缓存：`npm cache clean --force`

### API调用失败

1. 确认后端正在运行（http://localhost:8000/health）
2. 检查前端的API地址配置
3. 查看浏览器控制台的错误信息
4. 查看后端终端的日志输出
