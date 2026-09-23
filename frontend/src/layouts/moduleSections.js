/**
 * Modulos con menu de dos niveles: modulo -> seccion -> pantalla.
 *
 * Por que existe este archivo
 * ---------------------------
 * Logistica tenia su menu de dos niveles escrito a mano dentro de `Shell.jsx`,
 * en un bloque aparte del bucle que si lee permisos. Al integrar el punto de
 * venta habia que elegir entre duplicar ese bloque o volverlo dato: se eligio lo
 * segundo, porque un tercer modulo con secciones habria significado un tercer
 * bloque casi identico, y esa es la forma en que dos menus empiezan a
 * comportarse distinto sin que nadie lo decida.
 *
 * Que NO vive aqui
 * ----------------
 * Los permisos. Cada entrada declara contra que entidad o capacidad se gatea, y
 * quien decide si el usuario la ve sigue siendo `entity_permission` en el
 * backend. Este archivo solo dice como se agrupa y a donde va.
 *
 * Forma de cada entrada
 * ---------------------
 *   [claveDeTexto, rutaRelativa, entidadQueLaGatea?, compuertaEspecial?]
 *
 * `entidadQueLaGatea` en null significa que la entrada se muestra a cualquiera
 * que alcance el modulo. `compuertaEspecial` acepta "admin" (administrador de
 * empresa) o "technical" (solo la cuenta de arranque).
 */

export const moduleSections = [
  {
    // Clave del grupo en el estado de abierto/cerrado del menu. Se conserva el
    // valor con acento porque ya esta guardado asi en localStorage de los
    // usuarios; cambiarlo les colapsaria el menu sin motivo.
    key: "Logística",
    titleKey: "group_logistics",
    // Contra que modulo del plan se gatea el apartado entero. Hace falta
    // aparte de las entidades de cada entrada: dentro de Logistica hay dos
    // pantallas de facturacion, asi que un cliente que compro facturacion pero
    // no logistica seguia viendo el encabezado "Logistica" con esas dos
    // dentro. No era fuga de datos -el backend negaba lo demas- pero le
    // nombraba un modulo que no compro.
    modulo: "logistica",
    icon: "truck",
    basePath: "/logistica",
    sections: [
      { key: "section_commercial", items: [
        ["quotations", "cotizaciones", "logistics_quotation"],
        ["requests", "solicitudes", "logistics_service_request"],
        ["files", "expedientes", "logistics_file"],
      ]},
      { key: "section_operations", items: [
        ["trips", "viajes", "logistics_trip"],
        ["evidences", "evidencias", "logistics_evidence"],
        ["incidents", "incidencias", "logistics_incident"],
      ]},
      // Estas dos secciones no declaraban contra que se gatean, y una entrada
      // sin entidad se muestra a cualquiera. El resultado medido: el
      // almacenista, que no tiene ni una entidad de logistica, veia Flota,
      // Almacen y Administracion. Es fuga de menu y no de datos -el backend
      // seguia negando- pero ensena un almacen ajeno a quien no le toca, que
      // es justo la separacion que se pidio mantener.
      { key: "section_fleet", items: [
        ["units", "unidades", "logistics_unit"],
        ["trailers", "remolques", "logistics_trailer"],
        ["operators", "operadores", "logistics_operator"],
        ["maintenance", "mantenimientos", "logistics_maintenance"],
      ]},
      // Un solo almacen para los cuatro proyectos.
      //
      // Aqui habia cuatro pantallas propias -- almacenes, ubicaciones,
      // inventario y racks -- que competian con el almacen de verdad: dos
      // sitios donde preguntar cuanto hay, y dos respuestas. Los saldos ya los
      // unifican los puentes (`services/logistics_inventory_bridge.py`); esto
      // unifica la puerta, con la ruta absoluta del nucleo.
      //
      // Sus tablas y sus pantallas siguen ahi, sin entrada de menu: se retira
      // la duplicidad, no el codigo. Lo que deja de verse es la dimension "de
      // que cliente es esta mercancia", que solo existe en
      // `logistics_inventory` -- si vuelve a hacer falta, es devolver la
      // seccion, no reconstruirla.
      { key: "section_warehouse", items: [
        ["warehouse", "/inventory", "product"],
        ["locate", "/inventory/trace", "product"],
      ]},
      { key: "section_finance", items: [
        ["invoices", "facturas", "invoice"],
        ["branches", "sucursales", "logistics_branch"],
        ["receivables", "cuentas-cobrar", "logistics_receivable"],
        ["manual_invoice", "facturacion/manual", "invoice"],
      ]},
      { key: "section_foreign_trade", items: [
        ["suppliers", "proveedores", "customer_supplier"],
        ["shipments", "embarques", "logistics_shipment"],
      ]},
      // `section_administration` (Usuarios/Roles/Seguridad) se quito de aqui:
      // era un segundo camino a las MISMAS pantallas que ya viven, una sola
      // vez, bajo el engrane de Configuracion (ver
      // 20260903000000_configuracion_dentro_del_engrane.sql y `navItems` en
      // Shell.jsx). No se gateaba contra nada de logistica -"users" contra
      // `user`, "roles" contra ser admin, "security" contra `permission`-, asi
      // que cualquier rol con esas entidades veia "Administracion" colgando
      // de "Logistica" sin poder quitarlo desde el gestor de roles: ese
      // gestor no conoce esta estructura, solo `entity_permission`.
    ],
  },
  {
    key: "Punto de venta",
    titleKey: "group_pos",
    modulo: "pos",
    icon: "shopping-cart",
    basePath: "/pos",
    // Las secciones salen de las pantallas que el modulo trae de verdad
    // (modules/pos/frontend/src/pages), no de una agrupacion inventada.
    //
    // La caja ya tiene pantalla propia y habla con el POS por el puente del
    // nucleo, de modo que el usuario entra una sola vez, en TYAKXA. Las demas
    // entradas todavia no tienen pantalla: la ruta comodin devuelve al tablero,
    // asi que pulsarlas no rompe nada pero tampoco lleva a ningun lado.
    sections: [
      { key: "section_pos_till", items: [
        ["pos_terminal", "caja", "pos_terminal"],
        // El turno lo abre y lo cierra el mismo cajero que cobra: sin turno
        // abierto no hay venta, asi que va junto a la caja y no en otro grupo.
        ["shift", "turno", "pos_terminal"],
      ]},
      { key: "section_pos_catalog", items: [
        ["products", "productos", "pos_terminal"],
      ]},
      { key: "section_pos_warehouse", items: [
        // El mismo almacen que el resto, y por la misma puerta. El puente del
        // POS ya escribia sus ventas en el libro del nucleo con
        // `source_module = 'pos'`; esto hace que tambien se consulten ahi.
        //
        // Su pantalla propia -- que decia cuanto de su catalogo descuenta de
        // verdad -- sigue en el codigo y sin entrada de menu: era una vista de
        // conciliacion, y con un solo almacen no hay nada que conciliar.
        ["warehouse", "/inventory", "product"],
        ["locate", "/inventory/trace", "product"],
      ]},
      { key: "section_pos_reports", items: [
        ["dashboard", "tablero", "pos_admin"],
      ]},
      { key: "section_pos_marketing", items: [
        ["promotions", "promociones", "pos_admin"],
      ]},
      // Facturacion y administracion del POS no aparecen a proposito. La
      // decision es que haya un solo modulo de facturacion -el del nucleo, que
      // timbra CFDI- y una sola administracion de usuarios. Dejar aqui las del
      // POS invitaria a usar dos, que es como se acaba con dos verdades.
    ],
  },
];

