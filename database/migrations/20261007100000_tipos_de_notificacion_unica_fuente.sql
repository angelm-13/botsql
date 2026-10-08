-- `notification.notification_type_check`: UNICA fuente de la lista de tipos.
--
-- Por que existe
-- --------------
-- La restriccion se recreaba en tres migraciones (la que crea la tabla, la de los
-- avisos de almacen y la de notificaciones con destino), cada una con SU lista. Como
-- las migraciones se reaplican TODAS en cada arranque, una vieja volvia a poner una
-- lista mas corta que las filas ya existentes y el `ADD CONSTRAINT` fallaba; con
-- `set -e` + `ON_ERROR_STOP=1` el backend no arrancaba. Es el mismo defecto que ya
-- tumbo `proyect_event_event_type_check` (ver CLAUDE.md).
--
-- Desde ahora solo esta migracion toca la restriccion, y es la mas nueva: al correr
-- ultima, su lista es la que queda. Un tipo nuevo se agrega AQUI, o mejor, en la
-- migracion mas reciente que tenga que mantenerla; hay una prueba que lo vigila.
--
-- Tipos nuevos de este cambio: los avisos del flujo de compras (orden por autorizar,
-- autorizada, rechazada, comprada, recibida y recibida en parte). Sin ellos,
-- `create_notification` revienta en silencio (el aviso es "best effort") y la
-- campana nunca los muestra.
--
-- Idempotente: DROP IF EXISTS + ADD. La lista es un SUPERCONJUNTO de todo lo que
-- cualquier version anterior dejo escribir, asi que no choca con filas existentes.
BEGIN;

ALTER TABLE notification DROP CONSTRAINT IF EXISTS notification_type_check;

ALTER TABLE notification ADD CONSTRAINT notification_type_check CHECK (
    notification_type IN (
        'project_status_change',
        'project_modified',
        'activity_log_created',
        'task_assigned',
        'material_confirmed',
        'warehouse_voucher_custody_assigned',
        'warehouse_voucher_pickup_assigned',
        'warehouse_voucher_overdue',
        'warehouse_voucher_delivered',
        'purchase_order_pending',
        'purchase_order_authorized',
        'purchase_order_rejected',
        'purchase_order_purchased',
        'purchase_order_received',
        'purchase_order_partially_received',
        'custom'
    )
);

COMMIT;
