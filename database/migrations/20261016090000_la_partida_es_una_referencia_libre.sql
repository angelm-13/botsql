-- La partida del proyecto (`proyect.folio`) es una referencia libre (2026-10-16).
--
-- Adser captura ahi su propio numero -el del sistema anterior, p. ej. "1" o
-- "10130"- solo como referencia: puede repetirse entre proyectos y puede quedar
-- vacia. Antes `uq_proyect_folio` lo impedia y una partida repetida terminaba
-- en un 500 generico.
--
-- Esta migracion se reaplica en cada arranque, asi que es idempotente:
--   * retira el indice UNICO donde exista;
--   * deja un indice NORMAL para poder buscar por partida.
-- Las migraciones viejas (`20260911180000`, `20260918130000`) ya no crean el
-- unico ni rellenan folios; si lo siguieran haciendo, este DROP duraria hasta
-- el siguiente arranque y el CREATE de aquellas reventaria con duplicados.

BEGIN;

DROP INDEX IF EXISTS uq_proyect_folio;

CREATE INDEX IF NOT EXISTS idx_proyect_folio
    ON proyect (folio) WHERE folio IS NOT NULL AND deletion_date IS NULL;

COMMIT;
