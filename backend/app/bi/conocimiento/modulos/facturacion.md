---
modulo: facturacion
entidades_clave: [invoice, bank, ticket]
---
# Facturacion

## Que es y para que sirve
El modulo Facturacion sirve para emitir y controlar facturas electronicas (CFDI 4.0): capturarlas, revisarlas contra las reglas del SAT, timbrarlas con el proveedor de timbrado (PAC, Facturama), cancelarlas, cobrarlas en parcialidades con su complemento de pago (REP), emitir notas de credito y descargar el PDF y el XML. Tambien incluye cotizaciones, cuentas fiscales, bancos con sus estados de cuenta, tickets y el catalogo de servicios. Una factura de venta puede mover el almacen, y las ventas del punto de venta o del restaurante se facturan aqui, porque solo este modulo timbra.

## Pantallas y donde encontrarlas: facturas y cotizaciones
En el menu lateral, grupo Facturacion:
- **Facturas**: lista de todas las facturas, con busqueda, vista tabla o tablero, carga de XML y los botones de cada fila (editar, timbrar, aplicar al almacen, actos fiscales, PDF, XML).
- **Factura manual**: captura una factura nueva con sus conceptos, la revisa y la timbra.
- **Autorizacion / Seguimiento**: autoriza o rechaza partida por partida las de cotizaciones y facturas.
- **Cotizaciones** (grupo CRM): tablero de estados y lista para gestionar cotizaciones.
- **Configurar Facturama** (engrane, solo administrador): conexion de timbrado.

## Pantallas y donde encontrarlas: bancos, cuentas y tickets
En el mismo grupo Facturacion del menu:
- **Bancos**: catalogo de bancos y, debajo, los Estados de cuenta (importar PDF o CSV, ver movimientos y vincularlos a facturas).
- **Cuentas bancarias**: cuentas de cada banco (descripcion, sucursal, tipo, intereses, proyecto).
- **Cuentas fiscales**: catalogo de cuentas con descripcion y saldo.
- **Tickets**: registro de tickets con descripcion, estado y nota.
El catalogo de Servicios (descripcion, costo o tiempo promedio, marca) se usa en las partidas de cotizaciones y facturas. No documentado: en que lugar exacto del menu aparece Servicios, ni el flujo de las cuentas fiscales ni de los registros y sellos fiscales.

## Como crear una factura manual
1. Abre Factura manual.
2. Elige Proyecto, Cliente receptor y Empresa emisora (la empresa principal o un proveedor). Captura Emision y Vencimiento; el vencimiento no puede ser anterior a la emision.
3. Elige Moneda (si no es MXN, el Tipo de cambio es obligatorio), Forma de pago, Metodo de pago (PUE o PPD), Uso CFDI, Tipo de IVA y las retenciones de ISR o IVA si aplican.
4. En Conceptos captura Descripcion, Clave SAT de producto, Clave SAT de unidad, Cantidad, Precio unitario, Descuento y Objeto de impuesto. Agrega los conceptos que necesites.
5. Pulsa Vista previa para ver subtotal, IVA, retenciones y total.
6. Pulsa Guardar factura.
Al terminar la factura queda con estatus **pendiente**, sin folio fiscal, y aparecen los botones Revisar ante SAT, Timbrar y descargar. Guardar no timbra.

## Como revisar una factura antes de timbrar (Revisar ante SAT)
1. Guarda la factura en Factura manual.
2. Pulsa Revisar ante SAT.
3. Lee el resultado: dice si la factura es apta o no puede timbrarse todavia, el total calculado, los errores (impiden timbrar) y las advertencias (no impiden).
La revision no consume un timbre ni llama al SAT. Si hay errores, corrige los datos de la factura, del cliente o de la empresa emisora y vuelve a revisar. Una advertencia comun es que el total guardado difiere del total calculado: al timbrar, el sistema usa el total del comprobante.

## Que valida el sistema antes de timbrar: emisor y receptor
- Emisor: RFC valido y no generico, razon social, regimen fiscal del catalogo SAT que corresponda a persona fisica o moral segun su RFC, y codigo postal de 5 digitos (lugar de expedicion).
- Receptor: RFC valido, razon social, regimen fiscal del catalogo y compatible con su tipo de persona, codigo postal fiscal de 5 digitos y Uso CFDI del catalogo y compatible con ese regimen.
- Publico en general (RFC XAXX010101000): razon social PUBLICO EN GENERAL, regimen 616 y uso S01.
- Residente en el extranjero (RFC XEXX010101000): regimen 616 y uso S01.
Los datos fiscales del cliente y de la empresa se corrigen en Clientes y proveedores.

