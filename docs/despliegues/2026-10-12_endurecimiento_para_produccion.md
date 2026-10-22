# Endurecimiento para produccion (2026-10-12)

Que cambia en el comportamiento y que hay que revisar ANTES de promover un overlay.

## Que cambia

- `is_production()` **falla cerrado**: es produccion salvo que `APP_ENV`/`FLASK_ENV` digan
  `development`, `dev`, `local`, `test`, `testing` o `staging`. Antes solo lo era si decian
  exactamente `production`, y un despliegue sin la variable arrancaba con secretos de ejemplo.
- `k8s/base/backend.yaml` fija `APP_ENV=production` en `backend`, `celery-worker` y
  `celery-beat`. El overlay `tyakxa-dev` lo baja a `staging`; `docker-compose.yml` usa
  `development`.
- `entrypoint.sh` arranca **gunicorn** salvo que `FLASK_ENV` o `APP_ENV` sean `development`
  (antes, sin variable, arrancaba `flask run --debug`, con depurador que ejecuta codigo).
- Con `APP_ENV=production` el backend **no arranca** si falta o es debil alguno de:
  `JWT_SECRET`, `SECRET_KEY` (>= 32 caracteres y no de ejemplo), `CORS_ORIGINS`, o la
  contrasena del admin inicial (`BOOTSTRAP_ADMIN_PASSWORD`, >= 12; o
  `BOOTSTRAP_ADMIN_ENABLED=false`). Tambien se rechaza el proveedor de timbrado `fake`.
- El token del paso 1 del login con MFA ya no es una sesion. Las sesiones se revalidan contra
  la base cada 30 s (`SESSION_REVALIDATE_SECONDS`): un usuario dado de baja o con otro rol
  pierde el token sin esperar a que expire. Responde `errors.session_revoked` (401).
- Cabeceras de seguridad en Flask y en `frontend.prod.conf`; `GET /documents/manifest` exige
  sesion; HSTS solo en produccion y bajo HTTPS.
- `TRUSTED_PROXY_HOPS=N` (opcional): la IP del cliente se toma de la entrada N desde la
  derecha de `X-Forwarded-For`. Sin la variable queda como antes (primera entrada).
- Dependencias: gunicorn 23.0.0, Flask-Cors 4.0.2, requests 2.32.4.
- Contenedores: `allowPrivilegeEscalation: false` y `seccompProfile: RuntimeDefault`.

## Antes de promover (en el VPS, por cada namespace; NO imprime valores)

```bash
NS=adser-prod   # o torredigital-prod, vidrioyaluminios-prod
for k in JWT_SECRET SECRET_KEY CORS_ORIGINS STAMPING_PROVIDER BOOTSTRAP_ADMIN_PASSWORD BOOTSTRAP_ADMIN_ENABLED; do
  v=$(kubectl -n $NS get secret app-secrets -o jsonpath="{.data.$k}" 2>/dev/null | base64 -d 2>/dev/null)
  printf "%-28s %s\n" "$k" "$( [ -z "$v" ] && echo FALTA || echo "ok (${#v} caracteres)" )"
done
```

Lo que debe verse: `JWT_SECRET` y `SECRET_KEY` con 32+ caracteres, `CORS_ORIGINS` con el dominio real,
`STAMPING_PROVIDER` distinto de `fake` (en produccion fiscal real), y
`BOOTSTRAP_ADMIN_PASSWORD` con 12+ caracteres o `BOOTSTRAP_ADMIN_ENABLED=false`.
Si algo FALTA, el pod nuevo se queda en `CrashLoopBackOff` con el motivo en `kubectl logs`: el
rollout de la version vieja sigue sirviendo, pero hay que corregir el Secret antes de seguir.

Tambien: rotar la contrasena de `admin1` en cualquier ambiente real, y no correr
`scripts/init_test_data.py` ni `seed_usuario_compras.py` (ya se niegan en produccion).

## Que NO se cambio (y por que)

- **Contenedores como root**: el backend de adser-prod escribe en un `hostPath` cuyo dueno es
  root; pasar a no-root exige antes cambiar ese dueno, por cliente.
- **Candado de migraciones** (dos pods arrancando a la vez): con `replicas: 1` y `Recreate`
  no ocurre; un candado `pg_advisory_lock` real exige reescribir el bucle de `psql` y no se
  pudo probar en un cluster.
- **CSP**: puede romper el frontend (estilos y fuentes en linea); requiere pruebas con el
  bundle de produccion.
- **Tokens de 8 h**: siguen siendo 8 h, pero ya se revocan por baja o cambio de rol.
