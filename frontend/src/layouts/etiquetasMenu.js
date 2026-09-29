// Acentos de las etiquetas del menu lateral.
//
// Los grupos ("Facturacion") y muchas etiquetas ("Ordenes de servicio") no se
// escriben en el frontend: vienen de `entity_permission.menu_group` y
// `.menu_label`, que se siembran desde backend/app/modules/registry.py SIN
// acentos. Corregirlos en la base no es opcion: la siembra es `ON CONFLICT DO
// NOTHING` (una instalacion ya sembrada conserva lo que tiene), varias
// migraciones que se repiten en cada arranque los vuelven a escribir, y el
// nombre del grupo ("Configuracion") tambien es la LLAVE con la que Shell
// agrupa entradas fijas y entradas de la base.
//
// Por eso se acentua solo al MOSTRAR: la llave sigue intacta y una etiqueta que
// no este aqui -o que ya venga con acento- se muestra tal cual.

const GRUPOS = {
  Facturacion: "Facturación",
  Logistica: "Logística",
  Configuracion: "Configuración",
};

const ETIQUETAS = {
  "Categorias de documento": "Categorías de documento",
  "Ordenes de servicio": "Órdenes de servicio",
  "Tipos de ubicacion": "Tipos de ubicación",
  "Periodos de nomina": "Periodos de nómina",
  "Vales de almacen": "Vales de almacén",
  "Bitacora diaria de taller": "Bitácora diaria de taller",
  "Conexion al dispositivo Kronos": "Conexión al dispositivo Kronos",
  "Equipos y ordenes": "Equipos y órdenes",
};

/** Nombre de un grupo del menu, con acento, para mostrarlo. */
export function grupoParaMostrar(grupo) {
  return GRUPOS[grupo] ?? grupo;
}

/** Etiqueta de una entrada del menu, con acento, para mostrarla. */
export function etiquetaParaMostrar(etiqueta) {
  return ETIQUETAS[etiqueta] ?? etiqueta;
}

export const GRUPOS_ACENTUADOS = GRUPOS;
export const ETIQUETAS_ACENTUADAS = ETIQUETAS;
