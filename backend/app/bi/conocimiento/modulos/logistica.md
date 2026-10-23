---
modulo: logistica
entidades_clave: [logistics_trip, logistics_quotation, logistics_unit, logistics_service_request]   # 1 a 4 tablas del registro que un rol debe poder LEER para ver este manual
---
# Logistica

## Que es y para que sirve
El modulo Logistica sirve para operar el transporte y el almacenaje de mercancia de clientes: cotizar un servicio, recibir la solicitud del cliente, programar el viaje con unidad, remolque y operador, guardar la evidencia de entrega, atender incidencias, dar mantenimiento a la flota y cobrar. Tambien lleva embarques de comercio exterior y racks retornables. Todo se guarda por cliente (tabla customer_supplier, la misma de Clientes y proveedores). Logistica tiene su propio almacen de mercancia en custodia (logistics_warehouse, logistics_location, logistics_inventory), separado del Inventario general: dar acceso a Inventario no da acceso a Logistica.

## Pantallas y donde encontrarlas
En el menu lateral, grupo "Logistica", hay secciones.
Comercial: Cotizaciones, Solicitudes, Expedientes.
Operaciones: Viajes, Evidencias, Incidencias.
Flota: Unidades, Remolques, Operadores, Mantenimientos.
Almacen: Almacen y Localizar (son las pantallas del Inventario general, no hay almacen logistico aparte en el menu).
Finanzas: Facturas, Sucursales, Cuentas por cobrar, Factura manual.
Comercio exterior: Proveedores y Embarques.
Cada pantalla muestra una tabla con buscador, boton Actualizar y un formulario plegable para crear o editar.

## Pantallas de CRM que usa Logistica
En el grupo "CRM" del menu lateral aparecen cuatro pantallas que pertenecen a Logistica: Contactos, Direcciones, Contratos y Tarifas, ademas de Clientes. Ahi se registran los contactos operativos de un cliente, sus direcciones (tipo operativa por omision), sus contratos logisticos con nivel de servicio (SLA) estandar o premium, y las tarifas negociadas por tipo de servicio, origen, destino y tipo de unidad, en pesos (MXN) o dolares (USD). Dependen de tener permiso sobre las entidades de Logistica correspondientes.

## Como crear o editar un registro en Logistica
Es igual en casi todas las pantallas.
1. Abre la pantalla (por ejemplo Viajes).
2. Despliega el formulario "Nuevo ..." al inicio de la pagina.
3. Llena los campos obligatorios (los marcados) y elige cliente y relaciones en las listas.
4. Pulsa Guardar. El registro aparece en la tabla.
Para editar pulsa el lapiz de la fila: el formulario se abre con los datos; guarda de nuevo. Para eliminar pulsa el bote de basura y confirma. Si falta un dato o es invalido (por ejemplo un numero negativo), el sistema muestra un aviso en rojo y no guarda.

## Como llevar una operacion de transporte de principio a fin
1. En Cotizaciones registra la cotizacion del cliente (folio, tipo de servicio, origen, destino, kilometros, maniobras, almacenaje, total) en estatus borrador y pasala a enviada.
2. Si el cliente acepta, marca la cotizacion como aceptada.
3. En Solicitudes registra la solicitud de servicio del cliente (puede ligarse a la cotizacion del mismo cliente), con prioridad y fechas deseadas de recoleccion y entrega.
4. En Viajes crea el viaje: requiere cliente y solicitud; asigna unidad, remolque y operador, costos planeados y fechas.
5. Avanza el estatus del viaje hasta entregado y cerrado; despues facturado.
6. En Evidencias sube foto, firma y coordenadas de la entrega.
El sistema no obliga el orden de los estatus: tu eliges el que corresponde.

