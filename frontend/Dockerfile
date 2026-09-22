# syntax=docker/dockerfile:1
FROM node:24-alpine AS construccion
WORKDIR /app

# Las dependencias se copian solas primero para que su capa se reuse mientras
# no cambie package-lock.json: sin esto, cada cambio de una linea de React
# reinstala node_modules entero.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=construccion /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
