# `incident`/`nm_incident_product.creation_date`: sin default real en Postgres

**Para Alan — decisión pendiente, toca producción, no se actuó sin su OK.**

## Hallazgo

El modelo ORM (`app/models/incident.py`, `app/models/nm_incident_product.py`)
declara `creation_date` como `nullable=False, server_default=func.now()`.
`database/init.sql` (líneas 298 y 436) las crea como
`"creation_date" TIMESTAMP NULL` — **sin ningún `DEFAULT`**. Esto no es un
caso aislado: 49 de las 68 columnas `creation_date` de todo `init.sql` están
así, contra 19 que sí traen `NOT NULL DEFAULT`.

La mayoría de la app no lo nota porque `BaseService._fill_system_defaults()`
(`app/services/base_service.py:97-115`) rellena `creation_date` en Python al
crear cualquier entidad por el flujo genérico — el propio comentario del
código explica que existe justo para esto ("CSV generated init.sql may
define these columns as nullable"). `IncidentService.create()` hereda ese
comportamiento, así que un incidente capturado normal por la app sí trae
`creation_date`.

El problema es todo lo que inserta **sin pasar por ese servicio**:

- `backend/scripts/migrate_adser.py` (`migrar_incident`,
  `migrar_nm_incident_product`) inserta directo con `session.add(...)` — los
  139 incidentes y ~2768 renglones de vale migrados de Adser quedan con
  `creation_date` **NULL**.
- **Todo el módulo de vales de almacén**
  (`app/services/warehouse_voucher_service.py`) hace lo mismo por diseño (es
  una transacción de negocio compleja, no un alta simple) — esto no es solo
  un problema de datos migrados: **ningún vale de almacén, ni uno nuevo
  capturado hoy en producción real, tiene `creation_date`**.

### Impacto medido

`incidentes_resueltos_por_empleado_query` (KPI) agrupaba por
`func.date(Incident.creation_date)`: con esa columna en NULL,
`func.date(NULL) >= fecha_inicio` nunca es verdadero, así que **cualquier
incidente insertado por esos caminos quedaba invisible en cualquier rango**,
no solo los migrados. Ya corregido en el código (ver commit de esta tarea)
para usar `incident_date` en su lugar — ese sí llega bien poblado (confirmado
contra `migrate_adser.py`: `incident_date` viene directo de `fecha_incidente`
de origen, sin sentinel).

También afecta el **orden por default de la lista de incidentes**
(`incident_service.py:329`, usa `creation_date` cuando no se pide un `sort`
explícito) — cualquier incidente sin esa columna se va al fondo o al frente
del listado (depende de cómo Postgres ordene NULLs), mezclado sin criterio
real con los que sí la tienen.

## Propuesta (no aplicada — decisión de Alan, toca producción)

1. **Agregar el `DEFAULT now()`** a `incident.creation_date` y
   `nm_incident_product.creation_date` en Postgres, vía migración (
   `ALTER TABLE ... ALTER COLUMN creation_date SET DEFAULT now()`) — esto
   arregla altas **futuras** de cualquier camino que no use
   `_fill_system_defaults()` (vales de almacén, cualquier script), sin
   depender de que cada servicio lo rellene a mano.
2. **Rellenar las filas NULL existentes** con `incident_date` cuando exista
   (`UPDATE ... SET creation_date = incident_date WHERE creation_date IS
   NULL AND incident_date IS NOT NULL`) — no con `now()`, que falsearía la
   fecha real de cada incidente/vale ya migrado.
3. Revisar si el mismo patrón (`NULL` sin default real) aplica a otras de
   las 49 columnas identificadas — no se investigó una por una en esta
   tarea, solo `incident`/`nm_incident_product`.

No se tocó el esquema ni se escribió la migración: es una decisión de
producción real (adser-prod tiene datos migrados dependientes de este
comportamiento) que le corresponde a Alan.
