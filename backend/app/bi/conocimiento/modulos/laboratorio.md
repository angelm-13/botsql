---
modulo: laboratorio
entidades_clave: [laboratory_service_order, laboratory_equipment, laboratory_service_order_status_history]
---
# Laboratorio

## Que es el modulo Laboratorio y para que sirve
Laboratorio es el servicio tecnico: se registran los equipos que los clientes traen a reparar, se abre una orden de servicio por cada ingreso, se captura el diagnostico, se lleva la orden por un flujo de estatus (autorizacion, reparacion, entrega) y se emite un informe de diagnostico en PDF, con su version firmada. Cada cambio de estatus queda en un historial. El informe se archiva en el modulo Documentos.

## Pantallas y donde encontrarlas en Laboratorio
Menu lateral, grupo Laboratorio, opcion **Equipos y ordenes** (en los permisos puede llamarse "Ordenes de servicio" y "Equipos"). Es una sola pantalla titulada "Equipos de laboratorio" con tres paneles arriba: **Registrar equipo**, **Nueva orden** y **Ordenes activas** (lista con folio, contacto y estatus). Al pulsar una orden se abre abajo su espacio de trabajo: el formulario **Diagnostico** y el panel **Flujo y documentos** (cambio de estatus, Generar PDF, Subir firmado e Historial). El boton de arriba actualiza los datos.

## Como registrar un equipo en Laboratorio
1. En el panel **Registrar equipo** elige el **Cliente** (solo clientes, no proveedores).
2. Captura el **Tipo** (obligatorio), la **Marca**, el **Modelo** y el **Numero de serie**.
3. Pulsa **Registrar equipo**.
Al terminar el equipo queda disponible al crear ordenes de ese cliente. El numero de serie se guarda en mayusculas; si el mismo cliente ya tiene un equipo con esa serie, el sistema responde que esta duplicado y no lo guarda.

## Como crear una orden de servicio en Laboratorio
1. En **Nueva orden** elige el **Cliente**.
2. Elige el **Equipo** (solo aparecen los de ese cliente; si no esta, registralo primero).
3. Escribe el **Contacto** (nombre de quien entrega el equipo) y la **Falla reportada**; ambos son obligatorios.
4. Opcional: **Accesorios** entregados.
5. Pulsa **Crear orden**.
Al terminar se crea la orden con estatus **received** (Recibida), prioridad normal, fecha de recepcion de ese momento y un folio automatico con formato LAB-AAAAMM-numero. En el historial queda el primer registro "Registro inicial".

## Como capturar el diagnostico de una orden de Laboratorio
1. En **Ordenes activas** pulsa la orden.
2. En el formulario **Diagnostico** escribe el **Diagnostico tecnico** (obligatorio) y, si aplica, la **Reparacion recomendada**, el **Presupuesto** (numero, no negativo), el **Tiempo estimado** y observaciones.
3. Pulsa **Guardar diagnostico**.
Al guardar, el sistema anota la fecha de diagnostico si aun no tenia. Sin diagnostico tecnico no se puede pasar la orden a "pendiente de autorizacion" ni generar el PDF.

## Como cambiar el estatus de una orden de Laboratorio
1. Abre la orden en **Ordenes activas**.
2. En **Flujo y documentos** abre la lista **Siguiente estado**: solo muestra los estatus permitidos desde el actual.
3. Escribe **Comentarios**. Son obligatorios si el nuevo estatus es cancelled, not_authorized o not_repairable.
4. Pulsa **Cambiar**.
Al terminar la orden cambia de estatus y se agrega un renglon al Historial con el estatus anterior, el nuevo, el comentario y quien lo hizo. Al pasar a delivered se registra la fecha real de entrega.

## Como generar el informe de diagnostico en PDF
1. Abre la orden; debe tener diagnostico tecnico guardado.
2. En **Flujo y documentos** pulsa **Generar PDF**.
Se abre el PDF en una pestana nueva. El informe toma una fotografia de los datos de ese momento: empresa, cliente, contacto, equipo, accesorios, condicion de recepcion, falla, diagnostico, reparacion recomendada, presupuesto, tiempo estimado, tecnico y observaciones. Cada vez que lo generas se crea una version nueva en Documentos (documento con estado Emitido); no se borra la anterior.

## Como subir el informe de diagnostico firmado
1. Imprime el PDF, firmalo y escanealo.
2. Abre la orden y en **Flujo y documentos** elige el archivo con el selector (PDF) y pulsa **Subir firmado**.
Al terminar se agrega una version con origen "escaneo firmado" al documento del informe y ese documento pasa a estado Firmado. No cambia el estatus de la orden. Se descarga desde la pantalla Documentos, con el boton Versiones.

