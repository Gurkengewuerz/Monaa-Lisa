FROM oven/bun:1 AS builder

WORKDIR /app

COPY package.json ./
RUN bun install

COPY . .

# Generate Prisma client at build time without requiring a real database.
RUN bun run prisma:generate
RUN bun run build

FROM oven/bun:1 AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["bun", "dist/src/main.js"]
