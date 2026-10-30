# KPI `piezas_por_estado` — PENDIENTE DE CONCILIAR contra tyakxa-dev

**Estado: construido y probado, NO validado con datos reales. No está en el perfil de
permisos (`seed_kpi_permissions.py`) ni en la plantilla del tablero de Adser
(`seed_kpi_dashboard_template.py`). No mostrarlo a Adser hasta cerrar la conciliación de abajo.**

- **Código:** `backend/app/kpis/registry.py` (`piezas_por_estado_query`, `PIEZAS_CATEGORIAS`,
  `PIEZAS_COLORES`).
- **Pruebas:** `backend/tests/test_services/test_kpi_piezas_por_estado.py` (Postgres) y la muestra
  `backend/tests/fixtures/estado_de_piezas_adser_muestra.csv`.
- **Sin migración:** las filas de `kpi_definition` las siembra `init_db.py` en cada arranque. Tras
  desplegar, el KPI existe pero ningún rol lo ve hasta agregarlo al perfil.

## Qué mide

Una **foto de hoy** (snapshot, agregación `ultimo`, dona por defecto): cuántas piezas hay en cada
estado. Se cuentan filas de `product` con `deletion_date IS NULL` (en Adser, 2220); cada pieza cae en
UNA categoría, la primera que cumpla:

| Prioridad | Categoría | Regla | Color |
|---|---|---|---|
| 1 | Destruccion | `id_inventory_status` = `retirado` | `#e0559b` |
| 2 | Extraviado | `extraviado` | `#ef6f5c` |
| 3 | Dañado | `danado` | `#f0a93b` |
| 4 | En reparación | `en_reparacion` | `#8b6fe0` |
| 5 | Salida | renglón de vale abierto, dirección salida, de un vale que no sea de baja | `#2f8fe0` |
| 6 | Entrada | todo lo demás | `#22b573` |

Orden de lectura: Entrada, Salida, En reparación, Dañado, Extraviado, Destruccion. La suma de las 6 es el
total de piezas (probado). `material_por_estado` (el flujo por tipo de vale) no se tocó.

Detalles: dos renglones abiertos de la misma pieza cuentan una vez; el centinela de Adser
(`close_date = 1990-01-01`) cuenta como abierto; un vale de destrucción o extravío abierto no hace Salida;
una pieza dañada y prestada a la vez se cuenta como Dañado. Incluye todo `product` (`stock_purpose` es
`uso_interno` en las 2220 piezas de Adser y no separa herramientas de consumibles). El estado de catálogo
no guarda historia: no se reconstruyen días pasados, la historia empieza cuando corra la tarea nocturna.

## Por qué está pendiente

El CSV de Alan (`2026-09-30_estado_de_piezas_adser.csv`) trae el **texto antiguo** del estado
(`estado_guardado`), no `id_inventory_status`. Con él, la derivación da (calculada, no medida en la base):
Destruccion 86, Extraviado 65, Dañado 38, Salida ≈ 152, Entrada ≈ 1879. El 130 / 1901 del sistema anterior
es texto guardado, no préstamos abiertos: la diferencia (152 = 123 + 29) está explicada pieza por pieza en
el CSV. Falta comprobarlo contra `id_inventory_status` real y los renglones abiertos reales de tyakxa-dev.

## Conciliación (solo lectura, cuando haya acceso a tyakxa-dev)

```bash
kubectl -n tyakxa-dev exec -i deploy/db -- psql -U <usuario> -d <base> -At -F, \
    < backend/scripts/conciliar_piezas_por_estado.sql > piezas.csv
python3 backend/scripts/conciliar_piezas_por_estado.py piezas.csv \
    docs/despliegues/2026-09-30_estado_de_piezas_adser.csv
```
(El nombre del pod/Deployment de la base y el usuario dependen del clúster: confirmarlos.)

Debe dar: 86 / 65 / 38, Salida cerca de 152, total 2220, y solo unas pocas piezas que difieran del CSV
(que es del 30-sep). Revisar una por una las que difieran. Ojo, la columna de renglones abiertos del CSV
incluye vales de baja; los ~156 renglones de "Salida" sin baja se confirman con esta misma consulta.

## Para activarlo (después de conciliar)

1. Agregarlo a `seed_kpi_permissions.py` (perfil) y, si procede, a la plantilla del tablero.
2. Backfill no hace falta para la foto de hoy: la tarea nocturna la escribe sola; para verla ya,
   `python scripts/recalculate_kpi_snapshots_range.py <hoy> <hoy>`.
