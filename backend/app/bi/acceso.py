"""Que puede ver cada usuario en el modulo BI, segun su rol.

Reusa lo que el gestor de roles de tyakxa ya administra -- no inventa un
segundo sistema de permisos:

  * Tablas:   `entity_permission.scope_read != 0` para el rol del usuario.
              Sin fila, sin acceso (falla cerrado). Las tablas de permisos
              nunca se exponen a quien no es administrador.
  * Columnas: `field` + `nm_field_permission`. Si el rol tiene una fila para el
              campo y le falta el bit de lectura (2), la columna no existe para
              ese usuario: ni en el DDL que ve el modelo, ni en la consulta
              (el validador la rechaza), ni en el resultado.
  * Administrador: superusuario / bootstrap, o el rol llamado "Administrator"
              (o "Administrador"). Ve todo lo que el plan del despliegue permita.

Asi "el encargado de Operaciones no ve los movimientos de Finanzas" se configura
donde ya se configuran los demas permisos: quitando la lectura de esas
entidades -- o de la columna de importe -- al rol.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, replace

FIELD_READ_BIT = 2
NOMBRES_DE_ADMIN = {"administrator", "administrador"}
# Tablas de seguridad: solo las ve un administrador, aunque el rol las tenga.
SOLO_ADMIN = {
    "permission", "entity_permission", "nm_field_permission", "field",
    "bi_department_permission", "event_log", "user_mfa", "password_reset_token",
    "public_api_key", "pac_config",
}
# Sensibles y sin columna `created_by`: no se pueden acotar por dueno, asi que con
# alcance Propios/Mis grupos se niegan (solo las lee quien tiene Todos).
SIN_DUENO_SENSIBLES = {
    "bank_statement_movement", "invoice_cfdi_xml", "purchase_budget", "purchase_policy",
    "quotation_comment", "document_version", "kpi_snapshot",
}
# Ademas de `created_by`, quien tambien es dueno de la fila (misma regla que
# project_management_service: el lider ve su proyecto aunque no lo haya creado).
DUENO_ADICIONAL = {"proyect": "leader"}
_TTL_S = 60


@dataclass(frozen=True)
class Acceso:
    clave: str                               # identifica el perfil en las caches
    es_admin: bool
    tablas: frozenset[str] | None            # None = todas las que el extractor exponga
    columnas_negadas: frozenset[str] = frozenset()   # nombres en minusculas
    rol: str = ""
    # (entidad, crear, leer, actualizar, eliminar) con el alcance 0/1/2/4 del gestor.
    permisos: tuple = ()
    # Id del usuario de la peticion. Va aparte de la cache (que es por rol): se pone
    # con `con_usuario` en cada peticion.
    user_id: int | None = None

    def permite_tabla(self, nombre: str) -> bool:
        return self.tablas is None or nombre.lower() in self.tablas

    def con_usuario(self, user_data: dict | None) -> "Acceso":
        uid = _i((user_data or {}).get("id_user") or (user_data or {}).get("user_id")) or None
        return replace(self, user_id=uid)

    def alcance_lectura(self, tabla: str) -> int:
        """1 propios, 2 mis grupos, 4 todos. Admin y tablas sin fila de rol: todos."""
        if self.es_admin:
            return 4
        for ent, _c, leer, _u, _d in self.permisos:
            if ent == tabla.lower():
                return leer
        return 4


_cache: dict[str, tuple[float, Acceso]] = {}
_lock = threading.Lock()


def _i(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _plan_permite(entidad: str) -> bool:
    try:
        from app.modules.plan import entidad_habilitada
        return bool(entidad_habilitada(entidad))
    except Exception:
        return True


def resolver_acceso(user_data: dict | None) -> Acceso:
    """El acceso del usuario del token. Sin token valido: ninguno."""
    user_data = user_data or {}
    if user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"):
        return Acceso("admin", True, None, rol="superusuario")

    try:
        id_permission = int(user_data.get("id_permission") or user_data.get("permission_id"))
    except (TypeError, ValueError):
        return Acceso("sin-rol", False, frozenset(), rol="")

    ahora = time.time()
    with _lock:
        previo = _cache.get(str(id_permission))
        if previo and previo[0] > ahora:
            return previo[1]

    acceso = _calcular(id_permission)
    with _lock:
        _cache[str(id_permission)] = (ahora + _TTL_S, acceso)
    return acceso


def invalidar() -> None:
    with _lock:
        _cache.clear()


def _calcular(id_permission: int) -> Acceso:
    from app.models.entity_permission import EntityPermission
    from app.models.field import Field
    from app.models.nm_field_permission import NmFieldPermission
    from app.models.permission import Permission
    from app.models.session import transaction_context

    with transaction_context() as s:
        rol = s.query(Permission).filter(Permission.id_permission == id_permission).first()
        nombre_rol = (rol.permission_description if rol else "") or ""
        if nombre_rol.strip().lower() in NOMBRES_DE_ADMIN:
            return Acceso(f"rol-{id_permission}", True, None, rol=nombre_rol)

        filas = (
            s.query(EntityPermission.entity_name, EntityPermission.scope_read,
                    EntityPermission.scope_create, EntityPermission.scope_update,
                    EntityPermission.scope_delete)
            .filter(EntityPermission.id_permission == id_permission)
            .filter(EntityPermission.deletion_date.is_(None))
            .all()
        )
        permisos_entidad = tuple(
            (str(n).lower(), _i(c), _i(r), _i(u), _i(d)) for n, r, c, u, d in filas
            if str(n).lower() not in SOLO_ADMIN
        )
        tablas = {
            str(n).lower() for n, alcance, *_ in filas
            if str(alcance) not in ("0", "None") and str(n).lower() not in SOLO_ADMIN
            and _plan_permite(str(n))
        }

        negadas: set[str] = set()
        if tablas:
            # Misma regla que usan las rutas de la aplicacion: un campo es
            # visible solo si hay una fila viva con el bit de lectura. Si el rol
            # no tiene NINGUNA fila de campos para una tabla (no se configuro),
            # no se esconde nada de ella. Las llaves (id_*) siempre viajan: sin
            # ellas no hay JOIN posible y no son dato sensible.
            permisos = {
                p.id_field: int(p.control_type)
                for p in s.query(NmFieldPermission)
                .filter(NmFieldPermission.id_permission == id_permission)
                .filter(NmFieldPermission.deletion_date.is_(None))
                .all()
            }
            por_tabla: dict[str, list] = {}
            for f in s.query(Field).filter(Field.deletion_date.is_(None)).all():
                t = str(f.table_name).lower()
                if t in tablas:
                    por_tabla.setdefault(t, []).append(f)
            for t, campos in por_tabla.items():
                if not any(f.id_field in permisos for f in campos):
                    continue
                for f in campos:
                    nombre = str(f.field_name).lower()
                    if nombre.startswith("id_"):
                        continue
                    ct = permisos.get(f.id_field)
                    if ct is None or not (ct & FIELD_READ_BIT):
                        negadas.add(nombre)

    return Acceso(f"rol-{id_permission}", False, frozenset(tablas),
                  frozenset(negadas), rol=nombre_rol, permisos=permisos_entidad)


def usuario_del_token(peticion) -> dict:
    """Los datos del JWT de la peticion, o {} si no hay sesion valida.

    Mismas reglas que `token_required` (la clave, y rechazar el token publico
    del catalogo web), para que el modulo BI no abra una puerta distinta.
    """
    import jwt
    from app.utils.auth import PUBLIC_JWT_SCOPE, SECRET_KEY

    token = peticion.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {}
    try:
        datos = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return {}
    if str(datos.get("scope") or "").strip().lower() == str(PUBLIC_JWT_SCOPE).strip().lower():
        return {}
    return datos


def acotar_sql(sql: str, acceso, esquema) -> str:
    """Limita cada tabla con alcance Propios/Mis grupos a las filas del usuario.

    Antepone un CTE con el nombre de la tabla (`WITH invoice AS (SELECT * FROM
    invoice WHERE created_by = ...)`), que tapa a la tabla real en toda la
    consulta: lo que escriba el modelo ya no puede ver otras filas. Dueno de la
    fila = columna `created_by`; una tabla sin ella (catalogos) se trata como
    "Todos". Mis grupos = yo + quienes comparten un equipo (`nm_team_user`).
    """
    from . import security

    if acceso is None or acceso.es_admin:
        return sql
    por_tabla = {r.nombre.lower(): r for r in esquema.relaciones}
    acotadas = {}
    # Un CTE del modelo con el nombre de una tabla restringida taparia mi filtro
    # (y `relaciones_referenciadas` no lo cuenta como tabla): se rechaza.
    texto = security._sin_from_de_funciones(security.esqueleto(sql))
    for cte in {n.lower() for n in security._ALIAS_DE_CTE.findall(texto)}:
        if cte in por_tabla and (acceso.alcance_lectura(cte) != 4 or cte in SIN_DUENO_SENSIBLES):
            raise security.SqlRechazado("alcance_no_aplicable", cte)
    for ref in security.relaciones_referenciadas(sql):
        corto = ref.split(".")[-1].lower()
        rel = por_tabla.get(corto)
        alcance = acceso.alcance_lectura(corto)
        if alcance != 4 and corto in SIN_DUENO_SENSIBLES:
            raise security.SqlRechazado("alcance_no_aplicable", ref)
        if rel is None or alcance == 4 or not any(c.nombre.lower() == "created_by" for c in rel.columnas):
            continue
        if "." in ref or acceso.user_id is None or re.search(r"\brecursive\b", sql, re.I):
            # Con el nombre calificado se saltaria el CTE; sin usuario no hay filtro posible.
            raise security.SqlRechazado("alcance_no_aplicable", ref)
        acotadas[corto] = rel
    if not acotadas:
        return sql

    uid = int(acceso.user_id)
    grupo = ("SELECT id_user FROM public.nm_team_user WHERE deletion_date IS NULL AND id_team IN "
             f"(SELECT id_team FROM public.nm_team_user WHERE id_user = {uid} AND deletion_date IS NULL) "
             f"UNION SELECT {uid}")
    ctes = []
    for nombre, rel in acotadas.items():
        columnas = ["created_by"] + ([DUENO_ADICIONAL[nombre]] if nombre in DUENO_ADICIONAL else [])
        if acceso.alcance_lectura(nombre) == 1:
            filtro = " OR ".join(f"{c} = {uid}" for c in columnas)
        else:
            filtro = " OR ".join(f"{c} IN ({grupo})" for c in columnas)
        filtro = f"({filtro})"
        origen = f'"{rel.esquema}"."{rel.nombre}"' if rel.esquema else f'"{rel.nombre}"'
        ctes.append(f'"{rel.nombre}" AS (SELECT * FROM {origen} WHERE {filtro})')
    cuerpo = sql.lstrip()
    if re.match(r"with\b", cuerpo, re.I):
        return "WITH " + ", ".join(ctes) + ", " + cuerpo[4:].lstrip()
    return "WITH " + ", ".join(ctes) + " " + cuerpo
