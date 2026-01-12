# 1. Сборка фронта
FROM node:21.7.1-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

# 2. Финальный nginx-образ
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html