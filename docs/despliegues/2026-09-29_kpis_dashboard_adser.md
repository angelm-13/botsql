# Dashboard y KPIs de Adser: KPIs nuevos, backfill y widgets de tabla

- **Qué cubre:** la línea de commits del Dashboard de KPIs de Adser (registry
  con metadatos, 4 KPIs snapshot nuevos, `material_prestado_actual` en modo
  "vivo", Dashboard real con los componentes de `kpi-widgets/`, editor
  nuevo, rango relativo). Al promover, anota aquí el sha de la imagen.
- **Migraciones:** ninguna. Ni de esquema ni de datos.
- **Además de §7.1 hace falta:** un backfill de snapshots justo después del
  rollout. Sin él, los KPIs nuevos salen **vacíos** para todo lo anterior al
  despliegue.

## Qué cambia y por qué hace falta el backfill

**KPIs snapshot nuevos** (calculan una fila por entidad y día; la tarea
nocturna solo recalcula una ventana rodante de 7 días):

- `incidencias_abiertas_por_empleado`
- `incidencias_pendientes`
- `incidencias_abiertas_vs_cerradas`
- `material_por_estado`

**KPIs que ya existían y cambiaron su cálculo** (sus filas viejas quedaron
con la lógica anterior):

- `incidentes_resueltos_por_empleado`: ahora agrupa por `incident_date` y no
  por `creation_date`. En lo migrado de Adser `creation_date` es NULL (ver
  `docs/2026-09-28_creation_date_sin_default_en_incident.md`), así que antes
  esos incidentes no aparecían en ningún rango.
- `cancelaciones_por_empleado`: respeta el sentinel de cierre heredado
  (`1990-01-01`).

**No necesita backfill:** `material_prestado_actual`. Es un KPI "vivo": no
guarda snapshots, consulta el detalle al abrir el widget.

**Las filas de `kpi_definition` no vienen de una migración.** `init_db.py`
llama a `seed_kpi_definitions()` en cada arranque del backend y crea una fila
por KPI del registry. Con este despliegue el catálogo debe quedar en **21**
filas.

## Pasos

`tyakxa-dev` se despliega solo al hacer push a `initAlan`; los clientes se
promueven a mano. Sustituye `<ns>` por el namespace (`tyakxa-dev`,
`torredigital-prod`, `adser-prod`, `vidrioyaluminios-prod`).

### 1. Desplegar la imagen

El procedimiento normal de §7.1.

```bash
kubectl -n <ns> rollout status deployment/backend
kubectl -n <ns> rollout status deployment/celery-worker
```

`celery-worker` y `celery-beat` deben quedar en el mismo tag que el backend:
la tarea nocturna lee el registry del código que corre. Un worker o beat
con la imagen vieja no conoce los KPIs nuevos y no los recalcularía cada
noche, aunque el backfill de arriba sí los haya llenado una vez.

### 2. Verificar el catálogo de KPIs

```bash
kubectl -n <ns> exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
SELECT count(*) FROM kpi_definition WHERE deletion_date IS NULL;
SQL
```

Esperado: `21`. Si sale menos, el backend no llegó a correr `init_db.py`:
revisar los logs de arranque, busca `kpi_definition seeded from KPI_REGISTRY`.

### 3. Backfill

Rango: **365 días hasta hoy**, el máximo que la ruta deja consultar de una
vez (`KPI_RANGO_DIAS_MAX_POR_OMISION`). Si el plan del cliente declara otro
`kpi_rango_dias_max`, usa ese número.

```bash
kubectl -n <ns> exec deployment/backend -- python -c "
from datetime import date, timedelta
from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango
hoy = date.today()
print(recalcular_kpi_snapshots_rango(hoy - timedelta(days=364), hoy))
"
```

Esperado: `{'ok': True, 'message_key': 'jobs.kpis.snapshots_recalculated', 'filas': N, ...}`
con `N > 0` si hay incidentes o vales en el rango.

Es idempotente (upsert) y va en una sola transacción: si se corta no queda
nada a medias, y se puede volver a correr. Además recalcula todos los demás
KPIs snapshot, lo cual es inocuo (es lo que hace la tarea cada noche). Con
los volúmenes actuales se esperan segundos; no se midió contra datos reales.

