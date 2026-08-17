# Integracion funcional de TYAKXA

## Resumen de resultado

Trabajo iniciado y auditado el 16 de agosto de 2026. El producto destino es `tyakxa_tny`; `adser_all` y `cotizador_demo` se usaron solo como referencias de comportamiento. Ninguna fuente tiene licencia de proyecto verificable, por lo que las capacidades se reimplementaron sin copiar texto sustancial.

Resultado parcial verificable:

- Inventario: ledger append-only, movimiento transaccional, clave idempotente, bloqueo de producto, scope de proyecto y prohibición de saldo negativo. Faltan reportes/UI del ledger y prueba concurrente PostgreSQL con fixtures válidos.
- Cotizaciones: cálculo Decimal, ciclo de vida explícito, aprobación/rechazo, vínculo de partida con `Task` del mismo proyecto y portal cliente con propiedad backend. Faltan versiones, subtareas equivalentes completas y descarga segura de documentos desde el portal.
- CFDI: parser 3.3/4.0 con límite, rechazo DTD/entidades, UUID obligatorio y deduplicación. Falta persistir conceptos CFDI y cifrar datos fiscales sensibles.
- Timbrado: puerto inyectable, fake, cliente Facturama sandbox, operación idempotente y estado incierto. Faltan payload fiscal completo, cancelación, descarga y reconciliación persistente.
- Estados de cuenta: importación CSV segura, hash anti-duplicado, movimientos y totales Decimal con scope. Faltan PDF bancario, matching, conciliación y UI.
- La calificación efectiva posterior a remediación es 49.9/100, Riesgo alto. El cálculo bruto es 50.7, limitado por tenant/PII. No se declara éxito total.

Repositorios observados al inicio:

| Repositorio | Rama | Commit | Estado inicial |
|---|---|---|---|
| `tyakxa_tny` | `main` | `f5d7b3c` | Modificado: `backend/init_db.py`, correccion local del bootstrap de administrador |
| `cotizador_demo` | `initAlan` | `473b5cf` | Limpio |
| `adser_all/adser` | `main` | `cb66f17` | Limpio |
| `adser_all/adser_backend` | `main` | `304dcc2` | Limpio |

No se encontraron archivos `AGENTS.md` aplicables.

## Inventario de fuentes

### ADSER: almacen

- Catalogos de producto, material, marca, familia, ubicacion y tipo de ubicacion: modelos bajo `adser_all/adser_backend/flask_path/api/common/model/` y CRUD en `flask_path/api/`.
- Prestamo, devolucion, reparacion, destruccion, dano y extravio: `api/incidente.py`, `api/nm_incidente_producto.py` y `api/producto.py`. El enlace incidente-producto conserva cantidad y fecha de cierre.
- Estados observados: `ENTRADA`, `SALIDA`, `REPARACION`, `DESTRUCCION`, `DAÑADO` y `EXTRAVIADO`.
- Existencia de consumibles: `Producto.cantidad`; el prestamo descuenta cantidad. No se encontro kardex inmutable, reserva separada, valuacion, transferencia, picking, packing, embarque ni control de concurrencia.
- Imagen de producto con limite, extension y compresion: `api/producto.py`.
- Reportes de inventario actual, por mes y prestamos por empleado: `api/reporte_producto.py`.
- Interfaz de vales, productos, incidentes, catalogos y reportes: `adser_all/adser/src/components/FilterTableValeNuevo.js`, `FilterTableProducto.js`, `FilterTableIncidente.js` y componentes `Reporte*`.
- Roles observados: administrador, almacen, finanzas, ingenieria, lider, personal general, cliente y proveedor. El control fuente es principalmente por rol/ruta.
- Pruebas de prestamo y reportes: `adser_all/adser_backend/tests/test_prestamo_producto_diagnostico.py` y `test_reporte_producto_contratos.py`.

### Cotizador Demo: cotizaciones y dominios relacionados

