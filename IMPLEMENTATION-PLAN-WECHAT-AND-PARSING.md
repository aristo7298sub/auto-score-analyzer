# 实施方案（历史/备忘）：邮箱验证登录（阶段一）+ 全能文件解析 + 微信扫码登录（最终版）

> 注意：该文档为实施过程中的“定稿方案/计划备忘”，其中部分内容（例如“邮箱验证码登录”等）与当前线上行为可能已不一致。
> 当前生产/演示部署与排障请以 [CONTAINER-APPS-DEPLOYMENT.md](CONTAINER-APPS-DEPLOYMENT.md) 为准。

> 目标：在不引入额外“花哨”UX的前提下，新增两项核心能力：
> 1) 全能文件解析（Excel/Word/PPT，AI 理解结构 + 用户最小确认映射）；
> 2) 登录体系：
>    - 阶段一（即将实施）：注册必须填写邮箱并完成邮箱验证；登录支持“用户名+密码（JWT）”或“邮箱+6位验证码（JWT）”；本期同时上线“忘记密码/重置密码”。
>    - 最终版（延期）：微信开放平台「网站应用」扫码注册/登录（需备案条件满足后再做）。
>
> 重要约束：仓库内所有域名/资源标识均用占位符（例如 `<frontend-host>`、`<backend-host>`、`<primary-domain>`），避免真实基础设施信息进入 Git 历史。

---

## 0. 已确认决策（本方案依据）

- 阶段一登录方式：
  - 登录态：JWT（前端 `Authorization: Bearer <token>`），不切 Cookie。
  - 注册：必须填写邮箱并完成邮箱验证。
  - 登录：用户名+密码，或 邮箱+6位验证码。
  - 找回：本期必须包含“忘记密码/重置密码”。
- 最终版（延期）：微信开放平台「网站应用」扫码登录（PC Web）。
- 域名：已拥有自有域名。
- 邀请码：可选；无邀请码用户默认配额为 0；允许后补邀请码。
- 全能文件解析输入范围：Excel / Word / PPT（统一走同一套 Extract → Infer → Normalize → Validate 流程）。
- 文件解析：AI 负责“理解结构/产出映射规则 + 置信度/建议”，程序负责“全量计算解析结果”。
- 文件得分/扣分：Excel 中可能是得分项或扣分项，表头会明确标识，解析需识别并区分。
- 模型留口子：解析与分析未来可使用不同模型（解析可能用 reasoning，分析用更便宜更快）。
- 最小交互：在个人设置/配额页提供邀请码输入框；文件解析流程提供“确认映射”最小交互。

---

## 1. 域名与部署（阶段一 JWT + 为最终版预留）

### 1.1 推荐的域名形态（强烈建议）

- 前端：`https://www.<primary-domain>`（或根域 `https://<primary-domain>`）
- 后端 API：`https://api.<primary-domain>`

原因：
- 阶段一使用 JWT：对同站/跨站的限制较少，但仍建议统一自有域名以简化 CORS 与未来演进。
- 最终版若切到 Cookie 或接入微信回调：将 API 放在 `api.<primary-domain>` 仍是更稳的路线。

### 1.2 DNS / 自定义域名绑定（执行时）

- DNS：新增子域 `api` 记录（通常 `CNAME`）指向后端容器的默认域名（不写入仓库）。
- Azure Container Apps：后端绑定 `api.<primary-domain>`，启用 HTTPS（托管证书或自有证书）。
- 前端域名继续指向前端容器（现状已具备）。

### 1.3 前端 API 地址注入方式（已确认：构建时注入）

当前前端镜像为静态资源（nginx + Vite build），API 地址来自构建时 `VITE_API_URL`：
- 修改 `VITE_API_URL` 必须重建前端镜像并更新前端容器版本。
- 运行时在容器环境变量里修改通常不会影响已编译产物。

> 如未来需要“运行时切换 API”，再规划运行时注入（启动脚本生成 `config.js` / `env.json`）。本期不做。

---

## 2. 登录体系：阶段一（邮箱验证 + 双登录方式，JWT）与最终版（微信扫码）

### 2.1 阶段一：身份与账号模型原则

