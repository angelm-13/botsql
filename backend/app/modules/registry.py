"""Registro de modulos del sistema: quien es dueno de que.

Por que existe
--------------
El sistema creció por entidades, no por modulos. Nada en el codigo decia a que
modulo pertenece una tabla: se sabia por el nombre -`logistics_*`, `payroll_*`-
o por el grupo de menu que alguien escribio a mano en `entity_permission`. Con
ese criterio implicito ya pasaron dos cosas:

* los permisos se sembraron por dominios inventados al momento, que no
  coincidian con los modulos que el negocio reconoce;
* al conceder acceso a un modulo no habia forma de saber que entidades
  arrastraba, asi que unas quedaban dentro y otras fuera sin que nadie lo
  notara hasta ver una pantalla en blanco.

Aqui cada entidad pertenece a **exactamente un** modulo, y el archivo se niega
a cargar si alguna queda fuera o en dos. Es la unica fuente de verdad de esa
pertenencia.

Los cuatro almacenes
--------------------
Cuatro modulos tienen almacen propio, y ninguno comparte tabla con otro:

* **inventario**: `location` -> `inventory_stock` -> `inventory_ledger`, por
  producto y ubicacion, en piezas enteras.
* **logistica**: `logistics_warehouse` -> `logistics_location` ->
  `logistics_inventory`, por SKU, con lote y numero de serie.
* **restaurante**: `restaurant_inventory_item` ->
  `restaurant_inventory_movement`, por insumo y receta.
* **punto de venta**: dentro de su propia base, `pos_enterprise`. Es la
  separacion mas fuerte de las cuatro, porque no se puede cruzar ni por una
  consulta mal escrita.

Los tres primeros viven en la base del nucleo y no se cruzan en ningun servicio;
esta comprobado por prueba. Cada uno guarda algo distinto: logistica mercancia
de terceros que hay que rastrear por lote y serie, inventario material propio de
obra que se cuenta en piezas enteras, el restaurante insumos que se descuentan
por receta, y el punto de venta articulos de mostrador con kardex y bloqueo de
sobreventa. Unificarlos obligaria a que los cuatro pierdan lo que les es propio.

Al vivir en modulos distintos, conceder inventario a un rol NO le da acceso a
ninguno de los otros tres.

Capacidades
-----------
No todo permiso es una tabla. Hay derechos con nombre propio -autorizar un
proyecto, ajustar existencias, supervisar incidencias- que se guardan en la
misma tabla que las entidades pero no corresponden a ninguna. Van declarados
aparte porque se conceden por separado y porque perderlos al resembrar romperia
la separacion de funciones.
"""

from __future__ import annotations


# Mascara de bits que entiende `require_entity_permission`.
CREAR, LEER, ACTUALIZAR, BORRAR = 1, 2, 4, 8

TOTAL = CREAR | LEER | ACTUALIZAR | BORRAR   # 15  administrar
CAPTURA = CREAR | LEER | ACTUALIZAR          # 7   operar sin borrar
EDITAR = LEER | ACTUALIZAR                   # 6   mover lo que ya existe
CONSULTA = LEER                              # 2   solo ver

BITS_VALIDOS = TOTAL

NOMBRE_DE_BITS = {
    TOTAL: "administrar",
    CAPTURA: "capturar",
    EDITAR: "editar",
    CONSULTA: "consultar",
}


class Modulo:
    """Un submodulo del proyecto, con las entidades que le pertenecen."""

    def __init__(self, clave, etiqueta, icono, orden, entidades, *,
                 almacen=None, base_de_datos=None,
                 grupo_de_menu=None, icono_de_menu=None):
        self.clave = clave
        self.etiqueta = etiqueta
        self.icono = icono
        self.orden = orden
        # Bajo que nombre se agrupa en el menu, cuando no coincide con el del
        # modulo. Existe para poder tener un solo apartado de Configuracion en
        # la pantalla sin fusionar los modulos de permisos: si `seguridad` y
        # `configuracion` fueran uno solo, cualquier rol con configuracion
        # -que son casi todos, porque necesitan leer catalogos- heredaria
        # usuarios y permisos. La separacion de acceso se mantiene; lo que se
        # unifica es donde se ve.
        self.grupo_de_menu = grupo_de_menu or etiqueta
        self.icono_de_menu = icono_de_menu or icono
        self.entidades = tuple(entidades)
        # Cadena de tablas del almacen propio, si el modulo tiene uno. Solo se
        # declaran aqui las que viven en la base del nucleo; un modulo con base
        # propia lleva su almacen dentro y se declara en `base_de_datos`.
        self.almacen = tuple(almacen or ())
        # Nombre de la base cuando el modulo no comparte la del nucleo. Es la
        # separacion mas fuerte que hay: no se puede cruzar ni por error.
        self.base_de_datos = base_de_datos

    def __repr__(self):
        return f"<Modulo {self.clave} ({len(self.entidades)} entidades)>"


