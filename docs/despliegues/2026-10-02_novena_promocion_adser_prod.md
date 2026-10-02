# Novena promoción de adser-prod a `21ccb05`

**Estado: PREPARADA, sin ejecutar (espera el OK de Alan).**

- **De:** `cfe7820` (octava promoción, hecha el 2026-10-02).
- **A:** `21ccb05`, la misma versión que corre `tyakxa-dev` (pods 1/1, 0 reinicios; `db-migrate` terminó en
  `esquema al dia`). El overlay lleva `21ccb05` en db-init/backend/worker y `21ccb05-adser-prod` en el frontend.

## Qué entra

Solo `8c3a7a2`: **el Gestor de roles ya no se revierte al promover**
(`2026-10-02_el_gestor_manda_sobre_las_migraciones.md`). Una migración nueva,
`20260816000000_el_gestor_manda_sobre_las_migraciones.sql` (la primera en ejecutarse), más columna
`ajustado_por_gestor` y dos triggers. Sin cambios en `k8s/base`.

**Efecto en adser-prod:** la primera pasada congela lo que haya hoy en `entity_permission` y
`nm_field_permission`; a partir de ahí ninguna migración lo pisa. No cambia ningún permiso en esa pasada.

## Antes de ejecutar

1. **Revisar en el Gestor** los roles Administrator, Almacenista y Supervisor (la pasada de las 19:44 del
   2026-10-02 reescribió sus filas de Configuración, Inventario, Operaciones, Familias y Logística). Lo que
   esté al promover es lo que queda.
2. Respaldo de ambas tablas (para poder reconstruir si algo no queda como se esperaba):
   ```bash
   kubectl -n adser-prod exec postgres-0 -- sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t entity_permission -t nm_field_permission' > ~/respaldo_permisos_adser_$(date +%F).sql
   ```

## Procedimiento

1. Overlay `k8s/overlays/adser-prod/kustomization.yaml` a `21ccb05` (frontend `21ccb05-adser-prod`) y commit.
2. `scp` del `kustomization.yaml` al VPS (`/home/alanp/tyakxa_tny/k8s/overlays/adser-prod/`) y
   `kubectl apply -k` sobre el overlay.
3. `kubectl -n adser-prod rollout status` de backend, celery-worker, celery-beat y frontend; el initContainer
   `db-migrate` debe aplicar `20260816000000_...` y terminar en `esquema al dia`.

## Verificación posterior (solo lectura)

```sql
SELECT count(*) FILTER (WHERE ajustado_por_gestor IS NOT NULL), count(*) FROM entity_permission;  -- iguales
SELECT tgname FROM pg_trigger WHERE tgname IN ('trg_gestor_manda','trg_no_resucitar');            -- 3 filas
```
Y en el Gestor, los roles revisados deben verse igual que antes de promover.

## Reversa

Volver los 4 tags a `cfe7820` / `cfe7820-adser-prod` y repetir el `apply -k`. La columna y los triggers quedan
en la base (la imagen vieja no los quita).

**Ojo:** con la imagen vieja el ORM no conoce `ajustado_por_gestor`, así que un cambio hecho desde el Gestor
sobre una fila ya marcada **se descarta en silencio** (el trigger lo toma por una migración). Las migraciones
viejas, en cambio, tampoco pueden pisar esas filas. Si hay que quedarse en la versión anterior más que unas
horas, desactivar los triggers: `ALTER TABLE entity_permission DISABLE TRIGGER trg_gestor_manda;` (y lo mismo en
`nm_field_permission`, más `trg_no_resucitar`), sabiendo que vuelve el comportamiento de antes.
