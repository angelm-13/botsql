"""El catalogo que el gestor de roles ofrece, derivado del esquema real.

Por que existe
--------------
Este catalogo era un JSON de ~8700 lineas congelado dentro de
`app/routes/security.py`. Se genero una vez, contra un esquema que ya no es el
de hoy, y desde entonces la pantalla de roles enseñaba una cosa distinta de la
que tiene la base. Medido contra la base real antes de este cambio:

* **Cubria 51 de las 85 entidades del registro.** Los 21 modulos de logistica,
  los 4 de documentos, los 3 de laboratorio, los 4 de KPIs, `appointment`,
  `material_attribute` y `nm_permission_kpi` no aparecian en la pantalla. No es
  que salieran sin campos: no salian. No habia forma de conceder ni de quitar
  nada suyo desde ahi.
* **A 14 entidades les faltaban columnas que la tabla si tiene.** `proyect`
  declaraba 10 de 19 -sin `folio`, `id_supervisor`, `purchase_order` ni
  `delivery_date`-, `product` 20 de 26 -sin `tracking_mode` ni `lot_control`-,
  `invoice` 50 de 57 -sin `uso_cfdi` ni `forma_pago`-, `nm_incident_product`
  10 de 18 -sin `direction`, `id_location_from` ni `id_location_to`, que son
  las del vale de almacen-.
* **Agrupaba por un vocabulario propio** -`hr`, `scm`, `erp`, `finance`- que no
  es el de los modulos: `incident` e `incident_type` salian en CRM cuando son
  de Operaciones, `ticket` y `service` fuera de Facturacion,
  `entity_permission` y `nm_field_permission` en Recursos humanos.
* **Las etiquetas eran el nombre de la tabla en ingles** -"Proyect", "Nm
  Incident Product", "User"-, porque se habian generado a maquina del esquema.

Derivarlo de los modelos y del registro quita la clase entera de desfase: una
columna nueva aparece en la pantalla el dia que se agrega, una que se va deja
de ofrecerse sola, y ninguna entidad puede quedar fuera sin que el registro lo
diga -- que es justo lo que el registro se niega a permitir.

Que NO hace
-----------
No decide quien puede que: eso sigue siendo `entity_permission` y
`nm_field_permission` en la base, sembrados desde `filas_de_permisos()`. Este
archivo solo dice que se puede ofrecer y con que nombre.
"""

from __future__ import annotations

from app.utils.scope import soporta_alcance_de_dueno

from app.modules.registry import (
    CAPACIDADES,
    MENU,
    MODULO_POR_CLAVE,
    MODULOS,
    SOLO_ARRANQUE,
)


# Columnas que el sistema administra solo. Se publican -el gestor las recibe
# marcadas con `is_system_field`, y la pantalla las oculta- pero nadie las
# captura a mano. Es la misma lista que usa `scripts/sync_field_catalog.py`
# para poblar `field`, mas `created_by`, que lo fija el servicio con el usuario
# de la sesion.
COLUMNAS_DE_SISTEMA = frozenset({
    "created_by", "creation_date", "last_update_date", "deletion_date", "ajustado_por_gestor",
})

# Nombres de columna que sirven para reconocer un registro en un desplegable,
# en orden de preferencia.
CANDIDATAS_REPRESENTATIVAS = (
    "full_name", "username", "name", "description", "folio", "code", "label",
)

ACCIONES = (
    {"key": "create", "bit": 1, "label": "Crear"},
    {"key": "read", "bit": 2, "label": "Leer"},
    {"key": "update", "bit": 4, "label": "Actualizar"},
    {"key": "delete", "bit": 8, "label": "Eliminar"},
)

ACCIONES_DE_CAMPO = (
    {"key": "read", "bit": 2, "label": "Ver campo"},
    {"key": "update", "bit": 4, "label": "Editar campo"},
)

