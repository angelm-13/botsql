---
modulo: pos
entidades_clave: [pos_terminal, pos_admin]   # son permisos con nombre propio (capacidades), no tablas: el modulo se opera por pantalla
---
# Punto de venta

## Que es y para que sirve
El Punto de venta (POS) es la caja de mostrador: el cajero abre su turno, busca productos, cobra la venta, retira efectivo y al terminar hace el corte. Tambien tiene catalogo, tablero de ventas y promociones para quien administra. Es un modulo que se compra y se activa aparte (el plan de la empresa debe incluirlo) y se gobierna con dos permisos: Caja del punto de venta (pos_terminal, para el cajero) y Admin del punto de venta (pos_admin, para configuracion y reportes).

## Como se relaciona con el nucleo y con Inventario
Antes el punto de venta tenia su propia base de datos (pos_enterprise). Ya no: desde la migracion que lo integro corre sobre la misma base del sistema, y comparte tablas en lugar de copiarlas. Su catalogo ES el de Inventario (tabla product); sus categorias son las familias de producto; sus clientes son los de Clientes y proveedores; y al cobrar descuenta existencias del Inventario general en una ubicacion llamada "Punto de venta - mostrador". Por eso un producto o una existencia nunca se sincroniza ni se duplica. La factura (CFDI) de una venta se emite desde el modulo Facturacion; el POS no tiene facturacion propia.

## Pantallas y donde encontrarlas
Menu lateral, grupo "Punto de venta", con estas secciones:
Caja: "Punto de venta" (la caja para cobrar) y "Turno" (abrir, retirar efectivo y cortar). Permiso pos_terminal.
Catalogo: "Catalogo" de productos y categorias. Se ve con pos_terminal; dar de alta requiere pos_admin.
Almacen: "Almacen" y "Localizar", que son las pantallas del Inventario general.
Reportes: "Tablero". Permiso pos_admin.
Promociones: "Promociones". Permiso pos_admin.
Quien tiene el modulo en el plan pero ninguno de los dos permisos no ve el grupo.

## Como abrir un turno de caja
1. Entra a Caja > Turno.
2. Escribe el nombre de la caja (por ejemplo "Caja 1") y el fondo inicial, que es el efectivo con el que arranca el cajon.
3. Pulsa "Abrir turno".
Sin turno abierto no se puede cobrar. Solo puede haber un turno abierto por proyecto: si ya hay uno, el sistema no deja abrir otro. En la pantalla de cobro tambien hay un boton "Abrir turno de caja" que abre el turno con fondo cero.

## Como cobrar una venta en la caja
1. Entra a Caja > Punto de venta y confirma que diga "Turno abierto".
2. Busca el producto por nombre o SKU y tocalo para agregarlo; usa mas o menos para cambiar la cantidad.
3. Elige el tipo de venta (para llevar, en el lugar, a domicilio o en linea) y la forma de pago (efectivo, tarjeta o transferencia).
4. En efectivo captura lo recibido para ver el cambio.
5. Pulsa Cobrar. Se genera el ticket con folio (V000001, V000002...) que corre por proyecto.
La venta queda pagada, descuenta el inventario y se suma al corte del turno. El precio lo toma el sistema del producto, no del navegador.

## Que pasa si falta existencia o no hay turno
El cobro es todo o nada: la venta, su pago y el descuento de inventario se guardan juntos. Si algun producto no tiene existencia suficiente en el mostrador, no se cobra nada y no queda venta a medias. Si no hay turno abierto, tampoco se cobra. Las cantidades deben ser enteras (piezas). Si lo cobrado es menor al total, el sistema rechaza el pago e indica cuanto falta. Si en la caja ves un mensaje poco claro al cobrar, revisa primero que haya turno abierto y existencia del producto. Si fisicamente hay mercancia que el sistema no tiene, lo que falta es una entrada en Inventario, no vender a ciegas.

## Como retirar efectivo del cajon
1. En Caja > Turno, con el turno abierto, ve a "Retirar efectivo".
2. Captura el importe (mayor a cero) y el motivo (obligatorio).
3. Pulsa "Registrar retiro".
El retiro se resta del efectivo esperado en el corte. Sacar dinero sin registrarlo aparece despues como faltante.

## Como hacer el corte y cerrar el turno
1. En Caja > Turno, cuenta el cajon.
2. Declara a ciegas lo contado por cada forma de pago (efectivo, tarjeta, transferencia); hay que declarar al menos una. El sistema no muestra lo esperado antes de que declares.
3. Elige el tipo de corte: "Corte Z (cerrar)" para terminar el turno o "Corte X (revision)" para revisar a media jornada.
4. Pulsa el boton y revisa la tabla Esperado / Declarado / Diferencia.
Lo esperado es lo cobrado por forma de pago menos el cambio entregado; en efectivo, ademas, mas el fondo inicial y menos los retiros. Se guarda lo declarado, lo esperado y la diferencia.
No documentado: el sistema marca el turno con estatus closed_x tras un corte X y los turnos abiertos son solo los open, aunque la pantalla dice que la caja sigue abierta; si no puedes cobrar tras un X, abre otro turno.

## Como dar de alta un producto o una categoria
Solo con permiso pos_admin.
1. En Catalogo pulsa "Nuevo producto".
2. Captura SKU, nombre, categoria, precio de venta, existencia inicial y los dos datos obligatorios del Inventario: Factura de compra (numero de factura) y Material (numero de material). En el sistema un producto existe porque se compro; por eso se piden, y no se inventan.
3. Guarda. El producto queda en el Inventario general; la existencia inicial entra como movimiento de recepcion en el mostrador.
Una categoria nueva ("Nueva categoria") es una familia de producto; el color no se guarda.

