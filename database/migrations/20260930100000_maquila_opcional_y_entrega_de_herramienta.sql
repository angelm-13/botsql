-- Dos cambios pedidos juntos, sin relacion tecnica entre si mas que llegar el
-- mismo dia:
--
-- 1. `proyect.requires_maquila`: no todo proyecto pasa por el taller
--    (pinturas, drenaje, cimientos). El gerente lo autoriza igual, pero debe
--    poder marcarlo completado directo desde "autorizado", sin la espera de
--    material ni "en proceso" -- pasos pensados para cuando el taller SI
--    participa. Ver `project_management_service.py` (validate_project_transition,
--    transition_project, _scoped_query).
--
--    NOT NULL con DEFAULT true: un proyecto existente, capturado antes de que
--    este campo existiera, se asume que SI requiere maquila -- es el
--    comportamiento que ya tenia (recorrido completo de taller obligatorio).
--
-- 2. `nm_incident_product.id_user_delivered_to` / `custody_confirmed_date`:
--    a que operador u otro supervisor se le entrega la herramienta de un
--    renglon del vale, y cuando el supervisor dueño del vale confirma que la
--    recupero. Es un paso INTERMEDIO -- la pieza sigue fuera del almacen
--    (`close_date` sigue vacio) hasta que alguien la devuelva de verdad. Ver
--    `warehouse_voucher_service.py` (asignar_entrega_de_renglon,
--    confirmar_recepcion_de_renglon).
--
-- Se reaplica en cada arranque del pod (sin tabla de control, ver
-- ARQUITECTURA_TYAKXA_TNY.md 7.1): las tres son `ADD COLUMN IF NOT EXISTS`,
-- no hacen nada la segunda vez que ya existen.
BEGIN;

ALTER TABLE proyect
    ADD COLUMN IF NOT EXISTS requires_maquila BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS id_user_delivered_to INTEGER REFERENCES "user"(id_user);

ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS custody_confirmed_date TIMESTAMP;

COMMIT;
