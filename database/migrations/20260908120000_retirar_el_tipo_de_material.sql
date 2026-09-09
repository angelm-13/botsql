-- El tipo de material sale del flujo. La descripcion ya lo trae.
--
-- Por que
-- -------
-- Se reporto mirando los datos: en materiales hay "BROCA HELICOIDAL 3/4" y
-- "DADO 3/16". El nombre YA trae la familia, el tipo y la medida. Un nivel de
-- "tipo" aparte no distingue nada que la descripcion no distinga, y obliga a
-- capturar dos veces lo mismo.
--
-- Los datos lo decian desde el principio: el sistema anterior no tiene columna
-- de tipo en `material` -solo id, descripcion y unidad- porque nunca la
-- necesito. Y tras la carga eran 603 materiales con CERO tipos.
--
-- Que se retira
-- -------------
-- Las filas de permiso de `material_type`, en LOGICO. Sin rutas que las lean,
-- una fila viva en el gestor ofrece administrar algo que ya no existe.
--
-- Que NO se toca
-- --------------
-- Las tablas `material_type` y `material_attribute_option`, ni la columna
-- `material.id_material_type`. Hay 4 tipos capturados a mano y borrar la tabla
-- se los lleva por delante; que hacer con ellos no es una decision que un
-- cambio de pantalla deba tomar. Sin nada que las lea no estorban, y si algun
-- dia el tipo vuelve a hacer falta, el rastro sigue ahi.
--
-- La familia SI se queda: `material.id_product_family` es NOT NULL y hay 146
-- familias en uso. Lo que se va es el segundo nivel.

BEGIN;

UPDATE entity_permission
   SET deletion_date = now(),
       last_update_date = now()
 WHERE entity_name = 'material_type'
   AND deletion_date IS NULL;

-- Y la etiqueta de la familia, que quedo mintiendo.
--
-- El renglon decia "Familias y tipos" y en el menu se seguia leyendo asi
-- despues de retirar el tipo. No lo arreglaba el sembrado: desde
-- 20260901000000 una fila viva es del gestor y `ON CONFLICT DO NOTHING` no la
-- pisa, asi que el registro puede decir "Familias de producto" y la base
-- seguir con el nombre viejo para siempre.
--
-- Se acota al valor exacto que dejo el cambio anterior. Si el administrador le
-- pone otro nombre, este UPDATE ya no lo alcanza: la migracion se reaplica en
-- cada arranque y sin la cota le estaria borrando el nombre cada vez.
UPDATE entity_permission
   SET menu_label = 'Familias de producto',
       last_update_date = now()
 WHERE entity_name = 'product_family'
   AND menu_label = 'Familias y tipos'
   AND deletion_date IS NULL;

COMMIT;