- Cotizacion y partidas con vigencia, descuentos, IVA y estados: `cotizador_demo/backend/models/quotation.py`, `quotation_item.py` y `routes/quotations.py`.
- El enlace de tarea no enlaza una entidad Task independiente: cada partida tiene `create_task`, estado, responsable y observaciones; una partida tiene muchas `QuotationSubtask`, ordenables y opcionalmente visibles en PDF.
- Clientes, proveedores, datos fiscales y acceso de portal: `models/client.py`, `provider.py` y `routes/client_portal.py`.
- Portal separado por JWT de rol cliente y consultas por `client_id`: `routes/client_portal.py`; UI en `frontend/src/pages/ClientPortalPage.jsx`.
- CFDI 4.0 recibido: carga XML, emisor/receptor, partidas, UUID unico y clasificacion recibido/emitido en `routes/expenses.py`, `models/expense_invoice.py` y `expense_item.py`.
- Estados de cuenta PDF, deteccion de banco, hash de archivo, movimientos y conciliacion: `models/bank_statement.py`, `services/bank_statements/parsers/` y `routes/bank_statements.py`.
- Timbrado, cancelacion, consulta de cancelacion, XML/PDF y complemento de pago: `services/invoicing/` y `routes/invoices.py`. El adaptador `PACProvider` separa Facturama de la construccion CFDI y existe un proveedor mock.
- Concurrencia de timbrado mediante advisory lock PostgreSQL y restricciones unicas; credenciales PAC cifradas mediante `EncryptedString`.
- Pruebas de autorizacion, calculos CFDI y parseo bancario bajo `cotizador_demo/backend/tests/`.

## Matriz final de brechas: almacen

| ID | Capacidad | Fuente y evidencia | Estado en TYAKXA | Evidencia en TYAKXA | Decision | Componentes destino | Dependencias | Riesgos | Pruebas requeridas |
|---|---|---|---|---|---|---|---|---|---|
| ALM-01 | Producto, material, marca y familia | Modelos y CRUD ADSER | Parcial | `backend/app/models/product.py`, `material.py`, `brand.py`, `product_family.py`; CRUD generico | Extender | Modelos, servicio, API y UI de inventario | SQLAlchemy | Cantidad editable sin historial | CRUD, tenant, permisos |
| ALM-02 | Ubicaciones jerarquicas y tipos | `model_ubicacion.py`, `model_tipo_ubicacion.py` | Parcial | `location.py` permite `id_location_container`; no almacena tenant/almacen | Extender | Location, almacenes y alcance | PostgreSQL | IDOR y ciclos de ubicacion | Jerarquia, ciclos, tenant |
| ALM-03 | Prestamo y devolucion por empleado | Incidente y NM incidente-producto | Parcial | `inventory_service.py` soporta loan/return atomico; no enlaza automaticamente empleado/incidente ni tiene UI | Extender | Servicio de movimientos, API y UI | Transacciones | Flujo vertical incompleto | Concurrencia, retorno, idempotencia |
| ALM-04 | Reparacion, dano, destruccion y extravio | Estados de incidente ADSER | Parcial | Catalogos de incidente/producto sin transiciones validadas | Adaptar | Motor de movimientos y motivos | Estado inventario | Cambios arbitrarios | Transiciones negativas |
| ALM-05 | Existencia actual y disponible | `Producto.cantidad` | Parcial | Movimiento bloquea `Product` y actualiza cantidad; sin balance separado reservado/disponible | Extender | Balance por ubicacion y vista de disponibilidad | Numeric/locking | Reserva aun ausente | Reserva concurrente |
| ALM-06 | Kardex inmutable y trazabilidad | No existe completo en ADSER; requerido por objetivo | Parcial | `InventoryLedger`, migracion y endpoint de movimiento; sin endpoint de consulta/reportes | Extender | InventoryTransaction/Ledger | PostgreSQL | Auditoria de lectura incompleta | Inmutabilidad, reversa |
| ALM-07 | Reservado, comprometido y en transito | No encontrado en ADSER | Ausente | No se encontro evidencia | No portar | N/A | N/A | Sin valor fuente verificable | N/A |
| ALM-08 | Transferencias entre almacenes | No encontrado en ADSER | Ausente | No se encontro evidencia | No portar | N/A | N/A | Sin valor fuente verificable | N/A |
| ALM-09 | Recepcion, picking, packing y embarque | No encontrado en ADSER | Ausente | No se encontro evidencia | No portar | N/A | N/A | Sin valor fuente verificable | N/A |
| ALM-10 | Lotes, series y caducidad | No encontrado en ADSER | Ausente | No se encontro evidencia | No portar | N/A | N/A | Sin valor fuente verificable | N/A |
| ALM-11 | Imagen segura de producto | `api/producto.py` | Completa | `routes/product.py` limita 5 MiB, extension y nombre seguro | Conservar | Product API/UI | Werkzeug | Validacion por contenido ausente | Extension, tamano, traversal |
| ALM-12 | Reporte actual de inventario | `productos_actual()` | Parcial | Listados de producto y catalogo; no reporte por estado/ubicacion | Adaptar | Consultas y pagina de reportes | Balance de stock | Datos inconsistentes | Filtros, paginacion, tenant |
| ALM-13 | Reporte mensual por estado | `clasificar_productos_por_mes()` | Ausente | No se encontro equivalente funcional | Reimplementar | Kardex/reportes | Ledger | Historico no reconstruible | Periodos y estados |
| ALM-14 | Prestamos por empleado | `obtener_productos_prestados_por_empleado()` | Ausente | Relacion incidente-producto sin consulta de dominio | Reimplementar | API reporte/UI | Ledger/prestamo | Acceso cruzado | Propiedad y filtros |
| ALM-15 | Minimos, reorden y alertas | No implementado realmente en ADSER | Parcial | Jobs `tasks_scm.py` son respuestas estaticas | No portar | N/A | N/A | Fuente sin capacidad funcional | N/A |
| ALM-16 | Permisos granulares de almacen | Roles/rutas ADSER | Parcial | RBAC por entidad CRUD, sin acciones aprobar/ajustar/transferir | Extender | EntityPermission y guards de dominio | RBAC | Escalada horizontal | Matriz positiva/negativa |