# Etiqueta de las entidades que no tienen entrada de menu propia. Las que si la
# tienen la toman de `MENU`, para que la pantalla de roles y la barra lateral
# no se llamen distinto. Sin esto el gestor las mostraba humanizando el nombre
# de la tabla -"Nm Incident Product", "Laboratory Service Order Status
# History"-, que es lo que habia.
ETIQUETAS = {
    # facturacion
    "fiscal_record": "Registros fiscales",
    "fiscal_stamp": "Timbres fiscales",
    "invoice_material_service": "Partidas de la factura",
    "service": "Servicios",
    # inventario
    "material_attribute": "Caracteristicas del material",
    # operaciones
    "nm_incident_product": "Renglones de la incidencia",
    "nm_template_task": "Tareas de la plantilla",
    "task_note": "Notas de tarea",
    # logistica
    "logistics_address": "Direcciones",
    "logistics_branch": "Sucursales",
    "logistics_contact": "Contactos",
    "logistics_contract": "Contratos",
    "logistics_evidence": "Evidencias",
    "logistics_file": "Expedientes",
    "logistics_incident": "Incidencias de logistica",
    "logistics_inventory": "Inventario de logistica",
    "logistics_location": "Ubicaciones de logistica",
    "logistics_maintenance": "Mantenimientos",
    "logistics_operator": "Operadores",
    "logistics_quotation": "Cotizaciones",
    "logistics_rack": "Racks",
    "logistics_rate": "Tarifas",
    "logistics_receivable": "Cuentas por cobrar",
    "logistics_service_request": "Solicitudes de servicio",
    "logistics_shipment": "Embarques",
    "logistics_trailer": "Remolques",
    "logistics_trip": "Viajes",
    "logistics_unit": "Unidades de transporte",
    "logistics_warehouse": "Almacenes de logistica",
    # crm
    "appointment": "Citas",
    "nm_survey_user": "Respuestas de encuesta",
    "product_sale_config": "Configuracion de venta web",
    "public_api_key": "Llaves de API publica",
    "survey_multiple_answer": "Opciones de respuesta",
    "survey_question": "Preguntas de encuesta",
    # documentos
    "document_relation": "Relaciones del documento",
    "document_version": "Versiones del documento",
    # laboratorio
    "laboratory_service_order_status_history": "Historial de la orden",
    # kpis
    "kpi_dashboard": "Tableros",
    "kpi_dashboard_widget": "Widgets del tablero",
    "kpi_definition": "Definiciones de KPI",
    "nm_permission_kpi": "KPIs por perfil",
    # configuracion
    "status": "Estatus",
    "theme": "Temas",
    # seguridad
    "entity_permission": "Permisos por entidad",
    "event_log": "Bitacora",
    "field": "Campos",
    "nm_field_permission": "Permisos por campo",
    "user_mfa": "Segundo factor",
}


def _humanizar(nombre: str) -> str:
    return nombre.replace("_", " ").strip().capitalize()


def etiqueta_de(entidad: str) -> str:
    """Como se llama una entidad en la pantalla."""
    en_menu = MENU.get(entidad)
    if en_menu:
        return en_menu[0]
    return ETIQUETAS.get(entidad) or _humanizar(entidad)


def _tipo_simple(columna) -> str:
    """El tipo de la columna en una palabra, para quien lea el catalogo."""
    try:
        python_type = columna.type.python_type
    except (NotImplementedError, AttributeError):
        return "text"
    return {
        bool: "boolean",
        int: "integer",
        float: "decimal",
        str: "text",
    }.get(python_type, python_type.__name__.lower())


def _referencia(columna):
    """(tabla, columna) a la que apunta una llave foranea, o (None, None).

    Es lo que hace visible la RELACION en la pantalla: sin esto,
    `nm_incident_product.id_location_from` es un numero suelto y no se puede
    saber que es una ubicacion.
    """
    for fk in columna.foreign_keys:
        objetivo = fk.column
        return objetivo.table.name, objetivo.name
    return None, None


