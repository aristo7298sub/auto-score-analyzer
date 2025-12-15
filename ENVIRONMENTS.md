# 环境方案（Local / Hybrid / Cloud）

目标：在同一个仓库中长期维护三种可切换的运行方式，且**所有可提交内容均不包含敏感信息/数据**。

> 共同前提：分析能力仍通过 Azure OpenAI（需要在本机 `.env`/环境变量中提供 `AZURE_OPENAI_*`，不要提交到 GitHub）。

---

## A. 纯本地环境（Local-All，除 Azure OpenAI 外）

适用：日常功能开发/联调；希望所有数据、文件都只在本机。

- 后端：本机 FastAPI
- 数据库：本机 SQLite（`DATABASE_URL=sqlite:////app/data/score_analyzer.db` 或本地路径）
- 文件存储：本地（`STORAGE_TYPE=local`）
- 前端：本机 Vite Dev Server

**配置方式**
- 后端使用 `backend/.env`（该文件已被 `.gitignore` 排除）
- 参考模板：`backend/.env.local.example`

**启动**
```powershell
# 后端
cd backend
python run.py

# 前端
cd frontend
npm run dev
```

---

## B. 本地开发 + 云端数据库（Hybrid：Local code + Cloud DB）

适用：你提到的“本地测试也依托相同的云端账号/配额/历史记录”，但仍保留本机代码调试体验。

- 后端：本机 FastAPI
- 数据库：云端 PostgreSQL（`DATABASE_URL=postgresql+psycopg2://...`）
- 文件存储：默认建议仍为本地（避免污染云端）；如需与线上一致可切换到 Azure Blob
- 前端：本机 Vite Dev Server

**配置方式**
- 参考模板：`backend/.env.clouddb.example`
- 只需把 `DATABASE_URL` 换成云端连接串（不要提交）

**风险提示**
- 该模式会直接改动云端用户/配额/历史数据；请使用专用测试账号。

---

## C. 纯云端环境（Cloud-All：Azure Container Apps）

适用：生产/演示。

- 后端：Azure Container Apps（连接云端 PostgreSQL + Azure Blob）
- 前端：Azure Container Apps（静态 Nginx）
- 构建发布：ACR 远程构建 + `az containerapp update`

**发布模板**
```powershell
$rg  = '<resource-group>'
$acr = '<acr-name>'
$tag = "feature-xxxx-$(Get-Date -Format yyyyMMdd-HHmmss)"

az acr build -r $acr -t "score-analyzer-backend:$tag"  -f backend/Dockerfile  backend
az acr build -r $acr -t "score-analyzer-frontend:$tag" -f frontend/Dockerfile frontend

$loginServer = (az acr show -n $acr --query loginServer -o tsv)

az containerapp update -g $rg -n <backend-app>  --image "$loginServer/score-analyzer-backend:$tag"
az containerapp update -g $rg -n <frontend-app> --image "$loginServer/score-analyzer-frontend:$tag"

az containerapp revision list -g $rg -n <backend-app>  -o table
az containerapp revision list -g $rg -n <frontend-app> -o table
```

---

## 可提交 / 不可提交

**可提交**
- 代码（前后端）
- 文档（本文件、流程说明）
- 示例配置：`*.example`（不含真实值）

**不可提交**
- `.env`、`.env.*.local`、任何真实连接串/密钥
- 本地数据库文件（`.db/.sqlite`）
- 上传文件/导出文件/图表等数据目录
- Azure 资源导出 YAML（包含订阅/资源 ID）
