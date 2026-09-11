-- El proyecto de taller: lo que le falta para ser una orden de trabajo.
--
-- De que se parte
-- ---------------
-- `proyect` tenia siete columnas utiles: la empresa (`id_customer_supplier`),
-- el lider, el titulo, la descripcion y un estado. Le faltaba casi todo lo que
-- distingue un proyecto de taller de una carpeta con nombre: de que cotizacion
-- salio, contra que orden de compra se cobra, quien lo pidio, para cuando es y
-- que dibujo lo describe.
--
-- Se agrega sobre la tabla que ya hay en vez de crear una nueva: `task`,
-- `appointment` y los permisos ya apuntan a `proyect`, y duplicarla obligaria a
-- decidir cual de las dos es la buena cada vez que alguien consulte.
--
-- Dos estados, y solo UNO es nuevo
-- --------------------------------
-- El taller y la gerencia miran el MISMO proyecto y no preguntan lo mismo:
--
--     taller     autorizado -> en proceso -> en espera de material ->
--                terminado -> entregado
--     gerencia   pendiente por recibir orden de compra -> autorizado ->
--                cobrado, o cancelado
--
-- Con una sola columna esas dos vidas se pisan: un proyecto ENTREGADO que
-- todavia no se ha COBRADO no se puede representar, y quien quiera saber que
-- falta por cobrar tendria que deducirlo del estado de taller.
--
-- Pero el recorrido del TALLER ya existe. `project_management_service.py` lleva
-- una maquina de estados completa -- `draft`, `submitted`, `authorized`,
-- `in_progress`, `stopped`, `completed` -- con sus transiciones validas, sus
-- motivos obligatorios y su bitacora en `proyect_event`. Es esta misma lista en
-- ingles; solo le faltaban dos paradas: "en espera de material" y "entregado".
--
-- Asi que NO se crea una columna de taller paralela. Se amplia la que hay -- ver
-- `PROJECT_STATUSES` -- y se agrega solo `management_status`, que si es una
-- dimension nueva sin equivalente. Dos listas de estados sobre la misma tabla
-- acabarian discrepando, y el propio servicio ya advierte de eso en un
-- comentario: `task_service` llego a tener su copia escrita a mano.
--
-- `proyect_status` arranca en 'solicitado' por omision, que es lo pedido.
--
-- Las parcialidades van en tabla aparte
-- -------------------------------------
-- Un proyecto se cobra en varios pagos y cada uno tiene su fecha, su monto y el
-- porcentaje acordado. Tres columnas en `proyect` solo servirian para un pago;
-- con dos ya harian falta seis, y con tres, nueve. Una fila por pago es lo
-- unico que no se queda corto.
--
-- El porcentaje se GUARDA y no se calcula: lo que se acuerda con el cliente es
-- "40% al pedir", y si despues cambia el total del proyecto ese 40% pactado
-- sigue siendo el que se firmo. Recalcularlo contra el total de hoy reescribiria
-- el acuerdo.

BEGIN;

-- --- lo que le faltaba al proyecto --------------------------------------

ALTER TABLE proyect
    -- El numero con el que se le conoce dentro del taller. Nulo mientras no se
    -- le asigne: no todos los proyectos nacen con folio.
    ADD COLUMN IF NOT EXISTS folio VARCHAR(40),
    -- Quien lo pidio, por su nombre. Una empresa tiene varios ingenieros
    -- pidiendo cosas distintas, y `id_customer_supplier` solo dice la empresa.
    --
    -- Texto y no una llave a una tabla de contactos porque esa tabla no existe
    -- todavia -- solo hay `logistics_contact`, que es de otro modulo y de otra
    -- cosa. Inventar aqui el catalogo de contactos de toda la empresa es una
    -- decision mas grande que este cambio, y sin el catalogo el nombre suelto
    -- ya contesta "quien pidio esto".
    ADD COLUMN IF NOT EXISTS requested_by VARCHAR(160),
    -- La cotizacion de la que salio. Es una `invoice` con estado 'cotizacion':
    -- en TYAKXA la cotizacion y la factura son la misma tabla en dos momentos.
    ADD COLUMN IF NOT EXISTS id_quotation INTEGER REFERENCES invoice(id_invoice),
    -- La orden de compra del cliente. Es SU numero, de su sistema, asi que es
    -- texto: no hay fila nuestra a la que apuntar.
    ADD COLUMN IF NOT EXISTS purchase_order VARCHAR(60),
    -- El supervisor de taller. Distinto del `leader` que ya existia: el lider
    -- responde del proyecto ante el cliente y el supervisor manda en el piso.
    ADD COLUMN IF NOT EXISTS id_supervisor INTEGER REFERENCES "user"(id_user),
    -- La partida dentro de la orden de compra. Numero del documento del
    -- cliente, no de los nuestros.
    ADD COLUMN IF NOT EXISTS purchase_order_item INTEGER,
    -- Para cuando se comprometio.
    ADD COLUMN IF NOT EXISTS delivery_date DATE,
    -- El plano o la foto de lo que hay que hacer. Apunta al `document`, que ya
    -- lleva versiones, sha256 y tipo de archivo: guardar aqui una ruta suelta
    -- perderia todo eso y admitiria cualquier extension.
    ADD COLUMN IF NOT EXISTS id_drawing_document INTEGER REFERENCES document(id_document),
    -- La vida COMERCIAL del proyecto, la unica que no tenia donde vivir. El
    -- recorrido de taller se queda en `proyect_status`. Ver la cabecera.
    ADD COLUMN IF NOT EXISTS management_status VARCHAR(40)
        DEFAULT 'pendiente_orden_compra';

