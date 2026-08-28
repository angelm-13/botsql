"""Genera el sembrado de `entity_permission` a partir del propio codigo.

Contexto del hallazgo
---------------------
La revision previa a produccion encontro que 48 de las 63 entidades que el
backend protege no tenian ni una sola fila en `entity_permission`, y que ningun
usuario real de la base es superusuario: `is_superuser` solo lo otorga la cuenta
de arranque. El resultado practico era que ningun usuario real podia facturar,
ver un cliente, registrar un movimiento ni administrar usuarios. El sistema solo
se habia manejado con la cuenta de arranque, que salta todas las
comprobaciones, y por eso el hueco nunca se noto.

Por que se genera en lugar de escribirse a mano
-----------------------------------------------
Un archivo escrito a mano se desincroniza en cuanto alguien protege una entidad
nueva, y el sintoma es una pantalla en blanco sin explicacion. Aqui la lista de
entidades se lee de dos fuentes vivas -las llamadas a
`require_entity_permission` en el backend y los `entityName` de las rutas del
front- y el script se niega a generar nada si alguna entidad quedo sin
clasificar. Asi, olvidarse de una entidad rompe la generacion en lugar de
producir un permiso silenciosamente ausente.
"""

from __future__ import annotations

import pathlib
import re
import sys


RAIZ = pathlib.Path(__file__).resolve().parents[2]
RUTAS_BACKEND = RAIZ / "backend" / "app" / "routes"
APP_JSX = RAIZ / "frontend" / "src" / "App.jsx"

# Mascara de bits que ya usa `require_entity_permission`.
CREAR, LEER, ACTUALIZAR, BORRAR = 1, 2, 4, 8
TOTAL = CREAR | LEER | ACTUALIZAR | BORRAR   # 15
CAPTURA = CREAR | LEER | ACTUALIZAR          # 7  operar sin poder borrar
EDITAR = LEER | ACTUALIZAR                   # 6  mover sin poder dar de alta
CONSULTA = LEER                              # 2

# El codigo bloquea estas entidades para cualquiera que no sea la cuenta de
# arranque (BOOTSTRAP_ONLY_ENTITIES en app/utils/auth.py). Sembrarlas daria una
# fila que no sirve de nada y haria creer que el permiso existe.
SOLO_ARRANQUE = {"event_log", "user_mfa", "password_reset_token"}

# El restaurante es un modulo aparte, con sus propios perfiles ya sembrados.
FUERA_DE_ALCANCE = {
    "restaurant_admin", "restaurant_cashier",
    "restaurant_kitchen", "restaurant_waiter",
}

DOMINIOS: dict[str, tuple[str, ...]] = {
    "catalogos": (
        "brand", "unit", "status", "theme", "product_family", "location_type",
        "inventory_status", "task_type", "incident_type", "service", "level",
        "department", "subdepartment",
    ),
    "inventario": (
        "product", "material", "material_component", "location", "movement",
    ),
    "operaciones": (
        "proyect", "task", "task_note", "incident", "incident_detail",
        "nm_incident_product", "template", "nm_template_task", "appointment",
    ),
    "comercial": ("customer_supplier", "ticket", "product_sale_config"),
    "facturacion": (
        "invoice", "invoice_material_service", "fiscal_account",
        "fiscal_record", "fiscal_stamp", "bank", "bank_account",
    ),
    "nomina": (
        "payroll_concept", "payroll_detail", "payroll_movement",
        "payroll_period", "kronos_device",
    ),
    "seguridad": (
        "user", "permission", "entity_permission", "nm_field_permission",
        "field", "public_api_key",
    ),
    "logistica": (
        "logistics_address", "logistics_branch", "logistics_contact",
        "logistics_contract", "logistics_evidence", "logistics_file",
        "logistics_incident", "logistics_inventory", "logistics_location",
        "logistics_maintenance", "logistics_operator", "logistics_quotation",
        "logistics_rack", "logistics_rate", "logistics_receivable",
        "logistics_service_request", "logistics_shipment", "logistics_trailer",
        "logistics_trip", "logistics_unit", "logistics_warehouse",
    ),
    "encuestas": ("survey_question", "survey_multiple_answer", "nm_survey_user"),
}