### 4. Verificar

**a) Los KPIs tienen filas:**

```bash
kubectl -n <ns> exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT d.clave, count(s.*) AS filas, min(s.periodo) AS primer_dia, max(s.periodo) AS ultimo_dia
FROM kpi_definition d
LEFT JOIN kpi_snapshot s USING (id_kpi_definition)
WHERE d.clave IN ('incidencias_abiertas_por_empleado', 'incidencias_pendientes',
                  'incidencias_abiertas_vs_cerradas', 'material_por_estado',
                  'incidentes_resueltos_por_empleado', 'cancelaciones_por_empleado')
GROUP BY d.clave ORDER BY d.clave;
SQL
```

Esperado: `filas > 0` y `ultimo_dia` = hoy en cada KPI que tenga datos de
origen. Un KPI en `0` con incidentes reales en la base es una falla, no un
"sin datos".

**b) En el tablero** (con un usuario que vea los KPIs; el superusuario de
arranque los ve todos):

1. Un widget de "Incidencias abiertas vs. cerradas" o de "Material por
   estado" con el chip **90 días**: debe traer barras o dona con colores por
   categoría, no "Sin datos".
2. Un widget de **Tabla** con "Material prestado ahora": una fila por
   artículo sin devolver, con responsable, fecha del vale y días. En
   `tyakxa-dev` y `adser-prod` (que tienen lo migrado de Adser) la fecha
   viene de `incident_date`; revisa que no haya fechas de 1990.
3. Un widget "Incidentes resueltos por empleado" a 90 días: con datos
   migrados de Adser debe mostrar incidentes, cosa que antes no pasaba.
4. Los widgets que ya estaban guardados se ven con sus mismas fechas.

## Nota: `tipo_grafica='tabla'` (cambio de backend)

`KpiDashboardWidgetService.TIPOS_GRAFICA` ahora acepta `tabla`, además de
`numero`, `barras`, `linea`, `area` y `dona`. Antes un widget de tabla no se
podía guardar desde ningún lado: la API respondía 400 aunque el frontend ya
sabía pintarlo.

- Sin migración: `kpi_dashboard_widget.tipo_grafica` es `VARCHAR(30)` sin
  `CHECK`.
- El servicio **no** exige que el KPI del widget sea "vivo"; eso lo decide el
  editor (solo ofrece "Tabla" cuando el KPI la declara en
  `graficas_permitidas`). Un cliente que hable directo con la API podría
  guardar una tabla de un KPI que no es "vivo": el Dashboard la pinta como
  "Este tipo de tabla estará disponible próximamente", no revienta.
- Un widget de tabla guarda `parametros = {}`: son datos de "ahora", sin
  periodo ni filtros.

## Solo si el ambiente es `adser-prod`

El perfil `adser` de `backend/scripts/seed_kpi_permissions.py` cambió: ahora
asigna KPIs de incidencias y material. Hay que correrlo de nuevo, con
dry-run primero, según `2026-09-25_kpis_adser_permisos.md`:

```bash
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_permissions --perfil adser --dry-run
```

Revisa la lista que imprime antes de aplicar sin `--dry-run`. En `tyakxa-dev`
no hace falta: el usuario de arranque ve todos los KPIs.

## Si algo sale mal

- **El backfill truena:** la transacción se revierte completa. Revisar el
  error y volver a correrlo.
- **`kpi_definition` con menos de 21 filas:** reiniciar el backend
  (`kubectl -n <ns> rollout restart deployment/backend`) y revisar sus logs.
- **Volver a la imagen anterior:** no hay migración que deshacer. Los
  snapshots nuevos se quedan en `kpi_snapshot` sin estorbar. Los widgets de
  tabla ya guardados siguen en la base; con el backend viejo se leen, pero
  editarlos o crear otros daría 400.
- **Pendiente fuera de este despliegue:** el `DEFAULT now()` de
  `incident.creation_date` (decisión de Alan, en
  `docs/2026-09-28_creation_date_sin_default_en_incident.md`) y la plantilla
  del tablero de Adser (`seed_kpi_dashboard_template.py`).