def _campo_representativo(tabla) -> str | None:
    nombres = {c.name for c in tabla.columns}
    for candidata in CANDIDATAS_REPRESENTATIVAS:
        if candidata in nombres:
            return candidata
    # Convencion de la base: `<tabla>_description` es el texto con el que se
    # reconoce la fila en casi todos los catalogos.
    convencion = f"{tabla.name}_description"
    if convencion in nombres:
        return convencion
    for columna in tabla.columns:
        if columna.name.endswith("_description"):
            return columna.name
    return None


def _campos_de(tabla):
    campos = []
    for columna in tabla.columns:
        tabla_ref, columna_ref = _referencia(columna)
        campos.append({
            "field_name": columna.name,
            "label": _humanizar(columna.name),
            "type": _tipo_simple(columna),
            "raw_type": str(columna.type),
            "is_primary": bool(columna.primary_key),
            "is_foreign": tabla_ref is not None,
            "reference_table": tabla_ref,
            "reference_field": columna_ref,
            "is_representative": False,
            "is_required": bool(
                not columna.nullable
                and not columna.primary_key
                and columna.default is None
                and columna.server_default is None
            ),
            "is_encrypted": False,
            "is_system_field": columna.name in COLUMNAS_DE_SISTEMA,
        })
    return campos


def catalogo_base() -> dict:
    """El catalogo completo: una entrada por entidad del registro y por capacidad.

    Se arma de `Base.metadata`, o sea de los modelos, que es lo unico que
    siempre coincide con las tablas reales. La importacion va aqui dentro y no
    arriba porque `app.models` arrastra la configuracion de la aplicacion.
    """
    import app.models  # noqa: F401  (registra todos los modelos)
    from app.models.base import Base

    tablas = Base.metadata.tables
    entidades = []

    for modulo in MODULOS:
        for entidad in modulo.entidades:
            tabla = tablas.get(entidad)
            if tabla is None:
                # El registro se niega a cargar con una entidad que no exista,
                # asi que esto no deberia pasar; si pasa, se omite en vez de
                # tumbar la pantalla entera de roles.
                continue
            campos = _campos_de(tabla)
            representativo = _campo_representativo(tabla)
            for campo in campos:
                campo["is_representative"] = campo["field_name"] == representativo
            primaria = next(
                (c.name for c in tabla.columns if c.primary_key), None
            )
            entidades.append({
                "entity_name": entidad,
                "label": etiqueta_de(entidad),
                "module": modulo.clave,
                "domain": modulo.clave,
                "module_label": modulo.etiqueta,
                "primary_key": primaria,
                "representative_field": representativo,
                "is_bootstrap_only": entidad in SOLO_ARRANQUE,
                "is_permission_source": entidad == "permission",
                "permission_scope": "fields",
                "supports_owner_scope": soporta_alcance_de_dueno(entidad),
                "fields": campos,
            })

    for capacidad in CAPACIDADES:
        modulo = MODULO_POR_CLAVE.get(capacidad.modulo)
        entidades.append({
            "entity_name": capacidad.clave,
            "label": capacidad.etiqueta,
            "module": capacidad.modulo,
            "domain": capacidad.modulo,
            "module_label": modulo.etiqueta if modulo else None,
            "primary_key": None,
            "representative_field": None,
            "is_bootstrap_only": False,
            "is_permission_source": False,
            # Una capacidad no es una tabla: no tiene columnas que conceder, y
            # decirlo aqui es lo que hace que la pantalla ofrezca solo las
            # cuatro acciones en vez de una lista de campos vacia.
            "permission_scope": "actions_only",
            "supports_owner_scope": soporta_alcance_de_dueno(capacidad.clave),
            "fields": [],
        })

    entidades.sort(key=lambda e: (e["module"], e["label"]))

    return {
        "version": "2.0.0-derivado",
        "source": "app.modules.registry + sqlalchemy.metadata",
        "permission_model": {
            "role_entity": "permission",
            "user_role_field": "user.id_permission",
            "entity_permission_entity": "entity_permission",
            "field_permission_entity": "nm_field_permission",
            "control_type": "bitmask",
        },
        "actions": [dict(a) for a in ACCIONES],
        "field_actions": [dict(a) for a in ACCIONES_DE_CAMPO],
        "entities": entidades,
    }
