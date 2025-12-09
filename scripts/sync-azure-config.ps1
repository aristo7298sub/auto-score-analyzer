# Azure 配置同步脚本
# 自动从 Azure 获取资源信息并更新 .env 文件

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-score-analyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccountName = "stscoreanalyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$EnvFile = ".env"
)

Write-Host "🔄 正在同步 Azure 配置..." -ForegroundColor Cyan

# 检查是否已登录 Azure
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "❌ 未登录 Azure，请先运行: az login" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 已登录 Azure 账户: $($account.user.name)" -ForegroundColor Green
Write-Host "📋 订阅: $($account.name)" -ForegroundColor Gray

# 获取 Storage Account 连接字符串
Write-Host "`n🔍 获取 Storage Account 连接字符串..." -ForegroundColor Cyan
$connectionString = az storage account show-connection-string `
    --resource-group $ResourceGroup `
    --name $StorageAccountName `
    --query "connectionString" `
    --output tsv 2>$null

if (-not $connectionString) {
    Write-Host "❌ 无法获取连接字符串，请检查:" -ForegroundColor Red
    Write-Host "   - 资源组: $ResourceGroup" -ForegroundColor Yellow
    Write-Host "   - Storage Account: $StorageAccountName" -ForegroundColor Yellow
    Write-Host "`n💡 提示: 运行以下命令查看可用的 Storage Account:" -ForegroundColor Cyan
    Write-Host "   az storage account list --output table" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ 成功获取连接字符串" -ForegroundColor Green

# 获取 Storage Account 密钥
$storageKey = az storage account keys list `
    --resource-group $ResourceGroup `
    --account-name $StorageAccountName `
    --query "[0].value" `
    --output tsv 2>$null

# 获取 Blob 端点
$blobEndpoint = az storage account show `
    --resource-group $ResourceGroup `
    --name $StorageAccountName `
    --query "primaryEndpoints.blob" `
    --output tsv 2>$null

Write-Host "✅ Blob 端点: $blobEndpoint" -ForegroundColor Green

# 创建或更新 .env 文件
$envPath = Join-Path $PSScriptRoot ".." "backend" $EnvFile

if (-not (Test-Path $envPath)) {
    Write-Host "`n📝 创建新的 .env 文件..." -ForegroundColor Cyan
    $examplePath = Join-Path $PSScriptRoot ".." "backend" ".env.example"
    if (Test-Path $examplePath) {
        Copy-Item $examplePath $envPath -ErrorAction SilentlyContinue
    }
}

# 读取现有 .env 内容
$envContent = if (Test-Path $envPath) { Get-Content $envPath -Raw } else { "" }

# 更新或添加 Storage 配置
$storageConfig = @"

# Azure Storage Account Configuration (自动同步于 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
AZURE_STORAGE_CONNECTION_STRING=$connectionString
AZURE_STORAGE_ACCOUNT_NAME=$StorageAccountName
AZURE_STORAGE_ACCOUNT_KEY=$storageKey
AZURE_STORAGE_BLOB_ENDPOINT=$blobEndpoint

# Blob Container 名称
AZURE_STORAGE_UPLOADS_CONTAINER=uploads
AZURE_STORAGE_EXPORTS_CONTAINER=exports
AZURE_STORAGE_CHARTS_CONTAINER=charts

# 存储类型 (local | azure)
STORAGE_TYPE=azure
"@

# 移除旧的 Storage 配置（如果存在）
$envContent = $envContent -replace '(?ms)# Azure Storage Account Configuration.*?STORAGE_TYPE=\w+\s*', ''

# 添加新配置
$envContent = $envContent.TrimEnd() + "`n" + $storageConfig

# 写入文件
$envContent | Set-Content $envPath -NoNewline -Encoding UTF8

Write-Host "`n✅ 配置已更新到: $envFile" -ForegroundColor Green

# 验证 Blob 容器是否存在
Write-Host "`n🔍 检查 Blob 容器..." -ForegroundColor Cyan
$containers = @("uploads", "exports", "charts")

foreach ($container in $containers) {
    $exists = az storage container exists `
        --name $container `
        --connection-string $connectionString `
        --output tsv 2>$null
    
    if ($exists -eq "True") {
        Write-Host "  ✅ $container" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $container (不存在，正在创建...)" -ForegroundColor Yellow
        az storage container create `
            --name $container `
            --connection-string $connectionString `
            --public-access off `
            --output none 2>$null
        Write-Host "  ✅ $container (已创建)" -ForegroundColor Green
    }
}

Write-Host "`n🎉 Azure 配置同步完成！" -ForegroundColor Green
Write-Host "`n📋 下一步:" -ForegroundColor Cyan
Write-Host "  1. 查看 .env 文件确认配置" -ForegroundColor Gray
Write-Host "  2. 运行后端测试: cd backend && python run.py" -ForegroundColor Gray
Write-Host "  3. 测试文件上传功能" -ForegroundColor Gray
