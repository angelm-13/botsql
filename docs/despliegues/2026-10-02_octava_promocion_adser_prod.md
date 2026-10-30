# Octava promoción de adser-prod a `cfe7820`

**Estado: EJECUTADA el 2026-10-02, con el OK de Alan.**

- **De:** `c260f22` (séptima promoción).
- **A:** `cfe7820`, la misma versión que corría `tyakxa-dev` al promover (pods en 1/1, ~70 min sin reinicios).
  El overlay lleva `cfe7820` en db-init/backend/worker y `cfe7820-adser-prod` en el frontend.

## Qué entra (de Aurora Rodríguez)

- **Material prestado (10-01):** la tabla del dashboard filtra, busca, cuenta y pagina en el servidor sobre TODOS
  los renglones prestados (antes solo 50), y el encabezado de orden dice su sentido y ofrece las dos direcciones.
  Backend: `kpis/registry.py` y `routes/kpi.py`.
- **Familias de producto (10-02):** el buscador consulta al servidor, la búsqueda y la unicidad de
  `product_family` ignoran mayúsculas y acentos, y el selector de familia de Materiales carga todas.

## Migraciones

Una nueva: `20261001150000_indice_de_material_prestado.sql`, índice parcial con `CREATE INDEX IF NOT EXISTS`
(idempotente, apto para el replay en cada arranque). Sobre ~2768 renglones de Adser su costo es despreciable.
Sin cambios en `k8s/base`.

## Procedimiento

1. Tags del overlay `k8s/overlays/adser-prod/kustomization.yaml` a `cfe7820` (frontend `cfe7820-adser-prod`).
2. `scp` del `kustomization.yaml` al VPS (`/home/alanp/tyakxa_tny/k8s/overlays/adser-prod/`) y
   `kubectl apply -k` sobre el overlay.
3. `kubectl -n adser-prod rollout status` de backend, celery-worker, celery-beat y frontend; revisar los logs del
   initContainer `db-migrate` (debe terminar en `esquema al dia`).

## Reversa

Volver los 4 tags a `c260f22` / `c260f22-adser-prod` y repetir el `apply -k`. El índice nuevo es inofensivo para la
versión anterior.