## Que valida el sistema antes de timbrar: comprobante y conceptos
- La factura necesita al menos un concepto autorizado; solo los conceptos autorizados se timbran.
- Metodo de pago PUE o PPD. Con PPD la forma de pago debe ser 99 (Por definir); con PUE no puede ser 99.
- Moneda de tres letras. En MXN el tipo de cambio es 1; en otra moneda hay que capturarlo.
- Cada concepto: descripcion, cantidad mayor a cero, precio, Clave SAT de producto (8 digitos, del catalogo) y Clave SAT de unidad, descuento no mayor al importe, Objeto de impuesto valido y tasas de IVA del catalogo.
- El subtotal debe coincidir con la suma de los conceptos y el total no puede ser negativo.
- Una factura sin proyecto no se puede timbrar.

## Como timbrar una factura
1. En Facturas, ubica la factura sin folio fiscal.
2. Pulsa el boton Timbrar factura de su fila (tambien puedes pulsar Timbrar en Factura manual).
3. Espera la respuesta y recarga la lista.
Si el PAC acepta, la factura pasa a **timbrada**, recibe su folio fiscal (UUID) y fecha de certificacion, y se guarda el XML. Si el folio interno estaba vacio, el sistema asigna el siguiente folio consecutivo de la empresa emisora; un folio capturado a mano se respeta. Confirma siempre que la fila muestre el folio fiscal: si no lo muestra, el timbrado no se completo. Timbrar no mueve el almacen; eso es un paso aparte.

## Que pasa si el PAC rechaza o no responde
- Si el PAC rechaza (datos fiscales, CSD no registrado, credenciales, etc.), la factura NO se timbra: se queda sin folio fiscal y con su estatus anterior, y el intento queda registrado con estatus rejected y el motivo que dio el PAC. Corrige lo indicado y vuelve a timbrar.
- Si el PAC no contesta a tiempo, el intento queda uncertain (incierto): no se sabe si timbro. Antes de reintentar, revisa que la factura no tenga ya folio fiscal.
- Si el comprobante que devuelve el PAC no cumple las reglas del SAT, el sistema no lo da por timbrado.
- Sin credenciales configuradas el timbrado real se rechaza.
No documentado: una pantalla de historial de intentos de timbrado ni como reconciliar un intento incierto.

## Como configurar el timbrado y los ambientes (administrador)
1. Entra al engrane y abre Configurar Facturama (solo administradores).
2. En Proveedor elige: Simulado, sin validez fiscal (solo pruebas internas, no timbra ante el SAT); Facturama Pruebas (sandbox, comprobantes sin validez fiscal real); o Facturama Produccion (timbrado real).
3. Captura Usuario, Contrasena y Name ID / perfil (la contrasena se guarda cifrada).
4. Pulsa Probar conexion y despues Guardar.
La direccion del servicio la fija el sistema segun el modo elegido; no se captura. En produccion cada timbre es real y no se deshace sin cancelar ante el SAT. No documentado: el modo multiemisor no aparece en esta pantalla; lo habilita el equipo tecnico.

## Multiemisor y CSD por RFC
El multiemisor permite timbrar con una sola cuenta del PAC a nombre de varias empresas, cada una con su RFC. Es una capacidad que se contrata aparte de Facturacion (Multiemisor y CSD). Cada empresa emisora necesita su Certificado de Sello Digital (CSD: archivos .cer, .key y su contrasena) registrado en el PAC; el sistema no guarda la llave, solo la envia al PAC. Lo registra un administrador y la empresa guarda su estatus de CSD: sin registrar, registrado o con error. La empresa debe tener RFC. Cada timbre manda el RFC, nombre y regimen del emisor. Si el CSD no esta registrado, el PAC rechaza el timbrado. No documentado: pantalla para subir el CSD.