## Como registrar un mantenimiento
1. Abre Flota > Mantenimientos y crea uno nuevo.
2. Elige la unidad, escribe el tipo de mantenimiento, la fecha programada y el costo.
3. Deja el estatus en abierta mientras se trabaja; cambia a "en proceso" si ya inicio.
4. Para cerrarlo, cambia a cerrada Y captura la fecha de cierre: son obligatorias juntas.
Si el estatus no es cerrada no se puede dejar fecha de cierre, y la fecha de cierre no puede ser anterior a la programada. Registrar un mantenimiento no cambia solo la disponibilidad de la unidad; eso se edita en la unidad.

## Como registrar una incidencia de viaje
1. Abre Operaciones > Incidencias y crea una nueva.
2. Elige el viaje afectado, escribe el tipo de incidencia y la descripcion.
3. Elige la severidad (baja, media, alta o critica) y, si aplica, el responsable.
4. Guarda; empieza en estatus abierta.
5. Cuando avance, edita el estatus a en proceso, resuelta o cerrada (o cancelada si fue un error).

## Como registrar la evidencia de un viaje
1. Abre Operaciones > Evidencias y crea una nueva.
2. Elige el viaje y escribe el tipo de evidencia (texto libre, obligatorio).
3. Anota la ruta de la foto o de la firma y la referencia documental si las tienes.
4. Captura latitud (entre -90 y 90) y longitud (entre -180 y 180) si las conoces; fuera de ese rango no se guarda.
5. Guarda. Queda la fecha de captura; el campo "Capturada por" es opcional.
No documentado: la carga del archivo de foto o firma desde la pantalla; el formulario solo pide la ruta.

## Como registrar un expediente y su factura
Un expediente (Comercial > Expedientes) agrupa lo que se factura a un cliente por un servicio: folio, origen, destino, sucursal emisora, forma de pago (99 por omision), metodo de pago (PUE por omision) y uso de CFDI (G03 por omision). Su estatus es abierto, facturando o facturado. Si falla la facturacion, el campo "Ultimo error de facturacion" guarda el motivo. Los viajes pueden ligarse a un expediente. La factura se emite en Finanzas > Facturas o Factura manual (modulo Facturacion). No documentado: si el boton de facturar un expediente completo genera la factura automaticamente.

## Como llevar cuentas por cobrar
1. Primero la factura debe existir en Facturacion.
2. En Finanzas > Cuentas por cobrar crea una nueva: elige cliente y factura (deben ser del mismo cliente), importe (no negativo) y fecha de vencimiento.
3. Estatus inicial: pendiente. Al cobrarse, cambialo a pagado y captura la fecha de pago.
4. Si pasa la fecha sin pago, ponlo en vencido.
El sistema no cambia el estatus solo ni marca vencidos automaticamente; se captura a mano. No documentado: un calculo automatico de vencimiento.

## Estatus y que significan en Logistica: cotizaciones, solicitudes, viajes y cobranza
Cotizacion: borrador, enviada, aceptada, rechazada, vencida, cancelada.
Solicitud: solicitado, aprobado, programado, cancelado. Prioridad: baja, normal, alta, urgente.
Viaje: solicitado, planeado, asignado, cargado, en transito, en ruta, retrasado, entregado, cerrado, facturado, cancelado.
Expediente: abierto, facturando, facturado.
Embarque: registrado, en transito, en aduana, liberado, entregado.
Incidencia: abierta, en proceso, resuelta, cerrada, cancelada. Severidad: baja, media, alta, critica.
Mantenimiento: abierta, en proceso, cerrada.
Cuenta por cobrar: pendiente, pagado, vencido.

## Estatus y que significan en Logistica: flota, almacen y registros activos
Unidad: disponibilidad disponible, en viaje, mantenimiento, fuera de servicio; estado del registro activo o inactivo.
Remolque, operador, almacen, ubicacion, sucursal, contrato, tarifa, direccion, contacto: activo o inactivo.
Rack: en cliente, en almacen, pendiente de retorno, en reparacion; condicion bueno, regular o danado.
Inventario logistico: activo, pendiente de surtido, surtido, inactivo.
No hay transiciones obligatorias en ningun estatus de Logistica: se puede pasar de cualquier estatus valido a otro.