MODULOS = (
    Modulo(
        "facturacion", "Facturacion", "billing", 100,
        (
            "invoice", "invoice_material_service", "fiscal_account",
            "fiscal_record", "fiscal_stamp", "bank", "bank_account", "ticket",
            # El catalogo de servicios se consume en las partidas de la
            # factura, que es donde se cobra.
            "service",
        ),
    ),
    Modulo(
        "inventario", "Inventario", "inventory", 200,
        (
            "product", "material", "material_component", "location",
            "location_type", "movement", "inventory_status", "brand", "unit",
            "product_family",
        ),
        almacen=("location", "inventory_stock", "inventory_ledger"),
    ),
    Modulo(
        "operaciones", "Operaciones", "operations", 300,
        (
            "proyect", "task", "task_note", "task_type", "incident",
            "incident_detail", "incident_type", "nm_incident_product",
            "template", "nm_template_task",
        ),
    ),
    Modulo(
        "logistica", "Logistica", "logistics", 400,
        (
            "logistics_address", "logistics_branch", "logistics_contact",
            "logistics_contract", "logistics_evidence", "logistics_file",
            "logistics_incident", "logistics_inventory", "logistics_location",
            "logistics_maintenance", "logistics_operator", "logistics_quotation",
            "logistics_rack", "logistics_rate", "logistics_receivable",
            "logistics_service_request", "logistics_shipment",
            "logistics_trailer", "logistics_trip", "logistics_unit",
            "logistics_warehouse",
        ),
        almacen=("logistics_warehouse", "logistics_location", "logistics_inventory"),
    ),
    Modulo(
        "restaurante", "Restaurante", "restaurant", 500,
        # El restaurante se opera por pantalla, no por CRUD de tabla: sus
        # permisos son las cuatro capacidades de abajo. Sus tablas las gobierna
        # el propio modulo.
        (),
        almacen=("restaurant_inventory_item", "restaurant_inventory_movement"),
    ),
    Modulo(
        "pos", "Punto de venta", "pos", 550,
        # Corre su propio backend y su propia base (`pos_enterprise`), asi que
        # no tiene entidades en la del nucleo. Se opera por su pantalla, igual
        # que el restaurante.
        (),
        base_de_datos="pos_enterprise",
    ),
    Modulo(
        "crm", "CRM", "crm", 600,
        (
            "customer_supplier", "product_sale_config", "public_api_key",
            "survey_question", "survey_multiple_answer", "nm_survey_user",
            "appointment",
        ),
    ),
    # Documentos y Laboratorio llegan de tny_docs con sus tablas, sus rutas y su
    # sembrado, pero sin declararse aqui. La prueba de cobertura del registro lo
    # detecto: sus entidades estan protegidas con `require_entity_permission` y
    # no pertenecian a ningun modulo, asi que ningun rol podia alcanzarlas por la
    # matriz y el plan no podia venderlas ni apagarlas. Se declaran con los
    # grupos y el icono que su propia migracion usa.
    Modulo(
        "documentos", "Documentos", "file-text", 650,
        ("document", "document_category", "document_relation", "document_version"),
    ),
    Modulo(
        "laboratorio", "Laboratorio", "flask-conical", 660,
        (
            "laboratory_equipment", "laboratory_service_order",
            "laboratory_service_order_status_history",
        ),
    ),
    Modulo(
        "rh", "Recursos humanos", "hr", 700,
        ("payroll_concept", "payroll_detail", "payroll_movement", "payroll_period"),
    ),
    # --- infraestructura, no son submodulos de negocio -------------------
    Modulo(
        "configuracion", "Configuracion", "settings", 800,
        # Catalogos que cualquier pantalla necesita leer para pintar un select.
        # Sin acceso de lectura a `status` los desplegables quedan vacios, asi
        # que todos los roles los consultan.
        ("status", "theme", "department", "subdepartment", "level"),
    ),
    Modulo(
        "seguridad", "Seguridad", "security", 900,
        # Usuarios, perfiles y bitacora. Solo administracion.
        (
            "user", "user_mfa", "permission", "entity_permission",
            "nm_field_permission", "field", "event_log",
        ),
        # Se ve dentro de Configuracion: la peticion fue dejar un solo apartado
        # de configuracion, y usuarios y permisos son configuracion. Sigue
        # siendo un modulo aparte para conceder acceso, que es lo que importa.
        grupo_de_menu="Configuracion", icono_de_menu="settings",
    ),
)

