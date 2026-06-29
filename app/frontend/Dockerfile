# ----- Stage 1: build the Angular bundle -----
FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json ./
RUN npm install --no-audit --no-fund

COPY angular.json tsconfig.json tsconfig.app.json ./
COPY src ./src

RUN npm run build:prod

# ----- Stage 2: serve with nginx -----
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist/qa-frontend/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
