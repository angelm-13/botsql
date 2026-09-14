BEGIN;

-- El lugar de expedicion ahora sale siempre del domicilio (postal_code) de la
-- empresa marcada is_principal, nunca de una config global de cuenta -- una
-- cuenta de Facturama puede emitir por varias empresas/RFC (multiemisor), asi
-- que un solo CP de cuenta era ambiguo o, peor, ganaba en silencio sobre el
-- domicilio real de la empresa cuando ambos se capturaban por separado.
ALTER TABLE pac_config DROP COLUMN IF EXISTS expedition_place;

COMMIT;
