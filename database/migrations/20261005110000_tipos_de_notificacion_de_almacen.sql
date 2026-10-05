-- `notification.notification_type_check` solo se escribe al CREAR la tabla
-- (`20260925120000_notificaciones_y_bitacoras.sql`), asi que un tipo nuevo
-- hay que agregarlo aqui -- sin esto, `create_notification` revienta con
-- `CheckViolation` en silencio (el aviso es "best effort", envuelto en
-- try/except) y la notificacion simplemente nunca aparece, sin error visible
-- en ningun lado. Detectado probando el flujo de custodia de vales en vivo.
--
-- Tres tipos nuevos, todos de `warehouse_voucher_service.py`/
-- `tasks_warehouse.py`:
--   * warehouse_voucher_custody_assigned: al responsable, cuando el vale
--     queda en manos de alguien mas (recoger o `/deliver-to`).
--   * warehouse_voucher_pickup_assigned: a esa persona, que le toca pasar
--     por el material.
--   * warehouse_voucher_overdue: lo que ya debio volver y no ha vuelto
--     (job periodico, antes solo visible al abrir la pantalla de vales).
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
        'custom'
    )
);

COMMIT;
