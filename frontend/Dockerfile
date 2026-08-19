# Multi-stage build for FitTrack SvelteKit PWA frontend

# Stage 1: Install dependencies and build
FROM node:22-slim AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci || npm install

# Copy source
COPY . .

# Build SvelteKit
RUN npm run build

# Stage 2: Serve with node
FROM node:22-slim AS runner

WORKDIR /app

# Copy built output and node_modules
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["node", "build"]