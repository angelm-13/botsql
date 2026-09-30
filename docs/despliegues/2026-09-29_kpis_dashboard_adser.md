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

## Solo `adser-prod`: tablero de plantilla para `taroj`

`backend/scripts/seed_kpi_dashboard_template.py` le arma a `taroj` un tablero
("Operación Adser") con 5 widgets, por el mismo servicio que usa el editor:

En este orden (el orden del tablero es `posicion_orden`, de 100 en 100):

| # | Gráfica | KPI | Rango / tamaño |
|---|---|---|---|
| 1 | Tabla | Material prestado ahora | Sin rango (KPI en vivo). 2 columnas × 2 filas: `parametros = {"columnas": 2, "filas": 2}` |
| 2 | Número | Incidencias pendientes | Hoy, contra el mismo día de hace 30 días |
| 3 | Barras | Incidencias abiertas vs. cerradas | Este año |
| 4 | Barras | Incidencias abiertas por responsable | Este año |
| 5 | Dona | Material por estado | Hoy |

**Cómo se ve (masonry):** cada tarjeta conserva su **altura natural**; no se estira
para igualar a las vecinas. La tabla es el widget principal, a la izquierda, y las
tarjetas chicas se apilan a su derecha, cada una a su alto. Con 4 columnas (pantalla
ancha) la tabla ocupa 2 y las otras se reparten en las 2 columnas de la derecha; con
3 columnas, la tabla más una columna de tarjetas apiladas (el resto cae debajo, en
la columna que quede más corta); con 2 o 1 columna, todo apilado con la tabla
primero. La parte de abajo de un masonry es irregular por naturaleza: las columnas
no terminan a la misma altura.

**Cómo está hecho** (sin librería): `.kpi-widget-grid` tiene tope de 4 columnas y
filas de 4 px; cada tarjeta ocupa las filas que mide (`grid-row-end: span N`, lo
escribe `useMasonryRef`, en `components/kpi-widgets/useMasonry.js`, con un
`ResizeObserver` y directo en el DOM, no en el estado de React: la primera medida se
hace antes de pintar y un cambio de alto se corrige antes del siguiente cuadro, sin
parpadeo). `grid-auto-flow: dense` hace que cada tarjeta caiga en el primer hueco
donde cabe, que en la práctica es la columna más corta. El recuadro "Agregar
gráfico" es uno solo, a todo el ancho, al final. La tabla no se estira: su lista
se desplaza por dentro con un tope (22 rem, o 36 rem con `filas: 2`).

**Cómo se mapea `posicion_orden` al layout:** `posicion_orden` (de 100 en 100) es
el orden en que se **colocan** las tarjetas; el DOM sigue ese orden. Cada tarjeta
cae en el primer hueco libre (más arriba y, a igual altura, más a la izquierda). Por
eso el orden **visual** es por columnas y no por renglones, y puede no coincidir con
el lineal: la 4.ª puede quedar a la derecha de la 2.ª y arriba de la 3.ª. Lo
que sí es cierto siempre: mover una tarjeta antes en la lista la coloca antes.

**Arrastre:** mientras arrastras, las demás tarjetas se corren solas y la tarjeta
arrastrada deja un **hueco de su tamaño real** donde caería. No es una reja uniforme:
el hueco es la propia tarjeta (escondida, con su altura natural) puesta en el orden
que tendría al soltar, y el masonry real acomoda a las demás alrededor; las que
cambian de lugar se deslizan con una animación de 220 ms (FLIP). Lo que sigue al
puntero es una copia estática de la tarjeta (su HTML), no otra tarjeta viva: no vuelve
a pedir datos ni a montar gráficas. Al soltar se guarda `posicion_orden` con **ese
mismo orden**, así que el resultado coincide con lo que mostraba el hueco, sin saltos.
Con `prefers-reduced-motion` no hay animación de corrimiento (las tarjetas cambian de
lugar de golpe y la copia cae sin animación). Tras cada corrimiento se ignora el
movimiento durante 220 ms para que las tarjetas no "tiemblen" mientras la que se
acaba de mover todavía se está deslizando. Código:
`components/kpi-widgets/useReordenarTarjetas.js` y `kpi/kpiReorden.js`.

**Un tablero que ya existía no cambia de orden ni de tamaño:** la plantilla no
modifica lo que alguien ya tiene (regla de idempotencia de abajo). Para reacomodarlo,
se edita el widget de la tabla (el editor ofrece "Alto de la tabla" y "Ancho de la
tabla") o se borra el tablero y se corre la plantilla de nuevo. En `adser-prod` la
plantilla aún no se ha corrido, así que nace con el orden nuevo.

"Este año" y no 30 o 90 días porque en Adser el último vale migrado es del 15 de
agosto y no hay capturas nuevas desde la migración: un rango corto sale vacío.
Cuando vuelvan las capturas, el rango se puede acortar desde el editor.

Los de serie guardan `rango_relativo` más la foto de las fechas de hoy, así que
el Dashboard las recalcula cada vez que se abre. "Contra hace 30 días" se guarda
como `comparar_desfase_dias: 30`.

> **AVISO: no correr la tabla en `adser-prod` todavía.** "Material prestado
> ahora" depende de `incident.incident_date` (la fecha del vale). Hasta que Alan
> confirme, con una consulta de solo lectura, que esa fecha es confiable en lo
> migrado, la tabla puede mostrar fechas o días prestados equivocados. Mientras
> tanto, `--sin-tabla` crea los otros 4 widgets; la tabla se agrega después con
> una corrida normal (los 4 ya existentes se respetan). El script imprime este
> aviso cada vez que la tabla forma parte de lo que va a crear.

Requiere que `taroj` vea esos KPIs: correr antes `seed_kpi_permissions`
(paso de arriba). Si no los ve, el script no escribe nada y lo dice.

```bash
# Sin la tabla, hasta confirmar incident_date:
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template --sin-tabla --dry-run
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template --sin-tabla

# Ya confirmada incident_date, el tablero completo (agrega solo la tabla):
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template --dry-run
kubectl -n adser-prod exec deployment/backend -- python -m scripts.seed_kpi_dashboard_template
```

Es idempotente: reusa el tablero si ya existe, no repite un widget (misma
gráfica y mismo KPI), no pisa lo que alguien haya cambiado y no borra nada. Si
se borra un widget de la plantilla, volver a correrla lo crea otra vez. Códigos
de salida: `0` bien; `1` permisos o plantilla inválida (no se escribió nada);
`2` el usuario no existe. Opciones: `--usuario`, `--nombre` y `--sin-tabla`.

Verificar: `taroj` entra al Dashboard y ve el tablero "Operación Adser" con sus
tarjetas y los rangos rotulados ("Hoy · …", "90 días · …"). Un dry-run posterior
debe decir `ya existe, sin cambios` en todo.

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
- Un widget de tabla no guarda periodo ni filtros (son datos de "ahora"). Lo
  único que puede guardar es su tamaño: `columnas: 2` (dos columnas de la
  cuadrícula) y `filas: 2` (tabla alta: la lista se desplaza por dentro con un tope
  mayor, 36 rem en vez de 22); ausentes son 1 y 1, así que las tablas guardadas antes se ven igual. En pantallas donde solo cabe una
  columna, la tabla vuelve a ocupar una. Sin migración: `parametros` es JSON
  libre y el backend no lo valida.

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
  `docs/2026-09-28_creation_date_sin_default_en_incident.md`).
