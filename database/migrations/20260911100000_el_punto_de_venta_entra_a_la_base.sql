-- El punto de venta deja de ser una base aparte.
--
-- Que se absorbe y que no
-- -----------------------
-- El POS tenia 36 tablas. Solo 16 llegan aqui: las otras 20 ya existian en
-- TYAKXA con otro nombre, y no chocaban solo porque el POS usa plural.
--
--     products          -> product                users  -> "user"
--     categories        -> product_family         roles  -> permission
--     customers         -> customer_supplier      suppliers -> customer_supplier
--     warehouses        -> location               units_of_measure -> unit
--     product_lots      -> inventory_lot          audit_logs -> event_log
--     inventory_kardex  -> inventory_ledger       product_components -> material_component
--     invoices, invoice_items, invoicing_settings -> invoice, invoice_material_service
--
-- Esa columna de la derecha es el motivo de todo esto: son las tablas que se
-- COMPARTEN. Un producto capturado en la caja es el mismo renglon que el
-- almacen cuenta, no una copia que alguien tiene que sincronizar.
--
-- Por que llaves enteras y no los UUID que traia
-- ----------------------------------------------
-- El POS usaba UUID en sus 34 tablas; TYAKXA usa enteros en sus 127. Mientras
-- fueron dos bases daba igual. Al compartir tablas ya no: `pos_sale_item`
-- apunta a `product`, cuya llave es un entero, y no hay forma de que una
-- columna sea UUID de un lado y entero del otro.
--
-- Se pudo haber convertido. No hizo falta: la base del POS tenia ~600 filas de
-- DEMOSTRACION -- 33 ventas, 14 productos, 7 usuarios y una tabla `demo_state`
-- --, ningun dato real. Contado tabla por tabla, no con `pg_stat_user_tables`,
-- que reportaba 3 filas por estar sin analizar. Asi que se empieza limpio, que
-- es lo barato. Con ventas reales dentro, esta migracion seria otra cosa.
--
-- La columna que el POS no tenia
-- ------------------------------
-- `id_proyect`. Ni esa ni ninguna equivalente: el POS se penso como una
-- instalacion por negocio, asi que no necesitaba decir de quien era cada fila.
-- TYAKXA es multiinquilino y 28 de sus tablas la llevan. Se agrega a las 16.
--
-- Va en TODAS, incluidas las de detalle (`pos_sale_item`, `pos_payment`), que
-- podrian heredarla de su padre. Es una columna redundante a proposito: el
-- filtro por proyecto de `base_service` mira la tabla que consulta, y un
-- detalle sin `id_proyect` se escaparia del filtro en cuanto alguien lo liste
-- directo. `restaurant_inventory_movement` ya sigue esa misma regla.
--
-- Los enum se vuelven CHECK
-- -------------------------
-- El POS declaraba 13 tipos enum de Postgres. Aqui son `varchar` con CHECK,
-- que es lo que TYAKXA usa en todas partes (`logistics_inventory.status`,
-- `incident.incident_status`). No es cosmetico: agregar un valor a un enum de
-- Postgres es DDL y no se puede revertir dentro de una transaccion, mientras
-- que ampliar un CHECK es un ALTER normal. Con migraciones que se reaplican en
-- cada arranque, eso importa.

BEGIN;

-- --- la caja -----------------------------------------------------------
-- El turno es la raiz de todo lo demas: una venta sin turno abierto no se
-- puede cobrar, y el corte compara lo declarado contra lo esperado.

CREATE TABLE IF NOT EXISTS pos_cash_session (
    id_pos_cash_session     SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    register_name           VARCHAR(120) NOT NULL,
    id_user_opened          INTEGER NOT NULL REFERENCES "user"(id_user),
    id_user_closed          INTEGER REFERENCES "user"(id_user),
    opening_amount          NUMERIC(14,2) NOT NULL DEFAULT 0,
    opened_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at               TIMESTAMP,
    session_status          VARCHAR(20) NOT NULL DEFAULT 'open',
    -- Lo declarado a ciegas, lo que el sistema esperaba y la diferencia. Se
    -- guardan los tres y no solo el descuadre: sin los dos primeros, un corte
    -- con diferencia cero no distingue "cuadro" de "nadie conto".
    blind_declared_amounts   JSONB,
    system_expected_amounts  JSONB,
    discrepancy_amounts      JSONB,
    notes                   TEXT,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_cash_session_status
        CHECK (session_status IN ('open', 'closed_x', 'closed_z'))
);

CREATE INDEX IF NOT EXISTS idx_pos_cash_session_proyect
    ON pos_cash_session (id_proyect, session_status);

