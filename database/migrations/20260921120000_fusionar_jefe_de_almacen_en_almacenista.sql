-- "Jefe de almacen" deja de existir como rol: todo lo que podia hacer (crear
-- vales, autorizar/entregar, confirmar recepcion, ajustar inventario, operar
-- logistica) lo hace ahora "Almacenista" solo -- decision de negocio, ver
-- registry.py.
--
-- La tabla de roles es `permission`, identificada por NOMBRE
-- (`permission_description`), no por `id_permission` -- ese id lo asigna
-- Postgres y NO es estable entre instalaciones (confirmado: "Almacenista"
-- salio con id distinto en cada cliente real). Por eso todo se resuelve por
-- nombre, nunca con un id hardcodeado.
--
-- Ademas, Gerente y Supervisor ganan visibilidad de solo lectura sobre el
-- almacen (Gerente ve TODO sin poder tocar nada; Supervisor ya tenia
-- `warehouse_prevoucher`, aqui se le abre la puerta de lectura de vales ya
-- autorizados via el guard de rutas -- ver warehouse_voucher.py).

BEGIN;

DO $$
DECLARE
    id_almacenista INTEGER;
    id_jefe_almacen INTEGER;
BEGIN
    SELECT id_permission INTO id_almacenista FROM permission
        WHERE permission_description = 'Almacenista' AND deletion_date IS NULL LIMIT 1;

    IF id_almacenista IS NULL THEN
        RAISE NOTICE 'No existe el rol Almacenista en esta instalacion -- nada que fusionar.';
    ELSE
        SELECT id_permission INTO id_jefe_almacen FROM permission
            WHERE permission_description = 'Jefe de almacen' AND deletion_date IS NULL LIMIT 1;

        IF id_jefe_almacen IS NOT NULL THEN
            -- Reasignar a cualquier usuario real antes de tocar el catalogo.
            UPDATE "user" SET id_permission = id_almacenista WHERE id_permission = id_jefe_almacen;

            -- Copiar a Almacenista cualquier entity_permission que Jefe de
            -- almacen tuviera y Almacenista todavia NO TENGA EN ABSOLUTO
            -- (tipicamente logistica, inventory_adjustment,
            -- warehouse_voucher_authorize). Nunca se toca una fila que
            -- Almacenista ya tenga -- ni siquiera para subirle el bit de
            -- BORRAR en inventario -- porque el Gestor de roles y permisos
            -- manda sobre lo que un administrador ya haya ajustado a mano;
            -- una migracion que suba bits en cada reinicio del pod se
            -- llevaria por delante ese ajuste en el siguiente despliegue
            -- (ver test_manager_wins.py). Si algun cliente real quiere que
            -- su Almacenista ya existente tambien borre en inventario, es
            -- un ajuste del Gestor, no de esta migracion.
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
            ) THEN
                INSERT INTO entity_permission (
                    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
                    menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
                )
                SELECT id_almacenista, fuente.entity_name,
                       fuente.scope_create, fuente.scope_read, fuente.scope_update, fuente.scope_delete,
                       fuente.menu_location, fuente.menu_group, fuente.menu_group_icon, fuente.menu_label, fuente.menu_order,
                       1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM entity_permission fuente
                WHERE fuente.id_permission = id_jefe_almacen AND fuente.deletion_date IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM entity_permission destino
                      WHERE destino.id_permission = id_almacenista AND destino.entity_name = fuente.entity_name
                  );
            END IF;

            -- Retirar el rol del catalogo (borrado logico, no DROP).
            UPDATE entity_permission SET deletion_date = CURRENT_TIMESTAMP
                WHERE id_permission = id_jefe_almacen AND deletion_date IS NULL;
            UPDATE permission SET deletion_date = CURRENT_TIMESTAMP
                WHERE id_permission = id_jefe_almacen AND deletion_date IS NULL;
        END IF;
    END IF;
END $$;

-- Gerente ve el almacen completo (todos los vales, no solo los suyos -- no
-- tiene ninguno propio), sin poder crear/autorizar/cerrar nada: solo
-- scope_read, el resto en 0. El valor "concedido" en esta columna es 4
-- ("Todos"), no el bit viejo LEER=2 -- mismo criterio que ya usan las
-- migraciones anteriores (ver 20260910110000, que siembra scope_read=4).
-- Los campos de menu se copian de la fila de Almacenista para ese mismo
-- `warehouse_voucher` en vez de inventarlos, para que el renglon de Gerente
-- en el Gestor quede con la misma etiqueta/grupo/icono reales.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN
    INSERT INTO entity_permission (
        id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
        menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
    )
    SELECT gerente.id_permission, 'warehouse_voucher', 0, 4, 0, 0,
           COALESCE(referencia.menu_location, 'hidden'), referencia.menu_group,
           referencia.menu_group_icon, referencia.menu_label,
           COALESCE(referencia.menu_order, 299), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    FROM permission gerente
    LEFT JOIN permission almacenista ON almacenista.permission_description = 'Almacenista'
                                     AND almacenista.deletion_date IS NULL
    LEFT JOIN entity_permission referencia ON referencia.id_permission = almacenista.id_permission
                                            AND referencia.entity_name = 'warehouse_voucher'
                                            AND referencia.deletion_date IS NULL
    WHERE gerente.permission_description = 'Gerente' AND gerente.deletion_date IS NULL
      AND NOT EXISTS (
          SELECT 1 FROM entity_permission ep
          WHERE ep.id_permission = gerente.id_permission AND ep.entity_name = 'warehouse_voucher' AND ep.deletion_date IS NULL
      );
END IF;
END $$;

COMMIT;