## Como crear una promocion
Solo con permiso pos_admin.
1. En Promociones pulsa "Nueva promocion".
2. Escribe el nombre y elige el tipo de regla: descuento en porcentaje, descuento de importe fijo, compra X y llevate Y, unidad n gratis, hora feliz o precio de combo.
3. Captura los datos de la regla (porcentaje, importe, cantidades u horas), la prioridad y si se acumula con otras.
4. Guarda. Aparece en la tabla con su uso.
No documentado: que el cobro aplique las promociones automaticamente, y como editar o desactivar una promocion ya creada; el cobro actual solo registra un descuento si viene en el renglon de la venta.

## Estatus y que significan
Turno: open (abierto), closed_x (corte X), closed_z (cerrado).
Venta: open, suspended, paid (pagada), cancelled, refunded, partially_refunded. Al cobrar, la venta nace y queda en paid dentro de la misma operacion.
No documentado: como suspender, cancelar o devolver una venta; esos estatus existen pero la caja actual no los asigna.
Tipo de venta: para llevar, en el lugar, a domicilio, en linea.
Forma de pago aceptada: efectivo, tarjeta, transferencia, credito local, puntos de lealtad y plataforma de entrega; la caja ofrece efectivo, tarjeta y transferencia.
Promocion: activa o inactiva.
Gasto: recorded, approved, rejected. Orden de compra: draft, sent, partially_received, received, cancelled.

## Credito, lealtad, gastos, compras y variantes
Existen tablas para el credito del cliente (fiado, con limite y saldo), puntos de lealtad, gastos, ordenes de compra y variantes de producto (por ejemplo talla o color).
No documentado: pantalla o flujo para usarlas. Hoy el menu del POS no tiene esas pantallas; pagar con credito local o con puntos no mueve saldos de credito ni de lealtad. Los gastos solo se consultan por servicio, sin pantalla.

## Tablero y reportes
El Tablero muestra ingresos, tickets, ticket promedio y descuentos, y desgloses por categoria, por forma de pago y margen por producto, de ventas pagadas. El resumen del dia sale del turno abierto: sin turno abierto muestra cero. El margen usa el costo que se copio al vender; el producto no guarda costo, asi que si la caja no lo manda queda en cero y el margen se lee igual a la venta.
No documentado: algunas tarjetas del Tablero (ingresos, ticket promedio, descuentos) pueden verse en cero porque la pantalla y el servicio usan nombres de dato distintos. Para cifras confiables pregunta al asistente BI.

## Reglas y permisos importantes
pos_terminal permite usar la caja, el turno y ver el catalogo; pos_admin permite ademas dar de alta productos y categorias, crear promociones, ver gastos y el tablero. Para la caja basta tener cualquiera de los dos. De fabrica los tienen Administrator y Gerente; se cambian en el Gestor de roles y permisos.
Los turnos, ventas, retiros y promociones son del proyecto del usuario. El folio de venta es unico dentro del proyecto. El catalogo y las existencias son los de Inventario y no se acotan por proyecto.
Una existencia baja se considera 5 piezas o menos, porque el sistema no guarda un minimo por producto.

## Campos importantes
Fondo inicial: efectivo con el que se abre la caja.
Folio: numero de la venta (V000001...), unico por proyecto.
Subtotal, descuento, impuesto, total: partes del importe de la venta.
Cambio: lo devuelto cuando se paga de mas en efectivo.
Esperado / declarado / diferencia: lo que el sistema calculo, lo que contaste y la resta.
Tipo de venta: para llevar, en el lugar, a domicilio o en linea.
SKU: codigo del producto.
Existencia: piezas disponibles en el Inventario.
Prioridad y "se acumula": en una promocion, el orden y si suma con otras.

## Preguntas frecuentes
- ¿Por que no me deja cobrar? -> Revisa que haya turno abierto, que el producto tenga existencia y que el pago cubra el total.
- ¿Donde esta la base del POS? -> Ya no es aparte: usa la misma base y el mismo inventario del sistema.
- ¿Por que no puedo dar de alta un producto? -> Requiere permiso Admin del punto de venta y capturar factura de compra y material.
- ¿Puedo facturar una venta del POS? -> La facturacion es del modulo Facturacion. No documentado: facturar una venta desde la caja.
- ¿Que diferencia hay entre corte X y Z? -> El X es revision y el Z es el cierre del turno.
- ¿Por que la existencia del POS no coincide con Inventario? -> Debe coincidir: es la misma.
- ¿Puedo cobrar a credito? -> La forma existe pero la caja no la ofrece. No documentado.

## Preguntas de datos que se pueden hacer al asistente BI
- Ventas del punto de venta de hoy por forma de pago
- Total vendido este mes en el punto de venta
- Productos mas vendidos en la caja
- Ventas por categoria o familia de producto
- Cortes de caja con diferencia
- Retiros de efectivo del turno
- Productos con 5 piezas o menos
- Promociones activas y cuantas veces se usaron
- Margen por producto vendido
No documentado: estas tablas (pos_sale, pos_payment, pos_cash_session...) no tienen permiso de lectura propio por rol; si el asistente responde que la consulta no esta permitida, pide acceso al administrador.
