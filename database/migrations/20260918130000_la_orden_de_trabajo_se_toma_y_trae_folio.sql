-- La orden de trabajo: folio propio, responsable real, y supervisor que la toma.
--
-- Que cambia, y por que
-- ---------------------
-- **El folio ya NO lo genera el sistema (cambio del 2026-10-16).** Esta
-- migracion le ponia `OT-<anio>-<consecutivo>` a todo proyecto sin folio, y la
-- pantalla inventaba un "PRJ-000006" cuando no habia ninguno. Adser usa ese
-- campo -la "Partida"- como referencia propia, que puede repetirse y puede
-- quedar vacia: no se inventa nada. Ver el paso 2 de abajo.
--
-- **El supervisor TOMA el proyecto.** `id_supervisor` era un desplegable del
-- formulario, o sea que quien capturaba la orden repartia el trabajo del
-- taller desde su escritorio. Ahora el proyecto sale sin supervisor y lo toma
-- quien lo va a sacar adelante -- por capacidad `project_execution`, no por
-- nombre de rol. Eso necesita dos tipos de evento nuevos en el expediente,
-- que es lo unico que esta migracion cambia de esquema.
--
-- **El responsable es quien lo crea.** No hace falta migracion: es
-- `create_project` quien deja de aceptar `leader` del cuerpo. Los proyectos
-- que ya tengan un responsable distinto de su autor se quedan como estan --
-- reasignarlos seria reescribir a nombre de quien esta el trabajo de alguien.
--
-- **La orden de compra del cliente y su partida** salen del formulario por
-- peticion. Las columnas NO se borran: `purchase_order` y
-- `purchase_order_item` guardan el numero del documento del cliente, y tirarlo
-- perderia el unico dato que liga la orden con el papel que la autorizo.

BEGIN;

-- 1. El expediente tiene que poder contar que alguien tomo o solto el proyecto.
--
-- Esta migracion se reaplica en cada arranque del pod, en el mismo orden que
-- las que siguen (20260921100000 amplia esta misma lista con
-- 'document_attached'/'document_removed'). Si aqui se dejara solo lo que
-- este commit necesitaba, el DROP+ADD de esta migracion volveria a angostar
-- la lista un instante antes de que la siguiente la ampliara de nuevo -- y
-- si ya existe una fila real de esos eventos, el ADD CONSTRAINT revienta
-- contra esa fila. Se deja aqui de una vez la union completa.
--
-- 'task_status_changed'/'task_note' tambien van aqui por el mismo motivo:
-- `task_service.py` (transition_task/add_task_note) los escribe desde antes
-- de este commit, y un ADD CONSTRAINT que no los incluya revienta de
-- inmediato contra cualquier base con proyectos reales que ya tengan uno de
-- esos eventos -- no contra un volumen vacio, que es donde se probo esto
-- antes de encontrar el problema en datos reales (tyakxa-dev, 2026-09-28).
ALTER TABLE proyect_event DROP CONSTRAINT IF EXISTS proyect_event_event_type_check;

ALTER TABLE proyect_event ADD CONSTRAINT proyect_event_event_type_check CHECK (
    event_type IN (
        'created', 'status_changed', 'message', 'task_event',
        'task_status_changed', 'task_note',
        -- El recorrido comercial, que corre en paralelo al de taller.
        'management_transition',
        -- Lo acordado y lo cobrado, cada uno por su lado.
        'payment_agreed', 'payment_settled',
        -- Quien se hizo cargo del proyecto en el taller, y cuando lo solto.
        -- Van como evento y no como una columna de fecha porque un proyecto
        -- puede cambiar de manos varias veces, y lo que importa es la linea de
        -- tiempo: quien lo tenia cuando paso lo que paso.
        'taken', 'released',
        -- Adjuntos del expediente.
        'document_attached', 'document_removed'
    )
);

-- 2. (RETIRADO 2026-10-16) Folio automatico `OT-<anio>-<consecutivo>`.
--
-- Aqui se le ponia un folio inventado a todo proyecto sin partida, y como esta
-- migracion se reaplica en cada arranque, el numero que alguien veia en
-- pantalla cambiaba solo en el siguiente despliegue. La partida (`folio`) es
-- una REFERENCIA LIBRE de quien captura -opcional, puede repetirse- y vacia se
-- queda vacia. Lo que este paso ya escribio en bases existentes se limpia con
-- `backend/scripts/limpiar_folios_autogenerados.py` (con --dry-run y
-- respaldo), no con una migracion: una migracion corre sin parar y no debe
-- reescribir datos.

COMMIT;
