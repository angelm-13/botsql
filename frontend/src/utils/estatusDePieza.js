// El estatus de una pieza tal como lo guarda `product.product_status`, y el
// color con el que se pinta.
//
// Son los textos del sistema anterior -ENTRADA, SALIDA, DAÑADO, EQ. DAÑADOS,
// DESTRUCCION, EXTRAVIADO- mas los que escribe el vale de almacen (EN
// REPARACION). No todos tienen fila en el catalogo `inventory_status`:
// ENTRADA y SALIDA son direccion de movimiento, no estado de la pieza, y a
// proposito no la tienen (20260929120000). Por eso el color no puede depender
// solo del catalogo, y esta es la paleta de respaldo.
//
// El color va por GRAVEDAD, con los mismos cinco tonos que ya usan Inventario y
// Localizar (`TONO_DE_ESTATUS` en `InventoryPage.jsx` / `InventoryTracePage.jsx`),
// para que una pieza se vea igual en las tres pantallas:
//
//   verde  ENTRADA                    esta en el almacen
//   azul   SALIDA, RENTA              fuera, sin problema
//   ambar  DAÑADO, EQ. DAÑADOS,       hay que atenderlo
//          EN REPARACION
//   rojo   EXTRAVIADO                 se perdio
//   gris   DESTRUCCION                fin de vida
export const COLOR_POR_TONO = {
  ok: "#16a34a",
  info: "#2563eb",
  warn: "#d97706",
  crit: "#dc2626",
  muted: "#94a3b8",
};

const TONO_DE_ESTATUS = {
  ENTRADA: "ok",
  SALIDA: "info",
  RENTA: "info",
  DANADO: "warn",
  "EQ. DANADOS": "warn",
  REPARACION: "warn",
  "EN REPARACION": "warn",
  EXTRAVIADO: "crit",
  DESTRUCCION: "muted",
};

// Sin acentos y en mayusculas: en los datos conviven "DAÑADO" y "DANADO".
export function normalizarEstatus(valor) {
  return String(valor || "")
    .toUpperCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();
}

/** El tono (`ok`, `info`, `warn`, `crit`, `muted`) de un estatus, o "" si no se conoce. */
export function tonoDeEstatus(valor) {
  return TONO_DE_ESTATUS[normalizarEstatus(valor)] || "";
}

/** El color hexadecimal de un estatus, o "" si no se conoce. */
export function colorDeEstatus(valor) {
  return COLOR_POR_TONO[tonoDeEstatus(valor)] || "";
}