## Matriz final de brechas: cotizaciones e integraciones

| ID | Capacidad | Fuente y evidencia | Estado en TYAKXA | Evidencia en TYAKXA | Decision | Componentes destino | Dependencias | Riesgos | Pruebas requeridas |
|---|---|---|---|---|---|---|---|---|---|
| COT-01 | Cotizacion y partidas | Quotation/QuotationItem | Parcial | Invoice reutilizada como cotizacion e InvoiceMaterialService; UI `QuotationPage.jsx` | Extender | Dominio quotation sobre tablas actuales | Decimal | Contrato ambiguo factura/cotizacion | Totales y CRUD |
| COT-02 | Ciclo de vida y transiciones | Estados y rutas de quotations | Parcial | `quotation_service.py` y endpoint de transicion; CRUD legacy aun puede editar estado | Extender | Servicio de ciclo de vida | SQLAlchemy | Bypass por CRUD legacy | Matriz de transiciones |
| COT-03 | Calculo monetario decimal | Builder y modelos Numeric | Parcial | Conversion usa calculador Decimal; serializadores/UI legacy aun usan float/Number | Extender | Calculador central Decimal | decimal.Decimal | Redondeo en capas legacy | Casos limite y descuentos |
| COT-04 | Versiones, aprobacion y rechazo | Estados por partida | Parcial | `authorization_status` por partida; sin versiones | Extender | Partidas y auditoria | Event log | Sobrescritura | Aprobacion, rechazo, version |
| COT-05 | PDF de cotizacion | `pdf_generator.py` | Completa | `/documents/quotation_pdf/<id>` y plantillas locales | Conservar | Documents service | WeasyPrint | Acceso al PDF | Autorizacion y render |
| COT-06 | Enlace operativo de tarea por partida | Campos task y subtareas | Parcial | FK `InvoiceMaterialService.id_task` y validacion de proyecto; sin subtareas equivalentes/UI | Extender | FK partida-tarea y subtareas | Task existente | Flujo operativo incompleto | Cardinalidad y permisos |
| COT-07 | Clientes/proveedores y fiscal | Client/Provider | Parcial | CustomerSupplier unificado; datos fiscales limitados | Extender | CustomerSupplier | SQLAlchemy | RFC duplicado global | Tenant y validacion fiscal |
| COT-08 | Portal cliente de cotizaciones | client_portal | Parcial | Blueprint y `/portal-cliente`; lista/detalle/decision/comentario con propiedad | Extender | Blueprint/cliente JWT/UI separada | JWT publico | Sin tests IDOR/PDF | Acceso propio/ajeno |
| COT-09 | CFDI XML seguro y deduplicado | Expense XML/UUID | Parcial | Parser seguro, limite, version/UUID y unique index; conceptos no importados | Extender | Servicio parser y persistencia | XML stdlib seguro | Datos fiscales sensibles | Valido, XXE, grande, duplicado |
| COT-10 | Estados de cuenta y movimientos | BankStatement/parsers | Parcial | CSV, hash, modelos y API; sin PDF/matching/conciliacion/UI | Extender | Modelos, parser, conciliacion y UI | PDF parser | Conciliacion ausente | Fixtures, hash, matching |
| COT-11 | Facturama desacoplado | PACProvider/Facturama/mock | Parcial | `StampingProvider`, fake, sandbox y operacion idempotente | Extender | Puerto PAC, fake, persistencia y Celery | urllib/Celery | Payload/cancelacion incompletos | Fake exito/error/timeout/reintento |
| COT-12 | Cancelacion y reconciliacion PAC | Facturama cancelar/consultar | Ausente | No se encontro evidencia | Reimplementar | Servicio/tarea PAC | Celery | Cancelacion incierta | Estados e idempotencia |
| COT-13 | Complemento de pago y saldos | PaymentReceipt/pagos.py | Ausente | No se encontro equivalente | Adaptar | Movimientos de cuenta e invoice | Decimal | Saldo editable | Parcialidades y trazabilidad |
| COT-14 | Aislamiento empresa/sucursal | company_id/sucursal_id | Incompatible | `id_proyect` existe en algunas entidades, pero CRUD no lo fuerza ni filtra | Reimplementar | Scope central en backend | JWT/modelos | Acceso cruzado critico | IDOR/tenant negativos |
| COT-15 | RBAC por modulo/accion | Decoradores por modulo | Parcial | Permiso CRUD por entidad; admin de empresa omite ACL | Extender | Acciones de dominio | EntityPermission | Administrador sin scope | Negacion por defecto |
| COT-16 | Auditoria y correlacion | Auditoria PAC y estados | Parcial | Operaciones stamping/ledger trazables; AuditLog sin correlation/causation completos | Extender | Audit service/middleware | UUID | Trazabilidad insuficiente | Redaccion y correlacion |

