# Adser: asignar KPIs a Administrator (`nm_permission_kpi`)

- **Script:** `backend/scripts/seed_kpi_permissions.py`, con el perfil `adser`.
- **Qué hace:** da a **Administrator** (en Adser, `taroj`) los KPIs del perfil
  `adser`. La primera versión del script (`e73fcfc`) asignaba solo dos
  (`articulos_bajo_stock` e `incidentes_resueltos_por_empleado`); el perfil se
  cambió después a los de incidencias y material y hoy son **seis**:
  - `incidentes_resueltos_por_empleado`
  - `incidencias_abiertas_por_empleado` (ahora "Incidencias abiertas por responsable")
  - `incidencias_pendientes`
  - `incidencias_abiertas_vs_cerradas`
  - `material_por_estado`
  - `material_prestado_actual`

  Quedan fuera a propósito: `articulos_bajo_stock` (el almacén de Adser es de
  herramientas individuales, casi toda la existencia es 1) y
  `vales_vencidos_por_responsable` (`due_date` viene vacío y saldría siempre en
  cero). Almacenista no cambia. El script es **aditivo**: si `taroj` ya tenía
  asignado `articulos_bajo_stock`, se queda.
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

1. **`adser-prod` debe correr una imagen que traiga el script, la regla de
   agregación (`4c36348`) y el perfil de seis KPIs.** Hoy el overlay está en
   **`b21a793`** (Alan, 29-sep-2026), que ya trae las tres cosas y las
   migraciones `20260925130000` y `20260925140000` (venían desde `abf0929`, el
   punto anterior). Lo que `b21a793` **no** trae es lo posterior: la plantilla
   del tablero, el selector de KPI nuevo, la regla de unidades, "Tabla" solo para
   KPIs en vivo, los acentos del menú, la cabecera de tarjeta sin traslape y la
   etiqueta "responsable". Promover a un SHA posterior según §7.1 de
   `ARQUITECTURA_TYAKXA_TNY.md`.
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
  Administrator        material_prestado_actual                      INSERTAR
  Administrator        incidentes_resueltos_por_empleado             INSERTAR
  Administrator        incidencias_abiertas_por_empleado             INSERTAR
  Administrator        incidencias_pendientes                        INSERTAR
  Administrator        incidencias_abiertas_vs_cerradas              INSERTAR
  Administrator        material_por_estado                           INSERTAR
Se insertarian: 6 fila(s) en nm_permission_kpi.
```

Si ya se había corrido la primera versión del script, `incidentes_resueltos_por_empleado`
sale `ya existe, sin cambios` (y `Se insertarian: 5`); las filas que ya estaban,
incluida `articulos_bajo_stock`, no se tocan.

Si aparece `ROL INEXISTENTE` o un `AVISO`, parar y revisar antes de seguir.
Un `AVISO ... no tiene lectura de kpi_definition` significa que falta la
capa 1 en esa base.

### 2. Aplicar

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser
```

Esperado: las mismas líneas, con `Insertadas: 6 fila(s) en nm_permission_kpi.`
(o las que falten, según el párrafo anterior).

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

Esperado: `Administrator` con los seis KPIs del perfil (y, si ya los tenía,
`articulos_bajo_stock`), todos con `puede_ver = t`.

**En la aplicación:** `taroj` cierra sesión y vuelve a entrar. En el
Dashboard, el selector de KPIs muestra los seis del perfil, con datos si el
backfill ya corrió (la tabla "Material prestado ahora" no lo necesita).

## Orden completo para adser-prod

Todo en este orden. Salvo el paso 1, los comandos van en el VPS, en la
sesión SSH con acceso al clúster.

**Punto de partida: `b21a793`.** Es lo que Alan dejó en el overlay (commit
`deploy(adser-prod): promover a b21a793`); antes estaba en `abf0929`, y
`0bf9d69` (el que mencionaba la primera versión de este documento) ya no es el
punto de partida. `b21a793` es ancestro del destino, así que no hay que pasar
por ninguna versión intermedia.