- `email` 必填且唯一；必须完成邮箱验证后才能登录/消耗配额。
- `username` 仍作为用户名登录入口（保持兼容与迁移成本最低）。
- 避免账号枚举：发送验证码/重置密码等接口对“邮箱是否存在”返回统一提示。

### 2.2 阶段一：注册流程（必须邮箱验证）

建议交互（不新增页面）：
- `/register`：输入 `username`、`password`、`email`、`invite_code(可选)`
- 点击“发送验证码”→ 邮箱收到 6 位验证码
- 填写验证码→ 完成注册（或完成验证后再自动登录）

后端建议接口：
1) `POST /api/auth/email/send-verification-code`
- 输入：`email`
- 输出：统一提示（不暴露邮箱是否存在）

2) `POST /api/auth/email/verify`
- 输入：`email` + `code(6位)`
- 输出：验证成功/失败（失败需有冷却/次数限制）

3) `POST /api/auth/register`
- 输入：`username` + `password` + `email` + `invite_code(可选)` + `email_verification_proof`
- 输出：`access_token`（JWT）

> 说明：注册可设计为“先注册后验证”或“先验证后注册”。为了简化并避免垃圾账号，推荐“先验证邮箱再创建账号”。

### 2.3 阶段一：登录方式 A（用户名 + 密码，JWT）

- 复用现有 `POST /api/auth/login`（若已存在）
- 增加限制：若 `email_verified=false`，禁止登录或禁止消耗（建议直接禁止登录并引导完成验证）

### 2.4 阶段一：登录方式 B（邮箱 + 6 位验证码，JWT）

后端建议接口：
1) `POST /api/auth/email/send-login-code`
- 输入：`email`
- 输出：统一提示（不暴露是否存在）

2) `POST /api/auth/email/login`
- 输入：`email` + `code(6位)`
- 输出：`access_token`（JWT）

### 2.5 阶段一：忘记密码 / 重置密码（本期必须）

后端建议接口：
1) `POST /api/auth/password/reset/request`
- 输入：`email`
- 输出：统一提示（不暴露是否存在）

2) `POST /api/auth/password/reset/confirm`
- 输入：`email` + `code(6位)` + `new_password`
- 输出：成功/失败

安全最小要求（建议写入实现验收）：
- 验证码必须有 TTL（例如 10 分钟）+ 单次使用 + 错误次数限制（例如 5 次）
- 验证码存储必须哈希化（不要明文落库/落缓存）
- 发送频率限制（按 IP + email 维度）与冷却时间（例如 60 秒）

### 2.6 最终版（延期）：微信扫码注册/登录（网站应用）

> 由于备案条件限制，本节作为“最终版保留方案”，阶段一不实现。

### 2.1 身份与账号模型原则

- 内部唯一标识：`wechat_openid`（或 `unionid`，视开放平台能力）。
- 展示名：`wechat_nickname`（满足“用户名即微信名”的体验）。
- 不以昵称作为唯一键（昵称可变且可重复）。

### 2.2 邀请码与配额规则

- 注册/首次登录时：邀请码输入可选。
- 若无邀请码：账号创建成功，但默认配额为 0（无法实际消耗配额）。
- 允许后补邀请码：用户登录后在个人设置/配额页提交邀请码，校验成功后发放配额/解锁权限。

### 2.3 后端接口（建议）

1) `GET /api/auth/wechat/login-url?invite_code=<optional>`
- 生成 `state`（强随机、一次性、带 TTL）
- 暂存 `state -> invite_code`（缓存/DB）
- 返回微信登录二维码 URL（包含 `redirect_uri` 和 `state`）

2) `GET /api/auth/wechat/callback?code=...&state=...`
- 校验 `state`（存在、未过期、未使用）
- 使用 `code` 换取 openid（及昵称等）
- 查用户：存在则登录；不存在则创建用户（无邀请码则配额=0）
- 签发登录态：设置 HttpOnly Cookie
- 302 跳回前端（例如 `https://www.<primary-domain>/` 或 `.../login/success`）

3) `POST /api/auth/invite/bind`
- 登录态下提交邀请码
- 校验邀请码有效性与绑定规则
- 完成绑定并发放配额/解锁

### 2.4 Cookie 与 CORS 约束（必须满足）