## Diseno de integracion

### Mapeo fuente-destino

| Concepto fuente | Destino TYAKXA | Estrategia |
|---|---|---|
| Producto ADSER | `Product` | Conservar maestro; sacar cantidad operativa a balances y ledger |
| Ubicacion ADSER | `Location` | Conservar jerarquia y agregar alcance de proyecto/almacen |
| Incidente-producto ADSER | Movimiento/prestamo de inventario | Mantener referencia opcional al incidente; ejecutar por servicio transaccional |
| Quotation Cotizador | `Invoice` con tipo/estado de cotizacion | Compatibilidad con UI y PDF actuales; ciclo en servicio dedicado |
| QuotationItem | `InvoiceMaterialService` | Conservar partidas y agregar relacion opcional a Task |
| QuotationSubtask | Task/TaskNote | Usar Task como entidad operativa real; una partida puede enlazar una tarea padre |
| Client/Provider | `CustomerSupplier` | Mantener entidad unificada y aplicar scope por proyecto |
| ExpenseInvoice XML | `Invoice` importada | Parser separado, UUID deduplicado y archivo fuera del arbol de codigo |
| PACProvider | Puerto `StampingProvider` | Implementacion Facturama y fake inyectable; ninguna llamada real en pruebas |

### Decisiones arquitectonicas

