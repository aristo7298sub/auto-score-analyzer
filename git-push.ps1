# Git 提交脚本 (PowerShell)

Write-Host "📋 检查Git状态..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "📝 添加文件到暂存区..." -ForegroundColor Cyan
git add .

Write-Host ""
Write-Host "📊 查看将要提交的更改..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "💾 提交更改..." -ForegroundColor Cyan
git commit -m "feat: UI优化与功能完善

✨ 新增功能:
- 完整的管理后台系统(用户管理/数据统计/日志查看)
- 配额系统和推荐奖励机制
- 支持Excel/Word/PPT多格式文件上传
- 基于Azure OpenAI GPT-4的智能分析
- 批量并发分析(最多50并发)

🎨 UI/UX优化:
- 莫兰迪配色方案的登录/注册页面
- 主页面重构(合并搜索/优化进度显示)
- 移除冗余显示,提升用户体验
- 完善的响应式设计

🔧 技术改进:
- 数据库优化(添加file_size列,字段名修正)
- 前端超时优化(30s→180s)
- 完善错误处理和日志
- 本地/云端存储灵活配置

📝 文档更新:
- 完整的README文档
- 添加CHANGELOG
- 详细的项目结构说明
"

Write-Host ""
Write-Host "🚀 推送到GitHub..." -ForegroundColor Cyan
git push origin main

Write-Host ""
Write-Host "✅ 完成!" -ForegroundColor Green
