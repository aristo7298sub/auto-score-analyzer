# 环境配置说明

本项目使用 Vite 的环境变量系统来管理不同环境的配置。

## 环境变量文件

- `.env.development` - 本地开发环境（`npm run dev` 时使用）
- `.env.production` - 生产环境（`npm run build` 时使用）
- `.env.local` - 本地覆盖配置（优先级最高，不提交到 Git）
- `.env.example` - 环境变量示例文件

## 本地开发

```bash
# 启动开发服务器，自动使用 .env.development
npm run dev

# API 会自动连接到 http://localhost:8000
```

## 生产部署

### 方式 1: 使用默认配置
```bash
# 构建时使用 .env.production 中的配置
docker build -t frontend .
```

### 方式 2: 通过构建参数指定（推荐）
```bash
# 通过 --build-arg 传入后端 URL
docker build \
  --build-arg VITE_API_URL=https://your-backend-url.com \
  -t frontend .
```

### Azure Container Registry 构建
```bash
# 构建并推送到 ACR
az acr build \
  --registry <acr-name> \
  --image score-analyzer-frontend:<tag> \
  --build-arg VITE_API_URL=https://<backend-fqdn> \
  --file frontend/Dockerfile \
  frontend/
```

## 重要说明

⚠️ **Vite 的环境变量是在构建时打包进去的**，不是运行时读取的！

这意味着：
- 修改 Container App 的运行时环境变量 **不会** 生效
- 必须 **重新构建镜像** 才能更改 API URL
- 构建时必须传入正确的 `VITE_API_URL`

## 环境变量优先级

高 → 低：
1. `--build-arg` 构建参数
2. `.env.production`（生产构建）/ `.env.development`（开发环境）
3. 代码中的 fallback 值

## 验证配置

构建后可以检查打包后的文件：
```bash
# 查看构建产物中的 API URL
grep -r "localhost:8000" dist/
# 如果有输出，说明配置错误
```
