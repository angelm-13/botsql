-- Tres tipos de notificacion mas para el ciclo de vida del vale de almacen,
-- sumados a los tres de `20261005110000_tipos_de_notificacion_de_almacen.sql`.
-- Mismo motivo que esa migracion: `notification.notification_type_check`
-- solo se escribe al CREAR la tabla, y un tipo nuevo que falte aqui hace
-- que `create_notification` truene en silencio (try/except) sin avisar en
-- ningun lado.
--
-- Los tres, de `warehouse_voucher_service.py`:
--   * warehouse_voucher_prevoucher_pending: a quien puede autorizar
--     (Almacen), cuando un Supervisor deja un prevale nuevo.
--   * warehouse_voucher_delivered: al responsable (y a quien recoja, si
--     esta delegado), cuando el material sale del almacen -- un vale
--     directo al crearse, o un prevale al autorizarse (son el mismo
--     evento de negocio en este sistema).
--   * warehouse_voucher_custody_confirmed: a quien opera el almacen,
--     cuando el responsable confirma que recupero el material de la
--     persona a la que se le habia entregado.
--
-- Se reaplica en cada arranque del pod (ver ARQUITECTURA_TYAKXA_TNY.md 7.1):
-- DROP CONSTRAINT IF EXISTS + ADD CONSTRAINT no truena la segunda vez.
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
        'warehouse_voucher_prevoucher_pending',
        'warehouse_voucher_delivered',
        'warehouse_voucher_custody_confirmed',
        'custom'
    )
);

COMMIT;