# Que puede hacer cada perfil en cada dominio.
#
# Los criterios: nadie borra fuera de administracion, porque un borrado en un
# sistema con contabilidad y almacen deja huecos que no se pueden reconstruir;
# quien opera un dominio no administra sus catalogos; y la separacion de
# funciones que ya existia en operaciones y almacen se conserva -el que ejecuta
# no autoriza-.
PERFILES: dict[int, tuple[str, dict[str, int]]] = {
    1: ("Administrator", {
        "catalogos": TOTAL, "inventario": TOTAL, "operaciones": TOTAL,
        "comercial": TOTAL, "facturacion": TOTAL, "nomina": TOTAL,
        "seguridad": TOTAL, "logistica": TOTAL, "encuestas": TOTAL,
    }),
    2: ("gerente_administrativo", {
        "catalogos": CONSULTA, "inventario": CONSULTA, "operaciones": EDITAR,
        "comercial": CAPTURA, "facturacion": CAPTURA, "nomina": CAPTURA,
        "encuestas": CONSULTA,
    }),
    3: ("vendedor", {
        "catalogos": CONSULTA, "inventario": CONSULTA,
        "comercial": CAPTURA, "facturacion": CAPTURA,
    }),
    14: ("Jefe de taller", {
        "catalogos": CONSULTA, "inventario": CONSULTA, "operaciones": CAPTURA,
    }),
    15: ("Supervisor", {
        "catalogos": CONSULTA, "inventario": CONSULTA, "operaciones": CAPTURA,
    }),
    16: ("Gerente", {
        "catalogos": CONSULTA, "inventario": CONSULTA, "operaciones": EDITAR,
        "comercial": CAPTURA, "facturacion": CAPTURA, "nomina": CONSULTA,
        "encuestas": CONSULTA,
    }),
    17: ("Almacenista", {
        "catalogos": CONSULTA, "inventario": CAPTURA,
    }),
    18: ("Jefe de almacen", {
        "catalogos": CONSULTA, "inventario": TOTAL, "logistica": CAPTURA,
    }),
}

# Solo estas entidades aparecen en el menu. El resto queda accesible por
# permiso pero sin entrada propia: son catalogos de apoyo que se consultan
# desde las pantallas que los usan, y ponerlos todos convertiria el menu en un
# listado de tablas.
MENU: dict[str, tuple[str, str, str, int]] = {
    # entidad: (grupo, etiqueta, icono, orden)
    "movement": ("Inventario", "Movimientos", "inventory", 180),
    "material_component": ("Inventario", "Componentes", "inventory", 190),
    "proyect": ("Operaciones", "Proyectos", "operations", 80),
    "incident": ("Operaciones", "Incidencias", "operations", 120),
    "incident_detail": ("Operaciones", "Detalle de incidencias", "operations", 130),
    "invoice": ("Facturacion", "Facturas", "billing", 200),
    "customer_supplier": ("Facturacion", "Clientes y proveedores", "billing", 210),
    "fiscal_account": ("Facturacion", "Cuentas fiscales", "billing", 220),
    "bank": ("Facturacion", "Bancos", "billing", 230),
    "bank_account": ("Facturacion", "Cuentas bancarias", "billing", 240),
    "ticket": ("Facturacion", "Tickets", "billing", 250),
    "payroll_period": ("Recursos humanos", "Periodos de nomina", "hr", 300),
    "payroll_concept": ("Recursos humanos", "Conceptos", "hr", 310),
    "payroll_movement": ("Recursos humanos", "Movimientos", "hr", 320),
    "payroll_detail": ("Recursos humanos", "Detalle", "hr", 330),
    "user": ("Configuracion", "Usuarios", "settings", 400),
    "permission": ("Configuracion", "Perfiles", "settings", 410),
    "department": ("Configuracion", "Departamentos", "settings", 420),
    "subdepartment": ("Configuracion", "Subdepartamentos", "settings", 430),
    "level": ("Configuracion", "Niveles", "settings", 440),
}


def entidades_protegidas() -> set[str]:
    """Entidades que el backend protege o que el front sabe mostrar."""
    encontradas: set[str] = set()

    patron = re.compile(r"require_entity_permission\(\s*'([a-z_]+)'")
    for archivo in RUTAS_BACKEND.glob("*.py"):
        encontradas.update(patron.findall(archivo.read_text(encoding="utf-8", errors="ignore")))

    if APP_JSX.exists():
        encontradas.update(re.findall(
            r'entityName="([a-z_]+)"', APP_JSX.read_text(encoding="utf-8", errors="ignore")))

    return encontradas - SOLO_ARRANQUE - FUERA_DE_ALCANCE


