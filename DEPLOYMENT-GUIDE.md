# Azure VM 部署指南

## 🚀 首次部署步骤

### 1. SSH连接到Azure VM

```bash
ssh azureuser@40.81.16.161
```

### 2. 克隆仓库（如果GitHub Actions还未触发）

```bash
cd /opt
sudo git clone https://github.com/aristo7298sub/auto-score-analyzer.git
sudo chown -R azureuser:azureuser auto-score-analyzer
cd auto-score-analyzer
```

### 3. 配置环境变量（重要！）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

**必须配置的变量：**

```env
# Azure OpenAI 配置（必填）
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# 存储配置
STORAGE_TYPE=local

# 后端API地址（生产环境）
BACKEND_URL=http://40.81.16.161:8000

# CORS允许的源（生产环境）
CORS_ORIGINS=["http://40.81.16.161","http://localhost"]
```

保存并退出：`Ctrl+O` → `Enter` → `Ctrl+X`

### 4. 启动服务

```bash
# 启动所有容器
docker-compose up -d --build

# 查看启动日志
docker-compose logs -f

# 等待约3-5分钟让所有服务启动完成
```

### 5. 检查服务状态

```bash
# 查看容器状态
docker-compose ps

# 健康检查
curl http://localhost/health

# 查看后端日志
docker-compose logs backend

# 查看前端日志
docker-compose logs frontend
```

## 🔄 后续更新（自动化）

配置完成后，每次你推送代码到GitHub：

```bash
git add .
git commit -m "Your changes"
git push
```

GitHub Actions会自动：
1. SSH到Azure VM
2. 拉取最新代码
3. 重新构建并重启容器
4. 清理旧镜像

## 🌐 访问应用

- **前端：** http://40.81.16.161
- **API文档：** http://40.81.16.161/api/docs
- **健康检查：** http://40.81.16.161/health

## 🛠️ 常用命令

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f [service-name]

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全重新构建
docker-compose up -d --build --force-recreate

# 清理未使用的镜像
docker image prune -a -f

# 查看磁盘使用
docker system df
```

## ⚠️ 故障排除

### 服务启动失败

```bash
# 查看详细日志
docker-compose logs --tail=100 backend
docker-compose logs --tail=100 frontend

# 检查.env配置
cat .env
```

### 端口被占用

```bash
# 检查端口使用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# 停止占用端口的进程
sudo kill -9 <PID>
```

### 磁盘空间不足

```bash
# 清理Docker
docker system prune -a -f
docker volume prune -f

# 查看磁盘使用
df -h
```

## 🔐 安全建议

1. **定期更新密钥**
   - 在GitHub Secrets中更新SSH密钥
   - 更新Azure OpenAI API密钥

2. **监控日志**
   ```bash
   docker-compose logs -f | grep -i error
   ```

3. **备份数据**
   ```bash
   # 备份数据目录
   sudo tar -czf backup-$(date +%Y%m%d).tar.gz backend/data backend/exports
   ```

## 📊 性能优化

### 查看资源使用

```bash
# 容器资源使用
docker stats

# 系统资源
htop
```

### 限制容器资源（可选）

编辑 `docker-compose.yml` 添加：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

## 🎯 下一步

- [ ] 配置HTTPS（使用Let's Encrypt）
- [ ] 设置监控告警
- [ ] 配置自动备份
- [ ] 优化Docker镜像大小
