# Build with:   docker build -t IMAGE_NAME .
# Run with:     docker run -p 3000:3000 --rm --name IMAGE_NAME IMAGE_NAME

FROM node:20-alpine AS builder
WORKDIR /
COPY . /
RUN npm install --frozen-lockfile && \
  npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /package.json /package-lock.json  /app/
COPY --from=builder /node_modules /app/node_modules
COPY --from=builder /build /app/build

EXPOSE 5173
CMD ["node", "-r", "dotenv/config", "/app/build/index.js"]