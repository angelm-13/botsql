# Adser: asignar KPIs a Administrator (`nm_permission_kpi`)

- **Script:** `backend/scripts/seed_kpi_permissions.py`, con el perfil `adser`.
- **Qué hace:** da a **Administrator** (en Adser, `taroj`) dos KPIs:
  - `articulos_bajo_stock`
  - `incidentes_resueltos_por_empleado`

  `vales_vencidos_por_responsable` queda fuera a propósito: en Adser
  `due_date` viene vacío y el KPI saldría siempre en cero. Almacenista no
  cambia.
- **No toca `ROLES` ni `entity_permission`:** Administrator ya tiene el
  módulo `kpis` (la capa 1). El script solo agrega la capa 2, `puede_ver`
  por KPI.
- **Sobrevive a reinicios:** ninguna migración toca `nm_permission_kpi`. Se
  verificó en local que las filas siguen después de `db-migrate` y de
  reiniciar el backend.

## Por qué hace falta

`taroj` **no es superusuario**: solo lo es el usuario de
`BOOTSTRAP_ADMIN_USERNAME` (`backend/app/routes/auth.py:99-105`). Sin filas
en `nm_permission_kpi`, el Dashboard le dice "No tienes KPIs asignados",
aunque su rol tenga el módulo.

## Requisitos previos

1. **`adser-prod` debe correr una imagen que traiga el script y la regla de
   agregación** (`4c36348` o posterior). Hoy el overlay está en `0bf9d69`,
   que no tiene ninguno de los dos. Hay que promoverlo según §7.1 de
   `ARQUITECTURA_TYAKXA_TNY.md` a una imagen construida después de subir este
   cambio.
2. **Backfill de snapshots** después de promover, según
   `2026-09-25_kpi_agregacion.md` (paso 3). Sin él,
   `incidentes_resueltos_por_empleado` sale vacío para todo lo anterior al
   despliegue.

Comprobación rápida de que la imagen trae el script:

```bash
kubectl -n adser-prod exec deployment/backend -- ls scripts/seed_kpi_permissions.py
```

## Pasos

### 1. Dry-run (no escribe nada)

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser --dry-run
```

Salida esperada en una base sin asignaciones previas:

```
Perfil 'adser' (dry-run: no se escribe nada):
  Administrator        articulos_bajo_stock                          INSERTAR
  Administrator        incidentes_resueltos_por_empleado             INSERTAR
Se insertarian: 2 fila(s) en nm_permission_kpi.
```

Si aparece `ROL INEXISTENTE` o un `AVISO`, parar y revisar antes de seguir.
Un `AVISO ... no tiene lectura de kpi_definition` significa que falta la
capa 1 en esa base.

### 2. Aplicar

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser
```

Esperado: las mismas líneas, con `Insertadas: 2 fila(s) en nm_permission_kpi.`

Es idempotente. Una segunda corrida dice `ya existe, sin cambios` e
`Insertadas: 0`. Nunca quita nada.

**Cuidado al volver a correrlo:** desmarcar un KPI en `/kpi_permissions`
**borra** la fila (no la da de baja). Si después se corre el script otra
vez, ese KPI se vuelve a asignar. Para quitar un KPI de forma permanente,
hay que sacarlo también de `ASIGNACIONES` en el script.

**Códigos de salida:**

- `0`: bien.
- `1`: error de validación, no se escribió nada. Por ejemplo, un KPI con
  `alcance_proyecto=False` asignado a un rol acotado a proyecto.
- `2`: algún rol no existe; se reporta y no se crea.

### 3. Verificar

**En la base:**

```bash
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT p.permission_description AS rol, d.clave, n.puede_ver
FROM nm_permission_kpi n
JOIN permission p USING (id_permission)
JOIN kpi_definition d USING (id_kpi_definition)
WHERE n.deletion_date IS NULL
ORDER BY 1, 2;
SQL
```

Esperado: `Administrator` con los dos KPIs y `puede_ver = t`.

**En la aplicación:** `taroj` cierra sesión y vuelve a entrar. En el
Dashboard, el selector de KPIs muestra exactamente "Artículos bajo stock" e
"Incidentes resueltos por empleado", con datos si el backfill ya corrió.

## Orden completo para adser-prod

Todo en este orden. Salvo el paso 1, los comandos van en el VPS, en la
sesión SSH con acceso al clúster.