def clasificar() -> dict[str, str]:
    """entidad -> dominio, verificando que ninguna quede repetida."""
    mapa: dict[str, str] = {}
    for dominio, entidades in DOMINIOS.items():
        for entidad in entidades:
            if entidad in mapa:
                raise SystemExit(
                    f"'{entidad}' esta en dos dominios: {mapa[entidad]} y {dominio}.")
            mapa[entidad] = dominio
    return mapa


def _sql(valor: str) -> str:
    return "NULL" if not valor else "'" + valor.replace("'", "''") + "'"


def generar() -> str:
    protegidas = entidades_protegidas()
    mapa = clasificar()

    sin_clasificar = sorted(protegidas - set(mapa))
    if sin_clasificar:
        raise SystemExit(
            "Estas entidades estan protegidas pero no pertenecen a ningun dominio, "
            "asi que nadie podria alcanzarlas:\n  "
            + "\n  ".join(sin_clasificar)
            + "\n\nAgregalas a DOMINIOS en este script antes de continuar.")

    sobrantes = sorted(set(mapa) - protegidas)

    filas: list[tuple[str, str]] = []
    for id_permission, (nombre, concesiones) in sorted(PERFILES.items()):
        for dominio, bits in sorted(concesiones.items()):
            for entidad in sorted(DOMINIOS[dominio]):
                if entidad not in protegidas:
                    continue
                grupo, etiqueta, icono, orden = MENU.get(entidad, ("", "", "", 900))
                ubicacion = "sidebar" if entidad in MENU else "none"
                filas.append((
                    f"    ({id_permission}, '{entidad}', {bits}, '{ubicacion}', "
                    f"{_sql(grupo)}, {_sql(icono)}, {_sql(etiqueta)}, {orden})",
                    f"{nombre} / {dominio}",
                ))

    # La coma va ANTES del comentario: si queda despues, el `--` se la traga y
    # el siguiente renglon deja de ser una fila de VALUES.
    ultimo = len(filas) - 1
    cuerpo = "\n".join(
        f"{fila}{',' if indice < ultimo else ''}   -- {comentario}"
        for indice, (fila, comentario) in enumerate(filas)
    )

    return PLANTILLA.format(
        total_entidades=len(protegidas),
        total_filas=len(filas),
        sobrantes=(", ".join(sobrantes) or "ninguna"),
        filas=cuerpo,
    )


PLANTILLA = """-- Sembrado de permisos por entidad. GENERADO por
-- backend/scripts/seed_entity_permissions.py; no editar a mano.
--
-- La revision previa a produccion encontro que 48 de las 63 entidades que el
-- backend protege no tenian ninguna fila aqui, y que ningun usuario real de la
-- base es superusuario: is_superuser solo lo da la cuenta de arranque. En la
-- practica ningun usuario real podia facturar, ver un cliente, registrar un
-- movimiento ni administrar usuarios; el front bloquea cada pantalla contra
-- esta misma tabla, asi que quedaban en blanco. Solo se habia usado el sistema
-- con la cuenta de arranque, que salta todas las comprobaciones, y por eso no
-- se noto.
--
-- Entidades cubiertas: {total_entidades}. Filas generadas: {total_filas}.
-- Clasificadas pero no protegidas por ninguna ruta: {sobrantes}.
--
-- ON CONFLICT DO NOTHING es deliberado: las filas que ya existen se dejaron
-- con valores pensados uno por uno (el almacenista mueve ubicaciones pero no
-- las da de alta, el gerente ve proyectos pero no los crea). Este sembrado
-- llena huecos; no debe pisar decisiones anteriores.

BEGIN;

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT v.id_permission, v.entity_name, v.control_type, v.menu_location,
       v.menu_group, v.menu_group_icon, v.menu_label, v.menu_order, 1
FROM (VALUES
{filas}
) AS v (id_permission, entity_name, control_type, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order)
WHERE EXISTS (SELECT 1 FROM permission p WHERE p.id_permission = v.id_permission)
ON CONFLICT (id_permission, entity_name) DO NOTHING;

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
