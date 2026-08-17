# TYAKXA Infra Docker Nginx

Genera infraestructura ejecutable para un proyecto TYAKXA multi-módulo.

## Uso

```bash
cp .env.example .env
infra/ops/deploy.sh start
infra/ops/deploy.sh status
```

## Archivos generados

- docker-compose.yml
- docker-compose.prod.yml
- .env.example
- infra/docker/*.Dockerfile
- infra/nginx/*.conf
- infra/ops/*.sh

## Supuestos

- Backend expone /health en el puerto definido por `BACKEND_PORT` (default: 5001).
- Frontend Vite corre en puerto interno 3000.

## Configuración multi-instancia

Cada cliente o instancia define su propio archivo `.env` con el puerto deseado:

```env
BACKEND_PORT=5002
VITE_API_BASE_URL=http://localhost:5002
```

No se requiere modificar código fuente. El sistema usa `${BACKEND_PORT:-5001}` como valor por defecto en todos los archivos generados.
- PostgreSQL carga database/init.sql y database/seed.sql al crear volumen nuevo.
- Celery usa celery_worker.celery.
- MFA usa MFA_ISSUER y MFA_TOKEN_TTL_SECONDS.
