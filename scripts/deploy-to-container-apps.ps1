# Azure Container Apps 部署脚本
# 一键部署前端和后端到 Azure Container Apps

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-score-analyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastasia",
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerRegistry = "<acr-name>",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccount = "stscoreanalyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "cae-score-analyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$BackendAppName = "backend",
    
    [Parameter(Mandatory=$false)]
    [string]$FrontendAppName = "frontend"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 开始部署到 Azure Container Apps" -ForegroundColor Cyan
Write-Host "📋 配置信息:" -ForegroundColor Gray
Write-Host "  - 资源组: $ResourceGroup" -ForegroundColor Gray
Write-Host "  - 位置: $Location" -ForegroundColor Gray
Write-Host "  - Container Registry: $ContainerRegistry" -ForegroundColor Gray
Write-Host "  - Storage Account: $StorageAccount" -ForegroundColor Gray
Write-Host ""

# 检查 Azure CLI
Write-Host "🔍 检查 Azure CLI..." -ForegroundColor Cyan
$azVersion = az version 2>$null
if (-not $azVersion) {
    Write-Host "❌ 未安装 Azure CLI，请先安装: https://aka.ms/installazurecliwindows" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Azure CLI 已安装" -ForegroundColor Green

# 检查登录状态
Write-Host "`n🔍 检查 Azure 登录状态..." -ForegroundColor Cyan
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "❌ 未登录 Azure，正在启动登录..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "✅ 已登录: $($account.user.name)" -ForegroundColor Green
Write-Host "📋 订阅: $($account.name)" -ForegroundColor Gray

# 1. 创建资源组（如果不存在）
Write-Host "`n📦 检查资源组..." -ForegroundColor Cyan
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "false") {
    Write-Host "⚠️  资源组不存在，正在创建..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location --output none
    Write-Host "✅ 资源组创建成功" -ForegroundColor Green
} else {
    Write-Host "✅ 资源组已存在" -ForegroundColor Green
}

