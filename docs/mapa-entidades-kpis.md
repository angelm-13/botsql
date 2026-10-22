# Mapa entidad → tabla existente (Fase 0 de los KPIs nuevos)

Rama `initAlan` · 2026-10-12 · solo lectura, **sin commit**.

Fuentes del mapa: modelos de datos de Logística (NKPM) y Restaurante
(COMALY'SA), contra las tablas **reales** de la base local de Docker
(`tyakxa_erp`, sesión `default_transaction_read_only=on`) y el código de
`backend/app`. Todas las tablas de restaurante y logística están **vacías** en
esa base; ningún dato real de clientes se consultó. Lo no comprobable está
marcado **NO VERIFICADO**.

## 1. Hipótesis: confirmadas y refutadas

| Hipótesis | Veredicto | Evidencia |
|---|---|---|
| KPI / Reporte ejecutivo = `kpi_definition` / `kpi_snapshot` | **KPI: confirmada. Reporte ejecutivo: refutada como tabla.** | El "reporte" es una captura PDF del tablero hecha en el navegador (`Dashboard.jsx:12-13`, `html2canvas` + `jsPDF`); no hay tabla. |
| Cliente = `customer_supplier`; alta = `creation_date` | **Confirmada con matices** | `type` es enum **nullable** `client`/`supplier` (`models/customer_supplier.py:39`; CHECK en BD): hay que filtrar `type='client'` y decidir qué pasa con `NULL`. `creation_date` existe, pero que esté poblada en datos migrados de un legado: NO VERIFICADO (para `incident` sí falló, ver `registry.py:352-365`). No tiene `id_proyect`. |
| Viaje + Programación = `logistics_trip` (`planned_*`/`actual_*`) | **Confirmada** | `planned_pickup_at/delivery_at`, `actual_pickup_at/delivery_at`; CHECK de orden entre fechas. "Programada" además en `logistics_service_request.status='programado'`. |
| Rack = `inventory_asset` (+`_event`) | **REFUTADA** | `inventory_asset` es herramienta prestable (`status` disponible/en_uso/prestada…). El rack retornable es **`logistics_rack`** (`status` en_cliente/en_almacen/pendiente_retorno/en_reparacion, `sent_at`, `received_at`). |
| Almacén = `location` | **REFUTADA para logística** | `location` es del inventario núcleo. Logística tiene `logistics_warehouse` → `logistics_location` → `logistics_inventory` (con puente opcional `id_core_location`/`id_product`). |
| Documento = `document` | **Parcial** | `document` (`id_proyect NOT NULL`, `status`, `expiration_date`, `business_reference_type/value`) es el repositorio genérico. El expediente de un envío es `logistics_file` (folio, facturación, `id_invoice`). La evidencia de entrega es `logistics_evidence`. |
| Sesion_Mesa = `restaurant_visit` | **Confirmada** | `opened_at/closed_at`, `id_restaurant_table`, `id_restaurant_waiter`, `diners_count`. |
| Encuestas = `survey_*` | **Existen, pero no sirven como CSAT de clientes** | `nm_survey_user` responde por `id_user` (usuario del sistema), sin liga a cliente ni viaje. |
| Bitácora = tabla de auditoría | **Confirmada: `event_log`, con límites** | Ver huecos 9 y 10. |

## 2. Logística (NKPM)

| Entidad | Tabla real | Columnas usadas | Diferencias de granularidad | Dimensión necesaria |
|---|---|---|---|---|
| Cliente | `customer_supplier` (`type='client'`) | `id_customer_supplier`, `name`, `type`, `creation_date`, `deletion_date`, `sla_level`, `credit_limit` | Una sola tabla para clientes y proveedores | cliente |
| Cotización | `logistics_quotation` | `status` (borrador/enviada/aceptada/rechazada/vencida/cancelada), `total`, `id_customer_supplier`, `creation_date` | — | cliente |
| Tarifa | `logistics_rate` | `service_type`, `origin`, `destination`, `unit_type`, `amount`, `currency`, `status` | Por cliente | cliente |
| Contrato | `logistics_contract` | `contract_number`, `start_date`, `end_date`, `sla_level`, `status` (activo/inactivo) | — | cliente |
| SLA | `logistics_contract.sla_level` / `customer_supplier.sla_level` | etiqueta de texto | **Solo una etiqueta**; no hay meta medible (horas, %). Hueco 3 | cliente |
| Solicitud de servicio | `logistics_service_request` | `id_logistics_quotation` (FK → cotización), `status` (solicitado/aprobado/programado/cancelado), `requested_pickup_at/delivery_at`, `priority` | — | cliente |
| Programación de viaje | `logistics_trip` (+ solicitud en `programado`) | `planned_pickup_at`, `planned_delivery_at`, `creation_date` | No hay tabla aparte: programar = crear/editar el viaje | cliente, unidad, operador |
| Freight forwarding | `logistics_shipment` | `shipment_number`, `bl_number`, `provider`, `transport_mode`, puertos, `customs`, `status` | **Sin fechas de entrega ni de liberación**; solo `status` y fechas de auditoría | cliente |
| Viaje | `logistics_trip` | `status` (11 valores), `actual_*`, `planned_cost`, `actual_cost`, `revenue`, `kilometers`, `id_logistics_unit/_operator/_trailer` (nullables) | "Cerrado" no tiene fecha propia: solo `actual_delivery_at` y `status`. Hueco 4 (ciclo) | cliente, unidad, operador |
| Evidencia de entrega | `logistics_evidence` | `id_logistics_trip`, `evidence_type`, `photo_path`, `signature_path`, `captured_at` | Por viaje; `photo_path`/`signature_path` nullables (definir "con evidencia") | cliente (vía viaje) |
| Incidencia | `logistics_incident` | `id_logistics_trip`, `incident_type`, `severity`, `status` (abierta/en_proceso/resuelta/cerrada/cancelada), `creation_date`, `last_update_date` | **Sin fecha de cierre.** Hueco 4 | cliente (vía viaje) |
| Rack retornable | `logistics_rack` | `status`, `condition`, `quantity`, `sent_at`, `received_at`, `id_customer_supplier` | Un solo par enviado/recibido; **sin historial de eventos**. Hueco 6 | cliente |
| Proveedor de transporte | *sin tabla propia* | `logistics_trip.supplier_reference` (texto libre), `logistics_shipment.provider` (texto libre) | No hay FK a `customer_supplier(type='supplier')`. Hueco 2 | — |
| Unidad | `logistics_unit` | `plate`, `unit_type`, `availability_status` (disponible/en viaje/mantenimiento/fuera de servicio), `status`, vencimientos de seguro/verificación | `availability_status` es **estado actual**, sin historial | unidad |
| Operador | `logistics_operator` | `full_name`, `license_expiration`, `status` (activo/inactivo), `performance_score` | No está ligado a `user`. "Disponible" no existe como estado. Hueco 13 | operador |
| Mantenimiento | `logistics_maintenance` | `id_logistics_unit`, `maintenance_type` (**texto libre, 80 car., sin dominio**), `scheduled_at`, `closed_at` (obligatorio si `cerrada`), `cost`, `status` | Preventivo/correctivo no se distingue por columna. Hueco 5 | unidad |
| Inspección | *sin cobertura* | — | No existe tabla ni término en el código. Hueco 1 | — |
| Remolque | `logistics_trailer` | `plate`, `trailer_type`, `capacity`, `status` | — | — |
| Inventario del cliente | `logistics_inventory` | `id_customer_supplier`, `sku`, `quantity`, `lot`, `serial_number`, `status` | Cantidad actual; sin conteo físico ni ajustes. Hueco 12 | cliente |
| Almacén | `logistics_warehouse` / `logistics_location` | `name`, `capacity`, `status` | — | — |
| Factura | `invoice` (+ `logistics_file.id_invoice`, `logistics_receivable.id_invoice`, `invoice.source_module='logistica'`) | `date_emision`, `total`, `invoice_status`, `id_customer_supplier` | Las facturas de logística se identifican por tres caminos distintos: decidir uno | cliente |
| Cuenta por cobrar | `logistics_receivable` | `amount`, `due_at`, `status` (pendiente/pagado/vencido), `paid_at` | **Ningún código escribe `vencido`**: calcular por `due_at` | cliente |
| Pago | `invoice_payment` (núcleo) y `logistics_receivable.paid_at` | `paid_at`, `amount`, `status` | Dos fuentes de "pagado": decidir cuál manda | cliente |
| Documento | `document` / `logistics_file` | ver §1 | — | — |
| Usuario | `user` | `id_user`, `id_proyect`, … | — | persona |
| Bitácora de auditoría | `event_log` | `table_name`, `field_name`, `action`, `before_value`, `after_value`, `created_by`, `creation_date`, `id_proyect`, `event_detail` | **No guarda el id del registro afectado.** Huecos 4, 9, 10 | persona |
| Rol / Permiso | `permission`, `entity_permission`, `nm_permission_kpi` | — | — | — |
| KPI | `kpi_definition`, `kpi_snapshot` | — | — | — |
| Reporte ejecutivo | **No es entidad**: es la exportación a PDF del navegador (`Dashboard.jsx:12-13`, `html2canvas` + `jsPDF`); no hay tabla ni dato que mapear | — | — | — |

## 3. Restaurante (COMALY'SA)

| Entidad | Tabla real | Columnas usadas | Diferencias de granularidad | Dimensión necesaria |
|---|---|---|---|---|
| Usuario (mesero) | `restaurant_waiter` | `id_restaurant_waiter`, `name`, `nickname`, `status`, `max_tables`, `id_user` (**nullable**) | El mesero es una entidad propia, no un `user` | mesero |
| Mesa | `restaurant_table` | `number`, `capacity`, `is_active`, `location_description` | — | mesa |
| Sesión de mesa | `restaurant_visit` | `id_restaurant_table` (nullable: llevar/domicilio), `id_restaurant_waiter`, `opened_at`, `closed_at`, `diners_count`, `service_type`, `status` | — | mesa, mesero |
| Reservación | `restaurant_reservation` | `id_restaurant_table`, `reservation_date/time`, `guests`, `status`, `event_type` | — | mesa |
| Platillo | `restaurant_dish` | `title`, `category`, `price`, `production_cost`, `is_active` | — | platillo |
| Insumo | `restaurant_inventory_item` (+ `_movement`) | `description`, `quantity`, `unit`, `cost_per_unit`, `id_product`, `id_location` | — | — |
| Receta | `restaurant_recipe_item` | `id_restaurant_dish`, `id_restaurant_inventory_item`, `quantity` | — | platillo |
| Pedido | `restaurant_order` | `id_restaurant_visit`, `diner_index`, `id_restaurant_waiter` (nullable), `status` (borrador→pedido→en_preparacion→listo_para_entrega→entregado→pagado), `sent_at`, `cooked_at`, `ready_at`, `delivered_at`, `paid_at`, `tip_amount` | **Un "pedido" Tyakxa es una cuenta por comensal.** Los tiempos están **por orden, no por ítem** (COMALY los mide por ítem). Hueco 7 | mesero, mesa |
| Pedido_Item | `restaurant_order_item` | `id_restaurant_dish`, `quantity`, `unit_price` | **Sin marcas de tiempo propias.** El importe no es columna: `quantity × unit_price` (`models/restaurant.py:290-292`); el subtotal de la orden es propiedad Python (`:215-217`) | platillo |
| Pago | columnas de `restaurant_order` | `payment_method`, `received_amount`, `cash_amount`, `paid_at`, `tip_amount` | No hay tabla de pagos: un cobro es un cambio de estado de la orden; `pay_visit` reparte propina/efectivo entre órdenes | — |
| (caja) | `restaurant_cash_session` | `opened_by_id`, `closed_by_id`, `difference`, `status` | Sin equivalente en COMALY | cajero |

## 4. Huecos y escalera de la regla 1 (sin tablas nuevas)

Para cada hueco: **(a)** qué dato falta · **(b)** qué existente se evaluó y por
qué no sirve · **(c)** alternativa sin cambio de esquema · **(d)** efecto en el
ER si se agregara algo. **Ningún KPI de esta lista se construye hasta tu OK.**

| # | Hueco | (a) Falta | (b) Evaluado | (c) Sin cambio de esquema | (d) Impacto en el ER si se agregara |
|---|---|---|---|---|---|
| 1 | Inspección | Entidad completa | `logistics_maintenance`, `logistics_incident`, `document` | Registrar inspecciones como `document` con `business_reference_type='inspeccion'` (ver `document.business_reference_*`) — **definición de negocio pendiente**; o no medirlas | Tabla nueva ligada a `logistics_unit` (1:N) |
| 2 | Proveedor de transporte | FK a un proveedor | `supplier_reference`/`provider` son texto libre; `customer_supplier(type='supplier')` existe pero ningún viaje lo referencia | Dimensión por texto libre (agrupa mal por variantes de escritura) | Una FK nullable en `logistics_trip` hacia `customer_supplier` |
| 3 | SLA medible | Meta numérica del SLA | `sla_level` es etiqueta | No medir cumplimiento de SLA; solo `entregas_a_tiempo` | Columna(s) en `logistics_contract` |
| 4 | Fecha de cierre de incidencia y de viaje | `closed_at` | `creation_date`, `last_update_date`, `logistics_evidence.captured_at` (es por viaje), `event_log` (**no tiene id del registro**, no se puede atribuir a una incidencia) | `last_update_date` cuando el estado es resuelta/cerrada: **aproximación** (cualquier edición posterior la mueve); para el ciclo del viaje, `actual_delivery_at` como cierre | 1 columna en `logistics_incident` (y opcional en `logistics_trip`) |
| 5 | Preventivo vs correctivo | Dominio de `maintenance_type` | Es `VARCHAR(80)` sin CHECK; ningún valor `preventivo` aparece en el código ni en el frontend | Comparar por texto (frágil) | CHECK o catálogo sobre `maintenance_type` |
| 6 | Rotación de rack | Historial de movimientos | `logistics_rack` (un par `sent_at/received_at`); `inventory_asset_event` es de herramientas, no de racks | Medir solo el ciclo actual (días entre enviado y recibido) y la foto por `status` | Tabla de eventos de rack (análoga a `inventory_asset_event`) |
| 7 | Tiempos por ítem (COMALY) | Marcas por ítem | `restaurant_order_item` sin fechas; la orden sí | Medir por orden (`sent_at/cooked_at/ready_at/delivered_at`) | Columnas en `restaurant_order_item` |
| 8 | Disponibilidad histórica de flota | Historial de `availability_status` | Solo estado actual | Foto diaria desde que corra el job (`agregacion='ultimo'`); **no hay histórico hacia atrás** | Ninguno (el snapshot es el historial) |
| 9 | Accesos denegados / login fallido | Registro persistente | Login fallido: solo el limitador en memoria (`login_throttle`, `routes/auth.py:215-233`); permisos denegados en la guarda viva (`utils/auth.py:162`) **no escriben** en `event_log`; el escritor `audit_event` solo lo invoca `security/permissions.py:71`, módulo que ninguna ruta usa | **No construir**: un KPI daría 0 falso | Ninguno, pero exige cambiar la guarda (comportamiento) |
| 10 | Eventos de auditoría por usuario | — (viable) | `event_log.created_by` + `creation_date`; las altas/cambios/bajas de todo `CrudService` se registran (`base_service.py:190-205`) | Contar por `created_by`. Límite: las filas CRUD traen `id_proyect` NULL → solo sin alcance de proyecto | Ninguno |
| 11 | CSAT de clientes | Respuesta ligada a cliente/viaje | `nm_survey_user` responde por usuario del sistema | No medir | Tabla de respuestas con FK a cliente/viaje |
| 12 | Exactitud de inventario (logística) | Conteos físicos/ajustes | `logistics_inventory` solo cantidad actual. Si `logistics_inventory_bridge` registra ajustes: NO VERIFICADO | No medir hasta confirmar | Tabla de conteos |
| 13 | Utilización de operadores | Definición de "disponible" | `status` solo activo/inactivo; hay viajes con operador y fechas | Calcular días con viaje asignado / días del periodo — **necesita tu definición** | Ninguno |

## 5. Dimensiones necesarias y fuente de etiquetas

| Dimensión | `json_key` propuesto | Fuente de la etiqueta | Nota |
|---|---|---|---|
| mesero | `id_restaurant_waiter` | `restaurant_waiter.name` | Nullable → "Sin asignar" |
| platillo | `id_restaurant_dish` | `restaurant_dish.title` | Abierta (top 10) |
| mesa | `id_restaurant_table` | `restaurant_table.number` | Nullable (llevar/domicilio) |
| cliente | `id_customer_supplier` | `customer_supplier.name` | Sin eje de proyecto |
| unidad | `id_logistics_unit` | `logistics_unit.plate` | Nullable en viajes |
| operador | `id_logistics_operator` | `logistics_operator.full_name` | Nullable en viajes |

## 6. Qué sigue sin depender de cambio de esquema

Sin cambio de esquema (viables por lo mapeado): todo Restaurante de la Fase 2;
Punto de venta (Fase 3, tablas ya revisadas en `docs/arquitectura-kpis.md`);
en Logística: tasa de conversión y valor promedio de cotizaciones, clientes
nuevos, entregas a tiempo, tasa de incidencias por viaje, cumplimiento de
evidencia, disponibilidad de flota (desde hoy), costo de mantenimiento por unidad,
DSO y cartera vencida, margen por viaje; RH y Finanzas de la Fase 5.

**En pausa hasta tu respuesta** (hueco entre paréntesis): `resolucion_incidencias_horas`
(4), `cumplimiento_mantenimiento_preventivo` (5), `tiempo_ciclo_viaje` (4, solo
si aceptas `actual_delivery_at` como cierre), rotación de rack (6), CSAT (11),
accesos denegados (9), exactitud de inventario (12), utilización de operadores
(13), cumplimiento de SLA (3), inspección y proveedor de transporte (1, 2).

## 7. Evidencia de solo lectura (2026-10-12), sin implementar nada

**7.1 Facturas de logística: los tres caminos.** Conteos en la base local:
`invoice.source_module='logistica'` = 0, `logistics_file.id_invoice` no nulo = 0,
`logistics_receivable.id_invoice` no nulo = 0 (0 expedientes, 0 cuentas por
cobrar, 1 factura sin `source_module`). **No hay solapamiento que medir: no hay
datos.** Lo que sí dice el código:

- **`invoice.source_module='logistica'` no lo escribe nadie.** El único flujo que
  lo fija es `sale_invoicing_service.py`, y su `MODULOS = ("pos", "restaurante")`
  (`:56`); además `restaurante` responde 501 (`:183-185`). El valor `logistica`
  existe solo en el CHECK `ck_invoice_source_module`.
- **`logistics_file.id_invoice` y `logistics_receivable.id_invoice` los escribe
  una persona a mano**, eligiendo la factura en un desplegable de la pantalla
  (`LogisticsFilesPage.jsx:14`, `LogisticsReceivablesPage.jsx:10`) a través del
  CRUD genérico. El servicio solo valida que la factura exista y que sea del mismo
  cliente (`logistics_workflow_service.py:212-213`, `:237-238`). `logistics_file.status`
  admite `abierto/facturando/facturado`, pero ningún código lo cambia por sí solo.
- Conclusión por código: el flujo real son **los dos vínculos manuales**; el de
  `source_module` está sin usar. Pueden diverger (un expediente y una cuenta por
  cobrar apuntando a facturas distintas) porque nada los reconcilia.

**7.2 Cobro de logística y DSO.** Registrar un cobro **no toca** ninguna tabla
de logística: `invoice_payment_service.py` no menciona logística ni cuentas por
cobrar, y `logistics_receivable` solo se escribe desde su CRUD genérico
(`status` y `paid_at` capturados a mano, `amount` único). Pagos parciales:
`invoice_payment` **sí** los maneja (`instalment`, `previous_balance`,
`outstanding_balance`, factura en `parcial`: `invoice_payment_service.py:266-279`);
`logistics_receivable` **no** (un solo `amount`, un solo `paid_at`, sin abonos).
Por tanto, el DSO sale del lado de `invoice_payment` (fecha real de cobro por
abono) y `logistics_receivable.paid_at` es un dato declarativo, no un cobro.
Qué factura es "de logística" sigue dependiendo del vínculo manual de 7.1.

**7.3 Operador disponible.** `logistics_operator`: `id_logistics_operator`,
`full_name`, `license_number` (único), `license_expiration` (nullable), `status`
(`activo`/`inactivo`), `contact_phone`, `performance_score` (≥ 0) y columnas de
auditoría. **No existe un estado "disponible"/"en viaje"** (la unidad sí lo
tiene: `availability_status`). Asignación a un viaje: `logistics_trip.id_logistics_operator`
(nullable, FK), elegido en un desplegable (`LogisticsTripsPage.jsx:14`); el servicio solo
comprueba que el operador exista y no esté borrado (`_fk`, `logistics_workflow_service.py:50-53`,
`:144`). **Nada valida que esté `activo` ni que su licencia esté vigente**
(`license_expiration` no se lee en ningún servicio), y no hay conflicto de horario
entre viajes del mismo operador.

## 8. Checadas de asistencia (Comala, `operaciones`) — 2026-10-19

Sin tablas nuevas: una checada es una fila de `incident`. Detalle y decisiones en `docs/arquitectura-kpis.md` §2.7.

| Entidad | Tabla real | Columnas usadas | Criterio / diferencia | Dimensión |
|---|---|---|---|---|
| Checada | `incident` | `latitude`, `incident_date`, `close_date`, `incident_status`, `id_user`, `deletion_date` | **`latitude IS NOT NULL`** (`es_checada()`). La pantalla de incidencias acepta además longitud o distancia solas; el backend no. Sin baja y no cancelada. | — |
| Entrada | `incident` | `incident_date` (hora de pared GMT-6, sin zona) | El día es `date(incident_date)`, sin convertir | — |
| Salida | `incident` | `close_date` + estado de cierre | `abierta → cerrada` da 409: la salida queda en `resuelta`. Nada cierra una checada solo | — |
| Parque | `team` | `id_team`, `team_description`, `deletion_date` | Equipo = parque | `equipo` (`id_team`, catálogo cerrado) |
| Pertenencia | `nm_team_user` | `id_team`, `id_user`, `deletion_date` | Una persona en dos equipos cuenta en cada uno. Sin equipo vigente (sin membresía, o solo con membresías/equipos dados de baja) sale en la fila **«Sin equipo»** (entidad `None`, `sin_asignar=True`, etiqueta de la dimensión `equipo`) y no cuenta en ningún equipo | — |

**Unicidad de la pertenencia (cambio de esquema, 2026-10-22).** `nm_team_user` tenía `uq_nm_team_user UNIQUE (id_team, id_user)` sobre **todas** las filas, también las de baja; eso impedía volver a agregar a una persona a un equipo del que ya se le había dado de baja, y la única salida (reactivar la fila vieja) falsea el histórico (A → B → A). Ahora es el índice único **parcial** `uq_nm_team_user_vigente ON nm_team_user (id_team, id_user) WHERE deletion_date IS NULL`: no hay dos membresías **vigentes** iguales, y cada periodo en un equipo es su propia fila con su `creation_date` y su `deletion_date`. Migración `20261022100000_unicidad_nm_team_user_solo_vigentes.sql` (idempotente: `DROP CONSTRAINT IF EXISTS` + `CREATE UNIQUE INDEX IF NOT EXISTS`) y el mismo índice en `__table_args__` de `NmTeamUser`, con su equivalente en SQLite. Sin tablas ni columnas nuevas. Excepción puntual, autorizada por Aurora a la regla de «sin índices ni migraciones»; **pendiente de comentar con Alan**. Para revertirla: restaurar el constraint, lo que vuelve a prohibir la alta repetida.

| Umbral | Valor |
|---|---|
| «En turno» | checada abierta con **menos** de 12 h (`UMBRAL_SIN_SALIDA_HORAS`) |
| «Sin salida» | checada abierta con 12 h **exactas** o más |
| «Duración anómala» | checada **cerrada** con **más de** 16 h entre entrada y salida (`TOPE_DURACION_CHECADA_HORAS`); 16 h exactas **no** lo es |

**Abierta** = sin `close_date`, tenga el estatus que tenga: una `en_proceso` cuenta como abierta. **Reabrir** (`resuelta → en_proceso`) borra el `close_date` y **conserva la entrada original**.

| KPI | Dimensión · día | Frescura |
|---|---|---|
| `checadas_en_turno_por_equipo`, `checadas_sin_salida_por_equipo` | `equipo` · foto de hoy | cada 5 min, por clave (`KPIS_FRECUENTES`) |
| `checadas_entradas_por_equipo` | `equipo` · `date(incident_date)` | cada 5 min, solo las filas de hoy; el resto de los días, la corrida nocturna |
| `checadas_salidas_por_equipo` | `equipo` · `date(close_date)` | ídem |
| `checadas_en_turno_por_empleado` | `empleado` · foto de hoy (minutos); `ocultar_ceros`: la API omite a quien ya salió | cada 5 min, por clave |
| `horas_trabajadas_por_empleado` | `empleado` · `date(incident_date)` (día de la **entrada**); excluye las de más de 16 h | solo la corrida nocturna (ventana de 7 días) |
| `checadas_con_duracion_anomala` | `empleado` · `date(close_date)` (día de la **salida**); cuenta las de más de 16 h | solo la corrida nocturna |

`KPIS_FRECUENTES` son las cinco claves de las filas «cada 5 min». «Corrida nocturna» = 01:00 **UTC** = 19:00 de México (`CELERY_TIMEZONE` vale `UTC` por omisión; ver `docs/arquitectura-kpis.md` §2.1.1).
Rendimiento medido con 50 000 checadas en una base aislada: una corrida completa de 5 minutos escribe 243 filas y tarda ~215 ms (SELECT 62 ms, upserts 37 ms); todas las consultas son `Seq Scan` de 4–7 ms sin índices por fecha
(detalle, planes y los índices candidatos —solo descritos— en `docs/arquitectura-kpis.md` §2.7).

Fuera de alcance, y por qué: «llegadas tarde» (no hay turnos, horarios ni descansos) y «marcas fuera de radio» (se pidió no implementarlo).

## 9. NO VERIFICADO

- Que `customer_supplier.creation_date` esté poblada en datos migrados de un
  sistema legado.
- Si `logistics_inventory_bridge` registra ajustes o conteos.
- Cómo se identifican en producción las facturas de logística (`source_module`,
  `logistics_file.id_invoice` o `logistics_receivable.id_invoice`).
- Ningún dato real de clientes: todas las tablas de restaurante y logística están
  vacías en la base local.
- Checadas: no hay ninguna en la base local (0 con coordenadas), así que el volumen y la calidad de los datos reales de Comala (si n8n
  manda siempre latitud, qué estado usa para la salida, si hay entradas duplicadas) no se pudieron comprobar. Las pruebas usan fixtures propias.
  La medición de rendimiento (2026-10-20) usó 50 000 checadas **sintéticas** en una base aislada; el volumen real de Comala sigue sin conocerse.
- Si el tope de 16 h es el correcto para los turnos reales de Comala: es una constante (`TOPE_DURACION_CHECADA_HORAS`), no un dato medido.
