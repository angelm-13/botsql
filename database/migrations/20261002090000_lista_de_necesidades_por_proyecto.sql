-- La lista de necesidades de material de un proyecto.
--
-- Pedido de Adser: Compras ve los proyectos para saber que material hay que
-- comprar, y los supervisores ("ingenieros") declaran lo que necesita cada uno.
-- Hoy un proyecto no tiene ninguna lista de material que Compras pueda ver
-- (en adser-prod: 4 proyectos, 0 renglones de material).
--
-- Tabla propia y no `invoice_material_service`: aquel renglon cuelga de una
-- factura -precios, impuestos, claves SAT- y lo captura quien factura. Esta lista
-- la declara el supervisor, y mezclarlas obligaria a editar una cotizacion para
-- anotar que falta un tornillo. Queda una llave opcional al renglon de factura,
-- vacia, por si luego se quieren ligar.
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
    id_material                 INTEGER NOT NULL REFERENCES material(id_material),
    quantity                    INTEGER NOT NULL,
    needed_by                   DATE,
    note                        VARCHAR(300),
    need_status                 VARCHAR(20) NOT NULL DEFAULT 'open',
    id_invoice_material_service INTEGER
        REFERENCES invoice_material_service(id_invoice_material_service),
    created_by                  INTEGER NOT NULL DEFAULT 1,
    creation_date               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date               TIMESTAMP,
    CONSTRAINT ck_proyect_material_need_quantity CHECK (quantity > 0),
    CONSTRAINT ck_proyect_material_need_status
        CHECK (need_status IN ('open', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_proyect_material_need_proyect
    ON proyect_material_need (id_proyect) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_proyect_material_need_material
    ON proyect_material_need (id_material) WHERE deletion_date IS NULL;

COMMIT;
