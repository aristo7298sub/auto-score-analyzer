# Auto Score Analyzer

基于Azure OpenAI的智能成绩分析系统，支持Excel文件上传、自动分析、可视化和报告导出。

## 🚀 快速开始

### 前置要求

- Node.js 18+
- Python 3.13+
- Docker & Docker Compose（生产环境）
- Azure OpenAI API密钥

### 本地开发

#### 1. 克隆仓库

```bash
git clone https://github.com/your-username/auto-score-analyzer.git
cd auto-score-analyzer
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入Azure OpenAI配置
```

#### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端运行在 http://localhost:8000

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 http://localhost:5173

### Docker部署

#### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入生产环境配置
```

#### 2. 启动服务

```bash
docker-compose up -d
```

服务运行在 http://localhost

#### 3. 查看日志

```bash
docker-compose logs -f
```

#### 4. 停止服务

```bash
docker-compose down
```

## 📦 项目结构

```
auto-score-analyzer/
├── backend/                 # Python FastAPI后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务服务
│   ├── data/               # 数据存储
│   ├── uploads/            # 上传文件
│   ├── exports/            # 导出文件
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React + TypeScript前端
│   ├── src/
│   │   ├── components/    # React组件
│   │   ├── pages/         # 页面
│   │   ├── services/      # API服务
│   │   └── types/         # 类型定义
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # Docker编排
├── nginx.conf             # Nginx配置
└── README.md
```

## 🔧 技术栈

### 后端
- FastAPI - 高性能Web框架
- Azure OpenAI - AI分析能力
- pandas - 数据处理
- openpyxl - Excel文件处理
- matplotlib - 数据可视化

### 前端
- React 18 - UI框架
- TypeScript - 类型安全
- Vite - 构建工具
- Ant Design - UI组件库

### 部署
- Docker - 容器化
- Nginx - 反向代理
- GitHub Actions - CI/CD

## 🌐 Azure Blob Storage（可选）

支持使用Azure Blob Storage存储上传和导出文件：

1. 在 `.env` 中设置 `STORAGE_TYPE=blob`
2. 配置 `AZURE_STORAGE_CONNECTION_STRING` 等参数
3. 重启服务

## 使用说明

1. 访问前端界面
2. 上传Excel/Word/PPT文件
   - **Excel格式要求**：第一行为知识点名称，第一列（从第二行开始）为学生姓名，单元格中有值（任意非空值）表示该学生在该知识点有扣分（仅作标记，不代表真实扣分值），空值表示不扣分，最后一列为总分。
3. 系统会自动分析学生成绩并提供改进建议
4. 可以搜索特定学生的成绩信息
5. 支持导出分析报告

## 📝 API文档

启动后访问 http://localhost:8000/docs 查看Swagger API文档

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可

MIT License 