1. Mantener Flask Blueprints, SQLAlchemy 2, React/Vite y el esquema RBAC existente; agregar servicios de dominio, no reglas dentro del CRUD generico.
2. Usar `id_proyect` como scope de empresa vigente hasta que exista un tenant formal. Toda ruta nueva derivara el scope del JWT y no aceptara elevarlo desde el payload.
3. Introducir migraciones SQL incrementales bajo `database/migrations/`; el repositorio no tiene Alembic operativo. La brecha Alembic se conserva visible en auditoria.
4. Inventario se actualizara bajo transaccion y bloqueo de fila; el ledger sera append-only y una correccion se expresara como movimiento inverso.
5. Importes se calcularan con `Decimal` y cuantizacion explicita a dos decimales.
6. Facturama quedara detras de una interfaz inyectable. El proveedor fake sera el unico usado por pruebas; credenciales solo por configuracion externa.
7. Operaciones externas o reintentables usaran Celery con RabbitMQ. Redis esta ausente en la arquitectura actual y se registrara como brecha, no se fingira su uso.
8. No se copiaran implementaciones fuente porque no se encontro licencia de proyecto verificable.

### Matriz RBAC objetivo

| Recurso | Acciones | Scope obligatorio |
|---|---|---|
| Inventario | ver, recibir, prestar, devolver, ajustar, cancelar, exportar | proyecto y ubicacion |
| Cotizacion | ver, crear, editar borrador, enviar, aprobar, rechazar, convertir | proyecto y cliente |
| Tarea de cotizacion | ver, asignar, actualizar, cerrar | proyecto y asignado |
| CFDI XML | importar, ver, conciliar | proyecto |
| Estado de cuenta | importar, ver, conciliar | proyecto y cuenta |
| Timbrado | previsualizar, timbrar, cancelar, reconciliar | proyecto y emisor |
| Portal cliente | ver propia cotizacion, aceptar, rechazar, comentar, descargar | identidad y propiedad |

## Registro de validaciones y comandos

| Comando o herramienta | Entorno | Resultado real |
|---|---|---|
| Localizacion de raices y `pwd` | Solo lectura local | `unify` confirmado; cuatro rutas requeridas presentes |
| `git rev-parse`, rama, commit y `git status --short` en los cuatro repositorios | Solo lectura local | Estados registrados arriba; fuentes limpias |
| Busqueda de `AGENTS.md` | Solo lectura local | Ninguno encontrado |
| Busquedas estaticas de modelos, rutas, jobs, seguridad, Facturama, XML, tenant e inventario | Solo lectura local | Evidencia consolidada en inventarios y matrices |
| `python -m unittest tests.test_services.test_cfdi_xml -v` | Contenedor backend local | 4/4 correctas |
| `python -m unittest tests.test_services.test_inventory_service -v` | Contenedor backend local | 2/2 correctas |
| Smoke transaccional de inventario | PostgreSQL local | No ejecutable: no se encontro producto asociado a factura con proyecto |
| `python -m unittest tests.test_services.test_quotation_service -v` | Contenedor backend local | 3/3 correctas |
| `python -m unittest tests.test_services.test_stamping -v` | Contenedor backend local, fake | 3/3 correctas, cero red externa |
| `python -m unittest tests.test_services.test_bank_statement_import -v` | Contenedor backend local | 2/2 correctas |
| Suite focal consolidada | Contenedor backend local | 14/14 correctas |
| `python -m unittest discover -s tests -p 'test_*.py'` | Contenedor backend local | Fallida: 280 ejecutadas, 84 errores y 1 fallo |
| Suite posterior a primera remediacion | Contenedor backend local | Fallida: 285 ejecutadas, 83 errores y 0 fallos; auth corregido y cinco pruebas tenant nuevas |
| Suite posterior a factories compartidas | Contenedor backend local | Correcta: 285/285; modelos 51/51 y servicios 65/65 |
| `npm run build` | Contenedor frontend local | Correcto; advertencia de chunk de 1.3 MB |
| `npm run lint` | Contenedor frontend local | No ejecutable: falta `eslint-plugin-react-refresh` |
| Seis migraciones SQL con `psql -v ON_ERROR_STOP=1` | PostgreSQL local | Aplicadas correctamente |
| Downgrade de migraciones | Local | No ejecutado: no existe mecanismo Alembic/downgrade |
| Health backend | Docker local | Correcto y healthy |
| Compose desarrollo | Local | Correcto |
| Compose base + override produccion | Local | Correcto |
| Compose override aislado | Local | Fallo esperado: es un override sin build/image propio |
| Busqueda de referencias a ADSER/Cotizador | Solo lectura | Cero coincidencias de runtime |
| Busqueda conservadora de secretos | Solo lectura, sin `.env` | Defaults de desarrollo y fallback plaintext preexistentes; no se imprimieron secretos reales |
| Herramientas Ruff/Black/mypy | Contenedor backend | No disponibles; no instaladas |
| Diagnosticos del editor en archivos nuevos | Local | Sin errores salvo tipos parciales de decoradores Flask en `routes/stamping.py` |