## Como cargar facturas desde XML
1. Define antes una empresa principal con RFC en Clientes y proveedores (casilla Empresa principal; solo una a la vez).
2. En Facturas, usa el cargador de XML y elige uno o varios archivos .xml (y el proyecto).
3. El sistema crea una factura por archivo, con estatus pendiente, y la clasifica: **venta** si la empresa principal es la emisora, **compra** si es la receptora, **sin_clasificar** en otro caso.
Un XML cuyo folio fiscal ya existe se rechaza como duplicado. Las facturas de compra sirven para entradas de almacen y para el KPI de egresos.

## Como cancelar una factura
1. En Facturas, abre el boton Cancelar, cobrar o acreditar de la fila (solo aparece si la factura esta timbrada).
2. En la pestana Cancelacion elige el Motivo: 01 con errores y con relacion, 02 con errores sin relacion, 03 no se llevo a cabo la operacion, 04 operacion nominativa en factura global.
3. Con el motivo 01 captura el folio fiscal de la factura que la sustituye (debe existir y estar timbrada); con los demas no se captura.
4. Pulsa Solicitar cancelacion y confirma.
La solicitud puede quedar cancelada de inmediato o en proceso: el receptor tiene 72 horas para aceptar o rechazar; usa Consultar al SAT para actualizar. Al confirmarse, la factura pasa a **cancelada**, el almacen recupera lo facturado y los abonos se dan de baja. No se puede cancelar una factura sin timbrar.

## Como registrar un abono a una factura en parcialidades (PPD)
1. Abre el boton Cancelar, cobrar o acreditar de una factura timbrada y entra a la pestana Abonos.
2. Revisa Total, Pagado e Insoluto.
3. Captura Importe (se propone el saldo completo), Forma de pago (no existe la 99) y Fecha del pago.
4. Pulsa Registrar abono.
Solo aplica a facturas con metodo PPD: en las PUE el cobro ya queda acreditado al emitirlas. El abono no puede exceder el saldo. La factura pasa a **parcial** o, si el saldo llega a cero, a **pagada**. Cada abono queda numerado como parcialidad y exige su propio complemento de pago.

## Como timbrar el complemento de pago (REP)
1. En la pestana Abonos, pulsa Complemento en el renglon del abono.
2. Revisa el detalle: es un comprobante tipo P en ceros (el importe vive dentro del complemento) con uso CP01 y el folio fiscal de la factura relacionada.
3. Pulsa Timbrar complemento.
Si se timbra, el abono pasa a **timbrado** y se crea un comprobante tipo P con su propio folio fiscal, que se muestra como Folio fiscal del REP. Si el PAC lo rechaza no queda nada guardado y puedes reintentar. Si no responde, queda pendiente: verifica antes de repetir. Ya timbrado o cancelado, el abono no se vuelve a timbrar. Requiere que la factura original este timbrada.

## Como emitir una nota de credito
1. Abre Cancelar, cobrar o acreditar de una factura timbrada, pestana Notas de credito.
2. Elige el Tipo de relacion: 01 descuento o bonificacion (el almacen no se toca) o 03 devolucion de mercancia (lo acreditado vuelve al almacen del que salio; para eso indica el Producto del almacen).
3. Captura las partidas (descripcion, cantidad, precio, claves SAT) y pulsa Emitir nota de credito.
La nota no puede superar lo que queda por acreditar (total menos lo ya acreditado). Se crea sin timbrar, como comprobante de egreso; se timbra despues desde Facturas. No se acredita una factura cancelada.

## Como aplicar una factura al almacen
1. En Facturas, pulsa Aplicar al almacen en la fila.
2. Lee el aviso: una venta descontara del almacen y una compra lo sumara.
3. Confirma.
Todas las partidas se aplican juntas; si alguna no alcanza, no se mueve nada. Repetir la accion no descuenta dos veces. Una factura sin clasificar (ni venta ni compra) no mueve el almacen. Una factura que nace de una venta del punto de venta o del restaurante ya movio el almacen al cobrarse y no lo mueve otra vez. Una cotizacion no mueve el almacen.

