-- Datos del cobro en restaurant_order.
--
-- Antes solo se marcaba status='pagado' y se guardaba la propina: no quedaba
-- registro de con que se pago. Eso tenia dos consecuencias:
--
--   * El corte de caja (close_cash_session) sumaba TODAS las ventas al
--     efectivo esperado, asi que en cuanto habia un pago con tarjeta el
--     arqueo salia descuadrado por ese monto.
--   * No se podia reimprimir un ticket con la forma de pago ni el cambio.
--
-- Nada de esto es facturacion: el ticket es el comprobante interno de venta.
-- El CFDI vive en el modulo de facturacion del core.

BEGIN;

ALTER TABLE restaurant_order
    ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20),
    ADD COLUMN IF NOT EXISTS received_amount NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS cash_amount NUMERIC(10, 2);

ALTER TABLE restaurant_order
    DROP CONSTRAINT IF EXISTS ck_restaurant_order_payment_method;
ALTER TABLE restaurant_order
    ADD CONSTRAINT ck_restaurant_order_payment_method CHECK (
        payment_method IS NULL
        OR payment_method IN ('efectivo', 'tarjeta', 'transferencia', 'mixto')
    );

-- Montos no negativos: un recibido o un efectivo negativo solo puede ser un
-- error de captura.
ALTER TABLE restaurant_order
    DROP CONSTRAINT IF EXISTS ck_restaurant_order_received_amount;
ALTER TABLE restaurant_order
    ADD CONSTRAINT ck_restaurant_order_received_amount CHECK (
        received_amount IS NULL OR received_amount >= 0
    );

ALTER TABLE restaurant_order
    DROP CONSTRAINT IF EXISTS ck_restaurant_order_cash_amount;
ALTER TABLE restaurant_order
    ADD CONSTRAINT ck_restaurant_order_cash_amount CHECK (
        cash_amount IS NULL OR cash_amount >= 0
    );

-- cash_amount solo tiene sentido en un pago mixto: en los demas la parte en
-- efectivo se deduce del metodo (todo o nada).
ALTER TABLE restaurant_order
    DROP CONSTRAINT IF EXISTS ck_restaurant_order_cash_amount_only_mixto;
ALTER TABLE restaurant_order
    ADD CONSTRAINT ck_restaurant_order_cash_amount_only_mixto CHECK (
        cash_amount IS NULL OR payment_method = 'mixto'
    );

-- El corte de caja filtra por forma de pago sobre las ordenes cobradas
-- dentro del turno.
CREATE INDEX IF NOT EXISTS ix_restaurant_order_payment
    ON restaurant_order (payment_method, paid_at);

COMMIT;
