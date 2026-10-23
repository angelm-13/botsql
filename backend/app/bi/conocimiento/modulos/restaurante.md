---
modulo: restaurante
entidades_clave: [restaurant_waiter, restaurant_cashier, restaurant_kitchen, restaurant_admin]   # son permisos con nombre propio (capacidades), no tablas: el modulo se opera por pantalla
---
# Restaurante

## Que es y para que sirve
El modulo Restaurante lleva la operacion de un restaurante de principio a fin: el mesero abre mesas u ordenes para llevar y toma la comanda, la cocina la prepara, el mesero la entrega, la caja cobra y hace el corte, y la administracion mantiene el menu, las mesas, los meseros, las reservaciones, el inventario de insumos y las recetas. Al cobrar, el sistema descuenta los insumos segun la receta de cada platillo. Todo se guarda por proyecto (cada negocio ve solo lo suyo). El inventario de insumos es propio del restaurante, separado del Inventario general, aunque puede reflejarse en este ultimo.

## Pantallas y donde encontrarlas
En el menu lateral, grupo "Restaurante", hay cuatro pantallas, cada una con su propio permiso:
Meseros: servicio de mesas, comandas, ordenes para llevar y reservaciones.
Cocina: tablero de comandas por etapa (se actualiza solo cada 30 segundos).
Caja: cobro de cuentas entregadas, turno de caja, propinas y reporte de ventas.
Admin: administracion del restaurante, con pestañas Menu, Categorias, Mesas, Meseros, Reservaciones, Inventario, Recetas y Auditoria, y un resumen de venta acumulada, propinas, ticket promedio, mesas activas y tiempo promedio de entrega.

## Como atender una mesa (mesero)
1. En Meseros, toca una mesa libre del mapa de servicio: se abre una visita con un comensal. Si la mesa esta ocupada, toca la mesa para continuar su visita.
2. Si hay mas gente, pulsa "Agregar comensal": cada comensal tiene su propia cuenta.
3. Elige el comensal, selecciona el guisado cuando el platillo lo requiere (tacos, gorditas, quesadillas) y toca el platillo para agregarlo.
4. Revisa el detalle; usa "Quitar" para sacar un platillo.
5. Pulsa "Enviar a cocina": la comanda pasa a pedido. No se puede enviar una comanda vacia.
6. Cuando cocina la marque lista, aparece en "Salida de cocina": pulsa "Entregar".
Una mesa solo puede tener una visita activa a la vez.

## Como tomar una orden para llevar
1. En Meseros, en el mapa de servicio, escribe el nombre del cliente en "Orden para llevar" (obligatorio).
2. Pulsa "Para llevar". Se crea una orden con folio del dia (por ejemplo "Para llevar #7") que se reinicia cada dia y no ocupa mesa.
3. Agrega platillos y envia a cocina igual que en una mesa.
Una orden para llevar tiene un solo comensal: no se reparte la cuenta.

## Como cerrar una mesa o una orden
1. Entrega todos los platillos y cobra todas las cuentas en Caja.
2. En Meseros, con la visita seleccionada, pulsa "Cerrar mesa" (o "Cerrar orden" si es para llevar).
El boton se habilita solo cuando todas las cuentas con platillos estan cobradas ("Todo cobrado: la mesa se puede liberar"). Las cuentas vacias no estorban. Al cerrar, la mesa queda libre. Quitar un comensal solo es posible si su cuenta esta vacia y en borrador.

## Como trabaja la cocina
1. En Cocina hay tres columnas: Por preparar, En preparacion y Listo para entregar, ordenadas por antiguedad.
2. Pulsa "Comenzar" en una comanda pendiente: pasa a En preparacion.
3. Cuando termine, pulsa "Marcar listo": pasa a Listo para entregar y el mesero la ve para entregar.
Cocina solo puede mover esos dos pasos; no puede entregar ni cobrar. El tablero se refresca cada 30 segundos o con el boton Actualizar.

