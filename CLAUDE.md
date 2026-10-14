# Contexto de sesión — tyakxa_tny (para retomar en otra conversación)

Última actualización: 2026-10-05. Este archivo es el "dónde nos quedamos",
aparte de `ARQUITECTURA_TYAKXA_TNY.md` (referencia técnica estable) y de
`docs/PLAN_ACCION_MEJORA.md` (plan de mejora por auditoría). Cuando una
sección se resuelve, se puede recortar; mientras tanto se deja completa para
que una sesión nueva no tenga que releer el historial de chat.

## Bitacora 2026-10-13 — presupuesto de compras por proyecto y responsable del vale

**Presupuesto por proyecto** (`purchase_budget_service.py`, migracion `20261013100000`):
gerencia fija el tope (`PUT /purchase-budgets/<proyecto>`, permiso `purchase_policy`; Compras
solo consulta). Comprometido = ordenes por autorizar/autorizadas/compradas/recibidas/cerradas.
Una orden que haga pasar el tope queda `exceeds_budget` y va a autorizacion aunque este bajo
`authorize_above`; se reevalua al autorizar y exige nota; el autor no la libera. Sin
presupuesto = sin tope; moneda distinta = se trata como excedida. UI: panel
`PresupuestosDeCompra.jsx` en Ordenes de compra y tabla/aviso en el detalle de la orden.
**Vales**: al elegir proyecto el responsable es el supervisor de la obra; sin supervisor,
solo usuarios con rol Supervisor (se reconoce por el nombre del permiso: fragil si se
renombra el rol). `/user/options` trae `role`, `/proyect/options` trae `id_supervisor`.
Probado el ciclo de cada tipo (prestamo, reparacion, danado, destruccion, extraviado).

## Bitacora 2026-10-12 — auditoria de punta a punta (CRM, compras, operaciones, seguridad)

Cinco auditorias + dos de lo que quedo sin probar (timbrado/REP/cancelacion/notas de
credito/citas y flujos pendientes de compras). Usuario de prueba de Compras:
`backend/scripts/seed_usuario_compras.py` (compras1; la app solo acepta bcrypt).
Corregido, con pruebas: token de MFA a medias ya no es sesion; PAC `fake` rechazado con
`APP_ENV=production`; filtros/orden de listados solo sobre columnas reales (igualdad en
numeros); `stamp_invoice` no re-timbra con otra llave (`NO_SE_TIMBRA`); cancelar factura con
REP/nota de credito vivos da 409; total = subtotal - descuento + impuesto; abono en otra
moneda 409; conversion llena el receptor desde el cliente; citas: zona horaria y doble
reserva; CRM: RFC unico normalizado, tipo obligatorio, contactos validados; cotizacion
vacia no se envia; vales: cancelar (`POST /vouchers/<id>/cancel`), el responsable puede
verlos, baja sin fecha de regreso, responsable ya no se pisa con el Jefe de taller;
proyecto no se cierra/cancela con vales u ordenes vivas; tareas/bitacora no en proyectos
cerrados; compras: carrera de ordenes (bloqueo de necesidades), recepcion idempotente
(`idempotency_key` / cabecera `Idempotency-Key`), necesidad en orden viva no se edita ni se
devuelve, lo recibido sale de "por comprar", CFDI de orden cancelada reutilizable.

**Abierto (decision del equipo)**: recibir una orden NO da entrada al inventario (el codigo
dice que es a proposito); `APP_ENV` no esta fijado en k8s y la guarda de arranque falla
abierta; cuentas de dev con contrasenas debiles / init_test_data crea Administradores;
tokens de 8 h sin revocacion; contenedores como root, sin cabeceras de seguridad, imagenes
con CVEs por version; migraciones sin candado y 36 sin `ajustado_por_gestor`; vale de
reparacion deja la pieza "prestada"; `/assets/overdue` vs vales; pagos sobre factura sin
timbrar; ledger sin asiento de apertura (2201 productos); `nm_incident_product.status`
siempre 'disponible'; dos columnas de estado de proyecto que se contradicen; 9 `id_*` sin FK
y 84 FKs sin indice; tickets sin vinculo a cliente/proyecto; `user.id_proyect`/`supervisor`
NOT NULL heredados. Datos `AUD-*`/`AUD2-*`/`QAOPS-*`/`QAINV-*` quedaron en dev (limpiar con
script con --dry-run).

## Bitacora 2026-10-09 — vales: un solo flujo, tipos por rol, apartado vs fuera

Probado en navegador con almacen, supervisor (angelito) y jefe de taller, mas dos
barridos de API (inventario completo y proyectos/tareas, con usuarios de prueba
`QAINV-*`/`QAOPS-*` que quedaron en la base de desarrollo).

- **Flujo del vale (un solo camino).** Supervisor levanta prevale (borrador) ->
  Almacen autoriza (`en_espera`: el material queda APARTADO, no sale) ->
  Almacen "Marcar entregado" (`entregar_vale`: aqui sale del almacen, `en_transito`)
  -> el responsable "Confirmar que lo recibi" (`confirmar_recibido_del_vale`, `abierto`).
  Se retiraron las rutas paralelas `mark-as-shipped` y `confirm-supervision-receipt`
  (el supervisor no podia confirmar: exigian `warehouse_voucher_authorize`).
- **Tipos por rol, una regla** (`_prefijos_de_tipo_permitidos`): Gerencia
  (`project_authorization`) y admin todos; Almacen solo herramienta (prestamo,
  reparacion, danado, destruccion, extraviado); Supervisor solo prevales de prestamo,
  danado, extraviado y reparacion. El selector la usa: `/incident_type/options?para=vale`.
- **Apartado no es fuera.** Prevale/en espera no cuentan en Localizar, resumen del
  proyecto ni pantalla del vale. Lo fungible apartado se resta (`apartado_por_sitio`,
  `reserved`/`available` en Localizar): dos prevales ya no piden la misma unica unidad.
- **El aviso de autorizado nunca llegaba**: `notification_type_check` no traia
  `warehouse_voucher_prevoucher_authorized` ni `_return_pending` y el `except: pass`
  lo tragaba. Siguen en la migracion unica `20261007100000`. Si se agrega un tipo,
  agregarlo ahi y probar la insercion contra Postgres real, no SQLite.
- **Piezas**: el signo del movimiento sale de entrar/salir del saldo
  (`ESTADOS_EN_SALDO` = disponible + en_uso), no del nombre del evento.
- **Operaciones**: entradas invalidas ya dan 4xx (manejadores globales en
  `__init__.py`); Jefe de taller solo escribe tareas/notas de proyectos que tomo;
  un proyecto sin maquila ya no entra a "espera de material".
- **Sin decidir (preguntar a Alan/Tanya)**: `PUT /task` con `fase` reabre una tarea
  terminada (hay un comentario que dice que es a proposito); Supervisor puede
  escribir el catalogo `task_type`; `nm_template_task` acepta duplicados; catalogos
  (marca, unidad...) aceptan nombres repetidos; el selector de proyecto de un vale
  tambien lista proyectos cancelados.

## Reglas de trabajo — respetar la arquitectura, no parchar (pedido de Adser, 2026-10-07)

Aplican a toda sesión, humana o de IA.

1. **Primero entender cómo está resuelto hoy.** Antes de escribir código,
   buscar el mecanismo que ya existe para ese problema (servicio, registro de
   módulos, libro de inventario, gestor de permisos, `/options`, etc.) y
   usarlo. `ARQUITECTURA_TYAKXA_TNY.md` es la referencia.
2. **Causa raíz, no síntoma.** Si algo "no se ve" o "no cuadra", encontrar por
   qué antes de taparlo. Ejemplo real: "los materiales de Oscar no los ven los
   demás" parecía un permiso del Gestor y era un selector que solo cargaba la
   primera página.
3. **Una sola fuente por regla.** Una regla de negocio se define en un lugar y
   los demás la consumen; no se copia por pantalla. Ejemplo:
   `backend/app/utils/product_description.py` es la regla de la descripción de
   producto (el espejo en `frontend/src/utils/productDescription.js` se
   mantiene igual y se prueba con los mismos casos). La existencia se mueve
   por entrada, vale o ajuste, nunca escribiendo `product.cantidad`.
4. **Nada de atajos silenciosos:** no saltarse permisos, validaciones o el
   libro de movimientos para que algo "funcione"; no editar datos a mano en
   un ambiente sin dejar un script con `--dry-run` y respaldo.
5. **Si de verdad hay que cambiar la arquitectura, se habla con el equipo
   antes** (Alan, Tanya, Ángel). Se propone, se explica el porqué y las
   alternativas, y se espera el acuerdo; no se decide dentro de una tarea
   puntual.
6. **Dejar lo hecho verificable:** pruebas del comportamiento nuevo y suite
   completa en verde antes del push.

## ESTADO ACTUAL de `initAlan` (verificado 2026-10-02) — leer esto primero

`initAlan` es la rama que importa. Las bitácoras de abajo, hasta la de
"Plantilla del PDF de vale", están escritas desde `initAngm` (Ángel) y
conservan su texto original; donde dicen "falta mergear" o "sin desplegar" ya
no es cierto (ver "Superado"). Verificado con git, no de memoria.

**Estado de la rama.** `origin/initAngm` está contenida por completo en
`initAlan` (0 commits de Ángel sin traer; `initAlan` lleva 104 por delante).
Local y `origin/initAlan` iguales tras fast-forward (los últimos commits son
del bot de CD y de Aurora: orden de la tabla de material prestado).

**Imagen que dicen los overlays del repo** (no se consultó el clúster; antes de
afirmar qué corre en vivo, `kubectl get deploy -o wide`):

| Overlay | Tag |
|---|---|
| tyakxa-dev | `e19f3db` (auto-deploy de `initAlan`) |
| adser-prod | `c260f22` (séptima promoción manual) |
| torredigital-prod | `031970b` |
| vidrioyaluminios-prod | `abf0929` |

adser-prod va unos commits atrás de tyakxa-dev (dashboard de material
prestado de Aurora, aún sin promover). torredigital-prod y
vidrioyaluminios-prod llevan semanas sin promoción.

### Pendientes REALES (confirmados abiertos en `initAlan`)