## Como llevar una cotizacion hasta factura
1. En Cotizaciones crea la cotizacion con sus partidas (producto, servicio o concepto) y guardala; nace en Borrador.
2. En el tablero muevela a Enviada y despues a Aprobacion parcial, Aprobada o Rechazada. El cliente tambien puede aceptar o rechazar desde el Portal de cliente.
3. Si hace falta, en Autorizacion / Seguimiento autoriza o rechaza partidas una por una, con nota.
4. Con la cotizacion Aprobada, muevela a Convertida.
Al convertir, las partidas pendientes se autorizan solas, las rechazadas se excluyen, se recalculan los totales y la cotizacion pasa a ser una factura con estatus pendiente, lista para timbrar. No convierte una cotizacion vencida ni una sin partidas autorizadas.

## Como importar un estado de cuenta y conciliar
1. En Bancos, en Estados de cuenta, elige la Cuenta bancaria y el archivo (PDF de BBVA o CSV con fecha, descripcion, cargo y abono).
2. Pulsa Previsualizar para ver movimientos y validacion, y despues Importar.
3. Abre los movimientos y vincula cada uno con su factura.
El mismo archivo no se importa dos veces. Si las sumas de cargos y abonos o el saldo final no cuadran, el estado queda en Revisar; si cuadran, en Conciliado. Si el importe del movimiento difiere de la factura por mas de cinco centavos, el sistema pregunta si vincular de todas formas. Eliminar un estado borra tambien sus movimientos. Un PDF escaneado sin texto no se puede leer.

## Estatus de las facturas y que significan
Estatus de factura (columna invoice_status):
- **pendiente**: factura capturada o convertida, lista para revisar y timbrar.
- **timbrada**: ya tiene folio fiscal; se puede cancelar, cobrar, acreditar y descargar el XML.
- **parcial**: tiene abonos pero queda saldo (solo PPD).
- **pagada**: abonos suman el total.
- **cancelada**: cancelada ante el SAT.
- **captura**: documento interno que crea el sistema al dar de alta producto sin factura; no es un CFDI.
Pasos normales: pendiente, timbrada, parcial, pagada; desde timbrada o parcial o pagada se puede pedir la cancelacion. No confundir con el campo Estado (id_status), un catalogo general distinto.

## Estatus de cotizaciones, abonos, cancelaciones y timbrados
- **Cotizacion**: Borrador a Enviada; Enviada a Aprobacion parcial, Aprobada o Rechazada; Aprobacion parcial a Aprobada o Rechazada; Aprobada a Convertida; Rechazada vuelve a Borrador; Convertida no tiene salida. Una cotizacion antigua con estatus cotizacion se trata como Borrador.
- **Abono (complemento de pago)**: pendiente, timbrado o cancelado.
- **Solicitud de cancelacion**: solicitada, en_proceso, cancelado o rechazado. Con una solicitud solicitada, en proceso o cancelada no se puede pedir otra; con una rechazada si.
- **Intento de timbrado**: processing, stamped, rejected o uncertain.
- **Estado de cuenta**: Conciliado (completed) o Revisar (requires_review).
- **Partida**: pending, authorized o rejected.

## Reglas y permisos importantes: quien ve y opera facturas
- Cada rol tiene su alcance por accion (crear, leer, actualizar, eliminar) en el Gestor de roles y permisos. Por omision el Administrador tiene todo y el Gerente captura facturacion; otros roles no la ven.
- Una persona que no es administradora solo ve y opera las facturas de su propio proyecto, y no puede mover una factura a otro proyecto. Una factura sin proyecto solo la ve el administrador.
- Timbrar, cancelar, abonar, acreditar y aplicar al almacen exigen permiso de actualizar facturas.
- Configurar el timbrado y registrar un CSD son solo del administrador.
- Los permisos por campo pueden ocultar columnas (por ejemplo importes) a ciertos roles.
- Los bancos, estados de cuenta y cuentas bancarias tambien se acotan por proyecto.
- Solo quien tiene el modulo en su plan lo ve.

## Reglas y permisos importantes: cobros, timbres y cancelaciones
- Los timbres y las cancelaciones ante el SAT son irreversibles; revisa con Revisar ante SAT antes de timbrar.
- En ambiente Simulado o Pruebas los comprobantes no tienen validez fiscal.
- Una nota de credito de descuento no toca el almacen; la de devolucion si.
- Cancelar una venta con abonos da de baja los abonos (quedan como cancelados, no se borran).
- Un abono nunca excede el saldo ni usa la forma de pago 99.
- Los mismos datos repetidos no duplican: cada intento de timbrar, abonar o cancelar lleva una clave de idempotencia.
- Para facturar a publico en general el sistema agrega la informacion global requerida por el PAC.
- Una factura en moneda extranjera exige tipo de cambio.

