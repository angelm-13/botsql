# KPIs: regla de agregación por KPI y columna `kpi_snapshot.peso`

- **Commit:** `4c36348` — `fix(kpis): cada KPI declara su regla de agregacion; _totales() ya no suma todo`
- **Migración:** `database/migrations/20260925140000_kpi_snapshot_peso.sql`
  (`ALTER TABLE kpi_snapshot ADD COLUMN IF NOT EXISTS peso NUMERIC`,
  idempotente).
- **Además de §7.1 hace falta:** un backfill de snapshots justo después del
  rollout. Sin él, los 4 KPIs ponderados salen **vacíos** para todo lo
  anterior al despliegue.

## Por qué el backfill

Antes, `_totales()` sumaba todos los snapshots del rango y eso inflaba
porcentajes, promedios y existencias (medido: 1500 % en vez de 50 %). Ahora
cada KPI declara su regla (`agregacion`), y los de `promedio_ponderado`
necesitan un `peso` en cada fila:

- `desarrollo_por_empleado`
- `incidentes_resueltos_por_empleado`
- `tiempo_promedio_reparacion_laboratorio_por_tecnico`
- `costo_promedio_reparacion_laboratorio_por_tecnico`

Las filas que ya existen no tienen peso (`peso IS NULL`), así que la ruta
las **ignora**. Las de los dos KPIs de porcentaje además tienen la forma
vieja: una fila por empleado fechada en el último día, en lugar de una por
día. El backfill vuelve a calcular el año completo con la forma nueva.

`articulos_bajo_stock` (regla `ultimo`) y los KPIs de `suma` no necesitan el
backfill para dar números correctos, pero el backfill no les hace daño: es
el mismo upsert idempotente de cada noche.

## Pasos

Aplica a cada ambiente: `tyakxa-dev` se despliega solo al hacer push a
`initAlan`, y los clientes se promueven a mano. Sustituye `<ns>` por el
namespace (`tyakxa-dev`, `torredigital-prod`, `adser-prod`,
`vidrioyaluminios-prod`).

### 1. Desplegar la imagen

El procedimiento normal de §7.1. El initContainer `db-migrate` aplica
`20260925140000` **antes** de que arranque el backend nuevo, así que el
código nuevo nunca corre sin la columna. `celery-worker` y `celery-beat`
usan la misma imagen del worker; tienen que quedar en el mismo tag, porque
la tarea nocturna ya escribe `peso`.

```bash
kubectl -n <ns> rollout status deployment/backend
kubectl -n <ns> rollout status deployment/celery-worker
```

### 2. Verificar la columna

```bash
kubectl -n <ns> exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
SELECT column_name FROM information_schema.columns
WHERE table_name = 'kpi_snapshot' AND column_name = 'peso';
SQL
```

Las consultas van por heredoc (`exec -i` + `<<'SQL'`) y no dentro de
`sh -c '...'`: ahí cada comilla simple del SQL cerraría la del shell.

Esperado: `peso`.

### 3. Backfill (inmediatamente después del rollout)

Rango recomendado: **365 días hasta hoy**. Es el máximo que la ruta deja
consultar de una vez (`KPI_RANGO_DIAS_MAX_POR_OMISION`), así que calcular
más atrás no se vería en el tablero. Si el plan del cliente declara otro
`kpi_rango_dias_max`, usa ese número.

```bash
kubectl -n <ns> exec deployment/backend -- python -c "
from datetime import date, timedelta
from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango
hoy = date.today()
print(recalcular_kpi_snapshots_rango(hoy - timedelta(days=364), hoy))
"
```

Esperado: `{'ok': True, 'message_key': 'jobs.kpis.snapshots_recalculated', 'filas': N, ...}`.

Es idempotente: si se corta a la mitad no queda nada a medias, porque todo
va en una sola transacción, y se puede volver a correr.

**Duración:** en una base de prueba con 3 proyectos activos y un mes de
datos, el año completo tardó **0.3 s** (303 filas). El costo crece con
(proyectos activos × KPIs con alcance de proyecto) y con el volumen de
tareas, incidentes, órdenes y existencias. Para el tamaño de los ambientes
actuales (adser: 139 incidentes, 2220 productos) se esperan **segundos,
no minutos**. No se midió contra datos reales de cliente.

### 4. Verificar

**a) Los KPIs ponderados tienen filas con peso:**

```bash
kubectl -n <ns> exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT d.clave,
       count(*) FILTER (WHERE s.peso IS NOT NULL) AS con_peso,
       count(*) FILTER (WHERE s.peso IS NULL)     AS sin_peso_ignoradas,
       max(s.periodo)                             AS ultimo_dia
FROM kpi_definition d
JOIN kpi_snapshot s USING (id_kpi_definition)
WHERE d.clave IN ('desarrollo_por_empleado', 'incidentes_resueltos_por_empleado',
                  'tiempo_promedio_reparacion_laboratorio_por_tecnico',
                  'costo_promedio_reparacion_laboratorio_por_tecnico')
GROUP BY d.clave ORDER BY d.clave;
SQL
```

Esperado: `con_peso > 0` en cada KPI que tenga datos de origen (si un
cliente no usa laboratorio, esos dos KPIs no aparecen, y eso está bien).
`sin_peso_ignoradas` son las filas viejas; se quedan y no afectan.

**b) Ningún porcentaje pasa de 100 en los últimos 30 días** (antes del
arreglo daba miles):

```bash
kubectl -n <ns> exec -i statefulset/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT d.clave, round(sum(s.valor * s.peso) / nullif(sum(s.peso), 0), 2) AS pct_30_dias
FROM kpi_definition d
JOIN kpi_snapshot s USING (id_kpi_definition)
WHERE d.unidad = 'porcentaje' AND s.peso IS NOT NULL AND s.periodo >= current_date - 29
GROUP BY d.clave;
SQL
```

Esperado: valores entre 0 y 100.

**c) En el tablero:** abrir un widget de "Desarrollo por empleado" o
"Artículos bajo stock" con un rango de 30 días. El número debe ser un
porcentaje razonable o la existencia actual, no un múltiplo de los días
del rango.

## Si algo sale mal

- **El backfill truena:** la transacción se revierte completa y no queda
  nada a medias. Revisar el error: un `RuntimeError ... no regreso la
  columna peso` significa que un `query_builder` de `promedio_ponderado` no
  trae peso, y es un error de código, no de datos.
- **Volver a la imagen anterior:** es seguro. La columna `peso` es nullable
  y el código viejo la ignora. Pero el código viejo vuelve a sumar todo, así
  que los números inflados regresan.
- **Limpieza opcional (no necesaria, no está decidida):** las filas viejas
  sin peso de los 4 KPIs ponderados se pueden borrar para no dejar ruido.
  No se incluye aquí; hay que decidirlo aparte.