## Archivos modificados durante la ejecucion

- `backend/init_db.py`: cambio previo a esta auditoria dentro de la misma sesion para aislar fallos de filas bootstrap mediante savepoints.
- `docs/INTEGRACION_FUNCIONAL.md`: documento de trabajo requerido.
- Backend: `app/services/{cfdi_xml,inventory_service,quotation_service,stamping,bank_statement_import}.py`.
- Backend: modelos `inventory_ledger`, `stamping_operation`, `quotation_comment`, `bank_statement`; extensiones a invoice, partidas y cuenta bancaria.
- Backend: rutas `stamping`, `client_portal`, `bank_statements`; extensiones a invoice, partidas y product.
- Backend: tarea Celery `tasks_stamping.py` y registro de Blueprint/tarea.
- Frontend: `src/pages/ClientPortalPage.jsx` y ruta pública en `src/App.jsx`.
- Base de datos: seis migraciones incrementales `20260816220000` a `20260816231500`.
- Pruebas: cinco módulos de servicio bajo `backend/tests/test_services/`.
- `AUDITORIA_TECNICA.md`: auditoría final ponderada.

## Migraciones y activacion local

Aplicar en orden sobre una base local respaldada:

1. `20260816220000_unique_cfdi_uuid.sql`
2. `20260816221500_inventory_ledger.sql`
3. `20260816223000_quotation_task_link.sql`
4. `20260816224500_stamping_operation.sql`
5. `20260816230000_quotation_comments.sql`
6. `20260816231500_bank_statements.sql`

Reiniciar backend y worker. Mantener `STAMPING_PROVIDER=fake` hasta configurar y validar explícitamente un sandbox. No existe downgrade automático; debe incorporarse Alembic antes de producción.

## Variables previstas

Solo nombres y ejemplos ficticios:

| Variable | Ejemplo seguro |
|---|---|
| `STAMPING_PROVIDER` | `fake` |
| `FACTURAMA_BASE_URL` | `https://sandbox.example.invalid` |
| `FACTURAMA_USERNAME` | `sandbox-user` |
| `FACTURAMA_PASSWORD` | `sandbox-password` |
| `CFDI_XML_MAX_BYTES` | `5242880` |

## Limitaciones y pendientes actuales

- No existe licencia verificable en las fuentes; se reimplementara comportamiento.
- No existe Alembic operativo ni Redis en TYAKXA.
- `database/init.sql` y `seed.sql` presentan errores de datos/esquema durante el arranque local; no se ocultaran en la validacion final.
- El aislamiento `id_proyect` no es transversal en los CRUD preexistentes; es el bloqueo de seguridad principal.
- Product REST ya aplica scope por `Invoice.id_proyect` y el JWT interno incluye proyecto; los demas dominios y GraphQL siguen pendientes.
- La suite backend completa pasa 285/285; falta incorporarla a CI y medir cobertura.
- Facturama no esta completo y ninguna prueba llamo al servicio real.
- Inventario carece de UI/reportes de ledger y prueba concurrente PostgreSQL.
- Estados de cuenta carecen de PDF por banco, matching, conciliacion y UI.
- Portal carece de descarga PDF/XML autorizada, notificaciones y pruebas IDOR automatizadas.
- No existen Kubernetes, CI automatizado, Redis seguro, observabilidad distribuida ni cifrado de PII.