"""Genera el sembrado de permisos a partir del registro de modulos.

Reemplaza a `seed_entity_permissions.py`, que agrupaba las entidades en dominios
inventados al momento -catalogos, comercial, encuestas- que no coincidian con
los modulos que el negocio reconoce. Ahora la fuente de verdad es
`app/modules/registry.py`, donde cada entidad pertenece a exactamente un modulo
y el archivo se niega a cargar si alguna queda fuera o en dos.

A diferencia del anterior, este SUSTITUYE lo que hay en lugar de rellenar
huecos. Conservar filas viejas junto a las nuevas es como aparecieron los
descuadres anteriores: dos criterios conviviendo, sin forma de saber cual gano.
El borrado es logico -se marca `deletion_date`-, asi que lo anterior queda para
consulta y la operacion se puede revisar despues.

Las capacidades van dentro del mismo sembrado a proposito. Son derechos con
nombre propio -autorizar un proyecto, ajustar existencias, supervisar
incidencias- que viven en la misma tabla que las entidades sin corresponder a
ninguna; si se resembrara solo lo que es tabla, se perderian y con ellas la
separacion de funciones.

Uso:
    python scripts/seed_module_permissions.py             # imprime el SQL
    python scripts/seed_module_permissions.py destino.sql # lo escribe
"""

from __future__ import annotations

import pathlib
import sys


RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.modules.registry import (  # noqa: E402
    CAPACIDADES,
    MODULOS,
    MODULOS_CORE,
    NOMBRE_DE_BITS,
    ROLES,
    filas_de_permisos,
)


def _sql(valor):
    if valor is None or valor == "":
        return "NULL"
    return "'" + str(valor).replace("'", "''") + "'"


def generar() -> str:
    filas = filas_de_permisos()

    renglones = []
    ultimo = len(filas) - 1
    for indice, fila in enumerate(filas):
        (id_permission, entidad, bits, menu_location,
         menu_group, menu_icon, menu_label, menu_order, modulo_licencia) = fila
        rol = next(r.nombre for r in ROLES if r.id_permission == id_permission)
        coma = "," if indice < ultimo else ""
        renglones.append(
            f"    ({id_permission}, '{entidad}', {bits}, '{menu_location}', "
            f"{_sql(menu_group)}, {_sql(menu_icon)}, {_sql(menu_label)}, {menu_order}, "
            f"'{modulo_licencia}'){coma}"
            f"   -- {rol} / {NOMBRE_DE_BITS.get(bits, bits)}"
        )

    resumen = []
    for modulo in MODULOS:
        roles_con_acceso = [
            f"{r.nombre} ({NOMBRE_DE_BITS.get(r.modulos[modulo.clave], r.modulos[modulo.clave])})"
            for r in ROLES if modulo.clave in r.modulos
        ]
        almacen = "  [almacen propio]" if modulo.almacen else ""
        resumen.append(
            f"--   {modulo.clave:14s} {len(modulo.entidades):3d} entidades{almacen}\n"
            f"--     {', '.join(roles_con_acceso) or 'ningun rol'}"
        )

    return PLANTILLA.format(
        total_filas=len(filas),
        total_modulos=len(MODULOS),
        total_roles=len(ROLES),
        total_capacidades=len(CAPACIDADES),
        resumen="\n".join(resumen),
        filas="\n".join(renglones),
        modulos_core_sql=", ".join(f"'{clave}'" for clave in sorted(MODULOS_CORE)),
    )


