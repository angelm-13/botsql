# Compras: recepción, avisos y la restricción de tipos de notificación (2026-10-07)

## Qué se agregó

**Recepción de lo comprado.** La orden ya no termina en "comprada": el almacén registra
cuánto llegó de cada renglón, por partes. `POST /purchase-orders/<id>/receive` con
`{lines: [{id_purchase_order_line, quantity}], note}`.

- Cada llamada **suma** a lo ya recibido (`quantity_received`). La orden pasa a
  `partially_received` y, cuando todos los renglones están completos, a `received`.
- Recibir de más se rechaza (`errors.order_receive_exceeds`): es una discrepancia con la
  factura, no una recepción. Todo o nada: un renglón malo revierte los demás.
- **Quien compró no recibe** (`errors.purchase_same_person`), ni siquiera con la capacidad.
- Solo confirma **cantidad**. No da entrada al inventario: lo comprado suele ser material de
  obra en texto libre, sin producto ni ubicación donde meterlo.
- Capacidad nueva **`purchase_receive`** (módulo `compras`, oculta): la llevan Almacenista,
  Gerente y Administrator; **Compras no**. Va aparte de `purchase_order` porque el almacén solo
  consulta las órdenes y darle "actualizar" le habría dado editar, enviar y cancelar. La ruta se
  guarda con *leer*; la capacidad la comprueba el servicio.

**Avisos (campana)**, con destino a la orden (`target_entity = purchase_order`, abre
`/ordenes-de-compra?abrir=<id>`):

| Evento | A quién avisa |
|---|---|
| Orden enviada (o devuelta a autorización por exceso) | quienes pueden autorizar (`purchase_authorize`) |
| Autorizada / rechazada (con motivo) | quien pidió la orden |
| Comprada | quienes pueden recibir (`purchase_receive`) y quien la pidió |
| Recibida / recibida en parte | quien la pidió, quien la compró y los líderes y supervisores de los proyectos |

Quien hace la acción no se avisa a sí mismo. Una orden por debajo del límite de autorización
(autorizada por la política) no avisa a nadie. Un fallo al avisar nunca revierte la acción.

## Defecto encontrado y corregido: `notification_type_check`

La restricción se recreaba en **tres** migraciones, cada una con su propia lista, y todas se
reaplican en cada arranque. Una migración vieja volvía a poner una lista más corta que las filas
existentes: el `ADD CONSTRAINT` fallaba y, con `set -e` + `ON_ERROR_STOP=1`, el initContainer
impedía que el backend arrancara. Demostrado: con una fila `warehouse_voucher_delivered`, la lista
de `20261005110000` falla con *"check constraint violated by some row"*.

Hoy **no ha ocurrido**: `adser-prod` y `tyakxa-dev` solo tienen notificaciones `custom`. Pasaría
con el primer aviso de entrega de vale (y con los de compras) más un reinicio del pod.

Corrección: una sola dueña, la migración más nueva
(`20261007100000_tipos_de_notificacion_unica_fuente.sql`), con la lista completa; las otras dos
dejaron de tocar la restricción. Prueba que lo vigila:
`backend/tests/test_security/test_notification_types_constraint.py` (una sola migración la
recrea, es la más nueva, y cubre todos los tipos que escribe el código).

**Regla para el futuro:** un tipo de notificación nuevo se agrega en esa migración (o en una más
nueva que la reemplace), nunca en una vieja.

## Migraciones nuevas (idempotentes)

- `20261007090000_resembrar_recibir_compras.sql`: siembra `purchase_receive` (solo agrega filas).
- `20261007100000_tipos_de_notificacion_unica_fuente.sql`: la restricción.

## Para promover a adser-prod

Va con el resto de compras (que sigue sin promoverse). Ojo: **mientras `adser-prod` siga en
`3e830da`, conserva el defecto de la restricción** (latente). Quedará corregido con la próxima
promoción que incluya `20261007100000`.