## Reglas y permisos importantes
El acceso se da por rol en el Gestor de roles y permisos, entidad por entidad (logistics_trip, logistics_unit, etc.). Los roles de fabrica: Administrator todo; Almacenista captura (crea, lee y edita, no elimina); Gerente solo consulta. Esos valores solo aplican a instalaciones nuevas; tu empresa puede haberlos cambiado.
El cliente de un registro debe ser de tipo cliente (no proveedor). El viaje, la cotizacion, la solicitud y el expediente deben ser del mismo cliente que se elige. Las fechas de entrega no pueden ser anteriores a las de recoleccion. Los costos, kilometros e importes no pueden ser negativos. Los folios, numeros de contrato, placas y numeros de licencia no se pueden repetir.
Eliminar un registro lo oculta (no lo borra de la base).
Todo el modulo depende de que el plan de la empresa lo incluya.

## Almacen logistico y mercancia en custodia
La mercancia de clientes se registra con SKU, descripcion, cantidad, lote y numero de serie, en una ubicacion de un almacen logistico (almacen > ubicacion con codigo, zona y capacidad). Cada alta o cambio de cantidad que este ligada a un producto del Inventario general deja un movimiento de entrada o salida en el libro del Inventario, marcado como origen logistica. Si no esta ligada a un producto, solo cambia el saldo logistico y no queda rastro de cuanto entro o salio. Las pantallas propias de almacenes, ubicaciones, inventario y racks existen pero ya no aparecen en el menu lateral: en el menu se usa Almacen y Localizar del Inventario general.

## Campos importantes
Folio: identificador unico del viaje, cotizacion o expediente.
Cliente: empresa a la que se presta el servicio.
Costo planeado / costo real / ingreso: lo estimado, lo gastado y lo cobrado en un viaje.
Kilometros: distancia del viaje.
Recoleccion y entrega planeadas / reales: fechas y horas de lo programado y de lo que paso.
Referencia de proveedor, de ruta y de expediente: textos libres de apoyo en el viaje.
Restricciones: notas especiales del viaje.
Placas: identificador de unidad o remolque.
Kilometraje: odometro de la unidad.
Vencimiento de seguro y de verificacion: fechas de la unidad.
Puntaje de desempeno: calificacion numerica del operador.
Vencimiento de licencia: fecha del operador.
BL: numero de conocimiento de embarque.

## Preguntas frecuentes
- No me deja guardar un viaje: ¿que falta? -> Cliente y solicitud de servicio son obligatorios y deben ser del mismo cliente; revisa que fechas y costos sean validos.
- ¿Puedo ligar un viaje a una unidad que esta en mantenimiento? -> El sistema no lo impide; revisa la disponibilidad de la unidad.
- ¿Por que no veo Logistica? -> Tu rol no tiene lectura de entidades de Logistica o el plan de la empresa no lo incluye; pide acceso al administrador.
- ¿Donde veo cuanto hay en el almacen? -> En Almacen o Localizar del grupo Logistica (Inventario general).
- ¿Como cierro un mantenimiento? -> Cambia el estatus a cerrada y captura la fecha de cierre.
- ¿Se puede eliminar una cotizacion? -> Solo si tu rol tiene permiso de eliminar; queda oculta, no borrada.

## Preguntas de datos que se pueden hacer al asistente BI
- Cuantos viajes hay por estatus
- Viajes retrasados de este mes
- Ingreso total y costo real de viajes por cliente
- Top 5 clientes por ingreso en viajes
- Cotizaciones aceptadas contra rechazadas
- Unidades disponibles y unidades en mantenimiento
- Mantenimientos abiertos y su costo total
- Operadores con licencia vencida o por vencer
- Incidencias de logistica abiertas por severidad
- Cuentas por cobrar vencidas y su importe
- Embarques en aduana
- Racks por estatus y condicion
No documentado: si tu rol puede preguntar por todas estas tablas; el asistente solo responde sobre lo que tu rol puede leer.