CREATE TABLE IF NOT EXISTS pos_cash_withdrawal (
    id_pos_cash_withdrawal  SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_cash_session     INTEGER NOT NULL
        REFERENCES pos_cash_session(id_pos_cash_session),
    amount                  NUMERIC(14,2) NOT NULL,
    reason                  VARCHAR(250) NOT NULL,
    id_user_authorized      INTEGER NOT NULL REFERENCES "user"(id_user),
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_cash_withdrawal_amount CHECK (amount > 0)
);

CREATE INDEX IF NOT EXISTS idx_pos_cash_withdrawal_session
    ON pos_cash_withdrawal (id_pos_cash_session);

-- --- la venta ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS pos_sale (
    id_pos_sale             SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    folio                   VARCHAR(40) NOT NULL,
    sale_type               VARCHAR(20) NOT NULL DEFAULT 'takeout',
    sale_status             VARCHAR(20) NOT NULL DEFAULT 'open',
    table_number            VARCHAR(20),
    -- El cliente es un `customer_supplier`, la misma tabla que factura y que
    -- compra. Era el motivo de que un cliente del mostrador no apareciera en
    -- el CRM: vivia en otra base.
    id_customer_supplier    INTEGER REFERENCES customer_supplier(id_customer_supplier),
    id_user_waiter          INTEGER REFERENCES "user"(id_user),
    id_user_cashier         INTEGER REFERENCES "user"(id_user),
    id_pos_cash_session     INTEGER REFERENCES pos_cash_session(id_pos_cash_session),
    subtotal                NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_total          NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax_total               NUMERIC(14,2) NOT NULL DEFAULT 0,
    total                   NUMERIC(14,2) NOT NULL DEFAULT 0,
    -- El coste se copia al vender, no se consulta despues: el coste del
    -- producto cambia con cada compra, y un margen recalculado con el coste de
    -- hoy miente sobre la venta de ayer.
    total_cost              NUMERIC(14,2) NOT NULL DEFAULT 0,
    delivery_platform       VARCHAR(60),
    delivery_commission_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    notes                   TEXT,
    cancelled_reason        TEXT,
    paid_at                 TIMESTAMP,
    -- La factura de esta venta, cuando se emite. El POS traia `invoices`
    -- propias; se quedan fuera a proposito -- ya estaba decidido que el CFDI
    -- se emite desde TYAKXA, que es el unico modulo de facturacion.
    id_invoice              INTEGER REFERENCES invoice(id_invoice),
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_sale_type
        CHECK (sale_type IN ('dine_in', 'takeout', 'delivery', 'online')),
    CONSTRAINT ck_pos_sale_status
        CHECK (sale_status IN ('open', 'suspended', 'paid', 'cancelled',
                               'refunded', 'partially_refunded'))
);

-- El folio es unico DENTRO del proyecto, no global: dos negocios distintos en
-- la misma instalacion llevan su propia numeracion, y exigirles una comun
-- haria que el ticket de uno saltara numeros por las ventas del otro.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_sale_folio
    ON pos_sale (id_proyect, folio) WHERE deletion_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_pos_sale_session ON pos_sale (id_pos_cash_session);
CREATE INDEX IF NOT EXISTS idx_pos_sale_paid    ON pos_sale (id_proyect, paid_at);

