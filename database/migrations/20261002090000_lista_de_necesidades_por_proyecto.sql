-- La lista de necesidades de un proyecto.
--
-- Pedido de Adser: Compras ve los proyectos para saber que hay que comprar, y los
-- supervisores ("ingenieros") declaran lo que necesita cada uno. Hoy un proyecto no
-- tiene ninguna lista que Compras pueda ver (en adser-prod: 4 proyectos, 0
-- renglones de material).
--
-- Texto libre primero, catalogo despues. El almacen de Adser es de HERRAMIENTA: su
-- catalogo de materiales son tipos de herramienta y equipo, y lo que una obra
-- consume -tornillos, soldadura, discos- casi nunca esta ahi. Por eso la necesidad
-- se describe con texto y `id_material` es OPCIONAL: se llena cuando lo pedido si
-- existe en el catalogo.
--
-- Si el supervisor escribe algo que si hay en el almacen y no lo vincula, el
-- renglon queda "por revisar" hasta que alguien (`reviewed_by`, `reviewed_date`)
-- decida (`review_result`): `linked` -ya existe, se vinculo- o `buy` -de verdad
-- hay que comprarlo- o `returned` -no se entiende: vuelve al supervisor con su
-- `review_note`-. Nada se oculta por parecerse a algo del catalogo.
--
-- Tabla propia y no `invoice_material_service`: aquel renglon cuelga de una
-- factura -precios, impuestos, claves SAT- y lo captura quien factura. Queda una
-- llave opcional a ese renglon, vacia, por si luego se quieren ligar.
--
-- La necesidad NO dice como se cubre (existencia, compra o renta): eso lo decide
-- quien compra. Puede pedir mas de lo que hay; para eso sirve.
--
-- Se reaplica en cada arranque del pod (sin tabla de control): todo es IF NOT
-- EXISTS, y las restricciones van dentro del CREATE TABLE, que no se vuelve a
-- evaluar si la tabla ya existe.
BEGIN;

CREATE TABLE IF NOT EXISTS proyect_material_need (
    id_proyect_material_need    SERIAL PRIMARY KEY,
    id_proyect                  INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_material                 INTEGER REFERENCES material(id_material),
    description                 VARCHAR(200),
    unit                        VARCHAR(40),
    quantity                    INTEGER NOT NULL,
    needed_by                   DATE,
    note                        VARCHAR(300),
    need_status                 VARCHAR(20) NOT NULL DEFAULT 'open',
    review_result               VARCHAR(10),
    review_note                 VARCHAR(300),
    reviewed_by                 INTEGER,
    reviewed_date               TIMESTAMP,
    id_invoice_material_service INTEGER
        REFERENCES invoice_material_service(id_invoice_material_service),
    created_by                  INTEGER NOT NULL DEFAULT 1,
    creation_date               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date               TIMESTAMP,
    CONSTRAINT ck_proyect_material_need_quantity CHECK (quantity > 0),
    CONSTRAINT ck_proyect_material_need_status
        CHECK (need_status IN ('open', 'cancelled')),
    CONSTRAINT ck_proyect_material_need_review
        CHECK (review_result IS NULL OR review_result IN ('linked', 'buy', 'returned')),
    CONSTRAINT ck_proyect_material_need_what
        CHECK (id_material IS NOT NULL OR (description IS NOT NULL AND description <> ''))
);

CREATE INDEX IF NOT EXISTS idx_proyect_material_need_proyect
    ON proyect_material_need (id_proyect) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_proyect_material_need_material
    ON proyect_material_need (id_material) WHERE deletion_date IS NULL;

COMMIT;
