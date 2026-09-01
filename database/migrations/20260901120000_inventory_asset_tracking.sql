-- Rastreo de piezas una por una: herramienta, equipo, activo de uso.
--
-- El hueco
-- --------
-- El inventario llevaba cantidades: cuantas piezas de un producto hay en una
-- ubicacion, y un libro con cada movimiento. Eso alcanza para un insumo -da
-- igual cual de los veinte costales de cemento salio- pero no para una
-- herramienta.
--
-- Con solo cantidades hay preguntas que el sistema no podia contestar aunque el
-- saldo cuadrara: donde esta el taladro con etiqueta A-014, quien se lo llevo,
-- desde cuando, si esta prestado o en reparacion, y que le ha pasado desde que
-- se compro.
--
-- El tipo de movimiento `loan` ya existia y descontaba existencia, pero no
-- registraba a quien: un prestamo se veia como una resta.
--
-- Como se resuelve
-- ----------------
-- `product.tracking_mode` decide como se lleva cada producto:
--
--   * `fungible`   se cuenta. Es el valor por omision, asi que nada de lo que
--                  ya existe cambia de comportamiento.
--   * `serializado` cada unidad tiene su fila en `inventory_asset`, con estado,
--                  ubicacion y responsable, y su historia en
--                  `inventory_asset_event`.
--
-- Las dos formas comparten `inventory_stock` a proposito: una pieza disponible
-- suma al saldo igual que un insumo, de modo que quien solo quiera saber
-- cuantos taladros hay lo lee del mismo lugar de siempre. Cada cambio de estado
-- escribe su movimiento en el libro, asi que las dos vistas no se pueden
-- separar sin que la conciliacion lo note.

BEGIN;

-- Modo de rastreo del producto. Por omision `fungible`, que es como se ha
-- llevado todo hasta ahora: al aplicar esta migracion ningun producto cambia de
-- comportamiento.
ALTER TABLE product
    ADD COLUMN IF NOT EXISTS tracking_mode varchar(20) NOT NULL DEFAULT 'fungible';

ALTER TABLE product
    DROP CONSTRAINT IF EXISTS ck_product_tracking_mode;
ALTER TABLE product
    ADD CONSTRAINT ck_product_tracking_mode
    CHECK (tracking_mode IN ('fungible', 'serializado'));

COMMENT ON COLUMN product.tracking_mode IS
    'fungible: se lleva por cantidad. serializado: cada unidad es una fila en inventory_asset.';


-- Una pieza fisica concreta.
CREATE TABLE IF NOT EXISTS inventory_asset (
    id_inventory_asset  serial PRIMARY KEY,
    id_product          integer NOT NULL REFERENCES product (id_product),

    -- La etiqueta pegada en la carcasa: como se identifica la pieza en el mundo
    -- real. Unica, porque dos herramientas con la misma etiqueta vuelven inutil
    -- el rastreo.
    asset_tag           varchar(40) NOT NULL,
    serial_number       varchar(120),

    -- Queda en nulo cuando la pieza no esta en la empresa -prestada o
    -- extraviada-: decir que sigue en una ubicacion seria falso, y es ese dato
    -- falso el que hace que nadie la busque.
    id_location         integer REFERENCES location (id_location),

    status              varchar(20) NOT NULL DEFAULT 'disponible',

    -- Quien responde por ella ahora. Es el dato que convierte "falta un
    -- taladro" en "lo tiene tal persona desde tal dia".
    id_holder           integer,
    -- Cuando deberia volver. Sin fecha, un prestamo se vuelve permanente porque
    -- nunca esta vencido y nadie lo reclama.
    due_date            date,

    acquired_on         date,
    acquisition_cost    numeric(18,2),
    note                varchar(300),

    created_by          integer NOT NULL,
    creation_date       timestamp NOT NULL DEFAULT now(),
    last_update_date    timestamp NOT NULL DEFAULT now(),
    deletion_date       timestamp,

    CONSTRAINT uq_inventory_asset_tag UNIQUE (asset_tag),
    CONSTRAINT ck_inventory_asset_status CHECK (
        status IN ('disponible','en_uso','prestada','en_reparacion','extraviada','retirada')
    ),
    -- Una pieza asignada o prestada tiene responsable. Sin esta regla se puede
    -- perder el rastro de quien la tiene justo cuando mas importa saberlo.
    CONSTRAINT ck_inventory_asset_holder_required CHECK (
        (status IN ('en_uso','prestada') AND id_holder IS NOT NULL)
        OR status NOT IN ('en_uso','prestada')
    )
);

CREATE INDEX IF NOT EXISTS idx_inventory_asset_product ON inventory_asset (id_product);
CREATE INDEX IF NOT EXISTS idx_inventory_asset_location ON inventory_asset (id_location);
CREATE INDEX IF NOT EXISTS idx_inventory_asset_status ON inventory_asset (status);
CREATE INDEX IF NOT EXISTS idx_inventory_asset_holder ON inventory_asset (id_holder);
-- La consulta que mas se hace: que piezas de este producto estan disponibles.
CREATE INDEX IF NOT EXISTS idx_inventory_asset_product_status
    ON inventory_asset (id_product, status);
-- Los prestamos vencidos, que es la unica forma de que no se vuelvan olvidos.
CREATE INDEX IF NOT EXISTS idx_inventory_asset_overdue
    ON inventory_asset (due_date)
    WHERE status = 'prestada' AND due_date IS NOT NULL;


-- Historia de cada pieza. De solo agregado, igual que inventory_ledger: un
-- renglon equivocado no se edita, se escribe otro que dice lo que paso despues.
CREATE TABLE IF NOT EXISTS inventory_asset_event (
    id_inventory_asset_event serial PRIMARY KEY,
    id_inventory_asset       integer NOT NULL REFERENCES inventory_asset (id_inventory_asset),

    event_type               varchar(30) NOT NULL,

    -- Se guarda el antes y el despues completos en lugar de solo el cambio.
    -- Cuesta unas columnas y evita reconstruir el estado sumando renglones, que
    -- es donde una consulta mal escrita empieza a mentir.
    status_before            varchar(20),
    status_after             varchar(20) NOT NULL,
    id_location_before       integer REFERENCES location (id_location),
    id_location_after        integer REFERENCES location (id_location),
    id_holder_before         integer,
    id_holder_after          integer,

    due_date                 date,

    -- El movimiento de existencia que provoco, si provoco alguno. Amarra
    -- "quien se llevo el taladro" con "que renglon del libro lo descontó".
    id_inventory_ledger      integer REFERENCES inventory_ledger (id_inventory_ledger),

    reference_type           varchar(50),
    reference_id             varchar(100),
    reason                   varchar(300),

    created_by               integer NOT NULL,
    creation_date            timestamp NOT NULL DEFAULT now(),

    CONSTRAINT ck_inventory_asset_event_type CHECK (
        event_type IN ('alta','asignacion','prestamo','devolucion',
                       'envio_reparacion','regreso_reparacion','extravio','baja','traslado')
    )
);

CREATE INDEX IF NOT EXISTS idx_inventory_asset_event_asset
    ON inventory_asset_event (id_inventory_asset, id_inventory_asset_event);
CREATE INDEX IF NOT EXISTS idx_inventory_asset_event_holder
    ON inventory_asset_event (id_holder_after);
CREATE INDEX IF NOT EXISTS idx_inventory_asset_event_type
    ON inventory_asset_event (event_type);
CREATE INDEX IF NOT EXISTS idx_inventory_asset_event_ledger
    ON inventory_asset_event (id_inventory_ledger);

COMMIT;
