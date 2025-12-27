# 排障与发布记录（Auto Score Analyzer）

> 目的：把这段时间遇到的问题、根因、修复与发布流程沉淀成可复用的参考。
> 
> 原则：不记录任何密钥/连接串/个人隐私数据；命令中一律使用占位符。

## 2025-12-14

### 涉及系统

- 前端：Vite + React（路由 `/history`, `/admin`）
- 后端：FastAPI + SQLAlchemy + PostgreSQL（生产）
- 存储：Azure Blob Storage（uploads/exports/charts）
- 部署：Azure Container Apps（Frontend / Backend 分别一个 App）
- 镜像：Azure Container Registry（ACR 远程构建）

### 问题清单与处理结果

#### 1) 用户注册后不是管理员（期望：管理员账号）

- 现象：注册后默认不是管理员。
- 根因：注册逻辑默认 `is_admin=false`（符合常见安全策略）。
- 处理：通过管理员能力或数据库更新将指定用户标记为管理员（以及 VIP）。
- 经验：
  - 管理员权限应通过受控流程授予（后台按钮/API/运维脚本），不应在注册时直接开放。

#### 2) `/api/upload` 上传返回 500：`name 'status' is not defined`

- 现象：浏览器端收到 500，`detail` 指向 `status` 未定义。
- 根因：后端上传端点使用了 `status.HTTP_402_PAYMENT_REQUIRED`，但缺少 `from fastapi import status`。
- 修复：补齐 `status` 导入。
- 验证：再次上传不再报 NameError。

#### 3) 配额不足应返回 402，却被包装成 500

- 现象：配额不足场景返回 500，body 中出现 `402: 配额不足...` 的字符串。
- 根因：上传处理内部使用了 `except Exception`，把 `HTTPException` 也当作未知异常捕获，重新包装为 500。
- 修复：在内层 `try` 中增加 `except HTTPException: raise`，让预期的 HTTP 错误透传。
- 验证：配额不足场景稳定返回 `402`。

#### 4) History 页面时间显示 `NaN-NaN-NaN NaN:NaN:NaN`

- 现象：历史记录中“上传时间/分析时间”渲染为 NaN。
- 根因：后端时间字段对带时区的 `datetime.isoformat()` 又额外拼接 `'Z'`，形成 `...+00:00Z` 的非法格式，浏览器 `new Date()` 解析失败。
- 修复：
  - 后端：直接返回 `isoformat()`，不再拼 `Z`。
  - 前端：日期格式化函数增加 invalid-date 兜底，避免出现 NaN。
- 预期效果：前端按用户浏览器 local time 展示。

#### 5) 管理员后台增加“直接删除用户”

- 需求：方便删除测试账号。
- 实现：
  - 后端：新增管理员专用 `DELETE /api/admin/users/{user_id}`
    - 禁止删除当前登录管理员自身。
    - 删除用户及其关联数据（依赖 SQLAlchemy 关系级联）。
    - best-effort 清理该用户上传文件的 blob（失败不阻断删除）。
  - 前端：admin 用户列表增加“删除用户”按钮 + 二次确认，调用删除接口后刷新列表。

### 发布流程（Azure Container Apps + ACR 远程构建）

#### 1) 核心思路

- 不依赖 GitHub Actions 是否同步：直接用 `az` 查询线上状态，然后构建并更新容器镜像。
- 建议使用“带时间戳的 tag”，确保可回滚、可追溯。

#### 2) 常用命令模板（占位符）

```powershell
$rg  = '<resource-group>'
$acr = '<acr-name>'
$tag = "fix-xxxx-$(Get-Date -Format yyyyMMdd-HHmmss)"

# 远程构建并推送
az acr build -r $acr -t "score-analyzer-backend:$tag"  -f backend/Dockerfile  backend
az acr build -r $acr -t "score-analyzer-frontend:$tag" -f frontend/Dockerfile frontend

$loginServer = (az acr show -n $acr --query loginServer -o tsv)
$backendImage  = "$loginServer/score-analyzer-backend:$tag"
$frontendImage = "$loginServer/score-analyzer-frontend:$tag"

# 更新 Container App 镜像
az containerapp update -g $rg -n <backend-app>  --image $backendImage
az containerapp update -g $rg -n <frontend-app> --image $frontendImage

# 检查 revision/健康/流量
az containerapp revision list -g $rg -n <backend-app>  -o table
az containerapp revision list -g $rg -n <frontend-app> -o table
```