MODULOS_DE_NEGOCIO = tuple(
    m.clave for m in MODULOS if m.clave not in {"configuracion", "seguridad"}
)


class Capacidad:
    """Un derecho con nombre propio que no corresponde a ninguna tabla."""

    def __init__(self, clave, etiqueta, modulo, *, bits=CONSULTA, menu="hidden",
                 licencia_independiente=False):
        self.clave = clave
        self.etiqueta = etiqueta
        self.modulo = modulo
        # Casi todas son de si-o-no, asi que basta el bit de lectura: el codigo
        # que las consulta pregunta por ese bit.
        self.bits = bits
        self.menu = menu
        # Si es True, esta capacidad se vende aparte del modulo que la
        # contiene: necesita su propia clave en LICENSED_MODULES aunque el
        # cliente ya tenga licenciado `modulo` (ej. multiemisor dentro de
        # facturacion). Si es False (el default), viaja con la licencia del
        # modulo padre, como cualquier otro permiso normal de rol.
        self.licencia_independiente = licencia_independiente


CAPACIDADES = (
    Capacidad("project_authorization", "Autorizar proyectos", "operaciones", menu="hidden"),
    Capacidad("project_execution", "Ejecutar proyectos en taller", "operaciones", menu="hidden"),
    Capacidad("incident_supervision", "Supervisar incidencias ajenas", "operaciones"),
    # El ajuste es el unico movimiento sin documento detras y sin tope: crea o
    # destruye existencia por cualquier cantidad. Es la operacion con la que se
    # tapa un faltante, asi que se concede aparte de poder editar productos.
    Capacidad("inventory_adjustment", "Ajustar existencias", "inventario"),
    # Va en el engrane del encabezado, no en el menu vertical.
    #
    # Se habia movido a `sidebar` al retirar el engrane, razonando que habia
    # demasiados sitios donde configurar cosas. Era un error: el engrane no es
    # un cajon de sastre, es una UBICACION que el gestor de roles ofrece -Menu
    # vertical / Engrane / No mostrar- y que se elige por rol y por entidad.
    # Quitarlo no simplificaba el menu: le quitaba al sistema una opcion de
    # configuracion que alguien habia elegido a proposito.
    Capacidad("kronos_device", "Conexion al dispositivo Kronos", "rh", menu="settings"),
    Capacidad("restaurant_waiter", "Meseros", "restaurante", bits=CAPTURA, menu="sidebar"),
    Capacidad("restaurant_cashier", "Caja", "restaurante", bits=CAPTURA, menu="sidebar"),
    Capacidad("restaurant_kitchen", "Cocina", "restaurante", bits=EDITAR, menu="sidebar"),
    Capacidad("restaurant_admin", "Admin del restaurante", "restaurante", bits=TOTAL, menu="sidebar"),
    Capacidad("pos_terminal", "Caja del punto de venta", "pos", bits=CAPTURA, menu="sidebar"),
    Capacidad("pos_admin", "Admin del punto de venta", "pos", bits=TOTAL, menu="sidebar"),
)


class Rol:
    """Que puede hacer un perfil en cada modulo, y que capacidades tiene."""

    def __init__(self, id_permission, nombre, modulos, capacidades=()):
        self.id_permission = id_permission
        self.nombre = nombre
        self.modulos = dict(modulos)
        self.capacidades = tuple(capacidades)