## Como cobrar una cuenta (caja)
1. En Caja, abre el turno con "Abrir caja" capturando el fondo inicial (necesario para cobrar efectivo).
2. En "Por cobrar" elige la cuenta; solo aparecen las ya entregadas.
3. Elige la propina (porcentaje, 10% por omision, o monto fijo) y la forma de pago: efectivo, tarjeta, transferencia o mixto (indica la parte en efectivo).
4. En efectivo captura lo recibido: el sistema calcula el cambio o lo que falta.
5. Pulsa Cobrar. Puedes imprimir o reimprimir el ticket (no es comprobante fiscal).
Con "Cobrar todo junto" se cobran de una vez todas las cuentas entregadas de la mesa; la propina se reparte entre ellas. Tarjeta y transferencia se pueden cobrar con la caja cerrada; efectivo y mixto no.

## Como hacer el corte de caja
1. En Caja, en "Turno actual", revisa que diga "Caja abierta".
2. Cuenta el efectivo del cajon y capturalo en "Efectivo al cierre".
3. Pulsa "Cerrar y cuadrar caja".
El sistema calcula lo esperado: fondo inicial mas el efectivo cobrado desde la apertura (solo la parte en efectivo de pagos mixtos; tarjeta y transferencia no cuentan) y guarda la diferencia contra lo que contaste. Solo puede haber una caja abierta a la vez. Tambien puedes consultar el reporte de ventas por rango de fechas (venta, propinas y numero de cuentas por dia).

## Como administrar el menu (admin)
1. En Admin > Menu pulsa "Nuevo platillo".
2. Captura nombre, categoria, precio, costo, si requiere guisado y el horario (todos los dias, entre semana, fin de semana o un dia).
3. Guarda. El platillo aparece en la pantalla de Meseros solo si esta activo y disponible ese dia.
Los guisados se dan de alta con "Nuevo guisado". Las categorias se editan en la pestaña Categorias: si el restaurante aun no define ninguna, se usan las de fabrica (taco, gordita, quesadilla, platillo del dia, postre, agua, refresco, cafe, dulce); al crear la primera propia, esas dejan de usarse. Eliminar platillos, mesas, meseros, guisados o categorias los desactiva (no se borran de la base).

## Como administrar mesas, meseros y reservaciones
Mesas: numero, capacidad y ubicacion. Meseros: nombre, nombre corto, maximo de mesas (15 por omision) y, opcional, usuario del sistema; un mesero no puede abrir mas mesas activas que su maximo.
Reservaciones: se registran desde Meseros (nombre, fecha, hora, personas) y se consultan en Admin > Reservaciones, con estatus pendiente por omision.
No documentado: otros estatus de reservacion ni como cancelarla desde la pantalla.

## Como llevar inventario de insumos y recetas
1. En Admin > Inventario, "Agregar insumo": descripcion, cantidad, unidad y costo unitario.
2. Para mover existencias, "Nuevo movimiento": entrada (suma), salida o merma (restan) o ajuste (fija la cantidad contada). Un movimiento que dejaria el saldo en negativo se rechaza.
3. En Admin > Recetas, "Agregar componente": elige platillo, insumo, cantidad y unidad. La unidad debe ser exactamente la del insumo (no hay conversion g/kg).
El Kardex muestra cada movimiento con saldo antes y despues. Si un insumo esta ligado a un producto del Inventario general, el movimiento tambien se anota alli con origen restaurante (merma cuenta como salida); si falla no se deshace. No documentado: la pantalla para ligar un insumo con un producto.

## Descuento automatico de insumos al cobrar
Al cobrar una cuenta, el sistema resta de cada insumo lo que indica la receta por la cantidad vendida. Nunca bloquea el cobro. Si algo no se pudo descontar, la caja muestra "Avisos de inventario": platillo sin receta (no se descuenta nada), existencias insuficientes (se descuenta hasta cero y se informa el faltante) o unidad de receta distinta a la del insumo (no se descuenta). Cada descuento queda en el Kardex como salida con motivo "Consumo por venta".