#### 3) 冒烟验证建议

- 后端：`GET /health`、`GET /openapi.json`、上传/配额不足分支。
- 前端：`/history` 时间显示、`/admin` 删除用户按钮是否可用。

### 运维注意事项（避免踩坑）

- **不要把调试输出/配置导出 YAML**（含订阅/资源信息）提交到仓库。
- **不要提交本地数据库文件**（`.db/.sqlite`）。
- **不要提交数据目录**（uploads/exports/charts、示例成绩文件等）。
- 前端构建：若使用 `VITE_API_URL`，确保生产 `.env.production` 或构建参数正确，避免打包进 `localhost`。

### 变更回顾（本次落地的功能）

- 上传端点：错误处理与配额不足返回码修复。
- 历史记录：时间字段格式修复 + 前端格式化兜底。
- 管理后台：新增删除用户能力（后端 API + 前端按钮）。

---

如需继续完善：可以增加“软删除用户/保留审计日志”的策略，以及删除用户前的二次校验（例如输入用户名确认）。

## 2025-12-27 线上故障记录：登录被 CORS block，但根因是 DB 连接耗尽

> 关键词：`OPTIONS 400`、`Disallowed CORS origin`、revision 不健康、Postgres connection slots

### 1) 典型现象

- 浏览器控制台：`No 'Access-Control-Allow-Origin' header`
- Network：`OPTIONS /api/auth/login` 返回 `400` 或看不到 CORS 响应头
- Azure Container Apps：新 revision 反复 `Unhealthy/Degraded`，流量可能仍在旧 revision

### 2) 一线排查顺序（先确认“请求打到了哪”）

```powershell
$rg = '<resource-group>'
$backendApp = '<backend-app>'

# 1) 查当前最新 revision 与 readiness
az containerapp show -g $rg -n $backendApp --query "{activeRevisionsMode:properties.configuration.activeRevisionsMode,latestReadyRevisionName:properties.latestReadyRevisionName,latestRevisionName:properties.latestRevisionName}" -o json

# 2) 列出 revision 的健康与流量
az containerapp revision list -g $rg -n $backendApp -o table
```

### 3) 直接验证 CORS 预检（绕过浏览器）

```powershell
$backend = 'https://<your-backend-fqdn>'
curl.exe -i -X OPTIONS "$backend/api/auth/login" `
  -H "Origin: https://<your-frontend-domain>" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type" | findstr /I "HTTP/ access-control-allow-origin"
```

预期：`HTTP/1.1 200 OK` 且返回 `access-control-allow-origin: https://<your-frontend-domain>`。

### 4) 关键根因定位：看“最新 revision”的启动日志

如果你已经确认 `CORS_ORIGINS` 配置正确，但行为像没生效，优先检查日志是否出现 DB 连接耗尽：

```powershell
$rev = '<latest-revision-name>'
az containerapp logs show -g $rg -n $backendApp --revision $rev --tail 200
```

典型报错：Postgres “remaining connection slots are reserved …”。这会导致新 revision 无法启动，从而所有“新配置”看起来都没上线。

### 5) 生产止血建议（降低连接压力、保证发布可用）

```powershell
# 仅保留一个活动 revision，避免多版本同时占用连接
az containerapp revision set-mode -g $rg -n $backendApp --mode single

# 禁用 DEBUG/reload（避免进程/连接数膨胀）
az containerapp update -g $rg -n $backendApp --set-env-vars "DEBUG=false"
```

恢复后，再按第 3 步复测 CORS 预检；确认新 revision `Healthy/Running` 且流量 100%。
