-- Notificaciones con destino: cada aviso dice A QUE REGISTRO lleva, para que un
-- clic en la campana abra el proyecto o el vale que lo origino.
--
-- Hasta aqui la tabla solo ligaba a proyectos (`id_proyect`) y los avisos de
-- vales llevaban `id_incident` suelto en `metadata`: nada que el front pudiera
-- leer de forma uniforme. `target_entity` + `target_id` son ese par uniforme:
--   * 'proyect' -> /proyect?abrir=<id>
--   * 'voucher' -> /vouchers?abrir=<id>
-- Un valor que el front no conozca se ignora (el aviso se ve, sin clic).
--
-- Se reaplica en cada arranque del pod (sin tabla de control, ver
-- ARQUITECTURA_TYAKXA_TNY.md 7.1): `ADD COLUMN IF NOT EXISTS`, UPDATEs que solo
-- tocan filas con `target_entity IS NULL`, y el CHECK se recrea con DROP IF EXISTS.
BEGIN;

ALTER TABLE notification
    ADD COLUMN IF NOT EXISTS target_entity VARCHAR(40),
    ADD COLUMN IF NOT EXISTS target_id INTEGER;

-- Lo que ya existia: los avisos de proyecto ya traen `id_proyect`...
UPDATE notification
   SET target_entity = 'proyect', target_id = id_proyect
 WHERE target_entity IS NULL AND id_proyect IS NOT NULL;

-- ...y los de vales traen el vale en `metadata` (columna JSON, no JSONB: se lee
-- con ->> y se comprueba que sea numero antes de convertir).
UPDATE notification
   SET target_entity = 'voucher', target_id = (metadata ->> 'id_incident')::integer
 WHERE target_entity IS NULL
   AND notification_type LIKE 'warehouse\_voucher\_%'
   AND (metadata ->> 'id_incident') ~ '^[0-9]+$';

CREATE INDEX IF NOT EXISTS ix_notification_target ON notification (target_entity, target_id);

-- Tipo nuevo: almacen marco la entrega y el responsable tiene que confirmar el
-- recibido. Un tipo que no esta en el CHECK revienta `create_notification` en
-- silencio (el aviso es "best effort"), asi que se agrega aqui.
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
        'custom'
    )
);

COMMIT;
