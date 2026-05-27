FROM node:22-bookworm-slim AS deps

WORKDIR /app/apps/frontend
COPY apps/frontend/package.json ./
RUN npm install

FROM node:22-bookworm-slim AS builder

WORKDIR /app/apps/frontend
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8030
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
COPY --from=deps /app/apps/frontend/node_modules ./node_modules
COPY apps/frontend ./
RUN npm run build

FROM node:22-bookworm-slim AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3030
ENV NEXT_PUBLIC_API_URL=http://127.0.0.1:8030

COPY --from=builder /app/apps/frontend/.next/standalone ./
COPY --from=builder /app/apps/frontend/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
