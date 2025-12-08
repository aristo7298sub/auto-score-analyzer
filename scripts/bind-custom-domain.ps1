# 绑定自定义域名到 Azure Container App
param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-score-analyzer",
    
    [Parameter(Mandatory=$false)]
    [string]$AppName = "frontend"
)

Write-Host "🌐 绑定自定义域名到 Container App" -ForegroundColor Cyan
Write-Host "📋 域名: $Domain" -ForegroundColor Gray
Write-Host "📋 应用: $AppName" -ForegroundColor Gray

# 1. 获取 Container App 的默认域名
Write-Host "`n🔍 获取应用信息..." -ForegroundColor Cyan
$appFqdn = az containerapp show `
    --name $AppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

if (-not $appFqdn) {
    Write-Host "❌ 无法获取应用信息，请检查应用名称和资源组" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 应用默认域名: $appFqdn" -ForegroundColor Green

# 2. 添加自定义域名
Write-Host "`n📝 添加自定义域名..." -ForegroundColor Cyan
Write-Host "⚠️  请先在 DNS 中添加以下记录:" -ForegroundColor Yellow
Write-Host "  类型: CNAME" -ForegroundColor White
Write-Host "  名称: $Domain" -ForegroundColor White
Write-Host "  值: $appFqdn" -ForegroundColor White
Write-Host ""
$continue = Read-Host "是否已添加 DNS 记录? (y/n)"

if ($continue -ne "y") {
    Write-Host "❌ 已取消" -ForegroundColor Red
    exit 0
}

Write-Host "`n🔧 添加域名到 Container App..." -ForegroundColor Cyan
az containerapp hostname add `
    --hostname $Domain `
    --resource-group $ResourceGroup `
    --name $AppName

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 添加域名失败" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 域名添加成功" -ForegroundColor Green

# 3. 绑定证书（使用免费的托管证书）
Write-Host "`n🔒 绑定 SSL 证书..." -ForegroundColor Cyan
az containerapp hostname bind `
    --hostname $Domain `
    --resource-group $ResourceGroup `
    --name $AppName `
    --validation-method CNAME `
    --environment-managed-cert

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  证书绑定可能需要几分钟时间，请稍后检查" -ForegroundColor Yellow
} else {
    Write-Host "✅ SSL 证书绑定成功" -ForegroundColor Green
}

Write-Host "`n🎉 域名配置完成！" -ForegroundColor Green
Write-Host "  🌐 访问: https://$Domain" -ForegroundColor Cyan
Write-Host "`n💡 提示: DNS 传播可能需要几分钟到几小时" -ForegroundColor Yellow
