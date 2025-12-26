param(
    [Parameter(Mandatory=$false)]
    [string]$Domain
)

Write-Host "⚠️  scripts/bind-domain.ps1 已弃用" -ForegroundColor Yellow
Write-Host "该脚本会尝试修改运行时环境变量（例如 VITE_API_URL / CORS_ORIGINS），容易导致已知问题（例如 CORS 预检失败、前端构建期注入失效）。" -ForegroundColor Yellow
Write-Host "请改用: .\scripts\bind-custom-domain.ps1" -ForegroundColor Cyan
Write-Host "示例：" -ForegroundColor Gray
Write-Host "  .\scripts\bind-custom-domain.ps1 -Domain \"$Domain\" -ResourceGroup \"auto-score-analyzer-dev\" -AppName \"ca-score-analyzer-frontend\" -AdditionalDomains @(\"www.$Domain\")" -ForegroundColor Gray
exit 1