**Imagen a promover:** `e73fcfc`, el primer commit que trae el script de
permisos y la regla de agregación (`4c36348`). Antes de empezar, confirmar
en GitHub → Actions que el run de `e73fcfc` terminó en verde. Si no, las
imágenes no existen y el pod queda en `ImagePullBackOff`.

### 0. Respaldo antes de tocar nada

La promoción trae `20260925130000_bits_de_escritura_en_permisos_de_campo.sql`,
que reescribe `nm_field_permission` en cada arranque. Conviene poder comparar
el antes y el después.

```bash
kubectl -n adser-prod exec statefulset/postgres -- sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > ~/adser_antes_de_e73fcfc_$(date +%Y%m%d_%H%M).sql
ls -la ~/adser_antes_de_e73fcfc_*.sql
```

### 1. Promover la imagen (en el repo, no en el VPS)

En `k8s/overlays/adser-prod/kustomization.yaml`, cambiar los 4 `newTag`:
`"0bf9d69"` → `"e73fcfc"` (tres veces) y `0bf9d69-adser-prod` →
`e73fcfc-adser-prod`. Commitear y hacer push. Luego, desde la máquina con el
repo:

```bash
scp k8s/overlays/adser-prod/kustomization.yaml 168.231.67.33:/home/alanp/tyakxa_tny/k8s/overlays/adser-prod/kustomization.yaml
```

### 2. Aplicar y esperar el rollout (db-migrate corre aquí)

```bash
cd /home/alanp/tyakxa_tny
kubectl apply -k k8s/overlays/adser-prod
kubectl -n adser-prod rollout status deployment/backend
kubectl -n adser-prod rollout status deployment/celery-worker
kubectl -n adser-prod rollout status deployment/celery-beat
```

El initContainer `db-migrate` aplica las migraciones antes de que arranque el
backend nuevo. Confirmar que terminó y que aplicó las dos nuevas:

```bash
kubectl -n adser-prod logs deployment/backend -c db-migrate | grep -E "20260925130000|20260925140000|esquema al dia"
```

Esperado: las dos líneas `db-migrate: aplicando ...` y al final
`db-migrate: esquema al dia`.

### 3. Backfill de snapshots

```bash
kubectl -n adser-prod exec deployment/backend -- python -c "
from datetime import date, timedelta
from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango
hoy = date.today()
print(recalcular_kpi_snapshots_rango(hoy - timedelta(days=364), hoy))
"
```

Esperado: `{'ok': True, ... 'filas': N, ...}`. Detalle y verificaciones en
`2026-09-25_kpi_agregacion.md`.

### 4. Dry-run del script

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser --dry-run
```

Esperado: `Administrator` con los dos KPIs en `INSERTAR` y
`Se insertarian: 2`. Si aparece `ROL INEXISTENTE` o `AVISO`, parar.

### 5. Aplicar el script

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser
```

Esperado: `Insertadas: 2 fila(s) en nm_permission_kpi.` y código de salida 0.

### 6. Verificar con taroj

1. `taroj` **cierra sesión y vuelve a entrar**: el token anterior no ve el
   cambio.
2. En el Dashboard, el selector de KPIs muestra exactamente "Artículos bajo
   stock" e "Incidentes resueltos por empleado".
3. Crear un widget de cada uno con un rango de 30 días:
   - "Artículos bajo stock" muestra la existencia actual por producto, no un
     múltiplo de los días.
   - "Incidentes resueltos por empleado" muestra un porcentaje entre 0 y 100.

Si algo falla: volver a la imagen `0bf9d69` en el overlay (paso 1 y 2 al
revés). La columna `peso` y las filas de `nm_permission_kpi` pueden quedarse;
el código viejo no las usa. Lo que **no** se deshace solo son los bits que
`20260925130000` cambió en `nm_field_permission`: para eso está el respaldo
del paso 0.

## Resultado de la prueba local (2026-09-25)

Usuario de prueba con rol Administrator, sin ser superusuario, como `taroj`:

| | KPIs en `GET /kpi_definition/` | Valores |
|---|---|---|
| Antes del script | 0 | — |
| Después del script | 2 | `incidentes_resueltos_por_empleado` 50.0 % (4 incidentes: resuelta, cerrada, cancelada, abierta); `articulos_bajo_stock` 1 pieza |
| Después de `db-migrate` y reinicio del backend | 2 | Los mismos |

## Deshacer

Desde `/kpi_permissions`, como administrador: seleccionar el rol y desmarcar
los KPIs. Eso borra las filas, así que **no se debe volver a correr el
script** con esos KPIs en `ASIGNACIONES`, porque los reasignaría.
