# 本地开发环境快速启动指南

## 📋 前提条件

- Python 3.13+
- Node.js 18+
- 已配置 `backend/.env` 文件

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

### 停止服务

按 `Ctrl+C`

---

## 🔄 开发工作流

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

### 场景4：提交代码到GitHub（触发自动部署）

```powershell
# 在项目根目录
cd D:\Projects\2025\auto-score-analyzer

git add .
git commit -m "Your changes description"
git push
```

推送后会自动触发GitHub Actions部署到Azure VM！

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

## 📊 三个环境对比

| 环境 | 位置 | 后端URL | 前端URL | 用途 |
|------|------|---------|---------|------|
| **本地开发** | 你的电脑 | http://localhost:8000 | http://localhost:5173 | 日常开发 |
| **本地Docker** | 你的电脑 | http://localhost/api | http://localhost | 测试Docker |
| **生产环境** | Azure VM | http://40.81.16.161/api | http://40.81.16.161 | 线上服务 |

---

## ⚠️ 注意事项

### 环境变量

- **本地开发：** 使用 `backend/.env`
- **生产环境：** 使用 VM上的 `/opt/auto-score-analyzer/.env`
- 两个文件**独立配置**，互不影响

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
