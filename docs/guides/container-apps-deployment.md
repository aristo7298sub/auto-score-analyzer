# Azure Container Apps 部署指南

本项目支持一键部署到 Azure Container Apps，提供自动扩缩容、HTTPS 和自定义域名支持。

## 🚀 快速部署

### 前置要求

1. **Azure CLI**: [下载安装](https://aka.ms/installazurecliwindows)
2. **Azure 订阅**: 有效的 Azure 订阅
3. **Storage Account**: 已创建（用于存储文件）

### 部署步骤

#### 1. 配置环境变量

首先同步 Azure 资源配置：

```powershell
# 同步 Azure Storage Account 配置
.\scripts\sync-azure-config.ps1 -ResourceGroup "rg-score-analyzer" -StorageAccountName "stscoreanalyzer"
```

这会自动：
- 获取 Storage Account 连接字符串
- 创建 Blob 容器（uploads, exports, charts）
- 更新 `.env` 文件

#### 2. 检查 .env 配置

确保 `.env` 文件包含必要的配置：

```env
# Azure OpenAI（推荐：Responses API + 模型分离）
AZURE_OPENAI_API_KEY=your-key

# 直接使用 /openai/v1/responses；模型名写到 model 字段
AZURE_OPENAI_RESPONSES_URL=https://your-resource.openai.azure.com/openai/v1/responses
PARSING_MODEL=o4-mini
ANALYSIS_MODEL=gpt-4.1-nano

# 可选：第二 AOAI 资源（故障切换，仅对可恢复错误：timeout/network/429/5xx）
AZURE_OPENAI_API_KEY_2=your-key-2
AZURE_OPENAI_RESPONSES_URL_2=https://your-resource-2.openai.azure.com/openai/v1/responses

# 可选：第二资源上的模型名（不填则 fallback 使用同一个 model 字段值）
PARSING_MODEL_2=o4-mini
ANALYSIS_MODEL_2=gpt-4.1-nano

# 超时与重试（/responses）
OPENAI_REQUEST_TIMEOUT_SECONDS=600
OPENAI_REQUEST_MAX_RETRIES=2
OPENAI_REQUEST_RETRY_BACKOFF_SECONDS=0.8
OPENAI_REQUEST_RETRY_MAX_BACKOFF_SECONDS=8.0

# Storage (已自动配置)
STORAGE_TYPE=azure
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_STORAGE_ACCOUNT_NAME=stscoreanalyzer
```

#### 3. 一键部署

```powershell
# 部署到 Azure Container Apps
.\scripts\deploy-to-container-apps.ps1
```

部署脚本会自动：
1. ✅ 创建 Resource Group
2. ✅ 创建 Container Registry
3. ✅ 构建并推送 Docker 镜像
4. ✅ 创建 Storage Account 和 Blob 容器
5. ✅ 创建 Container Apps Environment
6. ✅ 部署后端 Container App
7. ✅ 部署前端 Container App
8. ✅ 配置自动扩缩容

部署完成后会显示访问 URL：
```
🎉 部署完成！

📋 访问信息:
  🌐 前端: https://frontend.xxxx.eastasia.azurecontainerapps.io
  🔌 后端: https://backend.xxxx.eastasia.azurecontainerapps.io
```

#### 4. 绑定自定义域名（可选）

```powershell
# 绑定自定义域名
.\scripts\bind-custom-domain.ps1 -Domain "score.yourdomain.com"
```

在运行前，需要先在 DNS 提供商处添加 CNAME 记录：
```
类型: CNAME
名称: score.yourdomain.com
值: frontend.xxxx.eastasia.azurecontainerapps.io
```

脚本会自动申请并绑定免费的 Let's Encrypt SSL 证书。

---

## 📊 架构说明

```
用户浏览器 (your-domain.com)
    ↓ HTTPS
Azure Container Apps Environment
    ├─ Frontend Container App
    │   ├─ 自动扩缩容: 0-5 实例
    │   ├─ CPU: 0.5 核
    │   └─ 内存: 1.0 GB
    │
    └─ Backend Container App
        ├─ 自动扩缩容: 0-3 实例
        ├─ CPU: 1.0 核
        ├─ 内存: 2.0 GB
        └─ 连接到 Azure Storage Account
            ├─ uploads 容器
            ├─ exports 容器
            └─ charts 容器
```

---

## 🔧 高级配置

### 自定义资源名称

```powershell
.\scripts\deploy-to-container-apps.ps1 `
    -ResourceGroup "my-rg" `
    -Location "eastus" `
    -ContainerRegistry "myacr" `
    -StorageAccount "mystorage"
```

### 更新已部署的应用

只需重新运行部署脚本，它会自动检测现有资源并进行更新：

```powershell
.\scripts\deploy-to-container-apps.ps1
```

### 查看日志

```powershell
# 前端日志
az containerapp logs show --name frontend -g rg-score-analyzer --follow

# 后端日志
az containerapp logs show --name backend -g rg-score-analyzer --follow
```

### 手动扩容

```powershell
# 修改最小/最大副本数
az containerapp update `
    --name backend `
    --resource-group rg-score-analyzer `
    --min-replicas 1 `
    --max-replicas 10
```

### 更新环境变量

```powershell
# 更新后端环境变量
az containerapp update `
    --name backend `
    --resource-group rg-score-analyzer `
    --set-env-vars "NEW_VAR=value"
```

---

## 💰 成本估算

基于按需计费（无流量时缩容到 0）：

| 资源 | 配置 | 估算月成本 |
|------|------|-----------|
| Container Apps Environment | 标准 | ~$10 |
| Backend (0-3 实例) | 1 vCPU, 2 GB | ~$20-60 |
| Frontend (0-5 实例) | 0.5 vCPU, 1 GB | ~$10-50 |
| Container Registry | Basic | ~$5 |
| Storage Account | Standard LRS | ~$2 |
| **总计** | | **$47-127/月** |

低流量场景下（自动缩容到 0）成本接近最低值 ~$50/月。

---

## 🛠️ 故障排查

### 0. 发布后 3 分钟自检（强烈建议每次部署都做）

部署完成后，先用最小验证把“构建期注入 / CORS / 镜像 tag”这三类问题快速排除：

```powershell
$backend = "https://<your-backend-fqdn>"

# 1) 健康检查（服务是否活着）
curl.exe -sS "$backend/health"

# 2) CORS 预检（自定义域名访问后端时，避免 OPTIONS 400）
curl.exe -i -X OPTIONS "$backend/api/auth/login" `
  -H "Origin: https://<your-frontend-domain>" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"

# 3) OpenAPI 验证（确认解析模块路由已加载）
curl.exe -sS "$backend/openapi.json" | findstr /C:"/api/files/parse/preview" /C:"/api/files/parse/confirm"
```

如果第 2 步没有看到 `Access-Control-Allow-Origin` 或返回 `400`，优先按下面 “CORS 预检 400” 排查。

### 1. 镜像构建失败

**问题**: `az acr build` 命令失败

**解决**:
- 检查 Dockerfile 路径
- 确保 ACR 有足够权限
- 查看构建日志：`az acr task logs --name buildTask --registry myacr`

### 2. 应用无法启动

**问题**: Container App 状态为 "Provisioning Failed"

**解决**:
```powershell
# 查看详细错误
az containerapp show --name backend -g rg-score-analyzer --query "properties.provisioningState"

# 查看日志
az containerapp logs show --name backend -g rg-score-analyzer --tail 100
```

### 3. 无法访问 Storage

**问题**: 后端日志显示 "Azure Storage 连接失败"

**解决**:
- 检查 `.env` 中的 `AZURE_STORAGE_CONNECTION_STRING`
- 确保 Storage Account 允许公共访问
- 验证 Blob 容器权限

### 4. 自定义域名证书失败

**问题**: SSL 证书绑定失败

**解决**:
- 确保 DNS CNAME 记录已生效（可能需要几小时）
- 使用 `nslookup` 验证：`nslookup score.yourdomain.com`
- 重新运行绑定命令

### 5. 登录 400 / 控制台提示 CORS blocked（常见：OPTIONS 400）

**现象**：
- Network 面板里 `OPTIONS /api/auth/login` 返回 `400 Bad Request`
- 控制台报：`No 'Access-Control-Allow-Origin' header`

**原因**：
- 后端环境变量 `CORS_ORIGINS` 没包含你的前端域名（例如 `https://xscore-app.com` / `https://www.xscore-app.com`）。
- 或者使用了旧版部署脚本：脚本在部署末尾把 `CORS_ORIGINS` 覆盖成“仅 ACA 默认前端域名”，导致你手动加过的自定义域名被冲掉。
- 近期踩坑：**看起来像 CORS 配置问题，但实际是新 revision 根本没启动成功**。当数据库连接耗尽（Postgres 报 “remaining connection slots are reserved …”）时，新 revision 会 `Unhealthy/Degraded`，流量可能仍在旧 revision 上，导致你怎么改 `CORS_ORIGINS` 都像“没生效”。

**解决（热修复）**：
```powershell
$rg = "rg-score-analyzer"
$backendApp = "backend"
$allowed = "https://<aca-frontend-fqdn>,https://<your-frontend-domain>,https://<your-frontend-domain-www>"
az containerapp update -n $backendApp -g $rg --set-env-vars "CORS_ORIGINS=$allowed"
```

**如果你已经设置了 `CORS_ORIGINS`，但仍然 OPTIONS 400 / 无 CORS 响应头**（高概率是 revision 不健康/没切上来）：

1) 确认当前在跑的是哪个 revision（以及是否健康）

