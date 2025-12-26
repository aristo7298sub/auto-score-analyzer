# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 构建参数 - 可以在构建时通过 --build-arg 传入
ARG VITE_API_URL

# 确保 Vite 构建进程能读取到该值（Vite 会从环境变量读取 VITE_*）。
ENV VITE_API_URL=$VITE_API_URL

# 复制package文件
COPY package*.json ./

# 安装所有依赖（包括devDependencies，用于构建）
RUN npm ci

# 复制源代码（包括 .env.production）
COPY . .

# 如果通过 ARG 传入了 VITE_API_URL，则覆盖 .env.production
# 否则使用 .env.production 中的默认值
RUN if [ -n "$VITE_API_URL" ]; then \
      echo "VITE_API_URL=$VITE_API_URL" > .env.production; \
    fi

# 生产构建必须显式注入真实后端地址，避免把占位符打进 bundle 导致 ERR_INVALID_URL / 不发请求。
RUN if [ -z "$VITE_API_URL" ] || echo "$VITE_API_URL" | grep -q "<backend-fqdn>"; then \
            echo "ERROR: VITE_API_URL is not set or is placeholder. Pass --build-arg VITE_API_URL=https://<your-backend-fqdn>"; \
            exit 1; \
        fi

# 再做一次文件层面的兜底检查（防止覆盖逻辑未生效）
RUN if grep -q "<backend-fqdn>" .env.production; then \
            echo "ERROR: .env.production still contains placeholder <backend-fqdn>."; \
            exit 1; \
        fi

# 构建生产版本（会自动使用 .env.production）
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
