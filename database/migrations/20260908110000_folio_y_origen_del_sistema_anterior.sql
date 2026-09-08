-- El rastro del sistema anterior: folio del vale e identificadores de origen.
--
-- Que hay que conservar, y por que
-- --------------------------------
-- Se pidio que "la tabla de vales traiga los numeros de vales creados en el
-- sistema original". Y mirando su esquema, ese numero NO es un campo aparte:
--
--     CREATE TABLE `incidente` (
--       `id_incidente` int(11) NOT NULL AUTO_INCREMENT,
--       ...
--
-- El numero de vale ES su llave primaria. No se puede reusar la nuestra:
-- `incident.id_incident` tiene su propia secuencia y la tabla ya trae filas, asi
-- que forzar los identificadores del sistema viejo chocaria con lo que hay y
-- dejaria la secuencia apuntando a un hueco.
--
-- Asi que el numero viejo se guarda como lo que es: el folio con el que la gente
-- conoce ese vale.
--
-- Los identificadores de origen, y para que sirven de verdad
-- ----------------------------------------------------------
-- No son decoracion ni "por si acaso". Son lo que hace que la importacion se
-- pueda REPETIR sin duplicar:
--
--   * son ~2 461 productos, ~139 vales y ~2 787 renglones. Una carga de ese
--     tamano se interrumpe, se corrige y se vuelve a correr;
--   * sin un identificador de origen, la segunda pasada no puede saber que ya
--     habia importado, y la unica salida seria borrar todo y empezar -que es
--     justo lo que no se puede hacer con una base en uso-;
--   * y son lo que permite ligar los renglones con su producto y su vale:
--     `nm_incidente_producto.id_producto` apunta al `id_producto` VIEJO, no al
--     nuestro.
--
-- Los indices unicos son parciales -solo sobre lo no nulo y no borrado- porque
-- lo que se da de alta en el sistema nuevo no tiene origen, y son la mayoria.
--
-- Que NO hace esta migracion
-- --------------------------
-- No importa nada. Solo abre el sitio donde va el rastro. La carga es un paso
-- aparte, y a proposito: los respaldos son de MySQL y el destino es PostgreSQL,
-- asi que no hay restauracion directa que valga -hay que leer los INSERT y
-- validar cada fila contra las reglas del almacen-.

BEGIN;

-- 1. El folio del vale: el numero con el que la gente lo conoce.
ALTER TABLE incident
    ADD COLUMN IF NOT EXISTS external_folio VARCHAR(40),
    -- De donde vino. Se declara porque puede haber mas de un sistema anterior,
    -- y un folio "140" no significa lo mismo en dos origenes distintos.
    ADD COLUMN IF NOT EXISTS external_source VARCHAR(30);

-- El mismo folio del mismo origen es el mismo vale. Es lo que hace que volver a
-- correr la carga actualice en lugar de duplicar.
CREATE UNIQUE INDEX IF NOT EXISTS uq_incident_external_folio
    ON incident (external_source, external_folio)
    WHERE external_folio IS NOT NULL AND deletion_date IS NULL;

-- Por donde se busca un vale cuando alguien pregunta por su numero de siempre.
CREATE INDEX IF NOT EXISTS idx_incident_external_folio
    ON incident (external_folio)
    WHERE external_folio IS NOT NULL;

-- 2. El producto: su identificador en el sistema anterior.
ALTER TABLE product
    ADD COLUMN IF NOT EXISTS external_id INTEGER,
    ADD COLUMN IF NOT EXISTS external_source VARCHAR(30);

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_external_id
    ON product (external_source, external_id)
    WHERE external_id IS NOT NULL AND deletion_date IS NULL;

-- 3. El renglon del vale: igual, para poder repetir la carga.
ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS external_id INTEGER,
    ADD COLUMN IF NOT EXISTS external_source VARCHAR(30);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nm_incident_product_external_id
    ON nm_incident_product (external_source, external_id)
    WHERE external_id IS NOT NULL AND deletion_date IS NULL;

-- 4. La ubicacion en texto libre que trae el sistema anterior.
--
--    Su `producto.id_ubicacion` es `VARCHAR(100)`, no una llave: es texto que
--    alguien escribio. Ahi esta el origen de "muchas cosas no estan en una
--    ubicacion particular". Se conserva tal cual para poder auditar el mapeo
--    despues -que texto acabo en que ubicacion, y que texto no se pudo mapear y
--    fue a la ubicacion general-.
ALTER TABLE product
    ADD COLUMN IF NOT EXISTS external_location_text VARCHAR(100);

COMMIT;
