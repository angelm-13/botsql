# 2026-10-15 — KPIs de restaurante: zona horaria, día operativo y tarjetas unificadas

**Para Alan. URGENTE: el defecto ya está en producción.** Los KPIs de restaurante, la corrida
frecuente y la vista previa (`7596bfc`, `ba56958`, `14d70bf`, `fbebe02`) están contenidos en
`4fb6691`, y los overlays de `adser-prod`, `torredigital-prod` y `comala-prod` apuntan a `4fb6691`
(verificado con `git merge-base --is-ancestor`, 2026-10-15). Los cambios de esta nota **todavía no están
promovidos**: hasta que se promuevan, los KPIs de restaurante de esos tres ambientes siguen agrupando por
**día UTC** (un cobro después de las 18:00 hora de México cuenta en el día siguiente).

Si ningún cliente real usa aún el módulo de restaurante, el impacto es nulo hoy; si alguno lo usa, las
cifras diarias de ventas, propinas, ticket, platillos, mesas, servicios y tiempo de entrega están corridas
para todo lo cobrado entre las 18:00 y las 24:00 hora local.

## Qué trae (sin migraciones ni columnas nuevas)

1. **Zona horaria.** `dia_local()` (`app/utils/tiempo.py`, usa `APP_TIMEZONE`) reemplaza a `date(columna)` en
   los KPIs de restaurante. La corrida frecuente fecha "hoy" con `hoy_negocio()`.
2. **Día operativo por sesión de caja** (`restaurant_rules.dia_operativo`). Un turno que cierra pasada la
   medianoche cuenta en el día en que abrió la caja; sin sesión que lo contenga, fecha calendario local. La
   desviación de caja pasa de `closed_at` a `opened_at`.
3. **Etiquetas** de `pedidos_del_dia`: Cobrado, Entregado sin cobrar, En curso.
4. **Tarjetas de "Administración del restaurante"** (`RestaurantService.kpis()`): mismas claves, ahora con los
   cálculos de los KPIs (consultas agregadas en SQL, no cargan todas las órdenes). Dos cambios de criterio:
   *entrega promedio* cuenta toda orden entregada (antes solo las cobradas); *mesas activas* excluye las de
   para llevar (antes las contaba). Venta, propinas y ticket siguen acumulados.

## Antes de promover

- **Beat de 5 minutos.** `recalculate-kpi-snapshots-frecuentes` corre cada 5 min (`KPI_FRECUENTES_INTERVALO_MIN`,
  1–60) y ya está en producción desde `4fb6691`. Con el día operativo cada corrida evalúa una subconsulta por
  orden del día; medido en local con 200 mil órdenes de un restaurante: 74 ms por día (ticket promedio), ~350–420 ms
  para `servicios_por_mesero`/`pedidos_del_dia` (su columna no tiene índice). Detalle y tabla en
  `docs/arquitectura-kpis.md` §2.1.2. Un índice `(id_proyect, opened_at)` en `restaurant_cash_session` lo bajaría a
  20 ms; **no se creó** porque sería una migración — decisión tuya.
- **Hay que decir al gerente** que el día operativo depende de cerrar la caja: una caja abierta varios días
  absorbe las ventas de los siguientes (riesgo documentado en `arquitectura-kpis.md`).

## Hallazgos para ti (no se tocaron)

1. **Celery y la zona horaria.** `app/config/celery_config.py` (el que carga `app/jobs/celery_app.py`) fija
   `timezone = os.getenv("CELERY_TIMEZONE", "UTC")` con `enable_utc = True`: `crontab(hour=1)` de la corrida
   nocturna corre a las **01:00 UTC = 19:00 hora de México**, no a la 01:00 local (`celery_worker.py` carga esa
   configuración; ni `docker-compose.yml` ni `k8s/` fijan `CELERY_TIMEZONE`). Además `app/celery_app.py` (otro
   archivo, usado solo por `app/tasks/erp_tasks.py`) fija `celery.conf.timezone` con `TZ`: dos criterios distintos. La corrida nocturna usa `date.today()` del
   contenedor; en k8s el backend lleva `TZ=America/Mexico_City` (los Deployments de celery también, según el
   YAML), así que "hoy" es local, pero a las 19:00 el día aún no termina: lo de las 19:00 a medianoche solo lo
   completa la corrida frecuente (restaurante/POS) o la ventana de 7 días de la noche siguiente (los demás módulos).
   No cambia nada con este commit; decidir si `CELERY_TIMEZONE` debe ser `America/Mexico_City` (movería todas las
   tareas programadas: inventario horario, citas, avisos de vales cada 6 h).
2. **El mismo desfase UTC puede afectar otros reportes.** Los 24 KPIs originales (`registry.py`) agrupan con
   `func.date(...)` sin convertir zona. Los de fecha de pared (`incident_date`, `close_date`, vencimientos) son
   correctos tal cual (ya son locales). Los de columnas en UTC **sí** tienen el desfase: `Task.creation_date`
   (`registry.py:250`) e `InventoryAssetEvent.creation_date` (`:722`), y `Invoice.date_emision` mezcla ambos
   (`convert_quotation_invoice` la escribe con `datetime.utcnow()`, la captura manual con hora local).
   Fuera de KPIs: `RestaurantService.sales_report` agrupa por `paid_at.date()` (UTC), `activity_log_service` y otros usan
   `date.today()` del contenedor, y `restaurant_service.py:343` ya recibe `tz_offset_minutes` del cliente. La nota
   `2026-10-14_fechas_utc_y_coordenadas_de_checada.md` ya lo marca como deuda ("fechas de negocio de otras
   tablas"). Solo lectura: no se modificó ninguno.
3. **`sales_report` del servicio** sigue por día UTC (no es una tarjeta ni un KPI; no estaba en el pedido).

## Reprocesar el histórico (decide Alan, no se hizo en producción)

Cambiar de día UTC a día operativo mueve ventas de un día a otro: **las cifras ya vistas en el Dashboard
cambian**. Para reprocesar, ya con la imagen nueva desplegada:

```bash
# dentro del pod de backend; ajusta el rango. Recalcula TODOS los módulos del rango (idempotente: upsert).
python scripts/recalculate_kpi_snapshots_range.py <fecha_inicio:YYYY-MM-DD> <fecha_fin:YYYY-MM-DD>
```

- Las **fotos** (`pedidos_del_dia`, `mesas_ocupadas`, `cuentas_sin_cobrar`) solo se escriben en la fecha final del
  rango y no se pueden reconstruir hacia atrás: no las reprocese esperando días pasados.
- En la base **local** no había órdenes de restaurante (0 órdenes, 1 sesión, solo 21 filas de fotos), así que no hubo nada que
  reprocesar; el comportamiento se probó con las pruebas de `test_kpi_restaurante.py`.
- Orden sugerido: promover → verificar una venta de la noche en el Dashboard → reprocesar el rango que Alan elija.
- Si algo sale mal: volver el overlay al tag anterior; el reproceso es un upsert por (KPI, día, entidad), se repite sin duplicar.

## Verificación

- `backend/ci/run_postgres_tests.sh -k kpi` (base limpia) y la suite completa en SQLite, ver el reporte del commit.
- En el ambiente: cobrar una orden a las 19:00–23:59 y comprobar que `ventas_restaurante` la cuenta en el día local.
