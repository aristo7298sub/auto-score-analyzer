#!/usr/bin/env pwsh
# Azure Container Apps 部署脚本

$ErrorActionPreference = "Stop"

# 配置
$REGISTRY = $env:ACR_NAME
$RESOURCE_GROUP = "auto-score-analyzer-dev"
$BACKEND_APP = "ca-score-analyzer-backend"
$FRONTEND_APP = "ca-score-analyzer-frontend"

if (-not $REGISTRY) {
    throw "Missing ACR name. Set env var ACR_NAME or edit deploy-to-azure.ps1 to provide it."
}

# 获取后端 URL
Write-Host "获取后端 URL..." -ForegroundColor Cyan
$BACKEND_URL = az containerapp show `
    --name $BACKEND_APP `
    --resource-group $RESOURCE_GROUP `
    --query "properties.configuration.ingress.fqdn" `
    -o tsv

$BACKEND_API_URL = "https://$BACKEND_URL"
Write-Host "后端 URL: $BACKEND_API_URL" -ForegroundColor Green

# 获取当前 Git commit hash
$GIT_HASH = git rev-parse --short HEAD
Write-Host "当前 commit: $GIT_HASH" -ForegroundColor Green

# 构建后端镜像
Write-Host "`n========== 构建后端镜像 ==========" -ForegroundColor Yellow
az acr build `
    --registry $REGISTRY `
    --image "score-analyzer-backend:latest" `
    --image "score-analyzer-backend:$GIT_HASH" `
    --file backend/Dockerfile `
    backend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "后端镜像构建失败!" -ForegroundColor Red
    exit 1
}

# 构建前端镜像（带正确的 API URL）
Write-Host "`n========== 构建前端镜像 ==========" -ForegroundColor Yellow
az acr build `
    --registry $REGISTRY `
    --image "score-analyzer-frontend:latest" `
    --image "score-analyzer-frontend:$GIT_HASH" `
    --build-arg "VITE_API_URL=$BACKEND_API_URL" `
    --file frontend/Dockerfile `
    frontend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "前端镜像构建失败!" -ForegroundColor Red
    exit 1
}

# 更新后端 Container App
Write-Host "`n========== 更新后端 Container App ==========" -ForegroundColor Yellow
az containerapp update `
    --name $BACKEND_APP `
    --resource-group $RESOURCE_GROUP `
    --image "$REGISTRY.azurecr.io/score-analyzer-backend:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "后端 Container App 更新失败!" -ForegroundColor Red
    exit 1
}

# 更新前端 Container App
Write-Host "`n========== 更新前端 Container App ==========" -ForegroundColor Yellow
az containerapp update `
    --name $FRONTEND_APP `
    --resource-group $RESOURCE_GROUP `
    --image "$REGISTRY.azurecr.io/score-analyzer-frontend:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "前端 Container App 更新失败!" -ForegroundColor Red
    exit 1
}

Write-Host "`n========== 部署完成! ==========" -ForegroundColor Green
Write-Host "前端地址: https://xscore-app.com" -ForegroundColor Cyan
Write-Host "后端地址: $BACKEND_API_URL" -ForegroundColor Cyan
Write-Host "镜像标签: latest, $GIT_HASH" -ForegroundColor Cyan