# Criterios de la matriz, para que se puedan discutir en lugar de adivinarse:
#
#   * Solo administracion borra. Un borrado con contabilidad y almacen de por
#     medio deja huecos que no se pueden reconstruir; el resto de los roles
#     cancela, acredita o ajusta, que si deja rastro.
#   * Quien opera un modulo lo captura; quien lo supervisa lo consulta.
#   * `configuracion` se consulta desde todos los roles porque sin leer
#     `status` las pantallas no pueden pintar un desplegable.
#   * `seguridad` solo la toca Administrator.
#   * Los tres almacenes viven en modulos distintos, asi que dar `inventario`
#     no da el almacen de logistica ni el del restaurante.
#   * Una capacidad que el acceso al modulo no puede ejercer no se concede: si
#     un rol solo consulta inventario, darle `inventory_adjustment` es una fila
#     que no sirve y que hace creer que puede ajustar.
ROLES = (
    Rol(1, "Administrator", {
        "facturacion": TOTAL, "inventario": TOTAL, "operaciones": TOTAL,
        "logistica": TOTAL, "restaurante": TOTAL, "pos": TOTAL, "crm": TOTAL, "rh": TOTAL,
        "configuracion": TOTAL, "seguridad": TOTAL,
    }, [c.clave for c in CAPACIDADES]),

    Rol(2, "gerente_administrativo", {
        "facturacion": CAPTURA, "crm": CAPTURA, "rh": CAPTURA,
        "operaciones": EDITAR, "inventario": CONSULTA, "logistica": CONSULTA,
        "configuracion": CONSULTA,
    }, ["incident_supervision", "kronos_device", "pos_admin", "pos_terminal"]),

    Rol(3, "vendedor", {
        "crm": CAPTURA, "facturacion": CAPTURA, "inventario": CONSULTA,
        "configuracion": CONSULTA,
    }),

    Rol(10, "Mesero", {"configuracion": CONSULTA}, ["restaurant_waiter"]),
    Rol(11, "Cocina", {"configuracion": CONSULTA}, ["restaurant_kitchen"]),
    Rol(12, "Caja Restaurante", {"configuracion": CONSULTA}, ["restaurant_cashier"]),
    Rol(13, "Admin Restaurante", {"configuracion": CONSULTA}, [
        "restaurant_admin", "restaurant_cashier", "restaurant_kitchen", "restaurant_waiter",
    ]),

    Rol(14, "Jefe de taller", {
        "operaciones": CAPTURA, "inventario": CONSULTA, "configuracion": CONSULTA,
    }, ["project_execution", "incident_supervision"]),

    Rol(15, "Supervisor", {
        "operaciones": CAPTURA, "inventario": CONSULTA, "configuracion": CONSULTA,
    }, ["incident_supervision"]),

    Rol(16, "Gerente", {
        "operaciones": EDITAR, "facturacion": CAPTURA, "crm": CAPTURA,
        "inventario": CONSULTA, "rh": CONSULTA, "logistica": CONSULTA,
        "configuracion": CONSULTA,
    }, ["project_authorization", "incident_supervision", "pos_admin", "pos_terminal"]),

    # El almacenista opera el almacen pero no lo administra, y no ajusta: es la
    # separacion de funciones que evita que quien mueve la mercancia tape su
    # propio faltante.
    Rol(17, "Almacenista", {
        "inventario": CAPTURA, "configuracion": CONSULTA,
    }),

    Rol(18, "Jefe de almacen", {
        "inventario": TOTAL, "logistica": CAPTURA, "configuracion": CONSULTA,
    }, ["inventory_adjustment"]),
)


# Entidades que el codigo bloquea para cualquiera que no sea la cuenta de
# arranque (BOOTSTRAP_ONLY_ENTITIES en app/utils/auth.py). Se declaran para que
# la comprobacion de cobertura no las exija.
SOLO_ARRANQUE = frozenset({"event_log", "user_mfa", "password_reset_token"})

