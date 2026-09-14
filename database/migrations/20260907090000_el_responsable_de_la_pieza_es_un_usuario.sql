-- El responsable de una pieza tiene que ser alguien que existe.
--
-- Que estaba flotando
-- -------------------
-- `inventory_asset.id_holder` es quien se llevo la herramienta, y no tenia
-- llave ajena. El servicio solo comprobaba que fuera un entero:
--
--     pieza.id_holder = _entero(payload.get("id_holder"), ..., obligatorio=True)
--
-- Asi que un prestamo a `id_holder = 9999` se guardaba tal cual. La pieza
-- quedaba PRESTADA a nadie: no aparece en la lista de lo que debe un usuario,
-- no se le puede reclamar, y el unico modo de encontrarla es notar que falta.
-- Lo mismo en la bitacora de la pieza, donde `id_holder_before` y
-- `id_holder_after` son el rastro de en manos de quien estuvo.
--
-- Medido antes de aplicar esto: 8 de 25 piezas con responsable, ninguna
-- huerfana todavia. El agujero no habia cobrado, pero estaba abierto.
--
-- Por que DEFERRABLE
-- ------------------
-- Igual que el resto de las llaves de este esquema: `user`, `permission`,
-- `proyect` y `customer_supplier` forman un ciclo, y sembrar la base exige
-- poder diferir la comprobacion al COMMIT.
--
-- Por que no ON DELETE
-- --------------------
-- El proyecto borra en suave -`deletion_date`- y no en duro. Poner
-- ON DELETE SET NULL invitaria a un borrado fisico que perderia el rastro de
-- quien tuvo la pieza; la ausencia de regla deja que la base lo impida.

BEGIN;

DO $$
BEGIN
    ALTER TABLE inventory_asset
        ADD CONSTRAINT fk_inventory_asset_holder
        FOREIGN KEY (id_holder) REFERENCES "user"(id_user)
        DEFERRABLE INITIALLY IMMEDIATE;
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

-- Se busca por responsable -"que trae Juan"- y sin indice eso es un recorrido
-- de la tabla entera.
CREATE INDEX IF NOT EXISTS idx_inventory_asset_id_holder
    ON inventory_asset (id_holder)
    WHERE id_holder IS NOT NULL;

DO $$
BEGIN
    ALTER TABLE inventory_asset_event
        ADD CONSTRAINT fk_inventory_asset_event_holder_before
        FOREIGN KEY (id_holder_before) REFERENCES "user"(id_user)
        DEFERRABLE INITIALLY IMMEDIATE;
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE inventory_asset_event
        ADD CONSTRAINT fk_inventory_asset_event_holder_after
        FOREIGN KEY (id_holder_after) REFERENCES "user"(id_user)
        DEFERRABLE INITIALLY IMMEDIATE;
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

COMMIT;