CREATE TABLE IF NOT EXISTS pos_sale_item (
    id_pos_sale_item        SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_sale             INTEGER NOT NULL REFERENCES pos_sale(id_pos_sale),
    -- Aqui esta el nudo de toda la integracion: el renglon de una venta apunta
    -- al producto del almacen. Antes apuntaba a `products.id` en otra base, y
    -- por eso hacia falta `pos_product_link` para emparejar dos mundos.
    id_product              INTEGER NOT NULL REFERENCES product(id_product),
    id_pos_product_variant  INTEGER,
    quantity                NUMERIC(14,3) NOT NULL,
    unit_price              NUMERIC(14,2) NOT NULL,
    unit_cost               NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_amount         NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax_amount              NUMERIC(14,2) NOT NULL DEFAULT 0,
    line_total              NUMERIC(14,2) NOT NULL DEFAULT 0,
    id_pos_promotion        INTEGER,
    kitchen_zone            VARCHAR(60),
    kitchen_status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    special_instructions    TEXT,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_sale_item_quantity CHECK (quantity > 0),
    CONSTRAINT ck_pos_sale_item_kitchen
        CHECK (kitchen_status IN ('pending', 'preparing', 'ready', 'served',
                                  'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_pos_sale_item_sale    ON pos_sale_item (id_pos_sale);
CREATE INDEX IF NOT EXISTS idx_pos_sale_item_product ON pos_sale_item (id_product);

CREATE TABLE IF NOT EXISTS pos_payment (
    id_pos_payment          SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_sale             INTEGER NOT NULL REFERENCES pos_sale(id_pos_sale),
    payment_method          VARCHAR(30) NOT NULL,
    amount                  NUMERIC(14,2) NOT NULL,
    tendered_amount         NUMERIC(14,2),
    change_amount           NUMERIC(14,2) NOT NULL DEFAULT 0,
    reference               VARCHAR(120),
    id_user_received        INTEGER NOT NULL REFERENCES "user"(id_user),
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_payment_method
        CHECK (payment_method IN ('cash', 'card', 'transfer', 'local_credit',
                                  'loyalty_points', 'delivery_platform'))
);

CREATE INDEX IF NOT EXISTS idx_pos_payment_sale ON pos_payment (id_pos_sale);

-- --- variantes ---------------------------------------------------------
-- Una talla o un color del mismo producto. No es un producto aparte porque
-- comparte coste, familia y proveedor; lo unico propio es el sobreprecio.

CREATE TABLE IF NOT EXISTS pos_product_variant (
    id_pos_product_variant  SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_product              INTEGER NOT NULL REFERENCES product(id_product),
    sku                     VARCHAR(60),
    barcode                 VARCHAR(60),
    attributes              JSONB,
    price_delta             NUMERIC(14,2) NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pos_product_variant_product
    ON pos_product_variant (id_product);

-- `current_stock` del POS NO se trae. La existencia de una variante es
-- existencia del almacen, y tenerla aqui volveria a crear las dos respuestas a
-- "cuanto hay" que toda esta integracion existe para eliminar.

-- --- promociones -------------------------------------------------------

CREATE TABLE IF NOT EXISTS pos_promotion (
    id_pos_promotion        SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    name                    VARCHAR(160) NOT NULL,
    rule_type               VARCHAR(30) NOT NULL,
    config                  JSONB,
    -- Listas de enteros: antes eran arreglos de UUID de la otra base.
    applicable_product_ids  INTEGER[],
    applicable_family_ids   INTEGER[],
    starts_at               TIMESTAMP,
    ends_at                 TIMESTAMP,
    requires_stock          BOOLEAN NOT NULL DEFAULT TRUE,
    max_uses_total          INTEGER,
    max_uses_per_customer   INTEGER,
    times_used              INTEGER NOT NULL DEFAULT 0,
    is_stackable            BOOLEAN NOT NULL DEFAULT FALSE,
    priority                INTEGER NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_promotion_rule
        CHECK (rule_type IN ('percent_discount', 'fixed_discount',
                             'buy_x_get_y', 'nth_unit_free', 'happy_hour',
                             'bundle_price'))
);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_activa
    ON pos_promotion (id_proyect, is_active, priority);

CREATE TABLE IF NOT EXISTS pos_promotion_redemption (
    id_pos_promotion_redemption SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_promotion        INTEGER NOT NULL
        REFERENCES pos_promotion(id_pos_promotion),
    id_pos_sale             INTEGER NOT NULL REFERENCES pos_sale(id_pos_sale),
    id_customer_supplier    INTEGER REFERENCES customer_supplier(id_customer_supplier),
    discount_amount         NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_redemption_promo
    ON pos_promotion_redemption (id_pos_promotion);

-- --- gastos ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pos_expense_category (
    id_pos_expense_category SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    name                    VARCHAR(160) NOT NULL,
    is_payroll              BOOLEAN NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pos_expense (
    id_pos_expense          SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_expense_category INTEGER
        REFERENCES pos_expense_category(id_pos_expense_category),
    description             VARCHAR(250) NOT NULL,
    amount                  NUMERIC(14,2) NOT NULL,
    id_customer_supplier    INTEGER REFERENCES customer_supplier(id_customer_supplier),
    receipt_url             VARCHAR(400),
    expense_status          VARCHAR(20) NOT NULL DEFAULT 'recorded',
    id_pos_cash_session     INTEGER REFERENCES pos_cash_session(id_pos_cash_session),
    expense_date            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                   TEXT,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_expense_status
        CHECK (expense_status IN ('recorded', 'approved', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_pos_expense_fecha
    ON pos_expense (id_proyect, expense_date);

-- --- credito del cliente (el fiado) ------------------------------------

CREATE TABLE IF NOT EXISTS pos_credit_account (
    id_pos_credit_account   SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_customer_supplier    INTEGER NOT NULL
        REFERENCES customer_supplier(id_customer_supplier),
    credit_limit            NUMERIC(14,2) NOT NULL DEFAULT 0,
    current_balance         NUMERIC(14,2) NOT NULL DEFAULT 0,
    payment_due_day         INTEGER,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pos_credit_movement (
    id_pos_credit_movement  SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_credit_account   INTEGER NOT NULL
        REFERENCES pos_credit_account(id_pos_credit_account),
    movement_type           VARCHAR(20) NOT NULL,
    amount                  NUMERIC(14,2) NOT NULL,
    -- El saldo despues del movimiento se guarda, no se recalcula. Es la misma
    -- regla que el libro del restaurante: un saldo recalculado hoy no prueba
    -- cual era el saldo el dia que se fio.
    balance_after           NUMERIC(14,2) NOT NULL DEFAULT 0,
    id_pos_sale             INTEGER REFERENCES pos_sale(id_pos_sale),
    notes                   TEXT,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_credit_movement_type
        CHECK (movement_type IN ('charge', 'payment', 'adjustment'))
);

CREATE INDEX IF NOT EXISTS idx_pos_credit_movement_cuenta
    ON pos_credit_movement (id_pos_credit_account);

-- --- lealtad -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS pos_loyalty_account (
    id_pos_loyalty_account  SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_customer_supplier    INTEGER NOT NULL
        REFERENCES customer_supplier(id_customer_supplier),
    points_balance          INTEGER NOT NULL DEFAULT 0,
    tier                    VARCHAR(40),
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pos_loyalty_movement (
    id_pos_loyalty_movement SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_loyalty_account  INTEGER NOT NULL
        REFERENCES pos_loyalty_account(id_pos_loyalty_account),
    movement_type           VARCHAR(20) NOT NULL,
    points                  INTEGER NOT NULL,
    balance_after           INTEGER NOT NULL DEFAULT 0,
    id_pos_sale             INTEGER REFERENCES pos_sale(id_pos_sale),
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_loyalty_movement_type
        CHECK (movement_type IN ('earn', 'redeem', 'expire', 'adjustment'))
);

CREATE INDEX IF NOT EXISTS idx_pos_loyalty_movement_cuenta
    ON pos_loyalty_movement (id_pos_loyalty_account);

-- --- compras -----------------------------------------------------------
-- La orden de compra del POS. Recibirla mueve existencia, y eso pasa por
-- `apply_movement_in_session` como todo lo demas -- no por una columna propia.

CREATE TABLE IF NOT EXISTS pos_purchase_order (
    id_pos_purchase_order   SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    folio                   VARCHAR(40) NOT NULL,
    id_customer_supplier    INTEGER NOT NULL
        REFERENCES customer_supplier(id_customer_supplier),
    id_location             INTEGER REFERENCES location(id_location),
    order_status            VARCHAR(24) NOT NULL DEFAULT 'draft',
    expected_date           DATE,
    notes                   TEXT,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_purchase_order_status
        CHECK (order_status IN ('draft', 'sent', 'partially_received',
                                'received', 'cancelled'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_purchase_order_folio
    ON pos_purchase_order (id_proyect, folio) WHERE deletion_date IS NULL;

CREATE TABLE IF NOT EXISTS pos_purchase_order_item (
    id_pos_purchase_order_item SERIAL PRIMARY KEY,
    id_proyect              INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_pos_purchase_order   INTEGER NOT NULL
        REFERENCES pos_purchase_order(id_pos_purchase_order),
    id_product              INTEGER NOT NULL REFERENCES product(id_product),
    quantity_ordered        NUMERIC(14,3) NOT NULL,
    quantity_received       NUMERIC(14,3) NOT NULL DEFAULT 0,
    unit_cost               NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT ck_pos_purchase_order_item_qty CHECK (quantity_ordered > 0)
);

CREATE INDEX IF NOT EXISTS idx_pos_purchase_order_item_orden
    ON pos_purchase_order_item (id_pos_purchase_order);

-- Las dos llaves que quedaron sueltas en `pos_sale_item`, puestas al final
-- porque sus tablas destino se crean despues de quien las referencia.
DO $bloque$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'fk_pos_sale_item_variant') THEN
        ALTER TABLE pos_sale_item ADD CONSTRAINT fk_pos_sale_item_variant
            FOREIGN KEY (id_pos_product_variant)
            REFERENCES pos_product_variant(id_pos_product_variant);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'fk_pos_sale_item_promotion') THEN
        ALTER TABLE pos_sale_item ADD CONSTRAINT fk_pos_sale_item_promotion
            FOREIGN KEY (id_pos_promotion)
            REFERENCES pos_promotion(id_pos_promotion);
    END IF;
END
$bloque$;

COMMIT;

-- --- y lo que deja de hacer falta ---------------------------------------
--
-- `pos_product_link` emparejaba un producto de la base del POS con uno de esta.
-- Con una sola base no hay dos mundos que emparejar: el renglon de la venta
-- apunta directo a `product`. La tabla estaba en cero -- se conto antes de
-- borrarla -- y la creo TYAKXA para el puente, no vino de ninguna migracion de
-- datos, asi que no se pierde nada de nadie.
DROP TABLE IF EXISTS pos_product_link;
