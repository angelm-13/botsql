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
    # NO se filtra por licencia aqui, a proposito. El SQL que sale de este
    # generador se commitea como migracion y se aplica a todos los ambientes:
    # recortarlo en tiempo de generacion hornearia el plan de un cliente dentro
    # de la migracion, y el siguiente cliente heredaria el recorte del anterior.
    #
    # El filtro va en el SQL, contra la variable `licensed_modules` que recibe
    # `psql -v` al aplicar. Cada fila lleva su `modulo_licencia` para eso.
    filas = filas_de_permisos()

    renglones = []
    ultimo = len(filas) - 1
    for indice, fila in enumerate(filas):
        (rol_nombre, entidad, bits, menu_location,
         menu_group, menu_icon, menu_label, menu_order, modulo_licencia) = fila
        coma = "," if indice < ultimo else ""
        renglones.append(
            f"    ({_sql(rol_nombre)}, '{entidad}', {bits}, '{menu_location}', "
            f"{_sql(menu_group)}, {_sql(menu_icon)}, {_sql(menu_label)}, {menu_order}, "
            f"'{modulo_licencia}'){coma}"
            f"   -- {rol_nombre} / {NOMBRE_DE_BITS.get(bits, bits)}"
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
        capacidades_sql=", ".join(f"'{c.clave}'" for c in sorted(CAPACIDADES, key=lambda c: c.clave)),
        roles_sql=",\n".join(
            f"    ({r.id_permission}, {_sql(r.nombre)})" for r in ROLES
        ),
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

-- NO se marca de baja lo vigente antes de sembrar.
--
-- Lo hacia, y corria en cada reinicio del pod: cualquier ajuste hecho desde el
-- gestor de roles se revertia en el siguiente despliegue. Medido antes del
-- cambio: un permiso subido de 2 a 15 en el gestor volvia a 2 al reaplicar.
--
-- La decision es que el gestor manda y el registro solo siembra lo que falta.
-- El registro sigue dando los valores POR OMISION -lo que recibe un modulo o un
-- rol nuevo- y deja de ser la fuente de la verdad sobre quien puede que.
--
-- Retirar un modulo cuando cambia la licencia ya no necesita borrar filas: el
-- plan se comprueba en cada peticion y filtra el menu, asi que un modulo fuera
-- del plan es inalcanzable aunque su fila exista. Ver `app/modules/plan.py`.

-- Antes de sembrar: se borran las bajas que dejo el mecanismo VIEJO.
--
-- Hasta este cambio, este archivo marcaba de baja todo lo vigente en cada
-- reinicio antes de insertar. Las filas que quedaron de baja por eso no las
-- quito nadie: son residuo. Y el sembrado nuevo respeta una baja -porque desde
-- ahora significa que el administrador la quito-, asi que sin esta limpieza
-- esos permisos no volverian nunca.
--
-- Se borran fisicamente para que el INSERT de abajo las vuelva a crear con el
-- valor por omision del registro, que es el punto de partida correcto.
--
-- La fecha esta fija a proposito. Esta migracion se reaplica en cada arranque
-- del pod: sin la cota, cada despliegue borraria tambien las bajas que el
-- administrador hizo despues, o sea el problema que estamos arreglando. Antes
-- de la cota es residuo; despues, decision de alguien.
DELETE FROM entity_permission
 WHERE deletion_date IS NOT NULL
   AND deletion_date < TIMESTAMP '2026-09-02 18:00:00';

-- Los roles que el registro declara, creados si esta base no los tiene.
--
-- Los escribia `database/seed.sql` a mano, y por eso una instalacion nueva
-- salia con los identificadores cruzados: el archivo ocupaba los ids 2 y 3 con
-- 'gerente_administrativo' y 'vendedor' -dos perfiles que el negocio no
-- reconoce- y empujaba a Supervisor y Gerente a numeros altos. El desastre que
-- eso causo en clientes reales esta documentado en
-- 20260908100000_roles_con_los_ids_de_la_base.sql.
--
-- Se crea por NOMBRE, no por numero: si el rol ya existe -con el id que sea- no
-- se toca nada. El id del registro solo se usa cuando ESTA LIBRE, que es el
-- caso de una instalacion nueva, para que los numeros salgan como el registro
-- los documenta. Nunca se mueve un rol existente de identificador: los
-- usuarios apuntan ahi, y moverlos es mover permisos de gente real.
INSERT INTO permission (
    id_permission, created_by, authorized_by, permission_description,
    id_department, id_subdepartment, id_level
)
SELECT r.id_permission, 1, 1, r.role_name, 1, 1, 1
  FROM (VALUES
{roles_sql}
       ) AS r(id_permission, role_name)
 WHERE NOT EXISTS (
         SELECT 1 FROM permission p
          WHERE lower(p.permission_description) = lower(r.role_name)
            AND p.deletion_date IS NULL
       )
   AND NOT EXISTS (
         SELECT 1 FROM permission p WHERE p.id_permission = r.id_permission
       );

-- El mismo rol, cuando su numero del registro ya lo ocupa otro. Deja que la
-- secuencia asigne uno: lo que importa es que el rol exista y se llame como el
-- registro dice, porque la matriz de abajo resuelve por nombre.
INSERT INTO permission (
    created_by, authorized_by, permission_description,
    id_department, id_subdepartment, id_level
)
SELECT 1, 1, r.role_name, 1, 1, 1
  FROM (VALUES
{roles_sql}
       ) AS r(id_permission, role_name)
 WHERE NOT EXISTS (
         SELECT 1 FROM permission p
          WHERE lower(p.permission_description) = lower(r.role_name)
            AND p.deletion_date IS NULL
       );

-- Los INSERT de arriba fijan identificadores explicitos, lo que NO avanza la
-- secuencia. Sin realinearla, el siguiente rol que alguien cree desde la
-- pantalla choca contra una llave ya usada.
SELECT setval(
    pg_get_serial_sequence('permission', 'id_permission'),
    GREATEST((SELECT MAX(id_permission) FROM permission), 1)
);

-- La matriz se resuelve por NOMBRE de rol, no por id_permission fijo.
--
-- Version anterior de este archivo escribia el numero de `id_permission`
-- directo en las VALUES, asumiendo que ese numero significa lo mismo en
-- cualquier instalacion. Es falso: los ids de `permission` dependen del
-- orden en que cada base sembro sus roles. Medido en dos ambientes reales
-- con la version vieja: en un cliente, el id que aqui se penso como
-- "gerente_administrativo" resulto ser de verdad "Supervisor", y Facturacion
-- se concedio a un rol operativo que nunca debia tenerla; en otro cliente, un
-- numero distinto choco con "Almacenista" en vez de con el rol pensado.
--
-- Se guarda la matriz completa (con el NOMBRE de cada rol, no su numero) en
-- una tabla temporal para no repetir las 300+ filas dos veces -una para
-- limpiar lo viejo, otra para sembrar lo nuevo-: ambos pasos hacen JOIN
-- contra `permission.permission_description` para resolver el id real de
-- ESTA base.
CREATE TEMP TABLE matriz_de_permisos AS
SELECT * FROM (VALUES
{filas}
) AS v (role_name, entity_name, control_type, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia);

-- Limpieza de lo que la version vieja (con id fijo) pudo haber sembrado en el
-- rol equivocado. Solo toca created_by=1 -nunca una fila que un
-- administrador haya ajustado desde el gestor de roles-, y solo entidades que
-- esta matriz gestiona: si el par (id_permission, entidad) que hoy existe no
-- es el que le corresponde por NOMBRE al rol que de verdad tiene ese id en
-- esta base, se borra. El INSERT de abajo la repone bien de inmediato.
DELETE FROM entity_permission ep
 WHERE ep.created_by = 1
   AND ep.entity_name IN (SELECT DISTINCT entity_name FROM matriz_de_permisos)
   AND NOT EXISTS (
     SELECT 1
       FROM matriz_de_permisos m
       JOIN permission p
         ON p.permission_description = m.role_name
        AND p.deletion_date IS NULL
      WHERE p.id_permission = ep.id_permission
        AND m.entity_name = ep.entity_name
        AND (
          m.modulo_licencia IN ({modulos_core_sql})
          OR :'licensed_modules' = ''
          OR m.modulo_licencia = ANY(string_to_array(:'licensed_modules', ','))
        )
   );

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, m.entity_name, m.control_type, m.menu_location,
       m.menu_group, m.menu_group_icon, m.menu_label, m.menu_order, 1
FROM matriz_de_permisos m
JOIN permission p
  ON p.permission_description = m.role_name
 AND p.deletion_date IS NULL
WHERE (
    m.modulo_licencia IN ({modulos_core_sql})
    OR :'licensed_modules' = ''
    OR m.modulo_licencia = ANY(string_to_array(:'licensed_modules', ','))
  )
-- La restriccion unica es por (perfil, entidad) sin importar la baja logica, y
-- aqui NO se toca la fila que ya existe: ni sus bits, ni su navegacion, ni su
-- baja.
--
-- Una fila viva es del gestor: pisarla revierte el trabajo del administrador.
-- Una fila de baja significa que la quitaron a proposito -el gestor la marca de
-- baja en vez de borrarla-, asi que reactivarla devolveria un acceso retirado.
--
-- Se siembra solo el par (perfil, entidad) que no existe todavia: un modulo
-- nuevo, una entidad nueva, un rol nuevo. Eso es "sembrar lo que falta".
ON CONFLICT (id_permission, entity_name) DO NOTHING;

-- El catalogo de campos, poblado con las columnas REALES de cada entidad que
-- esta matriz gestiona.
--
-- Por que hacia falta
-- -------------------
-- `nm_field_permission` -- la tabla que decide que atributos ve un rol -- se
-- deriva mas abajo cruzando `entity_permission` con `field`. Si `field` no
-- tiene las columnas de una tabla, ese cruce no produce NADA para ella, y la
-- pantalla generica no pinta ni una columna porque solo muestra los campos
-- concedidos (`canSeeField` en el frontend).
--
-- Medido en la base antes de este cambio: `field` cubria 34 tablas, y eran casi
-- todas de logistica, documentos y laboratorio -- las que llegaron de ramas que
-- traian su propio sembrado. Inventario, facturacion, CRM, recursos humanos y
-- configuracion tenian CERO filas. El efecto real: un Almacenista abria
-- Productos y no veia ninguna columna, aunque su rol concede `product` en
-- CAPTURA; solo la cuenta de arranque veia algo, porque salta la comprobacion.
--
-- La fuente es `information_schema`, no una lista escrita a mano: una lista se
-- desfasa en cuanto alguien agrega una columna, que es exactamente como se
-- llego aqui. Las capacidades no aparecen porque no son tablas y el JOIN no las
-- encuentra, que es lo correcto: no tienen campos que conceder.
INSERT INTO field (table_name, field_name, created_by)
SELECT c.table_name, c.column_name, 1
  FROM information_schema.columns c
  JOIN (SELECT DISTINCT entity_name FROM matriz_de_permisos) m
    ON m.entity_name = c.table_name
 WHERE c.table_schema = 'public'
   -- Una capacidad NO es una tabla, aunque se llame como una.
   --
   -- `restaurant_waiter` es las dos cosas: la capacidad "Meseros" que concede
   -- la pantalla, y una tabla real del restaurante. Sin esta exclusion el
   -- cruce de arriba le poblaria campos a la capacidad -- y el gestor pediria
   -- marcar columnas de una tabla que esa capacidad no gobierna. La lista sale
   -- del registro, no escrita a mano, para que una capacidad nueva con nombre
   -- de tabla no vuelva a colarse.
   AND c.table_name NOT IN ({capacidades_sql})
   -- Las administra el sistema: `created_by` lo fija el servicio con el
   -- usuario de la sesion, y las tres fechas las escribe el ORM. Publicarlas
   -- como configurables invita a capturarlas a mano.
   AND c.column_name NOT IN ('created_by', 'creation_date', 'last_update_date', 'deletion_date')
   AND NOT EXISTS (
     SELECT 1 FROM field f
      WHERE f.table_name = c.table_name
        AND f.field_name = c.column_name
        AND f.deletion_date IS NULL
   );

-- Y se retiran las columnas de sistema que sembrados anteriores si publicaron.
--
-- `field` traia 124 filas de `created_by`, `creation_date`, `last_update_date`
-- y `deletion_date` -- casi todas de logistica, documentos y laboratorio, que
-- llegaron con el sembrado de su propia rama. La pantalla ya las ocultaba, pero
-- la derivacion de mas abajo si les daba permiso, asi que cada rol cargaba
-- decenas de filas que no gobiernan nada.
UPDATE field f
   SET deletion_date = now(),
       last_update_date = now()
 WHERE f.deletion_date IS NULL
   AND f.field_name IN ('created_by', 'creation_date', 'last_update_date', 'deletion_date')
   AND EXISTS (SELECT 1 FROM matriz_de_permisos m WHERE m.entity_name = f.table_name);

-- Una columna que ya no existe en la tabla deja de ofrecerse. Se retira en
-- logico, como todo aqui, asi que el permiso que alguien le hubiera dado queda
-- para consulta. Si la columna vuelve, el INSERT de arriba la repone como fila
-- nueva en la siguiente corrida -- sin arrastrar los permisos de antes, que es
-- lo correcto: la columna de hoy puede no significar lo que significaba.
UPDATE field f
   SET deletion_date = now(),
       last_update_date = now()
 WHERE f.deletion_date IS NULL
   AND EXISTS (SELECT 1 FROM matriz_de_permisos m WHERE m.entity_name = f.table_name)
   AND f.table_name NOT IN ({capacidades_sql})
   AND NOT EXISTS (
     SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public'
        AND c.table_name = f.table_name
        AND c.column_name = f.field_name
   );

DROP TABLE matriz_de_permisos;

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
        -- Tambien cuenta la baja del CAMPO, no solo la de la entidad. Sin esta
        -- linea, retirar una columna del catalogo dejaba viva su concesion:
        -- eran las 124 filas de `created_by` y las tres fechas, que seguian
        -- concedidas despues de dar de baja el campo.
        AND f.deletion_date IS NULL
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
