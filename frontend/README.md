# 前端（React + TypeScript + Vite）

本目录为 Auto Score Analyzer 的前端工程。

## 开发

```powershell
cd frontend
npm install
npm run dev
```

默认地址以终端输出为准（仓库配置通常为 http://localhost:3000）。

## 连接后端

前端通过 `VITE_API_URL` 指定后端地址：

- Local/Hybrid：`http://localhost:8000`
- Cloud-All（ACA）：填写你的后端公开 URL

示例（不要提交包含真实值的 `.env`）：

```env
VITE_API_URL=http://localhost:8000
```

更完整的三环境说明见仓库根目录的 [ENVIRONMENTS.md](../ENVIRONMENTS.md)。
