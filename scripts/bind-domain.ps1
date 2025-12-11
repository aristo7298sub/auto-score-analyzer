# 自定义域名绑定脚本 - xscore-app.com
# 适用于 Azure Container Apps

param(
    [string]$ResourceGroup = "rg-score-analyzer",
    [string]$FrontendApp = "frontend",
    [string]$BackendApp = "backend",
    [string]$Domain = "xscore-app.com",
    [string]$Location = "eastasia"
)

Write-Host "🌐 开始配置自定义域名: $Domain" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Azure CLI 登录状态
Write-Host "📋 检查 Azure CLI 登录状态..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "❌ 未登录 Azure CLI，请先登录" -ForegroundColor Red
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "✅ 已登录: $($account.user.name)" -ForegroundColor Green
Write-Host ""

# 2. 获取 Container App 信息
Write-Host "📦 获取 Container App 信息..." -ForegroundColor Yellow
$frontendInfo = az containerapp show `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --query "{fqdn:properties.configuration.ingress.fqdn, customDomains:properties.configuration.ingress.customDomains}" `
    -o json | ConvertFrom-Json

if (-not $frontendInfo) {
    Write-Host "❌ 未找到前端 Container App: $FrontendApp" -ForegroundColor Red
    exit 1
}

$defaultFqdn = $frontendInfo.fqdn
Write-Host "✅ 默认域名: $defaultFqdn" -ForegroundColor Green
Write-Host ""

# 3. DNS 配置说明
Write-Host "🔧 DNS 配置说明" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host "请在你的域名注册商(如阿里云、Cloudflare)处添加以下DNS记录:" -ForegroundColor White
Write-Host ""
Write-Host "  记录类型: CNAME" -ForegroundColor Yellow
Write-Host "  主机记录: @" -ForegroundColor Yellow
Write-Host "  记录值: $defaultFqdn" -ForegroundColor Cyan
Write-Host "  TTL: 600" -ForegroundColor Yellow
Write-Host ""
Write-Host "  记录类型: CNAME" -ForegroundColor Yellow
Write-Host "  主机记录: www" -ForegroundColor Yellow
Write-Host "  记录值: $defaultFqdn" -ForegroundColor Cyan
Write-Host "  TTL: 600" -ForegroundColor Yellow
Write-Host ""
Write-Host "  记录类型: CNAME" -ForegroundColor Yellow
Write-Host "  主机记录: api" -ForegroundColor Yellow
Write-Host "  记录值: $defaultFqdn" -ForegroundColor Cyan
Write-Host "  TTL: 600" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

# 等待用户确认
$confirm = Read-Host "是否已完成DNS配置? (y/n)"
if ($confirm -ne 'y') {
    Write-Host "⏸️  请配置DNS后再运行此脚本" -ForegroundColor Yellow
    exit 0
}
Write-Host ""

# 4. 验证DNS解析
Write-Host "🔍 验证DNS解析..." -ForegroundColor Yellow
$dnsResolved = $false
$maxAttempts = 10
$attempt = 0

