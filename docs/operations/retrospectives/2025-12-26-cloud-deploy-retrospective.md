# 2025-12-26 云端部署复盘（本地验证通过，但 ACA 仍出现多类问题）

目标：解释“为什么本地测过了，云端还是踩坑”，并沉淀一套可复用的预防与自检流程。

> 约束：不记录任何真实密钥/连接串/域名；命令与配置使用占位符。

---

## 一、结论摘要

本次问题并不是“本地测试无效”，而是**本地验证覆盖不到云端关键差异**，主要集中在：

1) **构建期 vs 运行期差异**（尤其是 Vite 的 `VITE_*` 注入）
2) **CORS 预检（OPTIONS）只在真实跨域 + HTTPS 下稳定触发**
3) **云端数据库是“老库”**（schema 演进/缺列/类型差异，本地新库无法覆盖）
4) **timezone-aware vs naive datetime**（PostgreSQL 更容易暴露）
5) **环境漂移（env drift）与脚本覆盖**（脚本把线上配置“覆盖回滚”）

---

## 二、发生了什么（按问题类型归纳）

### 1) 前端“看起来没发请求”（ERR_INVALID_URL / Network 面板无请求）

- 本地为什么没暴露：
  - `npm run dev` 往往使用 Vite proxy/同源路径；即使 `VITE_API_URL` 配错，也可能仍能打到本地后端。
- 云端为什么必炸：
  - ACA 前端是静态产物（Nginx + Vite build），`VITE_API_URL` 是**构建期烘焙**进 bundle 的。
  - 镜像构建时如果没有注入真实后端 URL，产物会包含占位符/错误 URL，浏览器会直接拒绝发请求。

已采取的预防（当前仓库已落地）：
- 前端镜像构建时强制通过 `--build-arg VITE_API_URL=https://<backend-fqdn>` 注入。
- Dockerfile 增加构建失败保护：缺失/占位符则直接 fail fast。

### 2) CORS 预检失败（OPTIONS 400 / 无 Allow-Origin）

- 本地为什么没暴露：
  - 同源/代理下预检不一定触发，或者 allowlist 已包含 localhost。
- 云端为什么常见：
  - 自定义域名（root + www）/ ACA 默认域名等组合，会导致 Origin 多样。
  - 后端 `CORS_ORIGINS` 少一个域名就会预检失败。
- 复发根因：
  - 部署脚本在发布末尾覆盖 `CORS_ORIGINS`，把你手工加过的域名冲掉。

已采取的预防（当前仓库已落地）：
- 部署脚本改为“**合并并回写**” CORS allowlist（ACA 默认前端域名 + 自定义域名 + `.env` 显式配置）。

### 3) 云端老用户登录 500（数据库缺列/缺表）

- 本地为什么没暴露：
  - 本地通常是新 SQLite，启动 `create_all` 后 schema 与代码一致。
- 云端为什么常见：
  - PostgreSQL 是历史库（老 schema），新增字段后如果没有迁移会缺列。

应对策略：
- 长期：用 Alembic 做正式迁移（推荐）。
- 短期：best-effort 补列用于小范围兼容（但要控制范围与风险）。

### 4) datetime naive vs aware（TypeError）

- 本地为什么可能不触发：
  - SQLite/不同字段配置下返回值语义不同；或者测试路径没有覆盖到会比较时间的分支。
- 云端为什么稳定触发：
  - PostgreSQL + timezone-aware 字段返回 tz-aware datetime；代码若用 `datetime.utcnow()`（naive）比较会直接 TypeError。

已采取的预防（当前仓库已落地）：
- 统一使用 timezone-aware UTC `utcnow()`（内部用 `datetime.now(timezone.utc)`）。

### 5) 环境漂移（env drift）导致排障复杂、误配置风险高

- 典型表现：线上残留旧的 AOAI env（例如 `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_VERSION` / `AZURE_OPENAI_DEPLOYMENT_NAME`），虽然不一定立即坏，但会：
  - 误导排障（你看到变量还在，以为系统还在用）
  - 增加脚本/文档口径不一致概率

建议：
- 发布后把“无用旧变量”清理掉（保持最小集）。

---

## 三、为什么“本地测试”仍然重要（但需要补齐形态）

本地验证能确保：
- 代码逻辑正确、接口返回合理、前后端可跑通。

但要覆盖云端关键差异，还需要在本地补齐两类“同构验证”：

1) **生产构建形态验证**
- 前端：至少跑一次 `npm run build`（更进一步：本地 docker build，确保 build-arg 注入路径正确）
- 后端：`python -m compileall` + 关键接口冒烟

2) **云端依赖验证（尤其是 Postgres）**
- Hybrid 模式：本地代码连接云端 DB，跑一次登录/绑定邮箱/解析会话等会涉及时间比较与历史数据的路径。

---

## 四、发布后 3 分钟自检（每次必做）

> 目标：快速排除“构建期注入 / CORS / 路由加载”三大类高频问题。

```powershell
$backend = "https://<your-backend-fqdn>"

# 1) 健康检查
curl.exe -sS "$backend/health"

# 2) CORS 预检（根据你的前端域名替换 Origin）
curl.exe -i -X OPTIONS "$backend/api/auth/login" `
  -H "Origin: https://<your-frontend-domain>" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"

# 3) OpenAPI 验证（确认关键路由已加载）
curl.exe -sS "$backend/openapi.json" | findstr /C:"/api/files/parse/preview" /C:"/api/files/parse/confirm"
```

---

## 五、行动项（最小且高收益）

- 发布脚本：所有“写 env”的行为必须幂等，避免覆盖用户配置。
- 文档：统一口径（AOAI 使用 Responses URL + model 分离；Vite 必须构建期注入）。
- 数据库：把 Alembic 迁移纳入发布流程；best-effort 仅用于救火。
- 自检：把“3 分钟自检”加入每次发布 checklist，失败即回滚/修复，不进入功能排查。
