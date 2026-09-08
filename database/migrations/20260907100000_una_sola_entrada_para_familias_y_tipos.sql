-- Familias y tipos: una entrada de menu, no dos.
--
-- Lo que se reporto
-- -----------------
-- "hay dos modulos que hacen lo mismo, el de tipos de material y el de familias
-- de producto, ya que en esencia son lo mismo".
--
-- En el menu, si: dos entradas seguidas, "Familias de producto" y "Tipos de
-- material", que leidas una detras de la otra parecen la misma cosa dos veces.
--
-- En los datos, no
-- ----------------
-- Son los DOS NIVELES de una sola clasificacion, y la base ya lo dice:
--
--     material_type.id_product_family -> product_family(id_product_family)
--
-- Un tipo cuelga de una familia y no existe suelto. Medido en la base al hacer
-- este cambio:
--
--     familia "Desarmadores 112347"  ->  tipos "Plano", "De cruz"
--
-- Ninguna familia se llama "Plano" y ningun tipo se llama "Desarmadores": no
-- hay dos listas de lo mismo, hay una lista y sus subdivisiones.
--
-- Por que NO se funden las tablas
-- -------------------------------
-- Fundirlas obligaria a repetir el nombre de la familia en cada tipo. Entonces
-- renombrar "Desarmadores" seria renombrarlo renglon por renglon, y con que uno
-- falle quedan dos familias donde habia una. Es exactamente lo que una llave
-- ajena evita.
--
-- Lo que se junta es la PANTALLA, que es donde estaba la confusion: ahora la
-- familia es la cabecera y sus tipos van dentro, y el alta de un tipo se hace
-- desde la familia -asi no hay desplegable donde equivocarse y capturar "Plano"
-- como tipo de "Cemento"-.
--
-- El gestor manda
-- ---------------
-- Solo se tocan las filas que siguen diciendo exactamente lo que puso la
-- migracion anterior. Si un administrador renombro su entrada de menu, eligio
-- como se llama en SU instalacion y esto no lo pisa.
--
-- Y a `material_type` se le quita la ENTRADA DE MENU, no el permiso: la entidad
-- sigue existiendo con su `control_type`, su ruta sigue respondiendo y quien no
-- tenga permiso de escritura sigue sin poder crear tipos.

BEGIN;

UPDATE entity_permission
SET menu_label = 'Familias y tipos'
WHERE entity_name = 'product_family'
  AND menu_label = 'Familias de producto';

UPDATE entity_permission
SET menu_location = 'hidden'
WHERE entity_name = 'material_type'
  AND menu_label = 'Tipos de material'
  AND menu_location = 'sidebar';

COMMIT;