# Entradas de menu por entidad: grupo, etiqueta y orden dentro del modulo. Solo
# las que merecen pantalla propia; el resto queda accesible por permiso pero sin
# entrada, porque son catalogos de apoyo que se consultan desde donde se usan.
MENU = {
    # Documentos y Laboratorio, con las etiquetas de su propia migracion.
    "document": ("Documentos", 10),
    "document_category": ("Categorias de documento", 20),
    "laboratory_service_order": ("Ordenes de servicio", 10),
    "laboratory_equipment": ("Equipos", 20),
    "invoice": ("Facturas", 10),
    "customer_supplier": ("Clientes y proveedores", 20),
    "fiscal_account": ("Cuentas fiscales", 30),
    "bank": ("Bancos", 40),
    "bank_account": ("Cuentas bancarias", 50),
    "ticket": ("Tickets", 60),
    "product": ("Productos", 10),
    # Los catalogos de los que cuelga un producto. Sin etiqueta el registro los
    # siembra como `hidden` -es la regla de mas abajo- y eso los dejaba fuera de
    # todos los menus: las pantallas existian y sus rutas tambien, pero solo se
    # llegaba escribiendo la direccion a mano. `product_family` estaba asi para
    # los cinco roles, de modo que nadie podia dar de alta una familia.
    #
    # Van juntos y justo despues de Productos porque es el orden en que hay que
    # recorrerlos para dar de alta algo: familia, marca y unidad primero, luego
    # el material que las une, y al final el producto.
    "product_family": ("Familias de producto", 12),
    "brand": ("Marcas", 14),
    "unit": ("Unidades", 16),
    "location": ("Ubicaciones", 20),
    "location_type": ("Tipos de ubicacion", 30),
    "material": ("Materiales", 40),
    "movement": ("Movimientos", 50),
    "material_component": ("Componentes", 60),
    "inventory_status": ("Estado de inventario", 70),
    "proyect": ("Proyectos", 10),
    "task": ("Tareas", 20),
    "task_note": ("Notas de tarea", 30),
    "task_type": ("Tipos de tarea", 40),
    "incident": ("Incidencias", 50),
    "incident_detail": ("Detalle de incidencias", 60),
    "payroll_period": ("Periodos de nomina", 10),
    "payroll_concept": ("Conceptos", 20),
    "payroll_movement": ("Movimientos", 30),
    "payroll_detail": ("Detalle", 40),
    "user": ("Usuarios", 10),
    "permission": ("Perfiles", 20),
    "department": ("Departamentos", 30),
    "subdepartment": ("Subdepartamentos", 40),
    "level": ("Niveles", 50),
}


# --- comprobaciones que corren al importar ------------------------------

def _mapa_de_entidades():
    """entidad -> modulo. Revienta si una entidad esta en dos modulos."""
    mapa = {}
    for modulo in MODULOS:
        for entidad in modulo.entidades:
            if entidad in mapa:
                raise RuntimeError(
                    f"'{entidad}' pertenece a dos modulos: {mapa[entidad]} y {modulo.clave}. "
                    "Una entidad tiene exactamente un dueno."
                )
            mapa[entidad] = modulo.clave
    return mapa


ENTIDAD_A_MODULO = _mapa_de_entidades()
MODULO_POR_CLAVE = {m.clave: m for m in MODULOS}
CAPACIDAD_POR_CLAVE = {c.clave: c for c in CAPACIDADES}


def _solo_por_capacidad(clave) -> bool:
    """Modulos que no tienen entidades en la base del nucleo."""
    modulo = MODULO_POR_CLAVE.get(clave)
    return bool(modulo and not modulo.entidades)


