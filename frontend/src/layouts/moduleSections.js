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
    icon: "shopping-cart",
    basePath: "/pos",
    // Las secciones salen de las pantallas que el modulo trae de verdad
    // (modules/pos/frontend/src/pages), no de una agrupacion inventada.
    //
    // Limitacion conocida: las pantallas todavia no existen en este frontend.
    // El modulo corre su propio front contra su propia base, y rehacerlas aqui
    // -como se hizo con el restaurante- es trabajo aparte. Mientras tanto, la
    // ruta comodin de App.jsx devuelve al tablero, asi que pulsar una entrada
    // no rompe nada pero tampoco lleva a ningun lado.
    sections: [
      { key: "section_pos_till", items: [
        ["pos_terminal", "caja", "pos_terminal"],
        ["cash_sessions", "cortes", "pos_terminal"],
        ["expenses", "gastos", "pos_admin"],
      ]},
      { key: "section_pos_catalog", items: [
        ["products", "productos", "pos_admin"],
        ["categories", "categorias", "pos_admin"],
        ["promotions", "promociones", "pos_admin"],
        ["suppliers", "proveedores", "pos_admin"],
      ]},
      { key: "section_pos_warehouse", items: [
        // Almacen propio del modulo: no comparte tabla con el de inventario ni
        // con el de logistica, y de hecho vive en otra base.
        ["inventory", "inventario", "pos_admin"],
      ]},
      { key: "section_pos_invoicing", items: [
        ["invoices", "facturas", "pos_admin"],
        ["invoicing", "facturacion", "pos_admin"],
        ["invoicing_config", "facturacion/configuracion", "pos_admin"],
      ]},
      { key: "section_pos_reports", items: [
        ["dashboard", "tablero", "pos_terminal"],
        ["reports", "reportes", "pos_admin"],
      ]},
      { key: "section_administration", items: [
        ["users", "usuarios", "pos_admin"],
        ["audit", "auditoria", null, "technical"],
      ]},
    ],
  },
];

/** Modulos que hoy se pueden mostrar en el menu. */
export const availableModuleSections = moduleSections.filter(
  (modulo) => modulo.disponible !== false
);
