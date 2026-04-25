# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Frontend proxies /v1/* through nginx → backend at runtime.
# No VITE_API_BASE_URL needed at build time; the proxy rewrites the path.
RUN npm run build

# ── Production stage ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx template and entrypoint
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Remove default nginx site config so our template takes over
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