while (-not $dnsResolved -and $attempt -lt $maxAttempts) {
    $attempt++
    try {
        $result = Resolve-DnsName -Name $Domain -Type CNAME -ErrorAction SilentlyContinue
        if ($result) {
            Write-Host "✅ DNS已解析: $Domain -> $($result.NameHost)" -ForegroundColor Green
            $dnsResolved = $true
        } else {
            Write-Host "⏳ DNS尚未生效 (尝试 $attempt/$maxAttempts)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    } catch {
        Write-Host "⏳ DNS尚未生效 (尝试 $attempt/$maxAttempts)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}

if (-not $dnsResolved) {
    Write-Host "⚠️  DNS可能尚未完全生效，但我们将继续配置" -ForegroundColor Yellow
}
Write-Host ""

# 5. 为前端添加自定义域名
Write-Host "🔗 为前端添加自定义域名..." -ForegroundColor Yellow

# 添加主域名
Write-Host "  添加: $Domain" -ForegroundColor Cyan
az containerapp hostname add `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --hostname $Domain `
    2>&1 | Out-Null

# 添加 www 子域名
Write-Host "  添加: www.$Domain" -ForegroundColor Cyan
az containerapp hostname add `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --hostname "www.$Domain" `
    2>&1 | Out-Null

Write-Host "✅ 域名添加完成" -ForegroundColor Green
Write-Host ""

# 6. 绑定托管证书 (自动HTTPS)
Write-Host "🔒 配置托管SSL证书 (Let's Encrypt)..." -ForegroundColor Yellow

# 为主域名绑定证书
Write-Host "  为 $Domain 申请证书..." -ForegroundColor Cyan
az containerapp hostname bind `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --hostname $Domain `
    --environment $(az containerapp show --name $FrontendApp --resource-group $ResourceGroup --query properties.managedEnvironmentId -o tsv | Split-Path -Leaf) `
    --validation-method CNAME `
    2>&1 | Out-Null

# 为 www 子域名绑定证书
Write-Host "  为 www.$Domain 申请证书..." -ForegroundColor Cyan
az containerapp hostname bind `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --hostname "www.$Domain" `
    --environment $(az containerapp show --name $FrontendApp --resource-group $ResourceGroup --query properties.managedEnvironmentId -o tsv | Split-Path -Leaf) `
    --validation-method CNAME `
    2>&1 | Out-Null

Write-Host "✅ SSL证书配置完成" -ForegroundColor Green
Write-Host ""

# 7. 更新应用环境变量
Write-Host "⚙️  更新应用环境变量..." -ForegroundColor Yellow

# 更新前端环境变量
az containerapp update `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --set-env-vars "VITE_API_URL=https://$Domain" `
    2>&1 | Out-Null

# 更新后端CORS配置
az containerapp update `
    --name $BackendApp `
    --resource-group $ResourceGroup `
    --set-env-vars "CORS_ORIGINS=[`"https://$Domain`",`"https://www.$Domain`"]" "BACKEND_URL=https://$Domain" `
    2>&1 | Out-Null

Write-Host "✅ 环境变量更新完成" -ForegroundColor Green
Write-Host ""

# 8. 验证配置
Write-Host "🔍 验证配置..." -ForegroundColor Yellow
$updatedInfo = az containerapp show `
    --name $FrontendApp `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.customDomains" `
    -o json | ConvertFrom-Json

Write-Host "✅ 已配置的自定义域名:" -ForegroundColor Green
foreach ($domain in $updatedInfo) {
    $certStatus = if ($domain.bindingType -eq "SniEnabled") { "✓ HTTPS已启用" } else { "⏳ 等待证书" }
    Write-Host "  • $($domain.name) - $certStatus" -ForegroundColor Cyan
}
Write-Host ""

# 9. 完成提示
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host "🎉 域名配置完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📋 访问地址:" -ForegroundColor Cyan
Write-Host "  🌐 主站: https://$Domain" -ForegroundColor White
Write-Host "  🌐 WWW: https://www.$Domain" -ForegroundColor White
Write-Host "  📚 API文档: https://$Domain/docs" -ForegroundColor White
Write-Host "  ❤️  健康检查: https://$Domain/health" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  注意事项:" -ForegroundColor Yellow
Write-Host "  • SSL证书申请可能需要5-10分钟" -ForegroundColor Gray
Write-Host "  • DNS传播可能需要等待最多24小时(通常几分钟)" -ForegroundColor Gray
Write-Host "  • 首次访问可能需要等待容器启动" -ForegroundColor Gray
Write-Host ""
Write-Host "🔍 检查状态:" -ForegroundColor Cyan
Write-Host "  az containerapp show -n $FrontendApp -g $ResourceGroup" -ForegroundColor Gray
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Gray