1. **Notificaciones con deep-link** — sin una línea de código
   (`target_entity`/`destinoDeNotificacion` no existen). Diseño en memoria
   `project_tyakxa_tny_notificaciones_deeplink_pendiente`. Faltan dos
   decisiones de Alan: ¿abrir marca como leída? (recomendado: no) y ¿qué otros
   módulos notifican (vales, tareas, incidencias, citas)? Hoy el único
   productor es `_notificar_proyecto`, más los avisos de revisión de datos de
   Adser (`0f8c696`).
2. **Avisos de revisión de datos a `yesgo` (Adser)** — paso 6 de la promoción,
   espera el OK de Alan (`docs/despliegues/2026-09-30_avisos_revision_datos_adser.md`).
3. **KPI `piezas_por_estado`** — construido, NO validado con datos reales ni
   puesto en perfil/plantilla; no mostrar a Adser hasta conciliar contra
   tyakxa-dev con `conciliar_piezas_por_estado.sql/.py`
   (`docs/despliegues/2026-10-01_piezas_por_estado.md`).
4. **Dashboard de Adser:** falta confirmar `incident_date` como fecha
   confiable; hasta entonces la plantilla se corre con `--sin-tabla`.
   (Lo de `creation_date` ya está resuelto, ver "Superado".)
5. **Conciliación de inventario:** `sembrar_existencia_inicial` no escribe
   renglón de apertura en el libro y `reconcile_product_stock` lo exige;
   decisión de diseño pendiente (hallazgo de Aurora).
6. **Pruebas faltantes de maquila/custodia** — no hay ninguna para
   `requires_maquila`, `asignar_entrega_de_renglon` ni
   `confirmar_recepcion_de_renglon`; `validate_project_transition` solo tiene
   las de antes de la maquila. Escribirlas antes de tocar ese frente.
7. **Constraint `proyect_event_event_type_check`** sigue repetido en 4
   migraciones (`20260911180000`, `20260918130000`, `20260921100000`,
   `20260924190000`); al crecer la lista hay que tocar las CUATRO. Colapsar en
   una fuente de verdad sigue pendiente.
8. **Fase 2 de permisos** (filtrado real por Propios / Mis grupos / Todos):
   sin empezar. `_has_entity_permission` (`utils/auth.py`) sigue booleano
   (`scope != 0`); `incident_service`, `inventory_service` y
   `project_management_service` también leen `scope_read != 0`. Los filtros por
   dueño que existen (proyectos, vales, facturas) son ad hoc, no vienen del
   alcance.
9. **`LICENSED_MODULES`:** ningún overlay lo fija (la variable solo se lee
   opcional desde `app-secrets`). adser-prod: diferido por instrucción de Alan.
   torredigital-prod: política sin decidir. Rediseño central que propone Tanya
   sin empezar; no romper `multiemisor_csd`/`licencia_independiente`.
10. **Otros abiertos de menor peso:** CPU del clúster con reserva >90% (uso
    real 20-40%); `LICENSED_MODULES`/multiemisor de vidrioyaluminios sin
    decidir; traducciones pt/de apenas con corrección mínima.

### Superado (no volver a abrir)

- **`initAngm` "falta mergear a `initAlan`"**: ya mergeada completa.
- **`creation_date` de `incident`/`nm_incident_product` sin default**: migración
  `20260929110000` (DEFAULT now()) + `fix_adser_creation_date.py` de relleno
  (`docs/despliegues/2026-09-29_creation_date_de_vales.md`). La decisión de
  Alan ya se tomó. No verifiqué si el relleno se corrió en adser-prod: revisar
  `2026-09-25_kpis_adser_permisos.md` §3 antes de afirmarlo.
- **`sync_fields.sql` roto (tabla `field` vacía)**: `init_db.py` ahora siembra
  el catálogo desde los modelos (`scripts/sync_field_catalog.py`), idempotente
  en cada arranque.
- **`database/seed.sql` falla en volumen limpio**: el demo de restaurante ya
  corre solo si sus tablas existen.
- **REP (Fase 3 de facturación)**: ya commiteado (`fb4448c`) y en la rama; el
  "Falta commitear" del texto de la Fase 3 es viejo.
- **Maquila, custodia por renglón, tomar/soltar proyecto, Bitácora diaria,
  PDF del vale idéntico al anterior**: están en `initAlan` y en la imagen de
  adser-prod (`c260f22` contiene la punta de `initAngm`). torredigital-prod
  (`031970b`) NO los incluye.
## Bitácora 2026-10-05 (continuación) — merge de initAlan (129 commits) + flujo de entrega validado

**Merge de `origin/initAlan` a `initAngm`**, commit `309f32e` — sin
conflictos de código real (ni siquiera `CLAUDE.md` esta vez). Trae,
entre otras cosas, un cambio arquitectónico grande:
**`20260816000000_el_gestor_manda_sobre_las_migraciones.sql`** — un
trigger (`trg_gestor_manda`) que impide que las migraciones (que se
reaplican TODAS en cada arranque, sin tabla de control) reviertan lo
que un administrador ya ajustó a mano en el Gestor de roles y permisos.
Antes de este trigger, cada promoción deshacía silenciosamente esos
ajustes — medido en `adser-prod` el 2026-10-02 (reescribió 5 grupos de
`entity_permission` y 176 de `nm_field_permission` en una sola pasada).
Detalle completo en `docs/despliegues/2026-10-02_el_gestor_manda_sobre_las_migraciones.md`.

**Hallazgo real propio, corregido** (commit `9687325`): mi migración
`20260930090000_bitacora_diaria_entra_al_menu.sql` hace un `UPDATE
entity_permission` sin fijar `ajustado_por_gestor`. Como esa migración
es de fecha POSTERIOR a la del trigger, en una base que YA está en uso
y que nunca ha corrido ninguna de las dos (torredigital-prod,
adser-prod — "semanas sin promover") el trigger congelaría la fila
primero, dejando mi `UPDATE` descartado en silencio para siempre. Se
agregó `ajustado_por_gestor = now()` al `SET`. En tyakxa-dev no cambia
nada (la fila ya tenía el menú correcto). **Ojo para la próxima vez que
se promueva esta rama a esos dos ambientes**: por las fechas de archivo,
CUALQUIER migración entre `20260816000000` y la fecha de la última
promoción real de esos ambientes que haga `UPDATE`/`DELETE` sobre
`entity_permission`/`nm_field_permission` sin fijar esa columna corre
el mismo riesgo — no se auditaron las demás (quedan fuera del alcance
de esta sesión, y la mayoría son de antes del commit `9687325`, ya
aplicadas con éxito en tyakxa-dev).

Verificado con `docker compose up -d db-migrate`: `esquema al dia`, sin
error. Suite completa: **1583 passed, 0 failed, 188 skipped** (las KPI
de Postgres se saltan bajo SQLite por diseño, ver `backend/tests/README.md`
y `backend/ci/run_postgres_tests.sh` — no se corrieron en esta sesión,
quedó pendiente si se quiere verificar esa parte en detalle).

