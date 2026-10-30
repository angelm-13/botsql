// Cuantos recuadros punteados "Agregar gráfico" lleva la cuadricula del tablero. Aritmetica pura
// (ver kpiRelleno.test.js); components/kpi-widgets/useRellenoDelGrid.js le pasa las columnas reales.
//
// Cada recuadro mide lo mismo que una tarjeta chica de alto minimo (RELLENO_ALTO_PX, una columna) y
// entra en el masonry como una tarjeta mas, al final: cae en el primer hueco libre, o sea, debajo
// de las columnas mas cortas.

/** Alto de un recuadro de relleno (`min-height` de `.kpi-widget-placeholder`). */
export const RELLENO_ALTO_PX = 240;
/** Las tarjetas no bajan de esta cantidad de casillas: un tablero con una o dos se ve como invitacion
 * a llenarlo, no como un hueco. No es un tope: con mas tarjetas solo se completa la ultima fila. */
export const RELLENO_CASILLAS_MINIMAS = 6;
/** Un tablero vacio se llena con entre 2 y 4 filas de recuadros, segun lo que alcance a verse. */
export const RELLENO_FILAS_VACIO = { min: 2, max: 4 };

/** Cuantas filas de recuadros caben en `altoDisponiblePx` (con el hueco de 16 px entre ellas),
 * acotado a RELLENO_FILAS_VACIO. */
export function filasParaLlenar(altoDisponiblePx, hueco = 16) {
  const filas = Number.isFinite(altoDisponiblePx) ? Math.ceil((altoDisponiblePx + hueco) / (RELLENO_ALTO_PX + hueco)) : 0;
  return Math.min(RELLENO_FILAS_VACIO.max, Math.max(RELLENO_FILAS_VACIO.min, filas));
}

/** Cuantos recuadros de relleno hacen falta.
 *
 * - `cantidad`: tarjetas del tablero; `dobles`: cuantas ocupan 2 columnas (pesan 2 mientras haya al
 *   menos dos columnas).
 * - `columnas`: las del navegador ahora; `null` si todavia no se miden.
 * - Tablero vacio: `filasVisibles` filas completas (ver `filasParaLlenar`).
 * - Con tarjetas: lo que falta para que el total (tarjetas + recuadros) sea un multiplo de las
 *   columnas y no baje de RELLENO_CASILLAS_MINIMAS. */
export function casillasDeRelleno({ cantidad, dobles = 0, columnas = null, filasVisibles = RELLENO_FILAS_VACIO.min }) {
  if (columnas === null) return Math.max(0, RELLENO_CASILLAS_MINIMAS - cantidad);
  const pistas = Math.max(1, columnas);
  if (cantidad === 0) return pistas * Math.min(RELLENO_FILAS_VACIO.max, Math.max(RELLENO_FILAS_VACIO.min, filasVisibles));
  const peso = cantidad + (pistas >= 2 ? dobles : 0);
  const total = Math.ceil(Math.max(RELLENO_CASILLAS_MINIMAS, peso) / pistas) * pistas;
  return total - peso;
}
