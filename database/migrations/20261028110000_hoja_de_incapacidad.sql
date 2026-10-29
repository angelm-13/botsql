-- Categoria de documento para la hoja de incapacidad del IMSS.
--
-- De que se parte
-- ---------------
-- La incapacidad se registraba sin su comprobante. La revision contable
-- (2026-10-28) pidio que el empleado la reporte y suba su hoja, y que RH la
-- revise o la suba si se la entregaron en papel, para tenerla en archivo digital.
--
-- Que se agrega
-- -------------
-- document_category 'disability_certificate'   las hojas se guardan con el
--                     modulo de Documentos (document + document_version), un
--                     documento por incapacidad con referencia employee_leave/<id>
--                     (services/employee_leave_document_service.py). Solo las ven
--                     el propio empleado y RH: es un dato medico.
--
-- Reaplicable: ON CONFLICT (code) DO NOTHING. No toca entity_permission.
BEGIN;

INSERT INTO document_category (code, name, description, created_by)
SELECT 'disability_certificate', 'Hoja de incapacidad',
       'Hoja de incapacidad del IMSS ligada a una ausencia; solo la ven el empleado y RH',
       COALESCE((SELECT MIN(id_user) FROM "user"), 1)
WHERE EXISTS (SELECT 1 FROM "user")
ON CONFLICT (code) DO NOTHING;

COMMIT;
