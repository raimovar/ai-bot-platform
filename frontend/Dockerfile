# ═══════════════════════════════════════════════════════════════
# Multi-stage build for React frontend
# ═══════════════════════════════════════════════════════════════

FROM node:20-alpine AS base
WORKDIR /app

# ─────────────────────────────────────────────────────────────
# Development stage
# ─────────────────────────────────────────────────────────────
FROM base AS development
COPY package*.json ./
RUN npm install
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host"]

# ─────────────────────────────────────────────────────────────
# Build stage
# ─────────────────────────────────────────────────────────────
FROM base AS build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Production stage
# ─────────────────────────────────────────────────────────────
FROM nginx:alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Expose
EXPOSE 80

# Run
CMD ["nginx", "-g", "daemon off;"]
