# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 构建参数
ARG VITE_API_URL=http://localhost:8000

# 复制package文件
COPY package*.json ./

# 安装所有依赖（包括devDependencies，用于构建）
RUN npm ci

# 复制源代码
COPY . .

# 设置环境变量并构建生产版本
ENV VITE_API_URL=$VITE_API_URL
RUN node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置（处理SPA路由）
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
