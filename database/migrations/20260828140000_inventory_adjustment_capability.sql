-- Capacidad separada para ajustar existencias.
--
-- Por que: el ajuste es el unico movimiento de almacen sin documento detras y
-- sin tope. Puede crear existencia de la nada o destruirla por cualquier
-- cantidad, asi que es justo la operacion con la que se tapa un faltante.
-- Antes bastaba con el permiso de editar productos, el mismo que necesita
-- cualquiera que registre una entrada o una salida normal.
--
-- Los demas movimientos quedan acotados: una salida no puede exceder la
-- existencia, una entrada por compra viene de una factura, y las mermas exigen
-- motivo escrito.
--
-- Se concede a los roles que ya tienen responsabilidad de inventario, no a
-- todos: quien surte y despacha no necesita poder ajustar.

BEGIN;

INSERT INTO entity_permission (id_permission, entity_name, control_type, menu_location, menu_order, created_by)
SELECT p.id_permission, 'inventory_adjustment', 2, 'hidden', 999, 1
FROM permission p
WHERE p.permission_description IN ('Administrator', 'admin', 'Gerente', 'gerente_administrativo')
  AND p.deletion_date IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM entity_permission ep
    WHERE ep.id_permission = p.id_permission
      AND ep.entity_name = 'inventory_adjustment'
      AND ep.deletion_date IS NULL
  );

COMMIT;