## Campos importantes de la factura
- **Folio** (folio) y **Serie** (serie_csd): el folio se asigna solo al timbrar si esta vacio; la serie puede venir de la empresa emisora.
- **Folio fiscal** (folio_fiscal, UUID): identificador del SAT; si esta vacio no esta timbrada.
- **Fecha de emision** (date_emision) y **vencimiento** (date_expiration).
- **Subtotal, IVA (tax), Descuento y Total**; **retenciones** de ISR e IVA.
- **Estatus** (invoice_status), **Cliente** (id_customer_supplier), **Emisor** (id_issuer_customer_supplier) y **Proyecto** (id_proyect).
- **Metodo de pago** (PUE o PPD, metodo_pago) y **Forma de pago** (forma_pago, ej. 03 transferencia).
- **Uso CFDI** (uso_cfdi), **Moneda** (currency) y **Tipo de cambio**.
- **Tipo de comprobante** (I ingreso, E egreso, P pago).
- **Direccion** (invoice_direction): venta, compra o sin_clasificar.

## Campos importantes de abonos, bancos y cuentas
- **Abono**: Parcialidad, Saldo anterior, Importe, Insoluto, Forma de pago, Fecha del pago, Numero de operacion y su estatus.
- **Solicitud de cancelacion**: Motivo, Folio fiscal que sustituye y Nota interna.
- **Cuenta bancaria**: descripcion, banco, sucursal, tipo, interes ordinario, interes moratorio, anualidad, reembolso y proyecto.
- **Estado de cuenta**: periodo, cargos, abonos, saldo inicial y final, estado.
- **Empresa**: RFC, regimen fiscal, codigo postal, Empresa principal, Serie del CFDI y estatus del CSD.
- **Ticket**: descripcion, estado (texto libre) y nota.
- **Cuenta fiscal**: descripcion y saldo.

## Preguntas frecuentes sobre timbrado y cancelacion
- **Por que no puedo timbrar?** Pulsa Revisar ante SAT: la lista de errores dice que corregir. Revisa tambien que la factura tenga proyecto, conceptos autorizados y que tu rol pueda actualizar facturas.
- **Timbre pero no veo el folio fiscal.** El timbrado no se completo; revisa el rechazo del PAC y reintenta.
- **Puedo corregir una factura ya timbrada?** Fiscalmente se corrige con una cancelacion o una nota de credito, no editandola. No documentado: si el sistema bloquea la edicion de una factura timbrada.
- **La cancelacion sigue en proceso.** El receptor tiene 72 horas; usa Consultar al SAT.
- **Por que el motivo 01 pide un folio?** Porque sustituye el comprobante por otro ya timbrado.
- **Cual es el ambiente de Pruebas?** Comprobantes sin validez fiscal real; solo Produccion es real.

## Preguntas frecuentes sobre cobros, cotizaciones y bancos
- **Por que no me deja abonar?** La factura debe estar timbrada, ser PPD, tener saldo y el importe no puede pasar del saldo.
- **Cuando se timbra el REP?** Cada abono se timbra aparte, desde Complemento, con Timbrar complemento.
- **Por que mi factura PUE no admite abonos?** En PUE el pago ya se acredito al emitirla.
- **No me deja convertir la cotizacion.** Debe estar Aprobada, vigente y con partidas autorizadas.
- **Que es una empresa principal?** La propia empresa; su RFC clasifica los XML como compra o venta.
- **El estado de cuenta quedo en Revisar.** Las sumas o el saldo no cuadran; puedes vincular movimientos igual.

## Preguntas de datos que se pueden hacer al asistente BI
- Cuantas facturas hay por estatus.
- Total de facturas por cliente.
- Facturas timbradas este mes.
- Facturas pendientes de timbrar.
- Facturas canceladas en el ultimo trimestre.
- Facturas de venta contra facturas de compra.
- Total facturado por mes en grafica de barras.
- Facturas del cliente X con su total y folio fiscal.
- Facturas en dolares.
- Cuentas bancarias por banco.
- Cuantos tickets hay por estado.
- Servicios del catalogo por costo.
Los abonos y complementos de pago pueden no estar disponibles para consulta segun el rol.