**Pregunta de negocio resuelta sin tocar código** (Tania, vía el
usuario): el flujo de "solicitud adicional dentro del mismo proyecto,
recogida por un externo sin acceso al sistema" **ya funciona con lo
construido el 2026-09-30** (maquila/entrega de herramienta) — no hacía
falta ninguna función nueva. El flujo operativo correcto: el vale se
levanta normal (responsable = el propio supervisor, sin tocarlo);
**almacén** (que siempre puede gestionar la custodia de cualquier vale)
marca "Entregar a" = el externo al momento de surtir; cuando el externo
le entrega la herramienta al supervisor en planta, **el supervisor** ve
y usa "Confirmar recepción" automáticamente, porque sigue siendo el
responsable del vale. Verificado de punta a punta en navegador real
(vale #144): `POST /prevouchers` 201 → `POST /vouchers/144/authorize`
200 → `POST /vouchers/lines/2793/deliver-to` 200 (por almacén) →
`POST /vouchers/lines/2793/confirm-custody` 200 (por el supervisor) →
"Recuperado de Roberto Cisneros" visible en el vale.

**Corrección a la nota anterior** (de un borrador de esta misma entrada):
los 3 archivos con el fix del selector de marca (`MaterialPage.jsx`,
`ProductPage.jsx`, `ServicePage.jsx`) que en un momento parecieron
"de origen desconocido" en el working tree ya estaban commiteados y
pusheados a `origin/initAngm` como `3df49d9` ("fix(marcas): el selector
de marca en Material/Producto/Servicio ya trae el catalogo completo")
antes de que esta sesión terminara de revisarlos — probablemente de un
tick autónomo anterior de esta misma sesión, resumido fuera del
contexto visible. Nada quedó sin commitear; `git push` confirmó
"Everything up-to-date".

## Bitácora 2026-10-05 — el prevale puede quedar a nombre de otro operador

Pedido: una vez levantado el proyecto, poder generar un vale a nombre de
alguien distinto del supervisor -- el supervisor no siempre puede salir
de planta, y manda a un operador por la herramienta. Commit `93427c0`.

El "Responsable" del prevale era FIJO en el frontend (siempre el
supervisor que lo captura, sin selector) -- una regla de UI, no del
backend: `crear_vale` nunca exigio que `id_user` fuera el actor, acepta
cualquier usuario valido. Se quito el candado: el campo sigue
precargado con el actor (con "(tú)" junto a su nombre), pero ahora es
el mismo desplegable que ya usaba Almacenista. Quien CAPTURA el
prevale (`created_by`) no cambia; solo el responsable ante almacen
-quien firma y quien debe devolverlo- puede ser otra persona.

Probado en navegador real como Supervisor (`vicgo`): prevale creado a
nombre del operador Roberto Cisneros -- `POST /prevouchers` 201,
verificado en la respuesta que `created_by` sigue siendo vicgo (56)
pero `id_user` es el operador elegido (81).

## Bitácora 2026-09-30 (continuación) — plantilla del PDF de vale igual a la del sistema anterior

Pedido: rehacer el PDF del vale de almacén para que sea idéntico al del
sistema anterior (se dio una foto de un vale impreso real como
referencia). Commit `e27125e`.

Se reemplazó por completo `documents-reports/templates/warehouse_voucher.html`:
caja de firmas Entregado/Recibido Almacén/Personal, línea de
identificación (ID Incidente/ID Vale/Responsable/Fecha), Nota,
Descripción (el CLIENTE de la obra, no la descripción del proyecto —
confirmado comparando contra el papel de referencia, que mostraba un
nombre de empresa ahí) y la tabla de renglones con las columnas
#/IDdb/Código/Descripción/Tipo/Cantidad/Precio Bruto/Recibido Sello y
Firma. Todo duplicado dos veces en la misma hoja (copia Almacén / copia
Personal), igual que el papel de referencia.

**Dos bugs reales encontrados de paso, sin cobertura de pruebas
previa** (nadie probaba el CONTENIDO de `documento_del_vale`, solo que
el PDF se archivara):
- El código de producto se leía de una llave que el helper de fichas de
  producto nunca publica (`code` en vez de `product_code`) — la
  columna "Código" salía SIEMPRE vacía en el PDF, para cualquier vale.
- El precio bruto (campo nuevo de esta plantilla) viajaba como
  `Decimal` crudo hacia la ficha que se archiva como JSON junto con la
  versión del documento — tronaba con `TypeError` al archivar
  CUALQUIER vale cuyo producto tuviera precio capturado. Detectado
  corriendo la suite completa, no al escribir el código.

Verificado generando PDFs reales (no con datos mockeados) contra dos
vales reales de la base: uno sin proyecto (Descripción en blanco) y uno
con proyecto/cliente ligado (Descripción: "BMW Manufacturing de Mexico
SA de CV", igual al "APELSA" del papel de referencia). Sin LibreOffice
ni poppler instalados en este Windows local, así que la verificación
visual se hizo leyendo el PDF directamente (el propio Read del agente
sabe renderizar PDF), no con el `soffice.py`/`pdftoppm` que sugiere el
skill de docx (pensado para macOS/Linux).

## Bitácora 2026-09-30 (continuación) — prueba del flujo completo con Jefe de taller

Pedido: probar en navegador el flujo de proyectos con Jefe de taller
también (tras el punto de maquila/custodia de arriba). Se destapó un bug
real preexistente, no introducido en esta sesión: **`take_project`/
`release_project` (backend) y sus clientes de API (`takeProyect`/
`releaseProyect`) existían, pero ningún botón de `ProjectManagementPage.jsx`
los llamaba** — código muerto del lado del cliente. Jefe de taller no
tenía NINGUNA forma de tomar un proyecto libre desde el navegador, solo
vía script directo al backend (que es como se probó el flujo en sesiones
anteriores, sin darse cuenta de que la UI real no lo ofrecía).

Corregido: dos botones nuevos en `ProjectActions` — "Tomar proyecto"
(modo taller, cuando el proyecto sigue sin supervisor) y "Soltar
proyecto" (para quien ya lo tiene). Commit `0429574`.

Ciclo completo probado en navegador real con clics reales, con un
proyecto que SÍ requiere maquila: Jefe de taller toma → Gerente autoriza
→ espera de material → Jefe de taller crea una tarea → Gerente pasa a en
proceso → Jefe de taller cierra la tarea → Jefe de taller completa el
proyecto. Las 6 acciones con 200/201 real. También confirmado de nuevo
que el proyecto sin maquila (de la sección de arriba) sigue sin aparecer
en ninguna columna del tablero de Jefe de taller, incluida "Completado".

## Bitácora 2026-09-29 — QA de cotización/factura, alta de proyectos, alta de cliente

Pedido: revisar y probar (1) el flujo cotización→factura con fechas
correctas y el estatus "pendiente" (Facturama en modo pruebas, no
producción), (2) el flujo completo de creación de proyectos, anotando
inconsistencias, y (3) qué campos del alta de cliente/empresa son
realmente necesarios — quitar los que no, u ocultarlos si rompen tablas.
Se probó vía API (scripts dentro del contenedor) y también en navegador
real. 3 bugs reales encontrados y corregidos, commiteados y pusheados a
`initAngm`.

1. **IVA perdido al convertir cotización → factura.** `calculate_totals()`
   ignoraba `tax_applicable`/`line_tax`/`tax_rate` de cada renglón y
   recalculaba todo desde un solo `tax_rate` de cabecera — si ese campo
   de cabecera venía vacío (no es obligatorio), la factura convertida
   salía con IVA en $0 aunque la cotización sí lo hubiera capturado por
   renglón. Nueva función
   [totals_from_priced_lines()](backend/app/services/quotation_service.py)
   que respeta el impuesto de cada renglón, con `calculate_totals()`
   intacta para no arriesgar otros llamadores. Verificado con una
   cotización de prueba (renglón con `line_tax=1600.00`, sin `tax_rate`
   de cabecera): antes convertía a `tax: 0, total: 10000`; después,
   `tax: 1600.0, total: 11600.0`.
2. **`date_emision` de la factura se congelaba en la fecha de captura de
   la cotización.** Una cotización de 20 días de antigüedad se convertía
   en factura con esa misma fecha vieja — riesgo real de cumplimiento SAT
   (el CFDI debe timbrarse cerca de la fecha real). Se agrega
   `date_emision: datetime.utcnow()` al payload de
   [convert_quotation_invoice()](backend/app/routes/invoice.py).
   `date_expiration` se deja intacto a propósito (significado distinto
   después de convertir). Verificado: cotización con `date_emision` de
   hace 20 días → factura convertida con la fecha real de conversión.
3. **Alta de proyecto rota con 500 para CUALQUIER usuario.**
   `psycopg2.errors.NotNullViolation` en `priority`. Causa raíz: una
   migración vieja (ya borrada del repo) había dejado `priority` y
   `total_cost` con `NOT NULL` real en la base; la migración de
   reemplazo de `initAlan` usa `ADD COLUMN IF NOT EXISTS` (no-op sobre
   columna ya existente), así que la restricción vieja sobrevivía en
   cualquier base que ya la hubiera corrido. Corregido con
   `ALTER COLUMN ... DROP NOT NULL/DROP DEFAULT` +
   `20260929090000_prioridad_y_costo_ya_no_obligatorios.sql`. Probado el
   ciclo de vida completo del proyecto (crear → autorizar/denegar/cancelar
   → tomar → tarea → completar → entregar) con los 4 roles operativos.
4. **Alta de cliente/empresa: campos capturables sin ningún consumidor
   real.** Auditoría (agente de exploración, citando archivo:línea de
   cada consumidor real) sobre `CustomerSupplierPage.jsx` encontró
   `title`, `last_fiscal_certification_date` y `logistics_notes` sin
   ningún lector en el resto del sistema — se quitaron del formulario.
   `sla_level`/`credit_limit` sí son NOT NULL con DEFAULT en la base pero
   tampoco los lee ningún módulo real (ni facturación/POS, que tiene su
   propio `credit_limit`, ni logística, que tiene su propio `sla_level`
   en `logistics_contract`) — se ocultan del formulario pero se mantiene
   su valor por omisión en `baseEmptyForm` para no romper el alta.

(Esta misma auditoría destapó, un día después, que el selector de
"Vendedor" del mismo formulario en realidad estaba roto para cualquiera
que no fuera Administrator — ver la entrada de abajo, punto 4.)

## Bitácora 2026-09-29/30 — visibilidad de taller, bitácora diaria, vale de Almacenista, Vendedor en Clientes

Cuatro correcciones reales sobre `initAngm`, cada una probada en navegador
real (no solo API), commiteadas y pusheadas.

1. **Jefe de taller veía proyectos ya tomados por OTRO Jefe de taller.**
   `_scoped_query()` (`project_management_service.py`, scope `"execution"`)
   filtraba solo por estatus de taller activo, sin mirar quién lo había
   tomado. Ahora solo muestra lo propio (`leader == actor` o
   `id_supervisor == actor`) o lo que sigue libre
   (`id_supervisor IS NULL`); lo tomado por otro Jefe de taller queda
   fuera. Probado con dos Jefes de taller reales (`jefetaller1`/`jefetaller2`).
   Efecto secundario de la prueba: un insert de ORM crudo para el segundo
   usuario de prueba desincronizó la secuencia de `user.id_user` y pisó al
   empleado migrado de Adser "ALFREDO GONZALEZ" (id=35) — restaurado a mano
   y secuencia resincronizada (`setval` al `MAX(id_user)` real). Cuidado al
   crear usuarios de prueba con `db.add(User(...))` en una base con IDs
   migrados explícitos (adser): la secuencia puede no reflejar el máximo
   real.

2. **Bitácora diaria de taller sin pantalla.** El backend
   (`activity_logs.py`) y el permiso (`daily_activity_log`) ya existían
   desde antes, pero sin entrada de menú (`menu="hidden"`) ni componente
   React — Jefe de taller no tenía cómo llegar a subir su bitácora. Se
   agregó [ActivityLogPage.jsx](frontend/src/pages/ActivityLogPage.jsx)
   (alta con proyecto propio tomado + plantilla de obreros vía
   `getMyTeamWorkers()`, y listado propio), ruta en `App.jsx`, entrada de
   menú en `Shell.jsx`, `menu="sidebar"` en `registry.py` y la migración
   `20260930090000_bitacora_diaria_entra_al_menu.sql` (UPDATE explícito,
   porque el sembrado con `ON CONFLICT DO NOTHING` no actualiza el menú de
   una fila de `entity_permission` que ya existía). Probado end-to-end como
   `jefetaller1`: alta con trabajador seleccionado, aparece en el listado.

3. **Almacenista no podía levantar vale.** El catálogo `incident_type`
   ("Tipo de vale") vive en el módulo `operaciones`, al que Almacenista no
   tiene acceso — el desplegable de tipo volvía 403 y el vale quedaba
   imposible de levantar aunque `warehouse_voucher` estuviera bien
   concedido. Se agregó un guardia nuevo en
   [incident_type.py](backend/app/routes/incident_type.py)
   (`_require_incident_type_read`) que deja leer el catálogo a quien
   administra `incident_type` de verdad O a quien solo necesita
   clasificar un vale/prevale (`warehouse_voucher`/`warehouse_prevoucher`),
   sin darle a Almacenista el módulo "operaciones" completo (eso le habría
   mostrado Proyectos/Tareas/Incidencias de más). Segundo hueco relacionado,
   a nivel de CAMPO: `nm_field_permission` se deriva de `entity_permission`,
   y Almacenista nunca tuvo fila para `incident_type` — la respuesta llegaba
   solo con el id, sin descripción, y el desplegable se veía vacío igual
   (`_actor_reads_incident_type_by_capability`). Probado en navegador real
   como Almacenista: `POST /vouchers` 201, vale abierto con su renglón.
   Supervisor confirmado sin cambios: solo ve "Levantar prevale", nunca
   "Abrir vale" — el diseño de separación de deberes ya era correcto.

4. **Alta de cliente: "Vendedor" obligatorio pero imposible de elegir fuera
   de Administrator.** El selector se poblaba con `getAllUser()` →
   `GET /user/`, que exige el permiso completo de RH (módulo "seguridad",
   solo Administrator). Gerente (que sí puede dar de alta clientes, `crm`
   en CAPTURA) se topaba con el desplegable vacío — un campo obligatorio
   que ningún rol de negocio real podía llenar. Cambiado a
   `getUserOptions()` → `GET /user/options` (mismo patrón id+nombre sin
   permiso de entidad que ya usa `WarehouseVoucherPage.jsx` para elegir
   responsable de un vale), y de paso precargado con el usuario actual
   (sigue editable) para que la mayoría de las altas no tengan que elegirlo
   a mano. Probado en navegador real como Gerente: 47 opciones,
   preseleccionado, `POST /customer_supplier/` 201.

Todo esto quedó en 2 commits sobre `initAngm`
(`2013b4c` visibilidad+bitácora, `6c59ab6` vale de Almacenista+Vendedor),
ya pusheados. (Al 2026-10-02 ya mergeado a `initAlan` y en adser-prod.)

### Merge de `initAlan` (87 commits) a `initAngm` local — 2026-09-30

`git merge origin/initAlan` sin conflictos de código real — solo
`CLAUDE.md` (resuelto conservando ambas bitácoras, la de esta rama y la
del frente de Dashboard/KPIs de Adser de abajo). Trae el dashboard en
masonry de Adser, la reconciliación de vales migrados, y varios fixes de
`alan lopez`/Aurora Rodríguez del 2026-09-29 (ver sus propios mensajes de
commit).

**Bug real destapado al reconstruir y levantar el stack completo**: el
`db-migrate` truena con
`CheckViolation: proyect_event_event_type_check` al toparse con un evento
`'taken'` real (de haber "tomado" un proyecto durante las pruebas de
`jefetaller1`/`jefetaller2` de la sección de arriba). Causa: dos
migraciones viejas (`20260911180000`, `20260921100000`) reaplican su
propio `DROP CONSTRAINT` + `ADD CONSTRAINT` en **cada arranque del pod**
(sin tabla de control, ver sección de "Ambiente de desarrollo" más abajo)
y cada una afirmaba en su propio comentario traer "la lista FINAL,
idéntica a las otras" — pero a ambas les faltaban `'taken'`/`'released'`
(agregados después por `20260918130000`). Como corren en orden por
fecha, revertían el constraint a una versión más angosta que la vigente
y tronaban contra cualquier base con un evento `'taken'` real —
**exactamente el mismo patrón de regresión que ya tumbó tyakxa-dev el
2026-09-24** (documentado en el propio comentario de
`20260924190000`), esta vez en dos migraciones más viejas que nadie
había vuelto a revisar. Corregido agregando `'taken', 'released'` a las
dos listas; confirmado con `docker compose up -d db-migrate` de nuevo
sobre el mismo volumen (sin `down -v`): `esquema al dia`, sin error.
Commit `bc2e965`.

**Lección para la próxima vez que la lista de `event_type` crezca**: hay
que actualizar las CUATRO migraciones que la reaplican
(`20260911180000`, `20260918130000`, `20260921100000`, `20260924190000`),
no solo la más nueva — este bug es la prueba de que "solo la más nueva"
no es seguro, porque las viejas se lo llevan por delante en cada
arranque igual. Vale la pena, en algún momento, colapsar las cuatro en
una sola fuente de verdad (o mover el constraint a la más nueva
únicamente y que las viejas dejen de tocarlo) — no se hizo en esta
sesión por no ser parte del pedido original.

### Segundo hallazgo del merge: dos arreglos distintos para el mismo bug

`incident_type` (mi fix de esta sesión, ver arriba) e `initAlan` (de forma
independiente) resolvieron el MISMO problema — Almacenista sin acceso al
catálogo de tipos de vale — con mecanismos distintos: yo con un guardia a
medida (`_require_incident_type_read`) que ampliaba `GET /incident_type/`;
initAlan con el patrón ya establecido `/incident_type/options` (igual que
`/user/options`/`/proyect/options` — id+descripción, sin permiso de
entidad). El merge combinó los dos SIN conflicto de texto (tocaban líneas
distintas del archivo), pero un test que llegó con initAlan
(`test_a_role_without_incident_type_permission_can_list_the_options`)
asume que `GET /incident_type/` sigue devolviendo 403 para ese rol — cosa
que mi guardia rompía. Se adoptó el patrón de initAlan (más consistente
con el resto del código) y se revirtió el mío por completo.

**Lección**: un merge sin conflicto de texto no es sinónimo de "sin
conflicto real" — correr la suite completa después de todo merge grande
es lo que lo destapa, no la ausencia de `<<<<<<<`.

## Bitácora 2026-09-30 — maquila opcional + entrega de herramienta por operador

Pedido de negocio nuevo, 5 puntos, todos entregados y probados en
navegador real (commit `d7bdc6a`, sobre `initAngm`):

1. Checkbox "Requiere maquila" al crear/editar proyecto
   (`proyect.requires_maquila`, default `true` — compatible con lo
   existente).
2. Un proyecto sin maquila (pinturas, drenaje, cimientos): Gerente lo
   autoriza igual, y en cuanto el supervisor avisa que ya no falta nada
   lo completa DIRECTO desde "autorizado" — sin pasar por "en espera de
   material"/"en proceso" (pasos pensados para cuando el taller sí
   participa). `validate_project_transition()`/`transition_project()`
   en `project_management_service.py`.
3. Ya aparecía en el selector de proyecto del vale/prevale sin ningún
   cambio — `project_options()` nunca filtró por estatus.
4. El estado "completado" ya existía; y la visualización de material
   asignado/sin devolver (`material_summary`) también — ambas
   confirmadas, ninguna se tocó.
5. A qué operador u otro supervisor se le entrega la herramienta de un
   renglón del vale, y confirmación de que el supervisor dueño del vale
   la recuperó — **por renglón**, no por vale completo. Columnas nuevas
   `nm_incident_product.id_user_delivered_to`/`custody_confirmed_date`;
   rutas `POST /vouchers/lines/<id>/deliver-to` y `/confirm-custody`,
   candado propio (`_puede_gestionar_custodia`: el responsable del vale
   — normalmente Supervisor, que nunca tiene `warehouse_voucher` — o
   quien opera el almacén). Paso INTERMEDIO: la pieza sigue "fuera"
   hasta la devolución real (`close_date`, sin tocar).

Hallazgo lateral: Jefe de taller ya no ve un proyecto sin maquila en
absoluto (mismo `_scoped_query` de la corrección del 2026-09-29) — nunca
le toca, ni para tomarlo.

(Al 2026-10-02 ya mergeado a `initAlan` y en adser-prod.) Sin pruebas automatizadas
nuevas para esta entrega — solo verificación manual en navegador; si se
retoma este frente, vale la pena escribir los casos de
`validate_project_transition`/`asignar_entrega_de_renglon`/
`confirmar_recepcion_de_renglon` antes de tocarlo de nuevo.

## ESTADO: Dashboard y KPIs de Adser (2026-09-29) — frente actual

Entrega a Adser. Rama `initAlan`; los commits de esta línea se prueban en
local y NO se pushean hasta que Aurora los revise en el navegador.

- **Registry** (`backend/app/kpis/registry.py`): cada KPI declara dirección
  (alto/bajo es mejor), gráficas permitidas, unidad, `modo` y, si aplica,
  `colores_categoria`. `GET /kpi_definition/` los expone al Dashboard. Las
  filas de `kpi_definition` no vienen de una migración: `init_db.py` llama a
  `seed_kpi_definitions()` en cada arranque (una fila por KPI del registry).
- **Modo `snapshot` vs `vivo`**: `snapshot` se calcula por entidad-y-día
  (job `tasks_kpis.py`); `vivo` (ej. `material_prestado_actual`) es una
  consulta paginada "ahora" que el job se salta a propósito. Su widget es de
  tipo `tabla` (el backend lo acepta desde esta línea).
- **Fechas de Adser**: `incident.creation_date` viene NULL en lo migrado;
  los KPIs de incidencias usan `incident_date`. Decisión pendiente de Alan
  en `docs/2026-09-28_creation_date_sin_default_en_incident.md`.
- **Frontend**: la lógica pura del Dashboard vive en `frontend/src/kpi/`
  (no en `src/lib/`: el `.gitignore` de Python ignora cualquier `lib/`) y se
  prueba con `npm test` (node --test, sin dependencias). Cada tarjeta se
  pinta con el mapa `tipo_grafica → componente` de
  `components/kpi-widgets/tipoGraficaComponentes.js`. Un widget guarda
  `parametros.rango_relativo` además de sus fechas absolutas (aditivo).
- **Pruebas**: las de KPI solo corren en Postgres (en SQLite se saltan sin
  avisar): `backend/ci/run_postgres_tests.sh -k kpi` con el stack arriba.
  Detalle en `backend/tests/README.md`.
- **Despliegue**: pasos por cambio en `docs/despliegues/` (ej.
  `2026-09-25_kpis_adser_permisos.md`, `2026-09-25_kpi_agregacion.md`);
  procedimiento general en `ARQUITECTURA_TYAKXA_TNY.md` §7.1.
- **Vista previa aislada**: `/dashboard-preview` (datos demo); sus
  componentes viven en `frontend/src/components/kpi-widgets/`.
- **Plantilla del tablero de Adser**: `backend/scripts/seed_kpi_dashboard_template.py`
  (5 widgets para `taroj`: número de pendientes hoy contra hace 30 días, barras
  abiertas vs. cerradas y barras abiertas por responsable, ambas "este año" —el
  último vale migrado es del 15 de agosto—, tabla
  de material prestado —KPI en vivo, sin rango— y dona de material por estado
  hoy; `--dry-run`, `--sin-tabla`, idempotente; pasos en
  `docs/despliegues/2026-09-29_kpis_dashboard_adser.md`). **No correr la tabla en
  `adser-prod` hasta que Alan confirme que `incident_date` es confiable**
  (consulta de solo lectura); mientras, `--sin-tabla`.
- **Pendiente**: confirmación de Alan sobre `incident_date` (lo de
  `creation_date` se resolvió, ver ESTADO ACTUAL); correr la plantilla en
  `adser-prod` (aún no).

## ESTADO: alcance por acción en permisos + equipos de usuarios — Fase 1 (2026-09-14)

Contexto: se pidió reemplazar las 4 casillas booleanas del gestor de roles y
permisos (Crear/Leer/Actualizar/Eliminar) por un **alcance** de 4 niveles
(Sin acceso=0, Propios=1, Mis grupos=2, Todos=4), y crear una entidad nueva de
**equipo de usuarios** (`Team`/`NmTeamUser`) — sin confundirla con la columna
`entity_permission.menu_group`, que solo agrupa visualmente el menú.

**Hallazgo clave antes de diseñar nada**: hoy NO existían 4 casillas
booleanas como columnas — existía una sola `entity_permission.control_type`
(máscara de bits: CREAR=1, LEER=2, ACTUALIZAR=4, ELIMINAR=8), y el "alcance"
real (propios/todos) no estaba conectado a `entity_permission` en absoluto:
existían dos mecanismos ad hoc distintos (`project_management_service`
por proyecto/líder, `invoice_service` por igualdad estricta de `id_proyect`
del JWT). Por eso, junto con el usuario, se decidió una entrega **por
fases**:

- **Fase 1 (esta, completa)**: esquema nuevo (4 columnas de alcance en vez de
  `control_type`), entidad `Team`/`NmTeamUser`, migración de datos existentes,
  UI del gestor de roles y del gestor de equipos, pruebas. El guardia
  (`require_entity_permission`) sigue siendo booleano: `0` deniega, cualquier
  otro valor permite — **no hay filtrado real por Propios/Mis grupos/Todos
  todavía**.
- **Fase 2 (sin empezar)**: conectar el alcance a un filtrado real de
  consultas, módulo por módulo, reusando el filtrado por proyecto donde ya
  exista noción de dueño y tratando "Propios" como "Todos" donde no exista
  (catálogos sin dueño). Incluye las pruebas de "un usuario en varios grupos"
  que en un principio se pidieron para esta entrega y no se pudieron escribir
  de verdad todavía.

### Qué se hizo

1. Migración `database/migrations/20260914110000_equipos_y_alcance_por_accion.sql`:
   crea `team`/`nm_team_user`, agrega `scope_create/read/update/delete` a
   `entity_permission`, migra los datos existentes (bit encendido → Todos=4,
   apagado → Sin acceso=0) y elimina `control_type`.
2. Backend: modelo `EntityPermission` actualizado; modelos/servicios/rutas
   nuevos para `Team`/`NmTeamUser` (mismo patrón que `department.py`/
   `nm_field_permission.py`); `app/utils/auth.py` (el guardia REAL — no
   `app/security/permissions.py`, que resultó ser código muerto sin usar por
   ninguna ruta) reescrito para leer las 4 columnas; `registry.py` y
   `seed_module_permissions.py` adaptados (las definiciones de `ROLES` no
   cambiaron, solo la emisión final); `team`/`nm_team_user` agregados al
   módulo `seguridad`. `database/seed.sql` e `init_db.py` (bootstrap de
   instalación nueva) también corregidos — tenían su propia copia de la
   lógica de siembra.
3. **Bug real encontrado y corregido, no introducido por esta migración pero
   destapado por ella**: `incident_service.py`, `project_management_service.py`
   e `inventory_service.py` leían `record.control_type` directamente (bypass
   del guardia central) para permisos de capacidad (supervisión de
   incidencias, autorización/ejecución de proyectos, ajuste de inventario).
   Sin este fix habrían quedado con un `AttributeError` real (confirmado
   corriendo la suite completa), no un simple 403.
4. Frontend: `RolePermissionManagerPage.jsx` reescrito (4 selects con punto
   de color por acción, igual que el mockup); `TeamManagerPage.jsx` nuevo
   (alta/edición de equipos + agregar/quitar miembros); **se encontraron y
   corrigieron ~50 archivos más** que leían `entity_permission.control_type`
   del lado del cliente y se habrían roto en silencio: los ~46
   `pages/*Page.jsx` genéricos (gate de crear/editar/borrar), y — más grave
   todavía — `Shell.jsx` (arma el menú lateral completo a partir de esas
   filas) y `App.jsx` (`RoleAccessRoute`, la guarda de casi todas las rutas).
   Sin corregir estos dos últimos, el menú lateral se habría quedado vacío y
   ninguna ruta protegida habría abierto para nadie que no fuera bootstrap.
5. Documentación: este archivo y `ARQUITECTURA_TYAKXA_TNY.md` (sección 3.5 y
   tablas de entidades/blueprints) actualizados con el modelo de alcance
   nuevo y la advertencia explícita de que el filtrado real es Fase 2.

### Hallazgo importante sobre cómo corren las migraciones de verdad

`backend/scripts/apply_migrations.py` (con su tabla `schema_migration` y
verificación por checksum) **no es el mecanismo que realmente aplica las
migraciones**, ni en `docker-compose.yml` ni en k8s
(`k8s/base/backend.yaml`). Ambos usan el mismo bucle de shell:
`for f in /migrations/*.sql; do psql -f "$f"; done` — **sin ninguna tabla de
control**. Esto corre completo en cada arranque de contenedor/pod, para
siempre. La consecuencia real: **toda migración debe tolerar ejecutarse
infinitas veces**, no solo una — no es un detalle de estilo, es el
mecanismo real de producción. Se confirmó de la forma dura: un `DROP COLUMN
control_type` en la migración de esta sesión rompió una migración de
2026-08-22 que copiaba ese valor sin guardas — funcionaba en el primer
arranque (la columna todavía existía) y tronaba desde el segundo en
adelante. Hubo que corregir esa migración vieja también (no solo la nueva),
algo que en un principio parecía prohibido asumiendo que
`apply_migrations.py` protegía con checksums — no es así, ese script parece
no estar conectado a ningún lado real. Si se vuelve a tocar una columna que
otra migración ya referencia sin guardas, hay que repetir esta comprobación:
`docker compose down -v`, levantar y correr `db-migrate` DOS veces seguidas
desde cero — la primera pasada sola no destapa el problema.

### Explícitamente diferido / sin resolver

- **Fase 2 completa** (filtrado real por Propios/Mis grupos/Todos, módulo por
  módulo) — no iniciada.
- Ningún ambiente real (`tyakxa-dev`/`torredigital-prod`/`adser-prod`/
  `vidrioyaluminios-prod`) tiene equipos con miembros todavía — la tabla nace
  vacía, se puebla a mano desde `/team` cuando se decida usarla.
- No se tocó la promoción de overlays de los 3 clientes reales — esta
  migración se despliega primero a `tyakxa-dev` (auto-deploy de `initAlan`)
  y se valida ahí antes de promover manualmente.
- Traducciones (i18n) completas solo en español; inglés con las etiquetas
  principales corregidas, portugués/alemán con corrección mínima (fallback
  legible, no roto, pero no tan pulido como el español).

## ESTADO: migración real de adser completada (2026-09-07)

Contexto: adser es un cliente real (`adser-prod`, dominio
`adser.torredigital.mx`) cuyos datos viven en una base MySQL/MariaDB legacy
separada del clúster. Hay que migrarlos a la base Postgres de tyakxa_tny sin
tocar producción a ciegas.

**Principio acordado con Alan, palabras textuales:** *"pasar todo tal cual
hasta con sus id ya que no queremos mover o afectar nada de producción"* —
se preservan filas e IDs originales; solo se resuelven 2 colisiones de ID
verificadas (no más).

### Ya hecho y confirmado en esta sesión

1. Merge de la rama `initAngm` (Ángel, submódulo de restaurante) dentro de
   `initAlan`, resolviendo el choque de diseño documentos/laboratorio a
   favor de la versión de Ángel (`registry.py`, tests, migración
   `20260831020000_document_laboratory_modules.sql`). Pusheado, CI en
   verde.
2. Consolidación de "Configuración" en un solo ícono de engrane
   (`frontend/src/layouts/Shell.jsx`): MFA, gestor de roles, permisos,
   `/event_log` y `/user_mfa` movidos a `location: "settings"`. Migración
   `database/migrations/20260903000000_configuracion_dentro_del_engrane.sql`
   mueve `menu_group='Configuracion'` de `sidebar` a `settings` para
   instalaciones ya sembradas. Confirmado visualmente por Alan ("Confirmado,
   ya se ve el badge y el engrane").
3. `DEPLOYMENT_LABEL`: nuevo env var leído por `backend/app/modules/plan.py`
   (`_etiqueta_del_despliegue()`), badge visual en el topbar
   (`.deployment-badge` en `Shell.jsx` + `app.css`) y en el `<title>` de la
   pestaña. Configurado en `adser-prod` como `"Adser"` vía
   `kubectl -n adser-prod patch secret app-secrets` + `rollout restart`,
   confirmado funcionando. **`LICENSED_MODULES` sigue explícitamente
   diferido — Alan dijo "todavía no", no configurar sin luz verde nueva.**
4. Overlay `k8s/overlays/adser-prod/kustomization.yaml` promovido a la
   imagen `fa4de37` (las 4 imágenes), committeado, aplicado a mano vía `scp`
   + `kubectl apply -k` en el VPS (recordar: `/home/alanp/tyakxa_tny/k8s` no
   es un repo git). Rollout confirmado, todos los pods en 1/1.
5. Análisis exhaustivo (múltiples rondas) de los 19 dumps `.sql` reales de
   adser contra el esquema Postgres — metodología: cargar los dumps en un
   contenedor MariaDB desechable y verificar con queries reales, nunca
   contar/parsear el `.sql` a mano. Resultado publicado como artefacto vivo:
   **"Mapeo de Migración — Adser"** —
   `https://claude.ai/code/artifact/cbcc2f85-31ce-48c4-9726-c2b66e5cf278`
   (hallazgos, diagrama ER, orden de migración, mapeo columna-por-columna,
   12 decisiones ya resueltas, verificación de integridad referencial y
   CHECK constraints, metodología). Es la referencia autoritativa — si algo
   más cambia en el diseño de la migración, actualizar ese artefacto.
6. Script completo escrito, autorevisado (2 bugs reales encontrados y
   corregidos: IDs de `permission` hardcodeados en vez de resueltos por
   nombre en runtime; `empleado_por_id_usuario` sin filtrar contra usuarios
   reales, riesgo de colisión falsa) y committeado:
   **`backend/scripts/migrate_adser.py`** (~800 líneas, 14 funciones
   `migrar_*` en orden de dependencias, `--dry-run`, todo en una sola
   transacción con rollback si algo falla).

### Prueba en tyakxa-dev — COMPLETADA (2026-09-04)

Decisión de Alan: nunca correr el script contra los datos reales de
adser-prod sin antes probarlo de punta a punta contra tyakxa-dev (ambiente
de bajo riesgo). Todo esto corrió **dentro del clúster, vía la sesión SSH de
Alan al VPS** — no hay kubectl local en su máquina Windows.

Pasos ejecutados (para repetir el método con otro cliente en el futuro):
1. Pod de backend de `tyakxa-dev` ya traía el script (imagen del commit
   `694505b`, vía el bot `deploy(tyakxa-dev)`).
2. Dumps de adser copiados al VPS (`/home/alanp/adser_dumps`) y de ahí a un
   pod temporal de MariaDB en el namespace `tyakxa-dev`:
   ```bash
   kubectl -n tyakxa-dev run adser-temp-mariadb \
     --image=mariadb:10.11 \
     --env="MARIADB_ROOT_PASSWORD=temp1234" \
     --env="MARIADB_DATABASE=adser_prod" \
     --overrides='{"spec":{"containers":[{"name":"adser-temp-mariadb","image":"mariadb:10.11","env":[{"name":"MARIADB_ROOT_PASSWORD","value":"temp1234"},{"name":"MARIADB_DATABASE","value":"adser_prod"}],"resources":{"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"300m","memory":"256Mi"}}}]}}'
   ```
   (nota: el kubectl del clúster, v1.34.1, ya no soporta `--requests`/
   `--limits` directos en `kubectl run` — hay que usar `--overrides` con un
   patch JSON inline).
3. Los 19 `.sql` cargados sin error dentro del pod temporal.
4. `pymysql` instalado en el pod de backend de tyakxa-dev.
5. Un Pod suelto (`kubectl run`, sin Service) no tiene entrada DNS por
   nombre — hay que usar `kubectl get pod ... -o jsonpath='{.status.podIP}'`
   y apuntar el script a esa IP directamente.
6. **Dry-run inicial falló** con `ForeignKeyViolation: fk_user_id_status` —
   causa raíz investigada y confirmada: no era un bug del script, sino que a
   tyakxa-dev (volumen viejo, armado orgánicamente) le faltaban 2 filas del
   bloque de bootstrap de `init.sql` (`status` id=1, `customer_supplier`
   id=1) porque esos scripts de inicialización solo corren en un volumen
   nuevo. Detalle completo en memoria:
   `project_tyakxa_tny_dev_bootstrap_incompleto`. Se corrigió insertando a
   mano esas 2 filas exactas (mismo patrón `ON CONFLICT DO NOTHING` de
   `init.sql`) + ajuste de secuencias.
7. Dry-run y corrida real (sin `--dry-run`) confirmados exitosos después del
   fix — "Migracion confirmada.", conteos verificados de forma
   independiente contra la base (no solo el reporte del script).
8. Limpieza: `kubectl -n tyakxa-dev delete pod adser-temp-mariadb` ya
   ejecutado.

**Conteos finales verificados en tyakxa-dev** (post-migración real):
customer_supplier=3, user=43, product=2220, material=802, invoice=2,
incident=139, nm_incident_product=2768, ticket=2 — todos cuadran exacto con
lo reportado por el script.

### Merge de initAngm (segunda tanda) — completado 2026-09-04

Ángel había seguido trabajando en `initAngm` (20 commits nuevos: pantallas de
tipo de material y vale de almacén, validación de ClaveProdServ contra el
catálogo SAT, fix de tipo de cambio en cancelaciones, fix de idempotencia,
perf de rastreo de inventario, fixes de menú, y un fix de instalación limpia
en `init.sql`). Mergeado a `initAlan` sin conflictos (`git merge-tree`
limpio), verificado con la suite completa (**1076 passed, 10 skipped, 0
failures**) antes de pushear.

**Nota sobre el push**: mientras corría la suite, Aurora Rodríguez (hace las
bitácoras del equipo, documenta avances — no es código) pusheó un commit
trivial (`chore: ignora .DS_Store`) basado en el tip viejo de `initAlan`,
lo que dejó mi merge local momentáneamente sin pushear y aparentando (a
primera vista) que el trabajo de Ángel se había perdido de `initAlan`. No
se perdió nada — era solo una carrera de pushes normal. Se resolvió
mergeando `origin/initAlan` sobre mi rama local (que ya tenía el merge
completo de Ángel) y pusheando el resultado reconciliado. Documentado por si
se repite el patrón: un push de alguien más entre que yo mergeo y pusheo no
es señal de pérdida de datos, es una carrera normal — mergear de vuelta y
listo, nunca forzar.

### Migración real contra adser-prod — ✅ COMPLETADA (2026-09-07)

La prueba en tyakxa-dev salió bien, Alan confirmó explícitamente seguir con
la migración real, y se corrió de punta a punta contra `adser-prod`:

1. **Bloqueo encontrado y resuelto primero**: la imagen desplegada en
   `adser-prod` (`fa4de37`) era anterior al commit que agrega
   `migrate_adser.py` (`7e00725`) — el script no estaba en el pod (se
   verificó con `ls scripts/`, no se asumió). Se promovió el overlay
   `k8s/overlays/adser-prod/kustomization.yaml` a `0cd29ea` (commit
   `93811ac`, la misma imagen ya validada en `tyakxa-dev`), aplicado a mano
   en el VPS, los 4 deployments rodaron bien.
2. **Bootstrap de adser-prod verificado completo** (`status`/
   `customer_supplier` con su fila `id=1`) — a diferencia de tyakxa-dev, acá
   no hizo falta ningún insert manual.
3. **Dry-run** contra los 19 dumps reales (pod MariaDB temporal en el
   namespace `adser-prod`): conteos idénticos a la prueba de tyakxa-dev.
4. **Corrida real (sin `--dry-run`) confirmada**, conteos reverificados de
   forma independiente — coinciden exacto: product=2220, material=802,
   user=43, invoice=2, incident=139, nm_incident_product=2768, ticket=2,
   customer_supplier=3. (Ojo: `SELECT count(*) FROM user` sin comillas en
   SQL crudo resuelve `CURRENT_USER`, no la tabla — dio un falso "1" en el
   camino; con `"user"` citado o vía ORM dio el 43 correcto.)
5. **`fix_adser_product_image_paths.py` corrido real** ya con `product`
   poblada: 2133 filas de `path_imagen` corregidas, idempotencia
   reconfirmada.
6. Limpieza del pod temporal hecha.

Detalle completo en memoria: `project_tyakxa_tny_migracion_adser` y
`project_tyakxa_tny_persistencia_uploads`.

### Explícitamente diferido / sin resolver — no asumir nada

- `LICENSED_MODULES` para `adser-prod`: diferido por instrucción directa de
  Alan ("todavía no"). No configurar sin nueva luz verde. **Incidente
  2026-09-08:** se encontró configurada de todas formas
  (`inventario,operaciones`), sin aprobación — causaba `errors.module_not_in_plan`
  en pantallas reales (facturación, contactos) porque adser sí tiene datos
  migrados de `invoice`/`ticket`/`customer_supplier`, fuera de esos dos
  módulos. Revertido: `kubectl -n adser-prod patch secret app-secrets
  --type=json -p='[{"op": "remove", "path": "/data/LICENSED_MODULES"}]'` +
  `rollout restart deployment/backend`. No hace falta resembrar — el plan es
  un chequeo en memoria por proceso, leído una sola vez
  (`backend/app/modules/plan.py:250-254`), no depende de filas de
  `entity_permission`. Quién/cuándo la configuró originalmente no se
  investigó — si vuelve a aparecer, revisar eso antes de repetir el fix.
- Política de `LICENSED_MODULES` para `torredigital-prod`: pregunta abierta
  sin responder ("¿Cuál es su caso?" — ¿todos los módulos o también
  restringido?). No asumir ninguna respuesta.
- El "botón" de migración autoservicio que propuso Tanya (un flujo con un
  clic para migrar más rápido/seguro): explícitamente pospuesto por Alan
  ("este es un punto que podemos tocar sobre la marcha"). No iniciado.

## Persistencia de /uploads + fotos de adser conectadas a infra-k8s (2026-09-07)

Punto de partida: ningún ambiente (`tyakxa-dev`, `torredigital-prod`,
`adser-prod`) tenía almacenamiento persistente para archivos subidos
(imágenes de producto, XMLs de CFDI, estados de cuenta, documentos) —
vivían en el filesystem efímero del pod y se perdían en cada
reinicio/redeploy. Esto ya afectaba a `torredigital-prod` en producción real.

### Parte 1 — PVC en `/uploads`, completada y verificada en los 3 ambientes

- `k8s/base/backend.yaml`: PVC `uploads-data` (`local-path`, `ReadWriteOnce`,
  `5Gi`), montado en `/uploads` del Deployment `backend`, con
  `strategy: Recreate` (mismo patrón que `postgres.yaml`). Commit `0b24461`.
- Aplicado y verificado en los 3 ambientes vía `scp` + `kubectl apply -k`
  (procedimiento manual, ver sección "Rama y despliegue" más abajo — el
  cambio es en `k8s/base/`, no se aplica solo en ningún ambiente).
- **Prueba de aceptación real en `tyakxa-dev`**: archivo de prueba escrito,
  pod borrado a mano (`kubectl delete pod`), archivo confirmado intacto en
  el pod nuevo — así se validó el mecanismo antes de tocar producción.
- **`torredigital-prod`**: rescate obligatorio antes del apply (sí tenía un
  archivo real, `bank_statements/statement_2_file.pdf`, 469484 bytes) — con
  `kubectl cp` antes y después, integridad verificada byte a byte.
- **`adser-prod`**: nada que rescatar (ambiente sin archivos reales
  todavía, ver bloqueo más abajo).

### Fotos de producto de adser — conectadas a infra-k8s, no copiadas

Tanya pidió explícitamente que las ~2461 fotos de producto legadas de adser
(que ella sube y mantiene) **se queden** en su carpeta de siempre, y que una
foto nueva también se guarde ahí — no copiarlas a la PVC nueva de este
cliente.

- **Ruta real confirmada** (el plan original tenía mal la ruta):
  `/home/infra-k8s/imagenes/producto` en el nodo `k3s-master1` — **no**
  `/home/infra-k8s/db/imagenes/producto` como se asumió al principio.
  `/home/infra-k8s` es un repo git, propiedad de `root:root`, permisos
  `755`. Confirmado con `find /home /root /srv /opt -maxdepth 5 -iname
  "infra-k8s"` después de que la ruta asumida diera "No existe" incluso
  estando parado ahí — la carpeta correcta se encontró por tanteo directo,
  no asumida de un plan viejo.
- Nombres de archivo reales: `<id_producto>.<ext>` (ej. `1000.png`), sin el
  prefijo `p_` que usa la app para subidas nuevas — ambos conviven sin
  choque en la misma carpeta.
- El contenedor `backend` corre como **root** (`uid=0`, confirmado con
  `kubectl exec ... -- id`) — no hizo falta ajustar permisos del host para
  que la app pueda escribir ahí.
- `k8s/overlays/adser-prod/kustomization.yaml` (commit `2c56e69`): patch al
  Deployment `backend` agregando `nodeSelector:
  kubernetes.io/hostname: k3s-master1` (obligatorio, no afinidad suave —
  con afinidad suave el pod podría caer en otro nodo y la app fallaría en
  silencio con `/uploads/products` vacío en vez de quedarse en `Pending` de
  forma visible) + volumen `hostPath` (`type: Directory`) montado en
  `/uploads/products`, **además** del PVC que sigue sirviendo
  `/uploads/bank_statements`, `/uploads/cfdi_xml`, `/uploads/documents`.
- Verificado en ambos sentidos con un archivo de prueba: escrito desde el
  pod, visible de inmediato desde el host (`cat` directo en el VPS) y
  viceversa — es la misma carpeta física, no una copia.
- Riesgo aceptado explícitamente por Alan: `nodeSelector` obligatorio ata el
  backend de `adser-prod` a `master1` de forma permanente. Impacto acotado
  porque `master1` ya es el único punto de entrada de tráfico de todo el
  clúster (`ingress-nginx` con `hostNetwork`) — si se cae, todos los
  clientes pierden acceso igual, con o sin este pin. La única pérdida real
  es flexibilidad de scheduling en escenarios de presión de recursos
  específicos de `master1` (no de caída completa).

### `product.path_imagen` — ✅ corregido también en adser-prod real (2026-09-07)

`migrate_adser.py` copió `path_imagen` tal cual desde MySQL (ej.
`/uploads/producto/2.png`, carpeta vieja en singular) pero la ruta que sirve
la app es `/uploads/products/<filename>` (plural) — sin corregir esto, toda
foto migrada sale rota en el frontend aunque el archivo exista.

- Script: **`backend/scripts/fix_adser_product_image_paths.py`**
  (commit `2d4fab2`) — no copia ni renombra archivos, solo hace `UPDATE
  product SET path_imagen = 'uploads/products/<filename>'` para cada
  producto cuyo id coincide con un archivo real en `--imagenes-dir`
  (default `/uploads/products`). `--dry-run` con rollback explícito,
  idempotente.
- Probado antes contra datos reales de adser ya migrados a `tyakxa-dev`
  (idempotencia verificada) y **ya corrido real contra `adser-prod`** una
  vez resuelto el bloqueo de la migración de datos (ver sección de arriba):
  2133 filas de `path_imagen` corregidas, 87 productos sin imagen
  (esperado), 168 archivos huérfanos (esperado), idempotencia reconfirmada
  con una segunda corrida.

## Ambiente de desarrollo

- **El host Windows no tiene Python ni el CLI de Docker corriendo por
  defecto.** Para correr la suite de pytest o cualquier script de
  `backend/scripts/`: iniciar Docker Desktop, `docker compose build backend`,
  `docker compose up -d db rabbitmq backend`, luego
  `docker compose exec -T backend pip install -q -r requirements-ci.txt`
  (pytest no viene en la imagen normal) y
  `docker compose exec -T backend bash -c "export TESTING=1 JWT_SECRET=test-secret JWT_SS=test-secret MFA_ISSUER='TYAKXA Test'; pytest -q"`.
- El código de `backend/` está montado por volumen en el contenedor — los
  cambios se reflejan sin rebuild, solo hace falta el `pip install` una vez
  por contenedor nuevo.
- Al correr el stack local, `uploads/cfdi_xml/invoice_*.xml` se regeneran
  con timestamps nuevos (timbrado mock) — es ruido de git, no commitear
  (`git restore` antes de cada commit).
- Vite dentro de Docker en Windows a veces no detecta cambios en bind mounts
  — si un edit a un componente React no se refleja, forzar
  `docker compose restart frontend`.
- `database/seed.sql` tiene un bug preexistente (no introducido por esta
  sesión, confirmado igual en `initAlan` y `origin/initAngm`): el bloque
  demo de restaurante corre en la inicialización de Postgres, antes de que
  el servicio `db-migrate` cree las tablas que referencia — falla en un
  volumen realmente limpio. Sigue sin arreglarse, marcado como hallazgo
  pendiente, fuera de alcance de este trabajo.

## Rama y despliegue

- **`initAlan` es la rama de trabajo real y compartida** entre Alan, Ángel y
  Tanya — no solo de despliegue. Dispara build automático y **despliegue
  automático a `tyakxa-dev`** (diseñado a propósito como ambiente de bajo
  riesgo). `torredigital-prod` y `adser-prod` son promoción manual — ahí
  está el freno real de producción.
- **Regla acordada:** una función que no convence del todo se trabaja local
  o en una rama corta propia (probar con Docker Compose) y solo se sube a
  `initAlan` cuando ya se está conforme.
- **Antes de cada push:** `git fetch` + rebase — el bot de CI agrega su
  propio commit `deploy(tyakxa-dev): actualizar a <sha>` sobre lo recién
  pusheado casi siempre; es normal, no un conflicto real.
- **`/home/alanp/tyakxa_tny/k8s/` en el VPS no es un repositorio git** — es
  una copia plana que el pipeline solo mantiene al día para el tag de
  imagen de `tyakxa-dev`. Cualquier cambio a un archivo bajo `k8s/` (no solo
  el tag) se queda invisible en el clúster hasta copiarlo a mano (`scp` +
  `kubectl apply -k`). Procedimiento exacto en `ARQUITECTURA_TYAKXA_TNY.md`
  sección 7.1. Las deploy keys de GitHub están deshabilitadas por política
  de la organización Tyakxa — no es una opción para arreglarlo de raíz.
- Promoción manual de un overlay = editar los `newTag` en
  `k8s/overlays/<cliente>/kustomization.yaml`, commitear, y en el VPS: `scp`
  del `kustomization.yaml` actualizado + `kubectl apply -k` sobre el overlay
  correspondiente + `kubectl rollout status` para confirmar.
- `kubectl run` en la versión de kubectl del clúster (v1.34.1 cliente) NO
  soporta `--requests`/`--limits` directos — usar `--overrides` con un
  patch JSON inline (ver comando arriba). Siempre poner límites explícitos,
  el clúster tiene 3.8GB RAM por nodo sin swap.

## Plan de integración cotizador_demo → tyakxa_tny (trabajo aparte, en pausa)

Guardado en `C:\Users\TDW2\.claude\plans\snoopy-riding-quilt.md` (no vive en
este repo). 3 fases:

- **Fase 1 — Blindaje prod/sandbox** ✅ hecha y desplegada (commit `e3644ae`).
- **Fase 2 — Multiemisor + CSD por RFC** ✅ hecha y desplegada (commit
  `8cc59eb`). `multiemisor_csd` se declaró como capacidad de `facturacion`
  con licencia independiente (ver mecanismo de licencias abajo).
- **Fase 3 — REP real (complemento de pago)** ✅ **completa: backend +
  frontend, probada con timbrado real de punta a punta desde la UI,
  2026-09-08.** Ya commiteada (`fb4448c`). Ver detalle abajo.

### Fase 3 — spike en vivo contra Facturama real (2026-09-08)

**Cuenta usada:** `TorreDigital`, la compartida real de multiemisor (no una
cuenta sandbox aislada — Alan confirmó que es la misma cuenta con la que
distintos clientes emiten con sus propios RFC, como en `cotizador_demo`).
Se probó exclusivamente contra `https://apisandbox.facturama.mx` (con
`provider=facturama_multiemisor_sandbox`, que el blindaje de Fase 1 fuerza
sin excepción — nunca toca producción real). CSD de prueba usado: el
público del SAT (`EKU9003173C9`, Escuela Kemper Urgate), CSD real (no la
FIEL) subido con éxito vía `POST /customer_supplier/<id>/csd`.

**Timbrado real logrado, dos veces:** una factura tipo I (UUID
`695bf3cb-25b5-41af-ba74-96bdb93d1048`... revisar bitácora de sesión para el
detalle completo) y un **REP tipo P timbrado de verdad** con sello y firma
del SAT — confirma el formato completo del payload, no solo lectura de
documentación.

**Hallazgos reales que la documentación de Facturama NO menciona:**
- El nombre oficial del emisor para `EKU9003173C9` en el campo
  `Issuer.Name`/`Receiver.Name` es **`"ESCUELA KEMPER URGATE"`, sin
  `"SA DE CV"`** — con el nombre completo (el que trae el propio CSD),
  Facturama rechaza con "el Nombre del emisor debe pertenecer al nombre
  asociado al RFC registrado". Ojo si se reusa este RFC de prueba en otro
  lado.
- **Multiemisor exige `Folio` siempre**, en cualquier `CfdiType` (I o P) —
  sin él, rechazo `"The Folio field is required"`.
- Si el receptor es `XAXX010101000` "Público en general", **hace falta el
  nodo `GlobalInformation`** (`Periodicity`/`Months`/`Year`) — aplica igual
  a un REP tipo P, no solo a tipo I.
- `operation_number` va en **`Complemento.Payments[].OperationNumber`**
  (confirmado, aceptado tal cual).
- Moneda extranjera en el REP necesita **dos** campos no documentados:
  `Complemento.Payments[].ExchangeRate` (obligatorio si
  `Payments.Currency != MXN`) y `RelatedDocuments[].EquivalenceDocRel`
  (opcional). La reconciliación exacta de montos (`ImpPagado` dentro del
  límite permitido cuando hay conversión de moneda) quedó sin resolver del
  todo — es matemática de negocio para cuando se escriba
  `payment_complement_service.py`, no un problema de formato.

**Bug real encontrado y ya corregido, fuera del alcance de la Fase 3 pero
grave** (commit pendiente, ya en el árbol de trabajo): `stamping.py` mandaba
el campo `"ExchangeRate"` para moneda extranjera en el CFDI tipo I; Facturama
exige **`"CurrencyExchangeRate"`**. Con el nombre viejo, **ninguna factura en
moneda extranjera había timbrado nunca de verdad** contra Facturama (los
tests nunca lo detectaron porque no hacen red real, solo verifican el body
armado). Corregido en `stamping.py:250-254`, test actualizado en
`test_stamping.py`, 29/29 en verde. Esto afecta también `torredigital-prod`
en producción real — vale la pena confirmar si algún cliente real ya intentó
timbrar en moneda extranjera y falló en silencio.

**Segundo bug real encontrado igual (mismo motivo, mismo alcance de
producción real):** `build_request_body()` (tipo I) nunca armaba el nodo
`GlobalInformation`, obligatorio cuando el receptor es el RFC genérico
`XAXX010101000` (público en general) — confirmado que Facturama rechaza
*cualquier* comprobante a ese receptor sin ese nodo, sin importar lo demás.
Corregido en `stamping.py` (mismo bloque que `CurrencyExchangeRate`), test
nuevo `test_a_generic_public_receiver_gets_a_global_information_node`.
También afecta a cualquier cliente real que facture a público en general
(ventas de mostrador sin RFC del comprador) — mismo consejo: confirmar si ya
pasó en producción.

**Ya investigado y confirmado antes del spike** (sigue vigente):
- El endpoint de Facturama es el mismo `self.CFDIS_PATH` que ya usa `stamp()`
  (`/3/cfdis` sandbox, `/api-lite/3/cfdis` multiemisor) — solo cambia la
  forma del body según `CfdiType`.
- Formato base del payload (sin `Conceptos`/`Items`, sin
  `PaymentMethod`/`PaymentForm`/`Currency` a nivel raíz, `Receiver.CfdiUse`
  debe ser `"CP01"`, `RelatedDocuments[]` lleva `TaxObject`) — confirmado
  ahora con timbrado real, no solo con la guía de Facturama.
- `build_payment_complement(payment_id, user_data)` ya existe en
  `backend/app/services/invoice_payment_service.py:249-290` — arma el
  payload (payment + related_document) pero no timbra ni persiste nada.
- `InvoicePayment` (`backend/app/models/invoice_payment.py`) no tiene
  columnas propias de folio fiscal — esos datos van en la `Invoice` tipo P
  nueva, vía `id_payment_invoice` (línea 53 del modelo, ya existe el campo).
- La validación de forma de pago ≠ '99' en `register_payment()`
  **ya está implementada** (`invoice_payment_service.py:140-146`) — el plan
  original decía que faltaba, no es cierto.
- **`cfdi_validation.py` YA SE CORRIGIÓ** (revisar `git status`, puede
  seguir sin commitear): `_validate_concepts` ya no exige `Conceptos` cuando
  `TipoDeComprobante == "P"`. `_validate_totals`, `_validate_header` y
  `_validate_related` ya son compatibles con un CFDI sin partidas y
  subtotal/total en 0, sin necesitar cambios.
- `parse_cfdi()` (`cfdi_xml.py`) ya tolera un XML sin `Concepto`.
- Patrón de transacción a reusar: idéntico a `stamp_invoice()`
  (`stamping.py:576-646`) — todo dentro de un solo `transaction_context()`,
  crear la fila nueva + `db.flush()` antes de llamar al proveedor, dejar que
  cualquier excepción se propague para el rollback. Un resultado
  "uncertain" (timeout) NO lanza excepción — decidir cómo manejar ese caso
  para el REP.
- Campos NOT NULL de `Invoice` a llenar en la fila nueva (ver
  `manual_invoice_service.py:228-268`): `id_customer_supplier`,
  `id_issuer_customer_supplier`, `tax_certification_supplier`, `id_status`,
  `created_by`, `apply_tax`, `manual_capture`, `tax_rate`. Para el REP:
  `apply_tax=False`, `tax_rate=Decimal(0)`, `manual_capture=False`,
  `tipo_de_comprobante="P"` (vía `normalize_cfdi_type("PAGO")`), `uso_cfdi`
  forzado a `"CP01"` directo (no pasar por `normalize_cfdi_use()`, esa
  función solo sabe `""`/`"P01"` → `"G03"`).

**Implementado y probado con timbrado real 2026-09-08 (backend completo):**
1. ✅ `backend/app/services/payment_complement_service.py` (archivo nuevo) —
   `stamp_payment_complement(payment_id, idempotency_key, user_data,
   provider=None)`. Mismo patrón transaccional que `stamp_invoice()`, con
   una diferencia deliberada: un rechazo definitivo del PAC (`"rejected"`)
   **sí lanza excepción y revierte todo** (la factura tipo P se crea
   específicamente para el intento, a diferencia de `stamp_invoice` donde la
   factura ya existía antes) — un resultado `"uncertain"` (timeout) **no**
   revierte, se deja persistido para reconciliar después, igual que
   `stamp_invoice`.
2. ✅ `StampingProvider.stamp_payment_complement()` (rechazo por default) +
   `FakeStampingProvider.stamp_payment_complement()` (para tests) +
   implementación real en `FacturamaSandboxProvider` (heredada por
   `FacturamaMultiemisorProvider`, que solo agrega el nodo `Issuer` y quita
   `NameId`, igual que ya hace con `build_request_body`). `_post_cfdi()`
   extraído de `stamp()` como helper común.
3. ✅ `FacturamaSandboxProvider.build_payment_complement_request_body(payload)`
   — el payload que le pasa `payment_complement_service` ahora sí trae
   `issuer`/`receiver` (agregado a `_complement_payload()` en
   `invoice_payment_service.py`, que también sirve al preview de solo
   lectura `build_payment_complement()`). Pendiente sin resolver: la
   reconciliación exacta de montos cuando el pago es en moneda distinta a
   MXN (`ImpPagado` fuera del límite permitido en la prueba en vivo) — es
   matemática de negocio, no un problema de formato.
4. ✅ Endpoint `POST /stamping/invoices/payments/<id_payment>/stamp`
   (`routes/stamping.py`).
5. ✅ Tests en `backend/tests/test_services/test_payment_complement_service.py`
   (7 casos: éxito, rollback completo en rechazo, "uncertain" persiste sin
   asentar, idempotencia, factura original sin timbrar, abono ya timbrado,
   forma de pago '99' como defensa en profundidad).
6. ✅ **Frontend hecho y probado en navegador real** (no solo backend):
   `getPaymentComplement()` (preview) ahora también trae `status` y
   `stamped.{folio_fiscal,certification_date}` cuando ya se timbró
   (`_complement_payload` + `build_payment_complement()` en
   `invoice_payment_service.py`). `InvoiceFiscalPanel.jsx`: nueva función
   `timbrarComplemento()` + `stampPaymentComplement()` en `api/index.js` →
   `POST /stamping/invoices/payments/<id>/stamp`. El panel muestra un botón
   real **"Timbrar complemento"** mientras `status !== "timbrado"`, y una vez
   timbrado muestra el folio fiscal/UUID real del REP (no el de la factura
   original, que sigue apareciendo aparte como "Documento relacionado").
   Texto `fiscal.payment_registered` corregido a solo "Abono registrado."
   (ya no promete un complemento que todavía no existe). Probado en
   navegador real contra Facturama: timbrado desde el botón, UUID real
   `115040b0-8d06-4e6d-9e9b-58d7fb4a2746`.

**Prueba real de punta a punta ya hecha** (sandbox real de Facturama, cuenta
multiemisor `TorreDigital`, CSD de prueba `EKU9003173C9` ya registrado):
factura tipo I creada y timbrada por la API real (`POST /invoice/manual` +
`POST /stamping/invoices/<id>`, UUID `ad0e2f76-a72d-422e-9440-53627a874bd3`),
abono registrado (`POST /invoice/6/payments`), REP timbrado real por el
endpoint nuevo (`POST /stamping/invoices/payments/1/stamp`, UUID
`9a501980-fcc3-4a8c-b4aa-671254200471`) — verificado en la base que la
factura tipo P quedó en `invoice_status='timbrada'` con su propio
`folio_fiscal`, y el abono en `status='timbrado'` con
`id_payment_invoice` apuntando a ella. Suite completa: 1086+ pasan, 0
fallas.

## Mecanismo de licencia por módulo — en pausa para rediseño

Mecanismo general (`LICENSED_MODULES` por cliente en el Secret de k8s,
leído por el initContainer, filtrando qué módulos de `registry.py` se
siembran) — commit `0f37c01`, desplegado (fail-open: vacío = todos los
módulos, no cambia nada en los 3 ambientes reales hoy).

**Tanya cuestionó el diseño**: un Secret de k8s no está cifrado y cualquiera
con acceso al clúster lo edita directo — frágil como control de licencia,
sin auditoría ni dato de negocio. Propone una API central dentro de la
instancia de Torre Digital que las demás instalaciones consulten,
permitiendo además KPIs de suscripción. Rediseño grande, sin empezar.

**Decisión de Alan: terminar primero la migración de adser (y, después,
retomar la Fase 3 de facturación), tratar el rediseño de licencias
después.** No se ha tocado nada del mecanismo actual.

**Cuidado:** `multiemisor_csd` (Fase 2) depende del campo
`licencia_independiente` de `Capacidad` en `registry.py` — si se
rediseña/revierte el mecanismo de licencias, no romper esa dependencia a
ciegas.