**Destino: `8579bf4`**, mi último commit de código (`feat(dashboard): el selector
de KPI combina botones de módulo y lista`). No es un commit del bot ni uno de
documentación: esos no cambian el código. Se elige este SHA y no el más reciente de
la rama porque **las imágenes solo se construyen para el commit con el que termina
cada `push`** (el tag es `git rev-parse --short HEAD` del run, ver
`.github/workflows/build-images.yml`): `8579bf4` se subió como cabeza de su propio
push, así que sus imágenes existen; un commit intermedio de un push con varios
commits no tendría imagen. Antes de empezar confirma en GitHub → Actions que el run
de `8579bf4` terminó en verde, o el pod queda en `ImagePullBackOff`. Si más adelante
hay commits de código posteriores, usa el último *que se haya subido como cabeza de
un push* y sustituye el SHA en todo este documento.

**Qué cambia de `b21a793` a `8579bf4`: mi parte es solo código, pero llegan dos
migraciones de Alan.** En mi trabajo no hay migraciones ni cambios de esquema
(`git diff --name-status b21a793 8579bf4 -- database backend/app/models` no
muestra nada mío). El rango sí trae, de los commits `d775206` y `12b9ed3` de Alan:

- `20260929100000_material_no_se_repite.sql`: índice único para que un material no
  se capture dos veces. Es defensiva: si ya hay duplicados vivos no crea el índice y
  avisa (Alan midió 0 en los cuatro ambientes el 29-sep), así que no deja el backend
  en `CrashLoop`.
- `20260929110000_creation_date_por_defecto_en_vales.sql`: `DEFAULT now()` en
  `creation_date` de `incident` y `nm_incident_product`. Idempotente; no toca filas.
  El rellenado de lo ya migrado es un script aparte, con sus propios pasos en
  `2026-09-29_creation_date_de_vales.md`; **no forma parte de este documento**.

Por eso el respaldo previo **vuelve a recomendarse** (paso 0) y `db-migrate` sí tiene
algo que aplicar (paso 2). Lo que reescribía `nm_field_permission`
(`20260925130000`) y agregaba `peso` (`20260925140000`) llegó con `abf0929`. Lo que
**sigue aplicando**: el backfill, los permisos y la plantilla.

Lo que ya viene en `b21a793` y **no** hay que volver a hacer: la regla de
agregación y la columna `peso`, los 4 KPIs nuevos de incidencias y material, el
KPI en vivo `material_prestado_actual`, el tipo de widget `tabla`, el rango
relativo y el ErrorBoundary. Lo que llega con `8579bf4`: la plantilla del tablero,
el selector de KPI con botones de módulo y buscador, la regla de unidades, "Tabla" solo para
KPIs en vivo, la comparación contra "hace N días", los acentos del menú, la
cabecera de tarjeta sin traslape y la etiqueta "Responsable" (que llega sola a
`kpi_definition` en el siguiente arranque del backend).

> **Si el backfill (paso 3) y los permisos (pasos 4 y 5) ya se hicieron con
> `abf0929`/`b21a793`, verifica antes de repetir:** los tres son idempotentes,
> pero el perfil de permisos creció de dos KPIs a seis, así que el paso 4 casi
> seguro tendrá filas nuevas por insertar.

### 0. Respaldo (recomendado: hay dos migraciones de Alan)

Las migraciones nuevas son aditivas (un `DEFAULT` y un índice que solo se crea si
no hay duplicados), pero tocan esquema; un respaldo antes de aplicar cuesta poco:

```bash
kubectl -n adser-prod exec statefulset/postgres -- sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > ~/adser_antes_de_8579bf4_$(date +%Y%m%d_%H%M).sql
```

### 1. Promover la imagen (en el repo, no en el VPS)

En `k8s/overlays/adser-prod/kustomization.yaml`, cambiar los 4 `newTag`:
`"b21a793"` → `"8579bf4"` (tres veces) y `b21a793-adser-prod` →
`8579bf4-adser-prod`. Commitear y hacer push. Luego, desde la máquina con el
repo:

```bash
scp k8s/overlays/adser-prod/kustomization.yaml 168.231.67.33:/home/alanp/tyakxa_tny/k8s/overlays/adser-prod/kustomization.yaml
```

### 2. Aplicar y esperar el rollout

```bash
cd /home/alanp/tyakxa_tny
kubectl apply -k k8s/overlays/adser-prod
kubectl -n adser-prod rollout status deployment/backend
kubectl -n adser-prod rollout status deployment/celery-worker
kubectl -n adser-prod rollout status deployment/celery-beat
```