```powershell
$rg = "rg-score-analyzer"
$backendApp = "backend"

az containerapp show -g $rg -n $backendApp --query "{activeRevisionsMode:properties.configuration.activeRevisionsMode,latestReadyRevisionName:properties.latestReadyRevisionName,latestRevisionName:properties.latestRevisionName}" -o json
az containerapp revision list -g $rg -n $backendApp -o table
```

2) 直接看“最新 revision”的日志，确认是否是 DB 连接耗尽导致启动失败

```powershell
$rev = "<latest-revision-name>"
az containerapp logs show -g $rg -n $backendApp --revision $rev --tail 200
```

3) 生产建议的快速止血组合（避免多 revision / DEBUG reload 放大连接压力）

```powershell
# 仅保留一个活动 revision，避免多版本同时占用连接
az containerapp revision set-mode -g $rg -n $backendApp --mode single

# 强制关闭 DEBUG（不要在 ACA 里开 reload）
az containerapp update -g $rg -n $backendApp --set-env-vars "DEBUG=false"
```

**预防**：
- 使用最新版 `scripts/deploy-to-container-apps.ps1`（会自动合并 ACA 前端域名 + custom domains，避免覆盖回滚）。
- 生产环境保持 `activeRevisionsMode=Single`，并确保 `DEBUG=false`（避免 reload/多进程导致连接数膨胀）。
- 关注 Postgres 连接上限（`max_connections` / 连接池配置 / 后端实例数），避免发布时新 revision 因无法连库而启动失败。

