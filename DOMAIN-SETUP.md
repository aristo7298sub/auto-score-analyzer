# 域名配置快速指南 - <your-domain>

## 🎯 目标
将应用部署到 Azure Container Apps 并绑定自定义域名 `<your-domain>`

## 📋 步骤概览

### 1️⃣ 确保应用已部署到 Container Apps

如果尚未部署,先运行:
```powershell
cd d:\Projects\2025\auto-score-analyzer
.\scripts\deploy-to-container-apps.ps1
```

### 2️⃣ 配置DNS记录

登录你的域名注册商(购买域名的地方),添加以下DNS记录:

#### 需要添加的记录:

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| CNAME | @ | `<你的容器应用默认域名>` | 600 |
| CNAME | www | `<你的容器应用默认域名>` | 600 |

**获取默认域名:**
```powershell
az containerapp show --name frontend --resource-group rg-score-analyzer --query properties.configuration.ingress.fqdn -o tsv
```

输出类似: `frontend.xxxx.eastasia.azurecontainerapps.io`

**示例配置:**
```
记录类型: CNAME
主机记录: @
记录值: frontend.<your-unique-suffix>.eastasia.azurecontainerapps.io
TTL: 600

记录类型: CNAME  
主机记录: www
记录值: frontend.<your-unique-suffix>.eastasia.azurecontainerapps.io
TTL: 600
```

### 3️⃣ 运行域名绑定脚本

等待DNS配置生效后(通常5-30分钟),运行:

```powershell
cd d:\Projects\2025\auto-score-analyzer
.\scripts\bind-domain.ps1 -Domain "<your-domain>"
```

脚本会自动:
- ✅ 验证DNS解析
- ✅ 添加自定义域名到Container App
- ✅ 申请并绑定免费SSL证书(Let's Encrypt)
- ✅ 更新CORS和环境变量配置
- ✅ 启用HTTPS自动重定向

### 4️⃣ 验证部署

访问以下地址验证:
- https://<your-domain>
- https://www.<your-domain>
- https://<your-domain>/docs
- https://<your-domain>/health

## 🔧 完整命令流程

```powershell
# 1. 进入项目目录
cd d:\Projects\2025\auto-score-analyzer

# 2. 登录Azure(如果尚未登录)
az login

# 3. 部署应用(如果尚未部署)
.\scripts\deploy-to-container-apps.ps1

# 4. 获取默认域名
$defaultDomain = az containerapp show --name frontend --resource-group rg-score-analyzer --query properties.configuration.ingress.fqdn -o tsv
Write-Host "默认域名: $defaultDomain"

# 5. 配置DNS后,绑定自定义域名
.\scripts\bind-domain.ps1 -Domain "<your-domain>"
```

## ⚠️ 常见问题

### DNS未生效
```powershell
# 检查DNS解析
nslookup <your-domain>

# 清除DNS缓存
ipconfig /flushdns
```

### SSL证书未生效
证书申请需要5-10分钟,可以查看状态:
```powershell
az containerapp hostname list --name frontend --resource-group rg-score-analyzer
```

### 容器启动慢
首次访问时容器需要启动(自动扩容从0开始):
```powershell
# 设置最小副本数为1(避免冷启动)
az containerapp update --name frontend --resource-group rg-score-analyzer --min-replicas 1
```

## 📊 监控与管理

### 查看应用状态
```powershell
az containerapp show --name frontend --resource-group rg-score-analyzer
```

### 查看日志
```powershell
# 实时日志
az containerapp logs show --name frontend --resource-group rg-score-analyzer --follow

# 后端日志  
az containerapp logs show --name backend --resource-group rg-score-analyzer --follow
```

### 重启应用
```powershell
az containerapp revision restart --name frontend --resource-group rg-score-analyzer
```

## 💰 成本优化

Container Apps按使用付费,以下是优化建议:

1. **使用自动扩容**(已默认配置)
   - 无流量时自动缩减到0
   - 有流量时自动扩容

2. **调整资源配额**
   ```powershell
   # 降低CPU/内存(如果够用)
   az containerapp update --name frontend --resource-group rg-score-analyzer --cpu 0.25 --memory 0.5Gi
   ```

3. **使用消费计划**(Consumption)
   - 已默认使用,按实际使用计费

## 🎉 完成

配置完成后,你的应用将通过以下方式访问:
- ✅ HTTPS加密
- ✅ 自定义域名
- ✅ 自动SSL证书续期
- ✅ 全球CDN加速
- ✅ 自动扩缩容