def _validar():
    claves = [m.clave for m in MODULOS]
    if len(claves) != len(set(claves)):
        raise RuntimeError("Hay dos modulos con la misma clave.")

    for capacidad in CAPACIDADES:
        if capacidad.modulo not in MODULO_POR_CLAVE:
            raise RuntimeError(
                f"La capacidad '{capacidad.clave}' apunta al modulo inexistente "
                f"'{capacidad.modulo}'."
            )
        if capacidad.clave in ENTIDAD_A_MODULO:
            raise RuntimeError(
                f"'{capacidad.clave}' esta declarada como capacidad y como entidad."
            )

    for rol in ROLES:
        for clave, bits in rol.modulos.items():
            if clave not in MODULO_POR_CLAVE:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' concede el modulo inexistente '{clave}'."
                )
            if bits != (bits & BITS_VALIDOS) or bits <= 0:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' usa bits invalidos ({bits}) en '{clave}'."
                )
        for capacidad in rol.capacidades:
            if capacidad not in CAPACIDAD_POR_CLAVE:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' concede la capacidad inexistente "
                    f"'{capacidad}'."
                )
            modulo = CAPACIDAD_POR_CLAVE[capacidad].modulo
            if modulo not in rol.modulos and not _solo_por_capacidad(modulo):
                # Restaurante y punto de venta se operan solo por capacidades,
                # asi que no necesitan acceso de tabla al modulo.
                raise RuntimeError(
                    f"El rol '{rol.nombre}' tiene la capacidad '{capacidad}' del modulo "
                    f"'{modulo}' sin acceso a ese modulo: es una fila que no puede "
                    "ejercer y hace creer que si."
                )

    ids = [r.id_permission for r in ROLES]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Hay dos roles con el mismo id_permission.")


_validar()


def modulo_de(nombre):
    """A que modulo pertenece una entidad o una capacidad.

    Devuelve None si el nombre no esta declarado en ningun sitio.

    Incluye las capacidades a proposito. Sin ellas, un cliente cuyo plan no
    trae el punto de venta seguiria alcanzando el puente, porque el puente se
    gatea con `pos_terminal` y `pos_admin`, que son capacidades y no tablas.
    Lo mismo con el restaurante y con los ajustes de existencias.
    """
    modulo = ENTIDAD_A_MODULO.get(nombre)
    if modulo is not None:
        return modulo
    capacidad = CAPACIDAD_POR_CLAVE.get(nombre)
    return capacidad.modulo if capacidad is not None else None


def almacenes():
    """Modulo -> cadena de tablas de su almacen propio."""
    return {m.clave: m.almacen for m in MODULOS if m.almacen}


def filas_de_permisos():
    """La matriz completa, lista para sembrar.

    Devuelve tuplas (id_permission, entity_name, bits, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia).

    `modulo_licencia` es la clave que gobierna si la fila se siembra para un
    cliente dado: normalmente la del modulo dueno de la entidad/capacidad,
    salvo una capacidad con `licencia_independiente=True`, que usa su propia
    clave -- se vende aparte, no viaja con el modulo que la contiene.
    """
    filas = []
    for rol in ROLES:
        for clave, bits in sorted(rol.modulos.items()):
            modulo = MODULO_POR_CLAVE[clave]
            for entidad in sorted(modulo.entidades):
                if entidad in SOLO_ARRANQUE:
                    continue
                etiqueta, orden = MENU.get(entidad, (None, None))
                filas.append((
                    rol.id_permission, entidad, bits,
                    "sidebar" if etiqueta else "hidden",
                    modulo.grupo_de_menu if etiqueta else None,
                    modulo.icono_de_menu if etiqueta else None,
                    etiqueta,
                    modulo.orden + (orden or 90),
                    modulo.clave,
                ))
        for clave in sorted(rol.capacidades):
            capacidad = CAPACIDAD_POR_CLAVE[clave]
            modulo = MODULO_POR_CLAVE[capacidad.modulo]
            # Se ve en algun menu, no solo en el vertical. Con `== "sidebar"`
            # una capacidad puesta en el engrane salia sin etiqueta ni icono, y
            # el engrane mostraba un renglon en blanco. La etiqueta que habia
            # venia de una migracion escrita a mano, asi que se perdia en la
            # siguiente resiembra: es exactamente lo que paso con la conexion al
            # dispositivo Kronos.
            es_pantalla = capacidad.menu in ("sidebar", "settings")
            filas.append((
                rol.id_permission, capacidad.clave, capacidad.bits, capacidad.menu,
                modulo.grupo_de_menu if es_pantalla else None,
                modulo.icono_de_menu if es_pantalla else None,
                capacidad.etiqueta if es_pantalla else None,
                modulo.orden + 90,
                capacidad.clave if capacidad.licencia_independiente else modulo.clave,
            ))
    return filas


MODULOS_CORE = tuple(m.clave for m in MODULOS if m.clave not in MODULOS_DE_NEGOCIO)