### 6. 前端看起来“没发请求”（HAR 里没有 login / 报 ERR_INVALID_URL）

**现象**：
- 控制台报 `ERR_INVALID_URL` / `net::ERR_FAILED`
- Network 面板看不到真正的 API 请求

**原因**：
- Vite 的 `VITE_API_URL` 是**构建期**注入。
- 如果前端镜像构建时没有传真实后端 URL，产物里会烘焙占位符（如 `<backend-fqdn>`），浏览器会直接拒绝发请求。

**解决/预防**：
- 确保前端镜像构建通过 `--build-arg VITE_API_URL=https://<backend-fqdn>` 注入真实值。
- 项目已在 `frontend/Dockerfile` 中加入校验：若缺失/仍为占位符会直接构建失败（避免上线后才发现）。

### 7. 老用户登录 500 / 数据库列缺失（PostgreSQL schema 不一致）

**现象**：
- 部分老用户登录失败
- 后端日志出现类似 `column users.xxx does not exist`

**原因**：
- 旧库 schema 与新代码不一致（缺列/缺表）。

**解决**：
- 查看后端日志定位缺失列；必要时补 migration 或升级脚本。
- 本项目后端包含 best-effort 兼容补列逻辑（适用于少量字段变更）；但更推荐把 schema 迁移纳入正式流程。

### 8. 绑定邮箱/注册验证码/解析会话 500（naive vs aware datetime）

**现象**：
- 接口 500
- 日志出现：`TypeError: can't compare offset-naive and offset-aware datetimes`

**原因**：
- 数据库字段用的是 timezone-aware 时间（如 `DateTime(timezone=True)`），代码若用 `datetime.utcnow()`（naive）做比较会抛错。

**解决/预防**：
- 代码统一使用 timezone-aware UTC（例如 `datetime.now(timezone.utc)`）；本项目已引入 `utcnow()` 并替换关键路径。

### 9. “Environment 不存在”但明明有（环境名 vs defaultDomain 混淆）

**现象**：脚本或命令提示 containerapp environment 不存在。

**原因**：
- 把环境的 `defaultDomain` 前缀（例如 `blackwave-bc3cb801`）误当成了 environment 名。

**解决**：
- Environment 名应是类似 `cae-score-analyzer` 的资源名；先用 `az containerapp env list -g <rg>` 确认再传参。

---

## 📚 相关资源

- [Azure Container Apps 文档](https://learn.microsoft.com/azure/container-apps/)
- [Azure Blob Storage 文档](https://learn.microsoft.com/azure/storage/blobs/)
- [Azure CLI 参考](https://learn.microsoft.com/cli/azure/)

---

## 🔄 CI/CD 集成

可以配合 GitHub Actions 实现自动部署：

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy
        run: |
          chmod +x scripts/deploy-to-container-apps.sh
          ./scripts/deploy-to-container-apps.sh
```

详见后续完善的 CI/CD 配置。
