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
                 almacen=None, menu="sidebar",
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
        # En que menu se ven las pantallas del modulo: la barra lateral o el
        # engrane. Estaba fijo en `filas_de_permisos` como "sidebar" para toda
        # entidad con etiqueta, asi que Configuracion y Seguridad reaparecian en
        # la barra en cuanto alguien resembraba los permisos -- por mucho que
        # una migracion escrita a mano los hubiera movido antes al engrane.
        # Declararlo aqui es lo que hace que el arreglo sobreviva la resiembra.
        self.menu = menu
        self.grupo_de_menu = grupo_de_menu or etiqueta
        self.icono_de_menu = icono_de_menu or icono
        self.entidades = tuple(entidades)
        # Cadena de tablas del almacen propio, si el modulo tiene uno.
        #
        # Existio tambien `base_de_datos`, para un modulo que no compartiera la
        # del nucleo. Se retiro con la absorcion del punto de venta, que era el
        # unico que la declaraba: ya no queda ningun modulo con base aparte, y
        # un campo que nadie usa invita a volver a separar lo que costo unir.
        self.almacen = tuple(almacen or ())

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
            "product_family", "material_attribute",
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
        # Se opera por pantalla y no por CRUD de tabla, igual que el
        # restaurante: sus permisos son las dos capacidades de abajo.
        #
        # Hasta la migracion 20260911100000 corria contra su propia base
        # (`pos_enterprise`) y se declaraba con `base_de_datos`. Ya no: sus
        # tablas viven aqui y su catalogo ES `product`.
        (),
        # Sin `almacen` propio, y ahora es verdad en el fondo y no solo en la
        # forma: el punto de venta descuenta del almacen del nucleo.
    ),
    Modulo(
        "crm", "CRM", "crm", 600,
        (
            "customer_supplier", "customer_contact", "product_sale_config", "public_api_key",
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
    # Sus pantallas no tienen apartado propio en el menu lateral: viven dentro
    # del Home/Dashboard actual (ruta "/"), que ya es de acceso libre para
    # cualquier usuario autenticado. Por eso ninguna de sus cuatro entidades
    # tiene entrada en MENU, y quedan sembradas como "hidden".
    Modulo(
        "kpis", "KPIs", "bar-chart", 750,
        ("kpi_definition", "nm_permission_kpi", "kpi_dashboard", "kpi_dashboard_widget"),
    ),
    # --- infraestructura, no son submodulos de negocio -------------------
    Modulo(
        "configuracion", "Configuracion", "settings", 800,
        # Catalogos que cualquier pantalla necesita leer para pintar un select.
        # Sin acceso de lectura a `status` los desplegables quedan vacios, asi
        # que todos los roles los consultan.
        ("status", "theme", "department", "subdepartment", "level"),
        # Van en el engrane, no en la barra: son catalogos que se tocan una vez
        # al instalar, no pantallas de trabajo diario.
        menu="settings",
    ),
    Modulo(
        "seguridad", "Seguridad", "security", 900,
        # Usuarios, perfiles y bitacora. Solo administracion.
        #
        # `team`/`nm_team_user` (equipos de usuarios) van aqui y no en
        # `configuracion`: se administran, no se consultan desde todas
        # partes para pintar un select. `nm_team_user` es tabla puente -se
        # edita desde `team`, igual que `nm_field_permission` se edita desde
        # el gestor de permisos- por eso no tiene entrada en MENU.
        (
            "user", "user_mfa", "permission", "entity_permission",
            "nm_field_permission", "field", "event_log",
            "team", "nm_team_user",
        ),
        menu="settings",
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
    # El vale de almacen: quien se llevo que, de donde, y si ya lo devolvio.
    #
    # Va como capacidad y no como entidad porque su pantalla no es el CRUD de
    # una tabla: escribe en `incident` -el vale- y en `nm_incident_product`
    # -sus renglones-, y esa segunda esta fuera del menu a proposito, por ser
    # tabla puente que se edita desde su dueno.
    #
    # Con `bits=CAPTURA` porque levantar un vale es crear y leer; cerrarlo es
    # actualizar el renglon, que ya gobierna el permiso de la entidad.
    # El prevale: el supervisor PIDE material y el almacen lo surte. Es una
    # capacidad aparte de `warehouse_voucher` y no el mismo derecho con menos
    # bits, porque los bits de una capacidad son suyos y no del rol: con una
    # sola clave, dar de alta un prevale y dar de alta un vale serian el mismo
    # permiso, y entonces el supervisor podria surtirse a si mismo.
    Capacidad("warehouse_prevoucher", "Prevales de material", "inventario",
              bits=CAPTURA, menu="sidebar"),
    # Confirmar que lo pedido se entrego y se recibio. Va aparte de levantar el
    # vale porque son dos personas: uno pide, otro surte y confirma.
    Capacidad("warehouse_voucher_confirm", "Confirmar entrega de material",
              "inventario"),
    Capacidad("warehouse_voucher", "Vales de almacen", "inventario",
              bits=CAPTURA, menu="sidebar"),
    # Convertir un borrador en un vale, que es el acto que saca el material.
    #
    # Aparte de `warehouse_voucher` por el mismo motivo que el prevale esta
    # aparte: con una sola clave, quien escribe el borrador y quien lo autoriza
    # tendrian el mismo permiso y la separacion no separaria nada. El borrador
    # existe para que el material lo suelte alguien distinto del que lo pidio.
    #
    # Sin entrada de menu: no es una pantalla, es un boton dentro del vale.
    # `CAPTURA` y no los bits por omision: autorizar es una ACCION y la ruta se
    # guarda con `create`, asi que con los 2 bits de solo lectura que trae una
    # capacidad por omision el jefe de almacen recibiria un 403 en la puerta.
    Capacidad("warehouse_voucher_authorize", "Autorizar vales de material",
              "inventario", bits=CAPTURA, menu="hidden"),
    # La bitacora diaria del taller. Solo Jefe de taller la sube -- pidio
    # negocio explicito (2026-09-28): el supervisor levanta el proyecto y pide
    # material, pero quien reporta el avance del dia en el piso es Jefe de
    # taller, que es tambien quien tiene a su cargo la plantilla de obreros
    # (via `team`/`nm_team_user`, sin inventar un rol nuevo para el obrero).
    #
    # Va como capacidad y no como bit de la entidad `proyect`/`task` porque no
    # es un CRUD de una tabla del menu: la pantalla ya existe
    # (`activity_logs`) y lo unico que faltaba era la puerta.
    Capacidad("daily_activity_log", "Bitacora diaria de taller", "operaciones",
              bits=CAPTURA, menu="hidden"),
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
    # Se vende aparte de Facturacion: un cliente puede tener facturacion sin
    # multiemisor. licencia_independiente=True hace que necesite su propia
    # clave en LICENSED_MODULES aunque el modulo padre ya este licenciado.
    Capacidad("multiemisor_csd", "Multiemisor y CSD", "facturacion", bits=TOTAL, menu="sidebar",
              licencia_independiente=True),
)


class Rol:
    """Que puede hacer un perfil en cada modulo, y que capacidades tiene."""

    def __init__(self, id_permission, nombre, modulos, capacidades=(), *, excepciones=None):
        self.id_permission = id_permission
        self.nombre = nombre
        self.modulos = dict(modulos)
        self.capacidades = tuple(capacidades)
        # Entidad -> bits que sustituyen al del modulo, solo para ESTE rol.
        # Los bits de un modulo son parejos para todas sus entidades; esto es
        # la valvula de escape para la entidad que necesita MENOS que el
        # resto sin partir el modulo en dos "operaciones_lectura" /
        # "operaciones_captura". Solo para restringir: la comprobacion de
        # abajo exige que sea un subconjunto del bit del modulo, nunca mas.
        self.excepciones = dict(excepciones or {})


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
    # `documentos` y `laboratorio` solo los recibe Administrator por ahora: los
    # modulos se integraron desde la rama tny_docs, que los concedia a los 12
    # perfiles por igual -incluidos los del restaurante, que ya no existen-, y
    # que perfiles los operan de verdad es una decision de negocio que todavia
    # no se tomo. Ampliarlo es
    # agregar la clave a los roles que correspondan; dejarlo abierto era lo que
    # hacia que un mesero pudiera leer expedientes de empleados.
    # `kpis`, igual que `documentos`/`laboratorio` arriba: solo Administrator
    # por ahora, y que otro rol lo reciba -y con que bits- es una decision de
    # negocio pendiente, no tecnica.
    #
    # Los bits van parejos por modulo (`Rol.modulos` es un solo valor para las
    # cuatro entidades, no uno por entidad), asi que aqui las cuatro quedan en
    # TOTAL, igual que el resto de los modulos de Administrator. El criterio
    # que SI debe aplicarse entidad por entidad cuando se decida dar `kpis` a
    # un rol que no sea Administrator:
    #   * `kpi_definition` -- catalogo de solo lectura: CONSULTA alcanza para
    #     cualquiera con el modulo, nadie crea KPIs a mano.
    #   * `nm_permission_kpi` -- lo administra solo quien reparte permisos,
    #     igual que ya pasa con `nm_field_permission`: TOTAL.
    #   * `kpi_dashboard` / `kpi_dashboard_widget` -- datos propios del
    #     usuario (sus tableros): TOTAL.
    Rol(1, "Administrator", {
        "facturacion": TOTAL, "inventario": TOTAL, "operaciones": TOTAL,
        "logistica": TOTAL, "restaurante": TOTAL, "pos": TOTAL, "crm": TOTAL, "rh": TOTAL,
        "documentos": TOTAL, "laboratorio": TOTAL, "kpis": TOTAL,
        "configuracion": TOTAL, "seguridad": TOTAL,
    # Todas las capacidades MENOS las dos que sacan material del almacen.
    #
    # Es separacion de deberes, y se pidio asi: quien administra el sistema
    # puede dejar el prevale -- `warehouse_prevoucher` sigue ahi -- pero no
    # emitir el vale ni autorizarlo. El material lo suelta Almacenista.
    #
    # No afecta a la cuenta `admin1`: es el bootstrap admin y salta las
    # comprobaciones de capacidad por completo (`_sin_restriccion`). Esto
    # gobierna a cualquier OTRO usuario que lleve el rol Administrator.
    }, [c.clave for c in CAPACIDADES
        if c.clave not in ("warehouse_voucher", "warehouse_voucher_authorize")]),

    # Los cuatro roles del negocio, en los identificadores que tiene la BASE.
    #
    # Estaban declarados en los ids 14..18 mientras la base los tiene en 2..6, y
    # en los ids 2 y 3 este registro declaraba dos roles que la base no tiene
    # -gerente_administrativo y vendedor-. El efecto medido: Supervisor recibia
    # la concesion del gerente administrativo -73 filas de permiso, 53 en el
    # menu- y Jefe de taller se quedaba con 6.
    #
    # Manda la base. Si algun dia se renumera, se renumera alla y aqui se
    # sigue: los usuarios ya existen apuntando a esos identificadores, y
    # moverlos es mover permisos de gente real.

    # Pide material con un prevale y sigue sus propios proyectos. NO surte: no
    # tiene `warehouse_voucher`, asi que no puede levantar el vale con el que se
    # entrega, ni editar uno ya levantado.
    #
    # `task` e `incident` son la excepcion dentro de "operaciones": Supervisor
    # las CONSULTA nada mas -ve tareas e incidencias, no las crea ni las
    # modifica-, aunque conserve CAPTURA en el resto del modulo (sus propios
    # proyectos). Pedido de negocio explicito (2026-09-22): el supervisor
    # supervisa, no captura tarea ni incidencia. `incident_supervision` sigue
    # concedida -es "ver incidencias ajenas", no escribirlas- y no choca con
    # esto.
    #
    # Ojo: como en el resto de excepciones puntuales de este registro
    # (ver la nota de Gerente/`warehouse_voucher` mas abajo), esto solo fija
    # el valor por omision para una instalacion NUEVA. Un Supervisor que ya
    # existe (tyakxa-dev y los 3 clientes reales) no se toca por resiembra
    # -el Gestor de roles y permisos manda-: hay que ajustarlo a mano ahi,
    # por instalacion, una vez.
    Rol(2, "Supervisor", {
        "operaciones": CAPTURA, "inventario": CONSULTA, "configuracion": CONSULTA,
    }, ["incident_supervision", "warehouse_prevoucher"],
        excepciones={"task": CONSULTA, "incident": CONSULTA}),

    # Ve y busca el almacen sin modificarlo -`inventario` en CONSULTA- y
    # autoriza o cancela los proyectos de todos los supervisores.
    #
    # La visibilidad de solo-lectura de `warehouse_voucher` (ver vales, sin
    # poder crearlos/autorizarlos) NO se declara aqui: `Capacidad.bits` es un
    # solo valor para todo el que la tenga (CAPTURA = crear+leer+actualizar),
    # asi que agregarla a esta lista le daria a Gerente de mas. Se siembra
    # aparte, solo con `scope_read`, en
    # 20260921120000_fusionar_jefe_de_almacen_en_almacenista.sql.
    Rol(3, "Gerente", {
        "operaciones": EDITAR, "facturacion": CAPTURA, "crm": CAPTURA,
        "inventario": CONSULTA, "rh": CONSULTA, "logistica": CONSULTA,
        "configuracion": CONSULTA,
    }, ["project_authorization", "incident_supervision", "pos_admin", "pos_terminal"]),

    # Ve los proyectos autorizados y mueve su estatus en el taller.
    Rol(4, "Jefe de taller", {
        "operaciones": CAPTURA, "inventario": CONSULTA, "configuracion": CONSULTA,
    }, ["project_execution", "incident_supervision", "daily_activity_log"]),

    # Opera el almacen entero: da de alta productos, levanta vales, los
    # asigna, autoriza/entrega, confirma devoluciones y ajusta inventario.
    # Antes esto estaba partido con "Jefe de almacen" (separacion de
    # deberes); se fusiono aqui por decision de negocio -- un solo rol de
    # almacen, sin ese segundo nivel. Ver
    # 20260921120000_fusionar_jefe_de_almacen_en_almacenista.sql.
    Rol(5, "Almacenista", {
        "inventario": TOTAL, "logistica": CAPTURA, "configuracion": CONSULTA,
    }, ["inventory_adjustment", "warehouse_voucher",
        "warehouse_voucher_authorize", "warehouse_voucher_confirm"]),

    # Cuatro roles retirados, y por que
    # --------------------------------
    # `Mesero` (10), `Cocina` (11), `Caja Restaurante` (12) y
    # `Admin Restaurante` (13) llegaron con el restaurante desde `seed.sql`,
    # que los escribia a mano junto con sus filas de `entity_permission`. Cada
    # uno existia para cargar UNA capacidad -`restaurant_waiter`,
    # `restaurant_kitchen`, `restaurant_cashier`- que este registro ya declara
    # y que el gestor de roles ya ofrece por separado. Eran el mismo derecho
    # dicho dos veces, y dicho distinto: la base los tenia en 15 (administrar)
    # donde aqui dicen 7 y 6, porque el `seed.sql` los sembraba con sus propios
    # numeros.
    #
    # Retirar el rol NO retira la funcion: las cuatro capacidades del
    # restaurante siguen declaradas abajo en CAPACIDADES y se conceden a
    # cualquier rol -uno nuevo, o uno existente- desde el gestor. Lo que
    # desaparece es el rol vacio que no concedia nada mas.
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
    #
    # Una sola entrada para los DOS NIVELES de la clasificacion. Habia dos
    # -"Familias de producto" y "Tipos de material"- y leidas en el menu una
    # detras de la otra parecen la misma cosa dos veces. No lo son: el tipo
    # El TIPO se retiro del flujo: en estos datos la descripcion del material ya
    # lo trae -"BROCA HELICOIDAL 3/4", "DADO 3/16"-, asi que un nivel aparte no
    # distingue nada que la descripcion no distinga y obliga a capturar dos veces
    # lo mismo. El sistema anterior tampoco lo tenia, y tras la carga eran 603
    # materiales con cero tipos. La tabla se queda -hay 4 capturados a mano- pero
    # nada la lee.
    "product_family": ("Familias de producto", 12),
    "brand": ("Marcas", 14),
    "unit": ("Unidades", 16),
    "location": ("Ubicaciones", 20),
    "location_type": ("Tipos de ubicacion", 30),
    "material": ("Materiales", 40),
    "movement": ("Movimientos", 50),
    "material_component": ("Componentes", 60),
    "inventory_status": ("Estado de inventario", 70),
    # Operaciones. El orden es el del flujo, no el alfabetico: primero el
    # proyecto, luego las tareas en que se parte, y aparte las incidencias con
    # su catalogo de tipos. El menu se leia "Detalle de incidencias,
    # Incidencias, Notas de tarea, Proyectos, Tareas, Tipos de tarea" -orden
    # alfabetico, porque las etiquetas no decian el orden del trabajo- y para
    # entenderlo habia que saberse de memoria que cuelga de que.
    "proyect": ("Proyectos", 10),
    "task": ("Tareas", 20),
    # `task_note` no tiene entrada a proposito, no por descuido: su columna
    # `id_task` es NOT NULL, o sea que una nota no existe sin su tarea. Con
    # pantalla propia habia que abrir una tercera lista y elegir la tarea en un
    # desplegable para escribir una nota, y la bitacora de una tarea no se leia
    # en ningun sitio junta. Se captura y se lee dentro de la tarea, en el
    # expediente del proyecto. `nm_incident_product` y `nm_template_task` estan
    # fuera por lo mismo: son tablas puente, se editan desde su dueno.
    "incident": ("Incidencias", 30),
    "incident_type": ("Tipos de incidencia", 32),
    # La etiqueta anterior, "Detalle de incidencias", nombraba otra cosa:
    # `incident_detail.id_incident_type` apunta al TIPO, no a la incidencia, y
    # la pantalla estaba justo debajo de Incidencias. Quien buscaba el detalle
    # de una incidencia abria un catalogo de subtipos.
    "incident_detail": ("Subtipos de incidencia", 34),
    "template": ("Plantillas de tarea", 40),
    # `task_type` es un catalogo que hoy nadie consume: `task` no tiene
    # `id_task_type`, su columna `type` es un Enum('personal','business'). Se
    # queda en el menu -el permiso existe y la pantalla captura- pero al final
    # del grupo, para que no se lea como un paso del flujo.
    "task_type": ("Tipos de tarea", 42),
    # Logistica. Las 21 pantallas EXISTEN y la base las tenia en la barra con su
    # etiqueta -se la puso la migracion de tny_logistics a mano-, pero aqui no
    # habia ni una entrada. Consecuencia medida: `filas_de_permisos()` las
    # sembraba en `hidden`, asi que una instalacion NUEVA se quedaba con el
    # modulo entero sin menu -las rutas responden, pero solo se llega
    # escribiendo la direccion-, y la etiqueta escrita a mano se perdia en la
    # primera resiembra. Es el mismo descuido que ya habia pasado con la
    # conexion al dispositivo Kronos.
    #
    # El orden es el del trabajo, no el alfabetico, igual que en inventario y
    # operaciones: primero con quien se trabaja, luego donde se guarda, luego
    # lo que se mueve, luego con que se mueve, y al final la cobranza.
    "logistics_branch": ("Sucursales", 10),
    "logistics_address": ("Direcciones", 12),
    "logistics_contact": ("Contactos", 14),
    "logistics_contract": ("Contratos", 16),
    "logistics_rate": ("Tarifas", 18),
    "logistics_quotation": ("Cotizaciones", 20),
    "logistics_warehouse": ("Almacenes", 30),
    "logistics_location": ("Ubicaciones", 32),
    "logistics_rack": ("Racks", 34),
    "logistics_inventory": ("Inventario", 36),
    "logistics_service_request": ("Solicitudes de servicio", 40),
    "logistics_trip": ("Viajes", 42),
    "logistics_shipment": ("Embarques", 44),
    "logistics_evidence": ("Evidencias", 46),
    "logistics_incident": ("Incidencias", 48),
    "logistics_unit": ("Unidades", 50),
    "logistics_trailer": ("Remolques", 52),
    "logistics_operator": ("Operadores", 54),
    "logistics_maintenance": ("Mantenimientos", 56),
    "logistics_receivable": ("Cuentas por cobrar", 60),
    "logistics_file": ("Expedientes", 62),
    # El calendario de citas. Misma historia: la pantalla existe y la base la
    # tenia en la barra, pero bajo el grupo "Operaciones" -- y `appointment`
    # pertenece a CRM, que es de donde sale la cita. Declararlo aqui lo pone en
    # su propio grupo y deja de aparecer en dos sitios segun quien resiembre.
    "appointment": ("Calendario", 30),
    "payroll_period": ("Periodos de nomina", 10),
    "payroll_concept": ("Conceptos", 20),
    "payroll_movement": ("Movimientos", 30),
    "payroll_detail": ("Detalle", 40),
    "user": ("Usuarios", 10),
    "permission": ("Perfiles", 20),
    "department": ("Departamentos", 30),
    "subdepartment": ("Subdepartamentos", 40),
    "level": ("Niveles", 50),
    "team": ("Equipos", 60),
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
        for entidad, bits_excepcion in rol.excepciones.items():
            if entidad not in ENTIDAD_A_MODULO:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' tiene una excepcion para la entidad "
                    f"inexistente '{entidad}'."
                )
            modulo_de_entidad = ENTIDAD_A_MODULO[entidad]
            if modulo_de_entidad not in rol.modulos:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' tiene una excepcion en '{entidad}' pero no "
                    f"tiene acceso a su modulo '{modulo_de_entidad}'."
                )
            bits_modulo = rol.modulos[modulo_de_entidad]
            if bits_excepcion != (bits_excepcion & BITS_VALIDOS) or bits_excepcion <= 0:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' usa bits invalidos ({bits_excepcion}) en la "
                    f"excepcion de '{entidad}'."
                )
            if bits_excepcion & ~bits_modulo:
                raise RuntimeError(
                    f"El rol '{rol.nombre}' tiene en '{entidad}' una excepcion "
                    f"({bits_excepcion}) que da MAS de lo que ya concede su modulo "
                    f"'{modulo_de_entidad}' ({bits_modulo}). Una excepcion solo resta."
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

    # El sembrado real resuelve por `nombre`, no por `id_permission` (ver
    # `filas_de_permisos`), asi que dos roles con el mismo nombre chocarian en
    # la base real aunque aqui tengan ids distintos.
    nombres = [r.nombre for r in ROLES]
    if len(nombres) != len(set(nombres)):
        raise RuntimeError("Hay dos roles con el mismo nombre.")


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


def _alcance_desde_bits(bits):
    """Bit encendido -> Todos (4); apagado -> Sin acceso (0).

    `entity_permission` dejo de tener un solo `control_type` combinado y pasa
    a 4 columnas de alcance independientes (una por accion). Esta es la regla
    de migracion acordada: un bit que ya estaba encendido no le quita a nadie
    el acceso que ya tenia. Ajustar un modulo a Propios/Mis grupos para un rol
    puntual es decision posterior, desde el gestor de permisos -- este
    registro solo da el valor POR OMISION de un modulo o un rol nuevo.

    Devuelve (scope_create, scope_read, scope_update, scope_delete).
    """
    return (
        4 if bits & CREAR else 0,
        4 if bits & LEER else 0,
        4 if bits & ACTUALIZAR else 0,
        4 if bits & BORRAR else 0,
    )


def filas_de_permisos():
    """La matriz completa, lista para sembrar.

    Devuelve tuplas (role_name, entity_name, scope_create, scope_read,
    scope_update, scope_delete, menu_location, menu_group, menu_group_icon,
    menu_label, menu_order, modulo_licencia).

    El primer campo es el NOMBRE del rol (`permission_description`), no su
    `id_permission`. La base resuelve el numero real por nombre al aplicar la
    migracion -- ver `backend/scripts/seed_module_permissions.py`-- porque los
    ids de `permission` no son estables entre instalaciones (cada una siembra
    sus roles en un orden distinto). Un id fijo aqui ya causo que Facturacion
    quedara concedida al rol equivocado en mas de un cliente real: el numero
    coincidia con OTRO rol en esa base, no con el que se penso al escribirlo.

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
                bits_entidad = rol.excepciones.get(entidad, bits)
                scope_create, scope_read, scope_update, scope_delete = _alcance_desde_bits(bits_entidad)
                filas.append((
                    rol.nombre, entidad,
                    scope_create, scope_read, scope_update, scope_delete,
                    modulo.menu if etiqueta else "hidden",
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
            scope_create, scope_read, scope_update, scope_delete = _alcance_desde_bits(capacidad.bits)
            filas.append((
                rol.nombre, capacidad.clave,
                scope_create, scope_read, scope_update, scope_delete,
                capacidad.menu,
                modulo.grupo_de_menu if es_pantalla else None,
                modulo.icono_de_menu if es_pantalla else None,
                capacidad.etiqueta if es_pantalla else None,
                modulo.orden + 90,
                capacidad.clave if capacidad.licencia_independiente else modulo.clave,
            ))
    return filas


MODULOS_CORE = tuple(m.clave for m in MODULOS if m.clave not in MODULOS_DE_NEGOCIO)
