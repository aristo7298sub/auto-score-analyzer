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
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

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
