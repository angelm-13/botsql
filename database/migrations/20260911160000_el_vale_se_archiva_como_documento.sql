-- El vale impreso se guarda, no solo se genera.
--
-- Por que archivarlo
-- ------------------
-- El PDF se armaba al vuelo en cada descarga. Eso alcanza para imprimirlo, pero
-- no para lo que un vale es: un papel que alguien FIRMA. Si el documento solo
-- existe mientras dura la peticion, no hay forma de saber despues que decia el
-- que se firmo -- y un vale cambia: los renglones se van devolviendo, el estado
-- pasa de abierto a cerrado. Regenerarlo un mes despues devuelve otro papel.
--
-- Se archiva con el mecanismo que ya existe -- `document` + `document_version`,
-- el mismo del reporte de laboratorio -- en vez de inventar una carpeta o una
-- columna nueva. Eso trae gratis el control de versiones, el sha256, el tamano
-- y que el vale aparezca en el modulo de Documentos como cualquier otro papel.
--
-- Por que una categoria y no reusar una
-- -------------------------------------
-- Las que hay nombran a QUIEN pertenece el documento -- cliente, proveedor,
-- empleado -- o a un proceso ajeno -- recepcion de equipo, reporte de
-- diagnostico. Meter el vale en "proceso interno" lo volveria invisible entre
-- documentos de otra naturaleza, y el filtro por categoria es justo como la
-- gente busca en esa pantalla.
--
-- El vinculo con el vale va por `business_reference_type`/`business_reference_value`
-- y no por `document_relation`, que no tiene columna para incidencias. Es el
-- puntero generico que la tabla ya trae para exactamente esto.

BEGIN;

INSERT INTO document_category (code, name, description, created_by)
SELECT 'warehouse_voucher', 'Vale de almacen',
       'El vale de salida de material, listo para imprimir y firmar.', 1
 WHERE NOT EXISTS (
     SELECT 1 FROM document_category WHERE code = 'warehouse_voucher'
 );

COMMIT;