Cookie 建议：
- `HttpOnly=true`
- `Secure=true`
- `SameSite=Lax`（在 `www.<primary-domain>` → `api.<primary-domain>` 同站场景下更稳）
- 可选：`Domain=.<primary-domain>`（让 `www` 与 `api` 共享；如不希望共享则不设置）

CORS（FastAPI）建议：
- `allow_origins=["https://www.<primary-domain>"]`（不要 `*`）
- `allow_credentials=true`

### 2.5 微信开放平台配置（执行时）

- 创建应用类型：网站应用
- 获取 `AppID` / `AppSecret`
- 配置回调域名（常见做法）：`<primary-domain>`
- 统一回调地址：`https://api.<primary-domain>/api/auth/wechat/callback`

---

## 3. 全能文件解析（Excel/Word/PPT）

> 本期目标不是“只支持某一种模板的 Excel”，而是把 Excel / Word / PPT 都纳入同一条可扩展的解析管线：
> - Excel：以表格为主（多 Sheet / 多行表头 / 合并单元格 / 宽表/长表/混合）。
> - Word：以段落 + 表格为主。
> - PPT：以分页内容（标题/文本框/表格）为主。

### 3.1 总体架构：Extract → Infer → Normalize → Validate

目标：无论输入文件结构如何，都产出统一结构：
- `StudentScore(student_name, total_score, scores=[ScoreItem...])`

适用范围：
- 上传文件类型为 Excel/Word/PPT 时，均先提取 IR 摘要（按文件类型不同提取策略不同），再进入同一套 AI mapping + 程序化 normalize 的主链路。

关键原则：
- AI 不直接输出全量结果；AI 输出“结构理解 + 映射规则（mapping plan）+ 置信度 + 失败原因/建议”。
- 程序基于 mapping plan 读取全量数据生成结果（可重复、可校验、可控成本）。

### 3.2 中间表示（IR：Intermediate Representation）

Excel（重点）：
- sheet 列表（名称、可用区域）
- 表头候选（可能多行表头）
- 合并单元格信息（合并范围与值）
- 采样行（头/中/尾各 N 行）
- 列统计（数值占比、空值占比、文本长度分布）

Word：
- 段落列表（含标题层级信息）
- 表格二维数据

PPT：
- 按页提取文本框/标题/表格内容（页码 + 元素文本）

> 大文件不发送全量到模型，只发送“结构摘要 + 样本”，避免 token 爆炸。

### 3.3 AI 结构识别输出（严格 JSON）

建议输出字段（示例）：
- `confidence: 0..1`
- `detected_layout: "wide" | "long" | "mixed"`
- `mapping_plan: { ... }`
  - `student_identifier`：姓名列/姓名字段定位规则
  - `total_score`：总分列/字段（可选）
  - `items`：扣/得分项字段来源（知识点列、题目列、明细表等）
  - `scoring_mode`：`"deduction" | "gain"`（由表头/列名明确判断）
  - `deduction_value_field`：若存在真实分值字段则映射，否则为空
- `errors[]`（无法解析时原因）
- `recommendations[]`（建议用户提供的结构/模板）

### 3.4 语义方案：扩展 ScoreItem（推荐，已确认）

为兼容“得分项/扣分项”，建议扩展数据模型：
- 在 `ScoreItem` 增加 `direction: "deduction" | "gain"` 或 `score_delta: float`（正负表示加/扣）

推荐实现：
- 增加 `score_delta`（更通用）：
  - 扣分：`score_delta = -abs(value)`
  - 得分：`score_delta = +abs(value)`
- 同时保留一个统一展示字段（如仍需 `deduction`，可在输出时兼容映射，但内部以 `score_delta` 为准）。

> 这样未来做统计时可按方向聚合；也不强依赖“每题分值不同”的绝对数值。

### 3.5 程序化 Normalize（全量计算）

- 根据 mapping_plan 遍历全量表格/段落：
  - 关联学生（姓名/学号）
  - 解析条目（知识点/题号/描述 + 分值 + 方向）
  - 生成 `StudentScore[]`
- 若真实分值缺失：允许使用默认值（例如 1.0）并标记 `value_source="marker"`（可选）

### 3.6 Validate（校验 + 可解释失败）

- 姓名字段有效性：空值比例、重复率、是否像“姓名”
- 总分字段：数值占比、范围合理性
- 条目字段：是否能生成足够条目、异常比例

