# Azure Container Apps 部署脚本
# 一键部署前端和后端到 Azure Container Apps

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-score-analyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastasia",
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerRegistry = "",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccount = "stscoreanalyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "cae-score-analyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$BackendAppName = "backend",
    
    [Parameter(Mandatory=$false)]
    [string]$FrontendAppName = "frontend",

    [Parameter(Mandatory=$false)]
    [string]$ImageTag = ""
)

$ErrorActionPreference = "Stop"

if (-not $ContainerRegistry) {
    $ContainerRegistry = $env:ACR_NAME
}

if (-not $ContainerRegistry) {
    Write-Host "❌ Missing Container Registry name. Pass -ContainerRegistry or set env var ACR_NAME." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 开始部署到 Azure Container Apps" -ForegroundColor Cyan
Write-Host "📋 配置信息:" -ForegroundColor Gray
Write-Host "  - 资源组: $ResourceGroup" -ForegroundColor Gray
Write-Host "  - 位置: $Location" -ForegroundColor Gray
Write-Host "  - Container Registry: $ContainerRegistry" -ForegroundColor Gray
Write-Host "  - Storage Account: $StorageAccount" -ForegroundColor Gray
if ($ImageTag) {
    Write-Host "  - Image Tag: $ImageTag" -ForegroundColor Gray
}
Write-Host ""

if (-not $ImageTag) {
    try {
        $mainPy = Get-Content -Raw -Path (Join-Path $PSScriptRoot "..\backend\app\main.py")
        $m = [Regex]::Match($mainPy, 'version\s*=\s*"([^"]+)"')
        if ($m.Success) {
            $ImageTag = $m.Groups[1].Value
        }
    } catch {
        # ignore
    }
}

if (-not $ImageTag) {
    $ImageTag = (Get-Date -Format "yyyyMMddHHmmss")
}

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
$backendImage = "$ContainerRegistry.azurecr.io/score-analyzer-backend:$ImageTag"
Write-Host "  镜像: $backendImage" -ForegroundColor Gray

az acr build `
    --registry $ContainerRegistry `
    --image score-analyzer-backend:$ImageTag `
    --file backend/Dockerfile `
    backend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 后端镜像构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 后端镜像构建成功" -ForegroundColor Green

# 5. 构建并推送前端镜像

# 注意：前端是 Vite 构建，VITE_API_URL 需要在构建时注入（Docker build-arg）。
# 因此前端镜像的构建会在获取后端 FQDN 后再执行。

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
$envFilePath = "backend\.env"
if (-not (Test-Path $envFilePath)) {
    Write-Host "❌ .env 文件不存在: $envFilePath" -ForegroundColor Red
    Write-Host "💡 运行: .\scripts\sync-azure-config.ps1" -ForegroundColor Yellow
    exit 1
}

$envVars = @{}
Get-Content $envFilePath | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

function Get-EnvValueOrEmpty([hashtable]$Vars, [string]$Key) {
    if ($Vars.ContainsKey($Key)) { return $Vars[$Key] }
    return ""
}

function Require-Env([hashtable]$Vars, [string[]]$Keys, [string]$Hint) {
    $missing = @()
    foreach ($k in $Keys) {
        if (-not $Vars.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($Vars[$k])) {
            $missing += $k
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host "❌ 缺少必要环境变量: $($missing -join ', ')" -ForegroundColor Red
        if ($Hint) { Write-Host "💡 $Hint" -ForegroundColor Yellow }
        exit 1
    }
}

# 必要配置校验
# 新架构：直接使用 /openai/v1/responses + model 字段，不强依赖 api-version / deployment-name。
Require-Env $envVars @(
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_RESPONSES_URL",
    "PARSING_MODEL",
    "ANALYSIS_MODEL"
) "请在 backend/.env 中补齐以上变量（新架构所需）。"

$emailProvider = (Get-EnvValueOrEmpty $envVars "EMAIL_PROVIDER")
if ([string]::IsNullOrWhiteSpace($emailProvider)) { $emailProvider = "dev" }
if ($emailProvider -eq "acs") {
    Require-Env $envVars @(
        "ACS_EMAIL_CONNECTION_STRING",
        "ACS_EMAIL_SENDER"
    ) "EMAIL_PROVIDER=acs 时必须提供 ACS_EMAIL_CONNECTION_STRING 与 ACS_EMAIL_SENDER。"
}

# 11. 部署后端 Container App
Write-Host "`n🚀 部署后端 Container App..." -ForegroundColor Cyan

$backendExists = az containerapp show --name $BackendAppName --resource-group $ResourceGroup 2>$null

# 统一构造后端 env（明文 + secretref）
$backendEnvVars = @(
    "AZURE_OPENAI_API_KEY=secretref:openai-key",
    "AZURE_OPENAI_RESPONSES_URL=$($envVars['AZURE_OPENAI_RESPONSES_URL'])",
    "PARSING_MODEL=$($envVars['PARSING_MODEL'])",
    "ANALYSIS_MODEL=$($envVars['ANALYSIS_MODEL'])",
    "STORAGE_TYPE=azure",
    "AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn",
    "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccount",
    "AZURE_STORAGE_ACCOUNT_KEY=secretref:storage-key",
    "AZURE_STORAGE_BLOB_ENDPOINT=$blobEndpoint",
    "AZURE_STORAGE_UPLOADS_CONTAINER=uploads",
    "AZURE_STORAGE_EXPORTS_CONTAINER=exports",
    "AZURE_STORAGE_CHARTS_CONTAINER=charts",
    "EMAIL_PROVIDER=$emailProvider"
)

$optionalBackendKeys = @(
    "PARSING_REASONING_EFFORT",
    "ANALYSIS_TEMPERATURE",
    "OPENAI_REQUEST_TIMEOUT_SECONDS",
    "LOG_LEVEL",
    "DEBUG",
    "BACKEND_URL",
    "CORS_ORIGINS",
    "EMAIL_LOG_CODES_IN_DEV",
    "ACS_EMAIL_SENDER",
    "DATABASE_URL"
)

foreach ($k in $optionalBackendKeys) {
    if ($envVars.ContainsKey($k) -and -not [string]::IsNullOrWhiteSpace($envVars[$k])) {
        $backendEnvVars += "$k=$($envVars[$k])"
    }
}

$backendSecrets = @(
    "openai-key=$($envVars['AZURE_OPENAI_API_KEY'])",
    "storage-conn=$storageConnString",
    "storage-key=$storageKey"
)

# SECRET_KEY：用于 JWT + 邮箱验证码 hash 的 pepper。
# - 若 backend/.env 提供，则更新云端 secret（可用于首次部署 / 主动轮换）。
# - 若未提供且后端应用已存在，则不覆盖（保留云端现有配置）。
if ($envVars.ContainsKey('SECRET_KEY') -and -not [string]::IsNullOrWhiteSpace($envVars['SECRET_KEY'])) {
    $backendSecrets += "jwt-secret=$($envVars['SECRET_KEY'])"
    $backendEnvVars += "SECRET_KEY=secretref:jwt-secret"
} elseif (-not $backendExists) {
    Write-Host "❌ 首次创建后端应用时必须提供 SECRET_KEY（用于 JWT/验证码）。请在 backend/.env 中设置 SECRET_KEY。" -ForegroundColor Red
    exit 1
}

if ($emailProvider -eq "acs") {
    $backendSecrets += "acs-email-conn=$($envVars['ACS_EMAIL_CONNECTION_STRING'])"
    $backendEnvVars += "ACS_EMAIL_CONNECTION_STRING=secretref:acs-email-conn"
}

if ($backendExists) {
    Write-Host "⚠️  后端应用已存在，正在更新..." -ForegroundColor Yellow
    # 先确保 secrets 存在/更新
    az containerapp secret set `
        --name $BackendAppName `
        --resource-group $ResourceGroup `
        --secrets $backendSecrets `
        --output none

    az containerapp update `
        --name $BackendAppName `
        --resource-group $ResourceGroup `
        --image $backendImage `
        --set-env-vars $backendEnvVars `
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
            $backendSecrets `
        --env-vars $backendEnvVars `
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

# 12.5 构建并推送前端镜像（注入 VITE_API_URL）
Write-Host "`n🔨 构建并推送前端镜像（注入 VITE_API_URL）..." -ForegroundColor Cyan
$frontendImage = "$ContainerRegistry.azurecr.io/score-analyzer-frontend:$ImageTag"
Write-Host "  镜像: $frontendImage" -ForegroundColor Gray

az acr build `
    --registry $ContainerRegistry `
    --image score-analyzer-frontend:$ImageTag `
    --file frontend/Dockerfile `
    --build-arg VITE_API_URL=$backendApiUrl `
    frontend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 前端镜像构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 前端镜像构建成功" -ForegroundColor Green

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

# 15. 回写后端 CORS（允许前端域名 + 自定义域名）
Write-Host "`n🔧 更新后端 CORS_ORIGINS..." -ForegroundColor Cyan

$corsOrigins = @($frontendWebUrl)

try {
    $customDomainNames = az containerapp ingress show `
        --name $FrontendAppName `
        --resource-group $ResourceGroup `
        --query "properties.customDomains[].name" `
        --output tsv

    if ($customDomainNames) {
        foreach ($d in ($customDomainNames -split "`n")) {
            $domain = $d.Trim()
            if ($domain) {
                $corsOrigins += "https://$domain"
            }
        }
    }
} catch {
    # ignore
}

# 如果 backend/.env 提供了 CORS_ORIGINS，则合并（避免覆盖用户手动扩展的 allowlist）
if ($envVars.ContainsKey('CORS_ORIGINS') -and -not [string]::IsNullOrWhiteSpace($envVars['CORS_ORIGINS'])) {
    foreach ($origin in ($envVars['CORS_ORIGINS'] -split ',')) {
        $o = $origin.Trim()
        if ($o) {
            $corsOrigins += $o
        }
    }
}

$corsOriginsValue = ($corsOrigins | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique) -join ','

az containerapp update `
    --name $BackendAppName `
    --resource-group $ResourceGroup `
    --set-env-vars "CORS_ORIGINS=$corsOriginsValue" `
    --output none

Write-Host "✅ 后端 CORS 已更新: $corsOriginsValue" -ForegroundColor Green

Write-Host "`n🎉 部署完成！" -ForegroundColor Green
Write-Host "`n📋 访问信息:" -ForegroundColor Cyan
Write-Host "  🌐 前端: $frontendWebUrl" -ForegroundColor White
Write-Host "  🔌 后端: $backendApiUrl" -ForegroundColor White
Write-Host "`n💡 下一步:" -ForegroundColor Cyan
Write-Host "  1. 在浏览器中访问前端 URL 测试应用" -ForegroundColor Gray
Write-Host "  2. 绑定自定义域名: .\scripts\bind-custom-domain.ps1 -Domain your-domain.com" -ForegroundColor Gray
Write-Host "  3. 查看日志: az containerapp logs show --name $FrontendAppName -g $ResourceGroup --follow" -ForegroundColor Gray
