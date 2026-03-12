# --- STAGE 1: Dependencies ---
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# --- STAGE 2: Builder ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js collects completely anonymous telemetry about general usage.
# Learn more here: https://nextjs.org/telemetry
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --- STAGE 3: Runner ---
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy everything from the builder stage
COPY --from=builder --chown=nextjs:nodejs /app ./

USER nextjs

EXPOSE 3000

ENV PORT=3000

# Next.js uses 'npm start' for production, but we'll use 'dev' 
# if you still want hot-reloading on your Mac.
CMD ["npm", "run", "dev"]