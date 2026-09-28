BEGIN;

-- `transition_task` y `add_task_note` (backend/app/services/task_service.py)
-- escriben "task_status_changed" y "task_note" en `proyect_event.event_type`
-- desde que existen (endpoints `/task/<id>/transition` y `/task/<id>/notes"),
-- pero ninguna migracion anterior amplio el constraint para aceptarlos --
-- 20260911180000 y 20260921100000 lo ampliaron para otros tipos nuevos
-- (`management_transition`, `document_attached`, etc.) y se les quedo este
-- par afuera. El resultado real es un 500 (IntegrityError, CheckViolation) en
-- cualquier cambio de estatus de tarea o nota de tarea via esos endpoints, en
-- cualquier instalacion que ya tenga aplicada 20260921100000 -- confirmado
-- reproduciendolo en docker compose local.
ALTER TABLE proyect_event DROP CONSTRAINT IF EXISTS proyect_event_event_type_check;

ALTER TABLE proyect_event ADD CONSTRAINT proyect_event_event_type_check CHECK (
    event_type IN (
        'created', 'status_changed', 'message', 'task_event',
        'management_transition', 'payment_agreed', 'payment_settled',
        -- 'taken'/'released' se perdieron aqui al resolver a mano un merge
        -- de git (fusion de initAlan/initAngm, 2026-09-25): esta lista
        -- reemplaza por completo a la de 20260911180000 en cada arranque
        -- (mismo patron de la migracion de arriba), asi que un evento real
        -- 'taken' escrito por `take_project` tronaba con CheckViolation
        -- contra ESTA migracion, no la vieja. Repuestos.
        'taken', 'released',
        'document_attached', 'document_removed',
        'task_status_changed', 'task_note'
    )
);

-- Mismo problema, otra columna: `waiting_material` y `delivered` se agregaron
-- a PROJECT_STATUSES/PROJECT_TRANSITIONS (backend/app/services/
-- project_management_service.py) en la migracion 20260911180000 -- el
-- comentario de esa migracion hasta los menciona por nombre -- pero nunca se
-- amplio el CHECK de `proyect.proyect_status` para aceptarlos. El resultado:
-- CUALQUIER instalacion (una fresca via `database/init.sql`, o una vieja que
-- ya traia `ck_proyect_status` de 20260822190000) rechaza esos dos estatus
-- con un 500 (IntegrityError) en cuanto algo intenta escribirlos, aunque la
-- transicion ya haya pasado el candado de rol y de maquina de estados en
-- Python. Confirmado reproduciendolo en docker compose local al intentar
-- entregar un proyecto completado.
--
-- Hay DOS constraints duplicados sobre la misma columna con el mismo cuerpo:
-- `ck_proyect_status` (nombrado a mano en 20260822190000) y
-- `proyect_proyect_status_check` (el que Postgres nombra solo para el CHECK
-- inline de `database/init.sql`, el bootstrap de una instalacion nueva). Se
-- consolidan en uno solo -- mantener dos constraints identicos que hay que
-- recordar actualizar juntos es como se llego a este descuadre.
ALTER TABLE proyect DROP CONSTRAINT IF EXISTS ck_proyect_status;
ALTER TABLE proyect DROP CONSTRAINT IF EXISTS proyect_proyect_status_check;

ALTER TABLE proyect ADD CONSTRAINT ck_proyect_status CHECK (
    proyect_status IN (
        'draft', 'submitted', 'authorized', 'denied', 'blocked',
        'in_progress', 'waiting_material', 'stopped', 'completed', 'delivered'
    )
);

COMMIT;