PLANTILLA = """-- Permisos por modulo y accion CRUD. GENERADO por
-- backend/scripts/seed_module_permissions.py desde app/modules/registry.py.
-- No editar a mano: el registro es la fuente de verdad y cualquier cambio aqui
-- se pierde en la siguiente generacion.
--
-- Licencia por modulo/cliente
-- ---------------------------
-- El proyecto se vende por modulo: un cliente contrata Facturacion y
-- Restaurante, otro ademas Multiemisor+CSD. Los modulos de infraestructura
-- ({modulos_core_sql}) van siempre, sin importar licencia -- sin ellos ni
-- login ni un select de catalogo funcionan. Todo lo demas (incluida una
-- capacidad marcada `licencia_independiente=True`, como multiemisor dentro de
-- facturacion) solo se siembra si su clave aparece en la variable de entorno
-- LICENSED_MODULES del cliente (separada por comas), leida via `psql -v
-- licensed_modules=...` -- ver k8s/base/backend.yaml.
--
-- LICENSED_MODULES vacia o sin definir se interpreta como "todos los modulos":
-- una instalacion que nunca configuro esta variable (los 3 ambientes reales
-- de hoy) sigue viendo exactamente lo mismo que antes de este cambio, hasta
-- que alguien la restrinja a proposito.
--
-- Que cambia respecto al sembrado anterior
-- ----------------------------------------
-- Las entidades se agrupaban en dominios inventados al momento -catalogos,
-- comercial, encuestas- que no coincidian con los modulos del negocio. Ahora
-- cada entidad pertenece a exactamente un modulo declarado, y el registro se
-- niega a cargar si alguna queda fuera o en dos.
--
-- Este sembrado SUSTITUYE lo anterior en lugar de rellenar huecos: conservar
-- dos criterios conviviendo es como aparecieron los descuadres previos. El
-- borrado es logico, asi que lo anterior queda para consulta.
--
-- Los tres almacenes viven en modulos distintos y no comparten tabla ni
-- servicio. Conceder `inventario` a un rol NO le da el almacen de logistica ni
-- el del restaurante.
--
-- {total_modulos} modulos, {total_roles} roles, {total_capacidades} capacidades,
-- {total_filas} filas.
--
{resumen}

BEGIN;

-- Se marca de baja todo lo vigente antes de sembrar. Sin esto quedarian filas
-- de la matriz anterior con criterios distintos, y no habria forma de saber
-- cual gobierna. Corre en cada reinicio del pod, asi que tambien es lo que
-- retira un modulo si LICENSED_MODULES cambia a algo mas restringido.
UPDATE entity_permission
   SET deletion_date = now()
 WHERE deletion_date IS NULL;

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT v.id_permission, v.entity_name, v.control_type, v.menu_location,
       v.menu_group, v.menu_group_icon, v.menu_label, v.menu_order, 1
FROM (VALUES
{filas}
) AS v (id_permission, entity_name, control_type, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia)
WHERE EXISTS (SELECT 1 FROM permission p WHERE p.id_permission = v.id_permission)
  AND (
    v.modulo_licencia IN ({modulos_core_sql})
    OR :'licensed_modules' = ''
    OR v.modulo_licencia = ANY(string_to_array(:'licensed_modules', ','))
  )
-- La restriccion unica es por (perfil, entidad) sin importar la baja logica, asi
-- que se reactiva la fila en lugar de insertar una segunda.
ON CONFLICT (id_permission, entity_name) DO UPDATE
   SET control_type = EXCLUDED.control_type,
       menu_location = EXCLUDED.menu_location,
       menu_group = EXCLUDED.menu_group,
       menu_group_icon = EXCLUDED.menu_group_icon,
       menu_label = EXCLUDED.menu_label,
       menu_order = EXCLUDED.menu_order,
       deletion_date = NULL,
       last_update_date = now();

-- Los permisos de campo se derivan del permiso de entidad, asi que hay que
-- rehacerlos: un modulo que cambio de alcance arrastra sus campos. Se dan de
-- baja los que quedaron sin respaldo y se derivan los que faltan.
UPDATE nm_field_permission nfp
   SET deletion_date = now()
 WHERE nfp.deletion_date IS NULL
   AND NOT EXISTS (
     SELECT 1
       FROM entity_permission ep
       JOIN field f ON f.id_field = nfp.id_field
      WHERE ep.id_permission = nfp.id_permission
        AND ep.entity_name = f.table_name
        AND ep.deletion_date IS NULL
   );

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
-- entity_permission.control_type es `text` en la base real (no coincide con
-- el `SmallInteger` que declara el modelo -- deuda aparte, no de esta
-- migracion); sin el cast, LEAST(text, integer) no resuelve tipo comun.
SELECT f.id_field, ep.id_permission, LEAST(ep.control_type::integer, 15)::text, 1
FROM entity_permission ep
JOIN field f
  ON f.table_name = ep.entity_name
 AND f.deletion_date IS NULL
WHERE ep.deletion_date IS NULL
  -- `created_by` lo fija el servicio con el usuario de la sesion: si fuera
  -- capturable, cualquiera podria atribuir un registro a otra persona.
  AND f.field_name <> 'created_by'
  AND NOT EXISTS (
    SELECT 1 FROM nm_field_permission nfp
    WHERE nfp.id_field = f.id_field
      AND nfp.id_permission = ep.id_permission
      AND nfp.deletion_date IS NULL
  );

COMMIT;
"""


if __name__ == "__main__":
    destino = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    sql = generar()
    if destino:
        destino.write_text(sql, encoding="utf-8")
        print(f"escrito: {destino}")
    else:
        print(sql)