/**
 * Entidades PROPIAS de un modulo con secciones: las que empiezan con su
 * propio prefijo, no las que solo pidio prestadas de otro modulo para no
 * duplicar pantalla (Almacen/Facturas/Proveedores en Logistica son
 * `product`/`invoice`/`customer_supplier`, y esas SI son de otro modulo).
 *
 * Sin esta lista, un rol sin una sola entidad de logistica seguia viendo el
 * encabezado "Logistica" -con Almacen, Facturas y Proveedores dentro- en
 * cuanto tenia el modulo de Inventario, Facturacion o CRM, que es casi
 * cualquier rol. Y no habia forma de quitarlo desde el Gestor de roles y
 * permisos: nada ahi controla si "Logistica" se pinta, porque nada de lo que
 * lo sostenia era, en los hechos, de logistica.
 */
function entidadesPropias(modulo, prefijo) {
  const nombres = new Set();
  modulo.sections.forEach((seccion) => seccion.items.forEach(([, , entidad]) => {
    if (entidad && entidad.startsWith(prefijo)) nombres.add(entidad);
  }));
  return [...nombres];
}

// Prefijo de las entidades/capacidades PROPIAS de cada modulo con secciones.
// Punto de venta tiene la misma fuga que tuvo Logistica: "Almacen"/"Localizar"
// piden prestado `product` del modulo de Inventario para no duplicar
// pantalla, y sin este filtro cualquier rol con Inventario -casi cualquier
// rol- veia el encabezado "Punto de venta" sin tener ni una capacidad real
// de POS, y sin checkbox en el Gestor de roles que lo apagara.
const PREFIJO_PROPIO_POR_MODULO = { logistica: "logistics_", pos: "pos_" };

/** Modulos que hoy se pueden mostrar en el menu. */
export const availableModuleSections = moduleSections.filter(
  (modulo) => modulo.disponible !== false
).map((modulo) => {
  const prefijo = PREFIJO_PROPIO_POR_MODULO[modulo.modulo];
  return prefijo ? { ...modulo, entidadesPropias: entidadesPropias(modulo, prefijo) } : modulo;
});

/**
 * Los apartados que el plan del despliegue permite.
 *
 * `modulosDelPlan` es la lista que devuelve `/security/plan`. Mientras no haya
 * llegado -o si el servidor no la da- se muestran todos: un menu vacio mientras
 * carga se lee como un sistema roto, y el backend niega igual lo que no este en
 * el plan, asi que ocultar aqui es comodidad y no seguridad.
 */
export function moduleSectionsEnPlan(modulosDelPlan) {
  if (!Array.isArray(modulosDelPlan) || modulosDelPlan.length === 0) {
    return availableModuleSections;
  }
  const permitidos = new Set(modulosDelPlan);
  return availableModuleSections.filter(
    (modulo) => !modulo.modulo || permitidos.has(modulo.modulo)
  );
}
