# 环境方案（Local / Hybrid / Cloud）

目标：在同一个仓库中长期维护三种可切换的运行方式，且**所有可提交内容均不包含敏感信息/数据**。

> 共同前提：分析能力仍通过 Azure OpenAI（需要在本机 `.env`/环境变量中提供 `AZURE_OPENAI_*`，不要提交到 GitHub）。

---

## 如何告诉 Copilot：要开发 / 测试哪个环境

后续你给需求时，只要在开头补上 3–5 行“目标环境 + 验收方式”，我就能按你的预期实现和验证。

**环境代号（与本文一致）**
- A = Local-All（纯本地，除 Azure OpenAI 外）
- B = Hybrid（本地代码 + 云端数据库）
- C = Cloud-All（纯云端：Azure Container Apps）

**请求模板（复制后填空即可）**
```text
ENV: A | B | C
Component: backend | frontend | both
Run: local-process | docker-compose | ACA-deploy
Verify:
	- Steps: （复现/操作步骤）
	- Expected: （期望结果）
Config:
	- Backend env file: backend/.env (local only, do not commit)
	- Template reference: backend/.env.local.example | backend/.env.clouddb.example
Notes:
	- Do NOT paste real secrets/connection strings into chat; keep them only in your local .env.
```

**建议约定**
- 日常开发/联调默认用 A；需要与线上共享历史/配额/账号数据时用 B（建议专用测试账号）；发版/演示用 C。
- 验收优先写清楚“测哪个页面/接口 + 具体步骤 + 期望”，比描述实现细节更可靠。

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

# 重要：后端 env vars（示例）
# - 第二资源（可选）用于 AOAI 可恢复错误的快速切换
# - secrets 建议用 `az containerapp secret set` 管理 key，不要明文出现在命令行历史
#
# AZURE_OPENAI_RESPONSES_URL=https://<resource>.openai.azure.com/openai/v1/responses
# AZURE_OPENAI_RESPONSES_URL_2=https://<resource-2>.openai.azure.com/openai/v1/responses
# PARSING_MODEL=o4-mini
# PARSING_MODEL_2=o4-mini
# ANALYSIS_MODEL=gpt-4.1-nano
# ANALYSIS_MODEL_2=gpt-4.1-nano
# OPENAI_REQUEST_TIMEOUT_SECONDS=600
# OPENAI_REQUEST_MAX_RETRIES=2

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