# 2. 创建 Container Registry（如果不存在）
Write-Host "`n📦 检查 Container Registry..." -ForegroundColor Cyan
$acrExists = az acr show --name $ContainerRegistry --resource-group $ResourceGroup 2>$null
if (-not $acrExists) {
    Write-Host "⚠️  Container Registry 不存在，正在创建（需要几分钟）..." -ForegroundColor Yellow
    az acr create `
        --resource-group $ResourceGroup `
        --name $ContainerRegistry `
        --sku Basic `
        --admin-enabled true `
        --output none
    Write-Host "✅ Container Registry 创建成功" -ForegroundColor Green
} else {
    Write-Host "✅ Container Registry 已存在" -ForegroundColor Green
}

# 3. 获取 ACR 凭证
Write-Host "`n🔑 获取 Container Registry 凭证..." -ForegroundColor Cyan
$acrUsername = az acr credential show --name $ContainerRegistry --query "username" --output tsv
$acrPassword = az acr credential show --name $ContainerRegistry --query "passwords[0].value" --output tsv
Write-Host "✅ 凭证获取成功" -ForegroundColor Green

# 4. 构建并推送后端镜像
Write-Host "`n🔨 构建并推送后端镜像..." -ForegroundColor Cyan
$backendImage = "$ContainerRegistry.azurecr.io/score-analyzer-backend:latest"
Write-Host "  镜像: $backendImage" -ForegroundColor Gray

az acr build `
    --registry $ContainerRegistry `
    --image score-analyzer-backend:latest `
    --file backend/Dockerfile `
    backend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 后端镜像构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 后端镜像构建成功" -ForegroundColor Green

# 5. 构建并推送前端镜像
Write-Host "`n🔨 构建并推送前端镜像..." -ForegroundColor Cyan
$frontendImage = "$ContainerRegistry.azurecr.io/score-analyzer-frontend:latest"
Write-Host "  镜像: $frontendImage" -ForegroundColor Gray

az acr build `
    --registry $ContainerRegistry `
    --image score-analyzer-frontend:latest `
    --file frontend/Dockerfile `
    frontend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 前端镜像构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 前端镜像构建成功" -ForegroundColor Green

# 6. 检查 Storage Account
Write-Host "`n📦 检查 Storage Account..." -ForegroundColor Cyan
$storageExists = az storage account show --name $StorageAccount --resource-group $ResourceGroup 2>$null
if (-not $storageExists) {
    Write-Host "⚠️  Storage Account 不存在，正在创建..." -ForegroundColor Yellow
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS `
        --output none
    Write-Host "✅ Storage Account 创建成功" -ForegroundColor Green
} else {
    Write-Host "✅ Storage Account 已存在" -ForegroundColor Green
}

# 7. 获取 Storage 连接字符串
Write-Host "`n🔑 获取 Storage 连接字符串..." -ForegroundColor Cyan
$storageConnString = az storage account show-connection-string `
    --resource-group $ResourceGroup `
    --name $StorageAccount `
    --query "connectionString" `
    --output tsv

$storageKey = az storage account keys list `
    --resource-group $ResourceGroup `
    --account-name $StorageAccount `
    --query "[0].value" `
    --output tsv

$blobEndpoint = az storage account show `
    --resource-group $ResourceGroup `
    --name $StorageAccount `
    --query "primaryEndpoints.blob" `
    --output tsv

Write-Host "✅ Storage 信息获取成功" -ForegroundColor Green

# 8. 创建 Blob 容器
Write-Host "`n📦 创建 Blob 容器..." -ForegroundColor Cyan
$containers = @("uploads", "exports", "charts")
foreach ($container in $containers) {
    $exists = az storage container exists `
        --name $container `
        --connection-string $storageConnString `
        --output tsv
    
    if ($exists -eq "False") {
        az storage container create `
            --name $container `
            --connection-string $storageConnString `
            --public-access off `
            --output none
        Write-Host "  ✅ 容器 '$container' 创建成功" -ForegroundColor Green
    } else {
        Write-Host "  ✅ 容器 '$container' 已存在" -ForegroundColor Gray
    }
}

# 9. 创建 Container Apps Environment
Write-Host "`n📦 检查 Container Apps Environment..." -ForegroundColor Cyan
$envExists = az containerapp env show --name $Environment --resource-group $ResourceGroup 2>$null
if (-not $envExists) {
    Write-Host "⚠️  Environment 不存在，正在创建（需要几分钟）..." -ForegroundColor Yellow
    az containerapp env create `
        --name $Environment `
        --resource-group $ResourceGroup `
        --location $Location `
        --output none
    Write-Host "✅ Container Apps Environment 创建成功" -ForegroundColor Green
} else {
    Write-Host "✅ Container Apps Environment 已存在" -ForegroundColor Green
}

# 10. 读取环境变量
Write-Host "`n🔑 读取环境变量..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env 文件不存在，请先配置 .env 文件" -ForegroundColor Red
    Write-Host "💡 运行: .\scripts\sync-azure-config.ps1" -ForegroundColor Yellow
    exit 1
}

$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

# 11. 部署后端 Container App
Write-Host "`n🚀 部署后端 Container App..." -ForegroundColor Cyan

$backendExists = az containerapp show --name $BackendAppName --resource-group $ResourceGroup 2>$null

if ($backendExists) {
    Write-Host "⚠️  后端应用已存在，正在更新..." -ForegroundColor Yellow
    az containerapp update `
        --name $BackendAppName `
        --resource-group $ResourceGroup `
        --image $backendImage `
        --set-env-vars `
            "AZURE_OPENAI_ENDPOINT=$($envVars['AZURE_OPENAI_ENDPOINT'])" `
            "AZURE_OPENAI_API_VERSION=$($envVars['AZURE_OPENAI_API_VERSION'])" `
            "AZURE_OPENAI_DEPLOYMENT_NAME=$($envVars['AZURE_OPENAI_DEPLOYMENT_NAME'])" `
            "STORAGE_TYPE=azure" `
            "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccount" `
            "AZURE_STORAGE_BLOB_ENDPOINT=$blobEndpoint" `
            "AZURE_STORAGE_UPLOADS_CONTAINER=uploads" `
            "AZURE_STORAGE_EXPORTS_CONTAINER=exports" `
            "AZURE_STORAGE_CHARTS_CONTAINER=charts" `
        --replace-env-vars `
            "AZURE_OPENAI_API_KEY=secretref:openai-key" `
            "AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn" `
            "AZURE_STORAGE_ACCOUNT_KEY=secretref:storage-key" `
        --output none
} else {
    Write-Host "⚠️  后端应用不存在，正在创建..." -ForegroundColor Yellow
    az containerapp create `
        --name $BackendAppName `
        --resource-group $ResourceGroup `
        --environment $Environment `
        --image $backendImage `
        --target-port 8000 `
        --ingress external `
        --registry-server "$ContainerRegistry.azurecr.io" `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --secrets `
            "openai-key=$($envVars['AZURE_OPENAI_API_KEY'])" `
            "storage-conn=$storageConnString" `
            "storage-key=$storageKey" `
        --env-vars `
            "AZURE_OPENAI_ENDPOINT=$($envVars['AZURE_OPENAI_ENDPOINT'])" `
            "AZURE_OPENAI_API_KEY=secretref:openai-key" `
            "AZURE_OPENAI_API_VERSION=$($envVars['AZURE_OPENAI_API_VERSION'])" `
            "AZURE_OPENAI_DEPLOYMENT_NAME=$($envVars['AZURE_OPENAI_DEPLOYMENT_NAME'])" `
            "STORAGE_TYPE=azure" `
            "AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn" `
            "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccount" `
            "AZURE_STORAGE_ACCOUNT_KEY=secretref:storage-key" `
            "AZURE_STORAGE_BLOB_ENDPOINT=$blobEndpoint" `
            "AZURE_STORAGE_UPLOADS_CONTAINER=uploads" `
            "AZURE_STORAGE_EXPORTS_CONTAINER=exports" `
            "AZURE_STORAGE_CHARTS_CONTAINER=charts" `
        --cpu 1.0 `
        --memory 2.0Gi `
        --min-replicas 0 `
        --max-replicas 3 `
        --output none
}

Write-Host "✅ 后端部署成功" -ForegroundColor Green

# 12. 获取后端 URL
$backendUrl = az containerapp show `
    --name $BackendAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

$backendApiUrl = "https://$backendUrl"
Write-Host "  🔗 后端 URL: $backendApiUrl" -ForegroundColor Cyan

# 13. 部署前端 Container App
Write-Host "`n🚀 部署前端 Container App..." -ForegroundColor Cyan

$frontendExists = az containerapp show --name $FrontendAppName --resource-group $ResourceGroup 2>$null

if ($frontendExists) {
    Write-Host "⚠️  前端应用已存在，正在更新..." -ForegroundColor Yellow
    az containerapp update `
        --name $FrontendAppName `
        --resource-group $ResourceGroup `
        --image $frontendImage `
        --set-env-vars "VITE_API_URL=$backendApiUrl" `
        --output none
} else {
    Write-Host "⚠️  前端应用不存在，正在创建..." -ForegroundColor Yellow
    az containerapp create `
        --name $FrontendAppName `
        --resource-group $ResourceGroup `
        --environment $Environment `
        --image $frontendImage `
        --target-port 80 `
        --ingress external `
        --registry-server "$ContainerRegistry.azurecr.io" `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --env-vars "VITE_API_URL=$backendApiUrl" `
        --cpu 0.5 `
        --memory 1.0Gi `
        --min-replicas 0 `
        --max-replicas 5 `
        --output none
}

Write-Host "✅ 前端部署成功" -ForegroundColor Green

# 14. 获取前端 URL
$frontendUrl = az containerapp show `
    --name $FrontendAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

$frontendWebUrl = "https://$frontendUrl"

Write-Host "`n🎉 部署完成！" -ForegroundColor Green
Write-Host "`n📋 访问信息:" -ForegroundColor Cyan
Write-Host "  🌐 前端: $frontendWebUrl" -ForegroundColor White
Write-Host "  🔌 后端: $backendApiUrl" -ForegroundColor White
Write-Host "`n💡 下一步:" -ForegroundColor Cyan
Write-Host "  1. 在浏览器中访问前端 URL 测试应用" -ForegroundColor Gray
Write-Host "  2. 绑定自定义域名: .\scripts\bind-custom-domain.ps1 -Domain your-domain.com" -ForegroundColor Gray
Write-Host "  3. 查看日志: az containerapp logs show --name $FrontendAppName -g $ResourceGroup --follow" -ForegroundColor Gray
