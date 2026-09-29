-- Un material no se captura dos veces.
--
-- Origen: al migrar adser, el catalogo `material` llego con 199 filas
-- repetidas (mismo tipo de herramienta capturado varias veces, ver
-- `backend/scripts/dedupe_adser_material.py`). Se depuraron a mano, pero nada
-- impedia que volvieran: `MaterialService` era un CRUD sin ninguna validacion,
-- y con dos filas vivas la mitad de los productos apunta a una y la mitad a
-- la otra.
--
-- La identidad de un material es descripcion + unidad + marca + familia +
-- tipo, no solo descripcion y unidad: "Desarmador plano" de dos marcas son dos
-- materiales. El tipo es opcional, asi que un NULL cuenta como "sin tipo".
--
-- DEFENSIVA A PROPOSITO. Estas migraciones corren completas en cada arranque
-- del backend (initContainer db-migrate) y un CREATE UNIQUE INDEX falla si ya
-- hay duplicados vivos: el backend se quedaria en CrashLoop. Si los hay, no se
-- crea el indice, se avisa, y la validacion del servicio (`MaterialService`)
-- sigue protegiendo las capturas nuevas. Cuando se depuren, el siguiente
-- arranque crea el indice solo.
--
-- Medido antes de escribirla (2026-09-29): 0 grupos duplicados en tyakxa-dev,
-- torredigital-prod, adser-prod y vidrioyaluminios-prod.

DO $bloque$
DECLARE
    grupos_repetidos INTEGER;
BEGIN
    IF to_regclass('public.material') IS NULL THEN
        RETURN;
    END IF;

    SELECT count(*) INTO grupos_repetidos FROM (
        SELECT 1
        FROM material
        WHERE deletion_date IS NULL
        GROUP BY lower(btrim(material_description)), id_unit, id_brand,
                 id_product_family, coalesce(id_material_type, 0)
        HAVING count(*) > 1
    ) repetidos;

    IF grupos_repetidos > 0 THEN
        RAISE WARNING USING MESSAGE =
            'uq_material_identidad NO se creo: hay ' || grupos_repetidos::text
            || ' grupo(s) de material repetido(s). Depurarlos (ver dedupe_adser_material.py) y reiniciar el backend.';
        RETURN;
    END IF;

    CREATE UNIQUE INDEX IF NOT EXISTS uq_material_identidad
        ON material (
            lower(btrim(material_description)), id_unit, id_brand,
            id_product_family, coalesce(id_material_type, 0)
        )
        WHERE deletion_date IS NULL;
END
$bloque$;