失败时返回：
- 明确失败原因（例如“无法识别姓名列/总分列”）
- 推荐模板（例如“请提供一列姓名 + 一列总分 + 题目/知识点列”）

---

## 4. 文件解析最小交互：确认映射（MVP）

### 4.1 交互目标

- AI 猜对：用户 1 次确认即可继续
- AI 猜错：用户通过下拉框修正 1～2 个关键字段即可

### 4.2 前端展示要素（建议）

- 置信度提示（高/中/低）+ 失败原因/建议
- 下拉框（字段映射）：
  - 学生标识（姓名/学号）
  - 总分字段（可选）
  - 条目字段：知识点/题目/描述
  - 分值字段（可选）
  - 方向字段（得分/扣分：可从表头推断，必要时允许用户选择）
- 预览表（前 10 行），随映射变化实时刷新
- 按钮：确认并解析

### 4.3 后端 API（建议拆 2 段）

1) `POST /api/files/parse/preview`
- 输入：文件标识
- 输出：IR 摘要 + AI mapping + 预览数据 + recommendations（适用于 Excel/Word/PPT）

2) `POST /api/files/parse/confirm`
- 输入：用户确认后的 mapping
- 输出：最终 `StudentScore[]`

---

## 5. 个人设置/配额页：邀请码输入框（最小）

### 5.1 交互内容

- 一个输入框：邀请码
- 一个按钮：绑定/提交
- 状态提示：成功/失败原因

### 5.2 后端支持

- `POST /api/auth/invite/bind`（见 2.3）
- 校验：邀请码存在、可复用、绑定规则（是否允许重复绑定等）
- 发放额度：无邀请码用户绑定成功后为其发放初始额度（具体额度策略可配置）

---

## 6. 数据模型建议（ERD 文字版，最小改动优先）

本节描述“建议的数据模型”，并尽量复用现有后端的 SQLAlchemy 表结构（当前仓库已存在：`users`、`quota_transactions`、`analysis_logs`、`score_files`）。

### 6.1 核心实体与关系（文字 ERD）

- `users`（用户）
  - 1 -> N `quota_transactions`（配额流水）
  - 1 -> N `analysis_logs`（分析/解析日志）
  - 1 -> N `score_files`（上传文件记录）
  - 自关联：`users.referred_by -> users.id`（可选，表示邀请码绑定关系）

- `quota_transactions`（配额流水）
  - N -> 1 `users`
  - 用于记录：注册奖励、邀请码奖励、管理员加配额、分析扣费、退款等

- `analysis_logs`（请求日志）
  - N -> 1 `users`
  - 建议扩展：区分“解析预览/确认解析/分析总结”三类动作（可用 `status`/`file_type`/`description` 或新增字段）

- `score_files`（文件记录）
  - N -> 1 `users`
  - `analysis_result` 可继续用 JSON 字符串存完整结果（适合快速迭代，不强依赖结构迁移）

### 6.2 阶段一：邮箱登录/验证（建议新增字段，最小改动）

在 `users` 表新增字段建议：
- `email`：字符串，唯一索引（必填）
- `email_verified`：布尔，默认 `false`
- `email_verified_at`：时间戳，可空

验证码/令牌存储（推荐方案）：

**默认推荐：DB 表（生产已使用 PostgreSQL，且后端可能多副本时天然一致，无需额外 Redis 成本）**

新增表建议：`email_verification_codes`
- `id` (PK)
- `email`
- `purpose`：`verify` / `login` / `reset`
- `code_hash`
- `attempts`
- `expires_at`
- `used_at` (nullable)
- `created_at`

**可选增强：Redis/缓存（用于更强的限流、防刷、会话缓存；非本期必需）**
- key：`email_code:<purpose>:<email>`（purpose: verify/login/reset）
- value：`code_hash` + `expires_at` + `attempts`

> 结论：阶段一先落地 DB 表方案；若后续确需更强的限流/缓存能力，再引入 Redis。

### 6.3 最终版（延期）：微信登录（建议新增字段/表，二选一）

你当前 `users` 表里有 `username` 唯一约束 + `hashed_password` 非空约束。为了“最小改动”且不一次性破坏既有账号体系，我建议如下两种落地方式，优先推荐 A：

