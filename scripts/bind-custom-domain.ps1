# 绑定自定义域名到 Azure Container App
param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,

    [Parameter(Mandatory=$false)]
    [string[]]$AdditionalDomains = @(),
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "auto-score-analyzer-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$AppName = "ca-score-analyzer-frontend"
)

Write-Host "🌐 绑定自定义域名到 Container App" -ForegroundColor Cyan

$domainsToBind = @($Domain)
if ($AdditionalDomains -and $AdditionalDomains.Count -gt 0) {
    $domainsToBind += $AdditionalDomains
}

$domainsToBind = $domainsToBind | Where-Object { $_ -and $_.Trim().Length -gt 0 } | ForEach-Object { $_.Trim() } | Select-Object -Unique

Write-Host "📋 域名: $($domainsToBind -join ', ')" -ForegroundColor Gray
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
Write-Host "⚠️  请先在 DNS 中为以下域名添加 CNAME 记录，指向应用默认域名:" -ForegroundColor Yellow
foreach ($d in $domainsToBind) {
    Write-Host "  - $d -> $appFqdn" -ForegroundColor White
}
Write-Host ""
$continue = Read-Host "是否已添加 DNS 记录? (y/n)"

if ($continue -ne "y") {
    Write-Host "❌ 已取消" -ForegroundColor Red
    exit 0
}

Write-Host "`n🔧 添加域名到 Container App..." -ForegroundColor Cyan
foreach ($d in $domainsToBind) {
    Write-Host "  添加: $d" -ForegroundColor Cyan
    az containerapp hostname add `
        --hostname $d `
        --resource-group $ResourceGroup `
        --name $AppName

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 添加域名失败: $d" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ 域名添加成功" -ForegroundColor Green

# 3. 绑定证书（使用免费的托管证书）
Write-Host "`n🔒 绑定 SSL 证书..." -ForegroundColor Cyan
foreach ($d in $domainsToBind) {
    Write-Host "  绑定证书: $d" -ForegroundColor Cyan
    az containerapp hostname bind `
        --hostname $d `
        --resource-group $ResourceGroup `
        --name $AppName `
        --validation-method CNAME `
        --environment-managed-cert

    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  证书绑定可能需要几分钟时间: $d（请稍后检查）" -ForegroundColor Yellow
    } else {
        Write-Host "✅ SSL 证书绑定成功: $d" -ForegroundColor Green
    }
}

Write-Host "`n🎉 域名配置完成！" -ForegroundColor Green
foreach ($d in $domainsToBind) {
    Write-Host "  🌐 访问: https://$d" -ForegroundColor Cyan
}
Write-Host "`n💡 提示: DNS 传播可能需要几分钟到几小时" -ForegroundColor Yellow
