-- Los permisos de las caracteristicas del material.
--
-- El registro ya declara `material_attribute` como entidad del modulo de
-- inventario, asi que una instalacion nueva la siembra sola. Esta migracion es
-- para las bases que ya existen: la matriz de permisos no vuelve a pasar por
-- ellas -siembra con ON CONFLICT DO NOTHING- y sin fila no hay nada que el
-- gestor pueda editar.
--
-- El acceso se COPIA, no se escribe
-- ---------------------------------
-- Copia lo que el rol ya tiene sobre `material`. Declarar "largo" en la familia
-- de desarmadores es configurar el alta de todos los desarmadores, asi que va
-- con quien captura materiales. Escribir un valor fijo le daria configuracion a
-- quien solo consulta, o se la negaria a quien captura.
--
-- Sin entrada de menu, y no por descuido
-- --------------------------------------
-- `menu_location = 'hidden'`. Las caracteristicas se configuran DENTRO de la
-- familia, en la pantalla "Familias y tipos": una caracteristica sin su familia
-- no significa nada -"largo" es el largo DE un desarmador- y una entrada de
-- menu llamada "Caracteristicas de material" no diria de que familia son.
--
-- Queda declarado en `DENTRO_DE_OTRA_PANTALLA`, en
-- tests/test_security/test_menu_reachability.py, que es lo que impide que esto
-- pase por una entidad olvidada. Ahi hay ademas una prueba de que si la
-- pantalla anfitriona pierde su entrada, esta no se queda sin puerta en
-- silencio.
--
-- El gestor manda: si el par ya existe -vivo o retirado a proposito- no se
-- toca. Ver 20260903100000 para el mismo criterio.

BEGIN;

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, 'material_attribute', p.control_type, 'hidden',
       'Inventario', 'inventory', NULL, 219, 1
FROM entity_permission p
WHERE p.entity_name = 'material'
  AND p.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission x
      WHERE x.id_permission = p.id_permission
        AND x.entity_name = 'material_attribute'
  );

COMMIT;