-- Si una version anterior de esta migracion creo la columna de taller, se
-- retira: el recorrido de taller vive en `proyect_status`.
ALTER TABLE proyect DROP COLUMN IF EXISTS shop_status;

-- El folio es unico entre los proyectos vivos. Parcial y no total: un proyecto
-- dado de baja no debe impedir reusar su folio.
CREATE UNIQUE INDEX IF NOT EXISTS uq_proyect_folio
    ON proyect (folio) WHERE folio IS NOT NULL AND deletion_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_proyect_entrega
    ON proyect (delivery_date) WHERE deletion_date IS NULL;

-- Los estados validos. CHECK y no enum de Postgres, como el resto de TYAKXA:
-- ampliar un CHECK es un ALTER normal y ampliar un enum no se puede deshacer
-- dentro de una transaccion.
--
-- Se admite NULO en los dos: un proyecto recien solicitado no ha entrado al
-- taller todavia, y forzarle un estado de taller diria que si.
DO $bloque$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_proyect_management_status') THEN
        ALTER TABLE proyect ADD CONSTRAINT ck_proyect_management_status CHECK (
            management_status IS NULL OR management_status IN (
                'pendiente_orden_compra', 'autorizado', 'cancelado', 'cobrado'
            )
        );
    END IF;
END
$bloque$;

-- El estado general arranca en 'solicitado'. Se pone por omision en la columna
-- que ya existia, sin tocar las filas que ya tengan uno.
ALTER TABLE proyect ALTER COLUMN proyect_status SET DEFAULT 'solicitado';

UPDATE proyect SET proyect_status = 'solicitado'
 WHERE (proyect_status IS NULL OR proyect_status = '') AND deletion_date IS NULL;

-- --- la incidencia, enlazada al proyecto --------------------------------
--
-- `task` y `appointment` ya apuntaban a `proyect`; `incident` no, y era el
-- unico de los tres que no se podia contestar desde el proyecto: "que
-- incidencias tuvo este trabajo" no tenia consulta.
--
-- Nulo a proposito: un vale de almacen es un `incident` y no pertenece a ningun
-- proyecto. Exigirlo obligaria a inventar un proyecto para cada vale.
ALTER TABLE incident
    ADD COLUMN IF NOT EXISTS id_proyect INTEGER REFERENCES proyect(id_proyect);

CREATE INDEX IF NOT EXISTS idx_incident_proyect
    ON incident (id_proyect) WHERE id_proyect IS NOT NULL;

-- --- las parcialidades de pago ------------------------------------------

CREATE TABLE IF NOT EXISTS proyect_payment (
    id_proyect_payment  SERIAL PRIMARY KEY,
    id_proyect          INTEGER NOT NULL REFERENCES proyect(id_proyect),
    -- Cuando se acordo o se espera el pago.
    payment_date        DATE NOT NULL,
    amount              NUMERIC(14,2) NOT NULL,
    -- El porcentaje PACTADO, tal como se acordo. Ver la cabecera: no se deduce
    -- del monto contra el total, porque el total puede cambiar despues.
    agreed_percent      NUMERIC(6,2),
    -- Si ya entro. Se separa de la fecha acordada porque un pago puede caer
    -- tarde, y "acordado el 5" y "cobrado el 19" son dos hechos distintos.
    paid_at             DATE,
    notes               TEXT,
    created_by          INTEGER NOT NULL DEFAULT 1,
    creation_date       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date       TIMESTAMP,
    CONSTRAINT ck_proyect_payment_amount CHECK (amount > 0),
    CONSTRAINT ck_proyect_payment_percent
        CHECK (agreed_percent IS NULL OR (agreed_percent > 0 AND agreed_percent <= 100))
);

CREATE INDEX IF NOT EXISTS idx_proyect_payment_proyect
    ON proyect_payment (id_proyect, payment_date);

COMMIT;

-- --- el expediente admite los hechos nuevos -----------------------------
--
-- `proyect_event.event_type` solo aceptaba cuatro: created, status_changed,
-- message y task_event. El recorrido de gerencia y las parcialidades no caben
-- en ninguno, y meterlos como `message` los volveria texto libre: "que pagos se
-- acordaron en este proyecto" dejaria de tener consulta y habria que leer el
-- contenido de cada renglon.
--
-- Es la misma leccion que `event_log.action` (migracion 20260911120000): una
-- lista de tipos demasiado estrecha no impide que el hecho ocurra, solo obliga
-- a apuntarlo en otro sitio.
BEGIN;

-- Y los estados del recorrido comercial no caben en veinte caracteres:
-- 'pendiente_orden_compra' son veintidos. La columna se dimensiono cuando el
-- unico recorrido era el de taller, cuyo estado mas largo es 'waiting_material'.
ALTER TABLE proyect_event ALTER COLUMN previous_status TYPE VARCHAR(40);
ALTER TABLE proyect_event ALTER COLUMN new_status TYPE VARCHAR(40);

ALTER TABLE proyect_event DROP CONSTRAINT IF EXISTS proyect_event_event_type_check;

ALTER TABLE proyect_event ADD CONSTRAINT proyect_event_event_type_check CHECK (
    event_type IN (
        'created', 'status_changed', 'message', 'task_event',
        -- El recorrido comercial, que corre en paralelo al de taller.
        'management_transition',
        -- Lo acordado y lo cobrado, cada uno por su lado.
        'payment_agreed', 'payment_settled'
    )
);

COMMIT;