## Estatus y que significan
Comanda (cuenta de un comensal): borrador (se esta armando), pedido (enviada a cocina), en preparacion, listo para entrega, entregado, pagado. Solo avanza en ese orden, un paso a la vez; no se puede saltar ni regresar.
Visita (mesa u orden): active mientras esta abierta, closed al cerrarla.
Tipo de servicio: mesa o para llevar.
Turno de caja: open o closed.
Mesero: active (otros valores: No documentado).
Reservacion: pending por omision.
Forma de pago: efectivo, tarjeta, transferencia, mixto.
Movimiento de insumo: entrada, salida, merma, ajuste.
No documentado: cancelar una comanda; las pantallas muestran la etiqueta "Cancelada" pero el sistema no tiene un paso para cancelar.

## Reglas y permisos importantes
Cada pantalla tiene su permiso: Meseros (restaurant_waiter), Cocina (restaurant_kitchen), Caja (restaurant_cashier), Admin (restaurant_admin). Roles de fabrica: Mesero, Cocina, Caja Restaurante y Admin Restaurante (este ultimo ve las cuatro pantallas); Administrator tambien. Se ajustan en el Gestor de roles y permisos y requieren que el plan incluya Restaurante.
Con la configuracion de fabrica nadie tiene permiso de eliminar en Meseros, y por eso quitar un platillo de la comanda o quitar un comensal puede marcar "permiso denegado": hay que concederlo en el gestor.
Solo se edita una comanda en borrador. Efectivo exige caja abierta. Cada usuario ve solo datos de su proyecto.

## Campos importantes
Comensal: cada persona de la mesa, con su propia cuenta.
Guisado: guiso que acompana tacos, gorditas y quesadillas; un platillo puede exigirlo.
Propina: porcentaje o monto fijo sobre el subtotal; se suma al total de la cuenta.
Recibido / cambio: lo que entrega el cliente y lo que se devuelve.
Parte en efectivo: en pago mixto, lo cubierto en efectivo; solo eso entra al cajon.
Folio del dia: numero de la orden para llevar, reinicia cada dia.
Fondo inicial: efectivo con que arranca la caja.
Esperado / diferencia: lo que debia haber en el cajon y lo que falta o sobra.
Costo del platillo: costo de produccion; el precio es el de venta.
Maximo de mesas: tope de mesas activas por mesero.

## Preguntas frecuentes
- ¿Por que no puedo cobrar en efectivo? -> No hay caja abierta; abrela en Caja con el fondo inicial.
- ¿Por que no aparece una cuenta para cobrar? -> Solo se cobran cuentas en estatus entregado.
- ¿Por que no puedo enviar a cocina? -> La comanda esta vacia; agrega al menos un platillo.
- ¿Por que no puedo cerrar la mesa? -> Hay cuentas con platillos sin cobrar.
- ¿Puedo cobrar la mesa completa de una vez? -> Si, con "Cobrar todo junto".
- ¿Por que un platillo pide guisado? -> Esta marcado como "Requiere guisado" en el menu.
- ¿Por que no se descontaron insumos? -> El platillo no tiene receta o la unidad no coincide; revisa los avisos de inventario.

## Preguntas de datos que se pueden hacer al asistente BI
- Ventas del restaurante por dia de esta semana
- Platillos mas vendidos
- Propinas totales del mes
- Ticket promedio de las cuentas pagadas
- Mesas con mas servicios
- Insumos agotados o por debajo de cierta cantidad
- Valor del inventario de insumos
- Mermas del mes
- Reservaciones de esta semana
- Cierres de caja con diferencia
No documentado: estas tablas (restaurant_order, restaurant_visit, etc.) no tienen permiso de lectura propio por rol; si el asistente responde que la consulta no esta permitida, pide acceso al administrador.
