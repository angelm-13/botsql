# 2026-10-16 — Montaje de los fixtures de KPI en el contenedor del backend (infraestructura)

Para Alan: es un cambio de **infraestructura del entorno local**, no de la aplicación.
No hay migraciones, ni backfill, ni cambio en `k8s/`, y ninguna imagen de cliente lo
trae. Cubre `7aacb2b` (el montaje y la prueba que lo usa) y el commit que hace que esa
prueba se salte, con un mensaje, si el montaje no está.

## Qué cambió

`docker-compose.yml`, servicio `backend`, una línea nueva en `volumes`:

```yaml
- ./frontend/src/kpi/fixtures:/frontend/src/kpi/fixtures:ro
```

- Solo lectura, y solo esa carpeta: contiene dos JSON de prueba que ya están versionados en
  git (`catalogo_del_registry.json` y `material_prestado_actual.real.json`, una respuesta
  del backend usada por las pruebas de la tabla), no el frontend completo ni secretos.
  El contenedor no ve nada que el repo no tenga ya.
- Sigue el mismo patrón que `./database:/database:ro`, que ya usan las pruebas de
  migraciones.
- **Solo afecta a `docker compose` (desarrollo).** Ningún overlay de k8s monta nada
  parecido y la imagen de producción no incluye `frontend/`.

## Para qué sirve

Las pruebas del selector del Dashboard corren en node contra una **copia** de los KPIs de
`KPI_REGISTRY` (`frontend/src/kpi/fixtures/catalogo_del_registry.json`); node no puede
importar Python. Si el registry cambia y la copia no, esas pruebas siguen en verde contra
un catálogo que ya no existe. `backend/tests/test_services/test_kpi_catalogo_del_registry.py`
compara la copia con el registry y falla si no coinciden, pero el contenedor del backend
solo veía `./backend`: sin este montaje la prueba no tenía con qué comparar.

## Qué hay que hacer en cada máquina

Solo quien use `docker compose` en local, después de traer el commit:

```bash
docker compose ps                  # mirar primero qué está arriba y de quién es
docker compose up -d backend       # recrea SOLO el backend con el montaje nuevo
```

`up -d backend` reinicia el backend unos segundos; no toca `db`, `rabbitmq`, `celery-*`,
`frontend` ni `nginx`. En un stack compartido, avisar antes. No es obligatorio: sin el
montaje nada de la aplicación cambia, solo se pierde esa comprobación (ver abajo).

## Si el montaje no está

La prueba **se salta** (no falla) con un mensaje que lo dice:

```
SKIPPED ... SALTADA, no verificada: no hay /frontend/src/kpi/fixtures, asi que no se pudo
comparar el catalogo del frontend con KPI_REGISTRY. ...
```

Una prueba saltada no es una prueba en verde: no comprobó nada. Para ver los motivos de
lo que se salta, correr pytest con `-rs`. Si la carpeta está pero falta el archivo, la
prueba **falla** (alguien lo movió o lo borró).

## Cómo verificar

```bash
docker compose exec backend ls /frontend/src/kpi/fixtures
# catalogo_del_registry.json  material_prestado_actual.real.json
docker compose exec backend touch /frontend/src/kpi/fixtures/x
# touch: cannot touch '/frontend/src/kpi/fixtures/x': Read-only file system
docker compose exec -T backend pytest -q -rs tests/test_services/test_kpi_catalogo_del_registry.py
# 3 passed          (con el montaje)
# 1 passed, 2 skipped   (sin el montaje, con el motivo en la línea SKIPPED)
```

## Qué hacer si algo sale mal

- **El backend no arranca tras `up -d backend`:** no debería depender de esta carpeta. Quitar
  la línea del `docker-compose.yml` y repetir `docker compose up -d backend`; la prueba
  pasa a saltarse y nada más cambia.
- **La prueba falla por desfase real** (no por montaje): el mensaje lista qué KPI cambió y
  trae el comando para regenerar la copia con `backend/scripts/exportar_catalogo_kpis.py`.
  Después hay que correr las pruebas del front (`cd frontend && node --test
  --test-concurrency=1 src/kpi/`): un KPI nuevo puede cambiar los conteos que fijan.