**A) 仅扩展 `users` 表（实现最省事）**

新增字段建议：
- `auth_provider`：字符串/枚举，例如 `password` / `wechat`
- `wechat_openid`：字符串，唯一索引（网站应用维度唯一）
- `wechat_unionid`：字符串，可空（若可获取，跨应用更稳）
- `wechat_nickname`：字符串，可空（展示名）
- `wechat_avatar_url`：字符串，可空
- `password_login_disabled`：布尔，可选（若 `auth_provider=wechat` 则默认禁用密码登录）

`username` 字段如何满足“用户名即微信名”且保持唯一：
- 首选：`username = wechat_nickname`（若唯一）
- 若重名：`username = wechat_nickname + "#" + <openid 末尾 4~6 位>`（仍保持“看起来是微信名”）

`hashed_password` 处理建议（避免大迁移）：
- 对微信用户：写入一个随机不可猜的占位 hash（但在登录逻辑中禁止密码登录）

**B) 新增 `wechat_identities` 表（更规范，后续扩展更强）**

新增表建议：`wechat_identities`
- `id` (PK)
- `user_id` (FK -> users.id, unique)
- `openid` (unique)
- `unionid` (nullable)
- `nickname` / `avatar_url`
- `created_at`

优点：不污染 `users` 主表；未来如果要接入其它身份源（例如企业微信/飞书/Google）也更一致。
缺点：实现比 A 稍多一点点。

> 本期建议优先 A（快且足够），等需求再演进到 B。

### 6.4 邀请码机制（复用现有字段即可）

现有字段已基本满足：
- `users.referral_code`：每个用户唯一邀请码（可复用邀请多人）
- `users.referred_by`：可选，被谁邀请（支持“后补邀请码”）
- `users.referral_count`：统计成功邀请人数
- `users.quota_balance = 0`：满足“无邀请码默认 0 配额”的规则

后补邀请码推荐规则（避免滥用）：
- 仅允许绑定一次：`referred_by is NULL` 才能绑定
- 不允许自绑：`referrer.id != current_user.id`
- 绑定成功后：
  - 更新 `current_user.referred_by = referrer.id`
  - `referrer.referral_count += 1`
  - 用 `quota_transactions` 分别记录“邀请奖励/新用户奖励”（数值可配置）

### 6.5 文件解析会话（Preview/Confirm 的状态存储）

为了支持多副本部署（多实例）和“确认映射”交互的幂等性，建议保存一次预解析的中间状态。

两种方式：

**A) 使用 Redis/缓存（推荐，成本低）**
- key：`parse_session:<session_id>`
- value：IR 摘要、AI mapping、置信度、预览数据、过期时间

**B) 新增 DB 表（更可审计）**

新增表建议：`file_parse_sessions`
- `id` (PK)
- `user_id` (FK)
- `score_file_id` (FK, nullable：若 preview 在落库前发生)
- `status`：`previewed` / `confirmed` / `expired`
- `ir_json` (Text)
- `ai_mapping_json` (Text)
- `confidence` (Float)
- `created_at` / `expires_at`

> 本期如果你不想引入 Redis，可直接选 B；如果你计划扩容/多实例，A 更合适。

### 6.6 解析结果语义方案（ScoreItem 扩展建议）

当前 API 的 `ScoreItem` 只有 `deduction`，无法表达“得分项”。本期你已选择“语义方案”，建议按如下方式扩展：

建议新增字段（至少一个）：
- `score_delta: float`（推荐）：正数=得分，负数=扣分
- 可选 `direction: "gain"|"deduction"`（用于展示/调试；也可由 `score_delta` 推断）
- 可选 `value_source: "explicit"|"marker"`（明确给分值 vs 仅标记）

兼容策略（避免立刻影响前端/旧数据）：
- 保留 `deduction` 字段一段时间作为兼容输出（例如：`deduction = abs(min(score_delta, 0))`）
- 新前端优先使用 `score_delta` 做展示和统计

---

## 7. 模型配置：解析与分析分离（环境变量建议）

### 7.1 推荐方式

使用环境变量（适配容器与 ACA Secrets），并允许解析/分析分别配置：

