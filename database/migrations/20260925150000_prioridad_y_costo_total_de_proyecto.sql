-- Prioridad y costo total del proyecto, exclusivos de Gerencia.
--
-- Pedido explicito: "solo para gerente" -- mover la fecha de entrega junto a
-- la orden de compra, agregar una prioridad de 3 niveles visible en la tabla,
-- y un costo total cuya etiqueta de cobro (pendiente/cobrado/excedido) se
-- calcula contra lo YA COBRADO en `proyect_payment` (las parcialidades que
-- Gerencia ya usa para "Acordado/Cobrado/Pendiente" en el expediente -- ver
-- `_resumen_de_pagos`). No se toca `proyect_payment`: el costo total es un
-- dato nuevo e independiente de lo pactado en las parcialidades, y las dos
-- cifras se comparan, no se fusionan.
--
-- El candado real vive en `project_management_service.py` (misma capacidad
-- `project_authorization` que ya usa el recorrido comercial), no en
-- `nm_field_permission`: esa tabla nunca se sembro para `proyect` (ninguna
-- fila de `field` existe para esta tabla) y activarla a ciegas aqui
-- dejaria CIEGO/MUDO cada campo de Proyecto -no solo estos dos- para
-- cualquier rol no-administrador, al no existir permiso alguno que lo
-- autorice. Reconstruir ese catalogo completo es un cambio mucho mas grande
-- que el pedido, y no es este.

BEGIN;

ALTER TABLE proyect
    ADD COLUMN IF NOT EXISTS priority VARCHAR(10),
    ADD COLUMN IF NOT EXISTS total_cost NUMERIC(12, 2);

DO $bloque$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_proyect_priority') THEN
        ALTER TABLE proyect ADD CONSTRAINT ck_proyect_priority CHECK (
            priority IS NULL OR priority IN ('baja', 'media', 'alta')
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_proyect_total_cost') THEN
        ALTER TABLE proyect ADD CONSTRAINT ck_proyect_total_cost CHECK (
            total_cost IS NULL OR total_cost >= 0
        );
    END IF;
END
$bloque$;

COMMIT;
