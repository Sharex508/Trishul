# Build static assets and serve with Vite preview (production-like)
ARG BASE_IMAGE=node:20-alpine
FROM ${BASE_IMAGE}
WORKDIR /app
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci || npm install
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port 5173"]