- 通用：
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_API_VERSION`

- 解析专用：
  - `PARSING_MODEL` 或 `PARSING_DEPLOYMENT`
  - `PARSING_MAX_TOKENS`
  - `PARSING_TEMPERATURE`

- 分析专用：
  - `ANALYSIS_MODEL` 或 `ANALYSIS_DEPLOYMENT`
  - `ANALYSIS_MAX_TOKENS`
  - `ANALYSIS_TEMPERATURE`

### 7.2 回退策略

- 若未配置 `PARSING_*`，解析任务回退使用 `ANALYSIS_*` 或默认值。
- 解析任务建议：低温度 + 强制 JSON 输出 + 重试策略。

> 注意：Azure OpenAI 常见用法是“部署名（deployment）”而不是“模型名（model）”。建议在代码里同时支持两者，但以 `*_DEPLOYMENT` 为主。

---

## 8. UI 适配与丝滑迁移（完全复用现有 UI 框架）

本项目前端已使用 Ant Design（`ConfigProvider` + 大量页面组件），同时登录/注册页当前仍是自定义 HTML + CSS 表单。为了“完全使用现有 UI 框架、迁移成本最低”，建议在本期功能开发中把**需要改动的页面**统一迁移到 Ant Design 组件体系，避免引入任何新 UI 库。

### 8.1 现状快速盘点（与本方案相关）

- 路由结构：
  - `/login`、`/register` 为公开路由
  - `/quota` 在主布局内（已大量使用 AntD）
  - `/`（Home 上传与分析）已使用 AntD Upload/Card/Button 等

- 状态/鉴权：
  - 前端 `apiClient` 目前默认走 `Authorization: Bearer <token>`（JWT）
  - 阶段一确认：继续使用 JWT，不切 Cookie；最终版如接入微信扫码，可再规划 Cookie 或双栈迁移。

### 8.2 登录/注册页的“无痛改造”建议（不新增页面）

目标（阶段一）：注册必须邮箱验证；登录支持“用户名+密码”与“邮箱+验证码”；邀请码在注册时可选填写，也可在 `/quota` 后补绑定。

- **保留原有路由不变**：仍使用 `/login` 与 `/register`，不新增页面。
- `/register?ref=XXXX` 的兼容：
  - 保持 `ref` 参数预填邀请码输入框。
  - 这样无需改动邀请链接生成逻辑，迁移最丝滑。

- UI 组件统一使用 AntD：
  - 使用 `Card` + `Form` + `Input` + `Button` + `Alert` + `Space`
  - 登录页可用最小的 `Tabs`/`Segmented` 切换：密码登录 vs 邮箱验证码登录（不新增页面/弹窗）
  - 保留现有 i18n 体系：所有文案继续用 `t('...')`

### 8.3 配额/个人设置：邀请码后补入口放哪里（最小改动）

你选择了“个人设置/配额页一个输入框（最小）”。现状 `Quota` 页面已经包含邀请卡片与奖励说明，建议直接在该页加入：

- 一个输入框：输入邀请码
- 一个按钮：绑定
- 成功/失败提示：使用 AntD `message` 或 `Alert`

这样不需要实现“设置页”，也不会引入新导航入口。

### 8.4 文件解析的最小交互：在 Home 上传流程内插入确认映射

Home 页面已包含上传→解析→点击 AI 分析的两阶段流程。本期“确认映射”可以无缝插入在“解析完成、尚未 AI 分析”之间：

- 上传后先调用 `/parse/preview` 获取 mapping + 预览
- 在 Home 页面解析结果区新增一个 AntD `Card`：
  - 使用 `Select`（或 `Form.Item` 下拉）展示字段映射（姓名列/总分列/条目列/方向列等）
  - 使用 AntD `Table` 展示前 10 行预览
  - 一个“确认并解析”按钮调用 `/parse/confirm`

这样不新增页面、不新增弹窗，仅在现有页面增加一个卡片区块，迁移成本最低。

---

## 9. 迁移顺序（建议，低风险/可回滚）

本项目后端目前没有 Alembic 迁移体系，而是通过 `Base.metadata.create_all` + `ensure_schema_compatibility()` 做 best-effort 增量兼容。为避免一次性大改导致线上不可用，建议按以下顺序推进。

### 9.1 第 0 阶段：仅加字段/不改行为（后端可先上线）

1) 数据库：新增邮箱相关字段（按 6.2）
  - `users.email`（唯一）+ `users.email_verified` 等
  - 验证码存储：默认采用 DB 表（生产 PostgreSQL 下支持后端多副本一致性）
2) 数据模型：扩展 `ScoreItem`（语义方案）
  - 新增 `score_delta`（或 `direction`/`value_source`）
  - 输出兼容：仍可生成旧字段 `deduction`（短期兼容前端）
3) 新增（或预留）解析会话存储
  - 选 Redis：先加依赖与配置但不强制启用
  - 或选 DB 表：先建表但不接入流程

验收：旧登录/旧上传/旧分析不受影响。

### 9.2 第 1 阶段：后端新增接口（仍不破坏旧接口）

1) 阶段一邮箱体系接口新增（保持旧密码登录可用）：
  - `POST /api/auth/email/send-verification-code`
  - `POST /api/auth/email/verify`
  - `POST /api/auth/email/send-login-code`
  - `POST /api/auth/email/login`
  - `POST /api/auth/password/reset/request`
  - `POST /api/auth/password/reset/confirm`
2) 邀请码后补接口（延续既定）：
  - `POST /api/auth/invite/bind`
3) 文件解析新增 preview/confirm：
  - `POST /api/files/parse/preview`
  - `POST /api/files/parse/confirm`

验收：旧前端不改动也可继续使用旧登录/旧解析；新接口可用 Postman/脚本验证。

### 9.3 第 2 阶段：前端迁移（逐步切换）

1) 先改登录/注册页 UI（AntD 化）
  - `/login`：提供“密码登录 / 邮箱验证码登录”两种入口（同页切换）
  - `/register`：必须邮箱验证（读取 `ref` 参数预填邀请码）
2) 鉴权：继续 JWT（本期确认不切 Cookie）
3) 配额页增加“后补邀请码”输入框（AntD Input+Button）
4) Home 页插入“确认映射”卡片（AntD Select+Table）

验收：
- 新用户扫码登录后能进入系统
- 无邀请码用户配额为 0 且无法消耗
- 绑定邀请码后配额发放生效
- 文件解析 preview/confirm 流程可跑通

### 9.4 第 3 阶段：收口与清理（可选）

- 当邮箱体系稳定后：
  - 视情况要求 `email_verified=true` 才能消耗配额（或才能登录）
  - 完善风控阈值（限流/黑名单/审计）

### 9.5 最终版（延期）：接入微信扫码登录

- 备案条件满足后再启用微信扫码登录（保留本文件中 2.6 的方案）
- 可与邮箱体系并存：邮箱作为兜底登录方式（建议长期保留）

### 9.6 回滚策略（必须准备）

- 后端：保持旧 `/auth/login` 与 `/auth/register` 在一段时间内可用
- 前端：若扫码登录出现故障，可临时恢复旧登录页（保留旧代码分支或 feature flag）
- DB：本期建议仅做“加字段”式变更，不做破坏性迁移，便于回滚

---

## 10. 里程碑建议（执行顺序）

1) 域名规划确认：`api.<primary-domain>` 作为 API 入口（不在仓库写死）
2) 阶段一邮箱体系 MVP：邮箱验证 + 邮箱验证码登录（JWT）+ 忘记/重置密码 + 0 配额规则 + 邀请码后补接口
3) 前端登录/注册页替换：AntD 化 + 注册必须邮箱验证 + 登录双入口（密码/邮箱验证码）
4) 文件解析 MVP：IR 提取 + AI mapping JSON + 校验 + 失败建议 + 预览接口
5) 确认映射交互：前端面板 + confirm 接口
6) 覆盖更多模板：
  - Excel：多 sheet / 多表头 / 合并单元格 / 明细长表等
  - Word：多表格/段落混合、标题层级不规整等
  - PPT：多页结构差异、标题缺失、表格+文本混排等

7) 最终版（延期）：微信扫码登录（备案条件满足后）

---

## 11. 仓库降敏规则（必须遵守）

- 文档/脚本/配置中：所有真实 ACR 名、默认域名、FQDN、资源名一律用占位符。
- 示例域名统一用：
  - `<frontend-host>` / `<backend-host>` / `<primary-domain>` / `<acr-name>` 等。
- 任何命令示例禁止粘贴真实域名/资源名。
