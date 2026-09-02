FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
FROM node:20-alpine AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
FROM node:20-alpine AS build
WORKDIR /app
# Declarado ANTES del COPY: vite lee las variables VITE_* de
# process.env en tiempo de build. Sin este ARG, el único valor
# disponible sería el de un .env commiteado — y no puede haber
# uno por cliente sin ensuciar el repo.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./
RUN npm run build
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/nginx/frontend.prod.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
