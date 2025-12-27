# 后端 API（以 OpenAPI 为准）

本文件为早期阶段的手写说明，内容已明显滞后（路由、字段、环境变量均可能不准确）。

请以运行中的后端 OpenAPI 为准：
- `/docs`（Swagger UI）
- `/openapi.json`

补充说明：
- 认证体系以“用户名 + 密码”为主；邮箱仅用于注册验证 / 找回密码 / 绑定邮箱。
- Azure OpenAI 现推荐使用 `AZURE_OPENAI_RESPONSES_URL` + `PARSING_MODEL` + `ANALYSIS_MODEL`。