`db-migrate` aplica las dos migraciones de Alan (el resto ya estaba). Confirmar
que terminó y que el catálogo de KPIs está completo:

```bash
kubectl -n adser-prod logs deployment/backend -c db-migrate | grep -E "20260929100000|20260929110000|esquema al dia"
kubectl -n adser-prod exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
SELECT count(*) FROM kpi_definition WHERE deletion_date IS NULL;
SQL
```

Esperado: las dos líneas de las migraciones nuevas, `db-migrate: esquema al dia` y
`21`. Si `20260929100000` avisa de duplicados en `material`, el índice no se creó
(el backend arranca igual): resolverlo con `dedupe_adser_material.py` antes de
seguir. Después, el rellenado de `creation_date` según
`2026-09-29_creation_date_de_vales.md`.

### 3. Backfill de snapshots

Sigue haciendo falta. La tarea nocturna solo recalcula una ventana rodante de 7
días, así que sin backfill los 4 KPIs nuevos no tienen historia,
`incidentes_resueltos_por_empleado` sigue vacío para lo anterior (antes agrupaba
por una fecha que en lo migrado viene en NULL) y `cancelaciones_por_empleado`
conserva filas calculadas antes de corregir el sentinel de cierre.

```bash
kubectl -n adser-prod exec deployment/backend -- python -c "
from datetime import date, timedelta
from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango
hoy = date.today()
print(recalcular_kpi_snapshots_rango(hoy - timedelta(days=364), hoy))
"
```

Esperado: `{'ok': True, ... 'filas': N, ...}`. Detalle y verificaciones en
`2026-09-25_kpi_agregacion.md` y en `2026-09-29_kpis_dashboard_adser.md`.

### 4. Dry-run del script de permisos

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser --dry-run
```

Esperado: `Administrator` con los KPIs del perfil que aún no tenga en
`INSERTAR` (hasta seis) y el total en `Se insertarian: N`. Si aparece
`ROL INEXISTENTE` o `AVISO`, parar.

### 5. Aplicar el script de permisos

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser
```

Esperado: `Insertadas: N fila(s) en nm_permission_kpi.` y código de salida 0.

### 6. Plantilla del tablero de `taroj`

Detalle y opciones en `2026-09-29_kpis_dashboard_adser.md`. **La tabla
"Material prestado ahora" no se crea todavía:** depende de `incident_date` y falta
la confirmación de Alan (consulta de solo lectura). Mientras tanto:

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template --sin-tabla --dry-run
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template --sin-tabla
```

Esperado: `Creados: 1 tablero(s) y 4 widget(s).` Cuando Alan confirme
`incident_date`, una corrida normal (sin `--sin-tabla`) agrega solo la tabla.

### 7. Verificar con taroj

1. `taroj` **cierra sesión y vuelve a entrar**: el token anterior no ve el
   cambio.
2. En el Dashboard, el selector de KPI muestra una fila de botones de módulo
   (Operaciones, Inventario, Facturación, Laboratorio, Documentos y Variables, cada
   uno con su conteo) y, debajo, los KPIs del módulo elegido, con buscador.
3. El tablero "Operación Adser" aparece con sus 4 tarjetas y los rangos rotulados
   ("Hoy · …", "Este año · …"). El último vale migrado es del 15 de agosto: un rango
   de **30 días** (desde el 31 de agosto) sale vacío con toda razón, pero uno de
   **90 días** sí alcanza esa fecha, así que si sale vacío es que **falta el
   backfill** (los KPIs de serie no tienen historia más allá de la ventana de 7
   días de la tarea nocturna), no que falten datos. "Este año" trae todo el
   historial migrado una vez hecho el backfill.
4. "Incidentes resueltos por empleado" muestra un porcentaje entre 0 y 100, y los
   menús y encabezados de tarjeta se ven con acentos y sin traslape.

Si algo falla: volver a la imagen `b21a793` en el overlay (pasos 1 y 2 al
revés). Las dos migraciones de Alan son aditivas y pueden quedarse (el código de
`b21a793` no las usa ni se rompe con ellas); no hay migraciones mías que deshacer. Las filas nuevas de
`nm_permission_kpi`, los snapshots y el tablero sembrado pueden quedarse (el
código de `b21a793` no los rompe).

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
