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
      { key: "section_warehouse", items: [
        ["warehouses", "almacenes", "logistics_warehouse"],
        ["locations", "ubicaciones", "logistics_location"],
        ["inventory", "inventario", "logistics_inventory"],
        ["racks", "racks", "logistics_rack"],
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
      { key: "section_administration", items: [
        ["users", "usuarios", "user"],
        ["roles", "roles", null, "admin"],
        ["audit", "auditoria", null, "technical"],
        // La pantalla de seguridad tampoco declaraba nada, asi que la veia
        // todo el mundo. Se gatea contra el perfil, que es lo que administra.
        ["security", "seguridad", "permission"],
      ]},
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
        // El almacen del POS se lee desde el inventario unico: la pantalla dice
        // que tanto de su catalogo descuenta de verdad del almacen de TYAKXA.
        ["inventory", "inventario", "pos_admin"],
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

/** Modulos que hoy se pueden mostrar en el menu. */
export const availableModuleSections = moduleSections.filter(
  (modulo) => modulo.disponible !== false
);

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