## Como consultar el historial de estatus de una orden
Abre la orden en **Ordenes activas**: el **Historial** se muestra al final del panel Flujo y documentos, en orden cronologico, con el nuevo estatus, fecha y hora y el comentario de cada cambio. Si el panel no muestra historial, tu rol puede no tener lectura del historial de estatus.

## Estatus de una orden de Laboratorio y que significan
La pantalla muestra el codigo en ingles. **received** Recibida; **awaiting_diagnosis** En espera de diagnostico; **diagnosing** En diagnostico; **pending_authorization** Pendiente de autorizacion del cliente; **authorized** Autorizada; **not_authorized** No autorizada; **repairing** En reparacion; **awaiting_parts** En espera de refacciones; **repaired** Reparada; **not_repairable** Sin reparacion; **ready_for_delivery** Lista para entrega; **delivered** Entregada; **cancelled** Cancelada. Los significados se deducen de los nombres; el sistema no trae descripciones propias.

## Transiciones permitidas entre estatus en Laboratorio
- received: awaiting_diagnosis, diagnosing, cancelled.
- awaiting_diagnosis: diagnosing, cancelled.
- diagnosing: pending_authorization, not_repairable, cancelled.
- pending_authorization: authorized, not_authorized, cancelled.
- authorized: repairing, awaiting_parts, cancelled.
- not_authorized: authorized, cancelled.
- repairing: awaiting_parts, repaired, not_repairable, cancelled.
- awaiting_parts: repairing, cancelled.
- repaired: ready_for_delivery (no se puede cancelar).
- not_repairable: ready_for_delivery, cancelled.
- ready_for_delivery: delivered.
- delivered y cancelled: son finales, no admiten mas cambios.

## Reglas y permisos importantes de Laboratorio
- Por defecto solo el rol Administrator tiene Laboratorio; cada instalacion decide a que roles se le da.
- Crear equipos y ordenes requiere permiso de crear; guardar diagnostico, cambiar estatus y generar o subir informes requieren permiso de actualizar.
- Si la orden tiene tecnico asignado y quien intenta modificarla es un empleado distinto, el sistema responde como si la orden no existiera.
- Los usuarios cliente o proveedor solo ven sus propias ordenes y equipos.
- Cancelar, no autorizar o declarar sin reparacion exigen comentario. Pasar a pendiente de autorizacion exige diagnostico.
- Una orden no se elimina desde el sistema; se cancela.

## Campos importantes de Laboratorio
- **Folio**: identificador de la orden, unico por proyecto.
- **Falla reportada**: lo que el cliente dice que falla.
- **Diagnostico tecnico / Reparacion recomendada**: lo que concluye el tecnico.
- **Presupuesto estimado** y **Costo final**: importes de la orden. No documentado: captura del costo final desde la pantalla.
- **Prioridad**: low, normal, high o urgent; desde la pantalla las ordenes se crean en normal.
- **Tecnico**: empleado asignado. No documentado: asignarlo desde la pantalla.
- **Fecha de recepcion / diagnostico / entrega estimada / entrega real**.
- **Accesorios entregados** y **Condicion de recepcion**.

## Preguntas frecuentes de Laboratorio
- **No encuentro el equipo al crear la orden.** Primero registralo y confirma que elegiste el mismo cliente.
- **Por que no me deja pasar a Pendiente de autorizacion?** Falta el diagnostico tecnico.
- **Por que no aparece "Cancelada" como siguiente estado?** Desde Reparada y desde Lista para entrega ya no se puede cancelar.
- **Puedo regresar una orden a un estatus anterior?** Solo si esta en la lista de transiciones permitidas.
- **Donde descargo el informe firmado?** En Documentos, version con origen escaneo firmado.
- **Dice serie duplicada.** Ese cliente ya tiene un equipo con esa serie.

## Preguntas de datos que se pueden hacer al asistente BI sobre Laboratorio
- "ordenes de laboratorio por estatus"
- "ordenes pendientes de autorizacion"
- "ordenes urgentes abiertas" (prioridad urgent)
- "ordenes recibidas este mes"
- "ordenes por cliente" y "equipos por cliente"
- "ordenes entregadas con su fecha de entrega"
- "ordenes asignadas a cada tecnico"
- "historial de estatus de una orden"
Tablas usadas: laboratory_service_order, laboratory_equipment y laboratory_service_order_status_history.
