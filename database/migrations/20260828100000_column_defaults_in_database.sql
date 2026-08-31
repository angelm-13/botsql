-- Valores por omision del lado de la base, no solo del programa.
--
-- Por que importa: los modelos declaraban el valor por omision en Python
-- (`default=`), no en la base (`server_default=`). Cuando el esquema lo crea
-- el arranque a partir de los modelos, la columna queda NOT NULL y sin valor
-- por omision, de modo que cualquier INSERT en SQL directo que la omita
-- falla.
--
-- El sintoma real: `seed.sql` abortaba en su PRIMER renglon de datos, porque
-- insertaba en customer_supplier sin `is_principal`. Como el archivo completo
-- va dentro de una sola transaccion, todo lo que venia despues quedaba sin
-- aplicar: los catalogos de tipos de incidencia, tipos de tarea, plantillas,
-- servicios, departamentos, niveles y estados de inventario nunca se
-- sembraban. Por eso los modulos de Operaciones aparecian vacios y no se
-- podian usar. Y como el arranque atrapa ese error como no fatal, fallaba en
-- silencio en cada reinicio.
--
-- No se toca entity_permission.created_by, que tambien tiene el valor por
-- omision solo en Python: poner un autor por omision en la base ocultaria
-- filas creadas sin autor, y eso es peor que el estado actual.

BEGIN;

ALTER TABLE customer_supplier
    ALTER COLUMN is_principal SET DEFAULT FALSE;

ALTER TABLE invoice
    ALTER COLUMN manual_capture SET DEFAULT FALSE;

ALTER TABLE proyect
    ALTER COLUMN proyect_status SET DEFAULT 'draft';

-- Filas que hubieran quedado nulas antes de fijar el valor por omision.
UPDATE customer_supplier SET is_principal = FALSE WHERE is_principal IS NULL;
UPDATE invoice SET manual_capture = FALSE WHERE manual_capture IS NULL;
UPDATE proyect SET proyect_status = 'draft' WHERE proyect_status IS NULL;

COMMIT;

-- Segunda tanda: entity_permission omitia menu_location y menu_order en la
-- siembra, y ambos son NOT NULL con el valor por omision solo en Python.
BEGIN;

ALTER TABLE entity_permission
    ALTER COLUMN control_type SET DEFAULT 15,
    ALTER COLUMN menu_location SET DEFAULT 'sidebar',
    ALTER COLUMN menu_order SET DEFAULT 100;

COMMIT;
