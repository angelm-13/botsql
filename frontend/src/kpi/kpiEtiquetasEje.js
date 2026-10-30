// Como se dibuja una grafica de barras segun cuantas categorias trae. Puro y sin React -- ver kpiEtiquetasEje.test.js.
//
// - Una serie con 13 o mas categorias pasa a barras horizontales (tope de 20 filas).
// - Con mas de una serie (varios indicadores o comparacion) NO hay horizontal: queda vertical y se queda en 12 categorias.
// - Por periodo el eje es de tiempo, no de categorias: no se pasa a horizontal ni se recorta (se perderia parte del rango).
// - Las etiquetas largas se recortan con "..." (18 caracteres en vertical, 28 en horizontal); el nombre completo sigue en el tooltip.
export const MAX_CATEGORIAS_VERTICAL = 12;
export const MAX_CATEGORIAS_HORIZONTAL = 20;
export const RECORTE_VERTICAL = 18;
export const RECORTE_HORIZONTAL = 28;
export const ANGULO_ETIQUETA = -40;
// Ancho de la grafica mientras no se ha medido (primer pintado, o render en servidor): el de una tarjeta de dos columnas.
export const ANCHO_GRAFICA_POR_OMISION = 340;

const ANCHO_CARACTER = 6.2; // px a 11 px de fuente
const ALTO_FILA_HORIZONTAL = 24;
const ALTO_EJE_HORIZONTAL = 24;
const ALTO_AREA_VERTICAL = 192;
const ALTO_EJE_PLANO = 28;
const ALTO_FILA_LEYENDA = 24;
const SERIES_POR_FILA_DE_LEYENDA = 3;
const ANCHO_MAX_EJE_Y = 190;
const HOLGURA_ENTRE_ETIQUETAS = 6;
const MARGEN_DERECHO = 8;
const SENO = Math.sin((Math.abs(ANGULO_ETIQUETA) * Math.PI) / 180);
const COSENO = Math.cos((Math.abs(ANGULO_ETIQUETA) * Math.PI) / 180);

/** Recorta a `maximo` caracteres (contando el "..."), sin partir un caracter compuesto. */
export function recortarEtiqueta(texto, maximo) {
  const letras = Array.from(String(texto ?? "").trim());
  if (letras.length <= maximo) return letras.join("");
  return `${letras.slice(0, Math.max(1, maximo - 1)).join("").trimEnd()}…`;
}

/**
 * Decide modo, categorias visibles, alturas y margenes.
 * `etiquetas` son los rotulos ya en el orden en que se dibujan (los cortos, si los hay); `anchoEje` es el ancho del eje de valores y
 * `anchoGrafica` el ancho medido de la grafica: las etiquetas solo se inclinan cuando NO caben rectas en su banda.
 */
export function disenoDeBarras({
  etiquetas, cantidadSeries = 1, porPeriodo = false, anchoEje = 60, anchoGrafica = ANCHO_GRAFICA_POR_OMISION,
}) {
  const total = etiquetas.length;
  const horizontal = !porPeriodo && cantidadSeries <= 1 && total > MAX_CATEGORIAS_VERTICAL;
  let mostradas = total;
  if (horizontal) mostradas = Math.min(total, MAX_CATEGORIAS_HORIZONTAL);
  else if (!porPeriodo) mostradas = Math.min(total, MAX_CATEGORIAS_VERTICAL);

  const maxCaracteres = horizontal ? RECORTE_HORIZONTAL : RECORTE_VERTICAL;
  const largo = Math.max(0, ...etiquetas.slice(0, mostradas).map((nombre) => Array.from(recortarEtiqueta(nombre, maxCaracteres)).length));
  const base = { modo: horizontal ? "horizontal" : "vertical", total, mostradas, recortado: mostradas < total, maxCaracteres };

  if (horizontal) {
    return {
      ...base,
      alto: mostradas * ALTO_FILA_HORIZONTAL + ALTO_EJE_HORIZONTAL,
      anchoEjeCategorias: Math.min(ANCHO_MAX_EJE_Y, Math.ceil(largo * ANCHO_CARACTER) + 12),
    };
  }

  // El area de barras empieza donde termina el eje de valores (el margen izquierdo base es -16) y deja un margen a la derecha.
  const banda = (anchoGrafica - anchoEje + 16 - MARGEN_DERECHO) / Math.max(1, mostradas);
  const inclinar = mostradas > 1 && largo * ANCHO_CARACTER + HOLGURA_ENTRE_ETIQUETAS > banda;
  const altoEjeX = inclinar ? Math.ceil(largo * ANCHO_CARACTER * SENO) + 12 : ALTO_EJE_PLANO;
  const filasDeLeyenda = cantidadSeries > 1 ? Math.ceil(cantidadSeries / SERIES_POR_FILA_DE_LEYENDA) : 0;
  // La etiqueta inclinada termina en el tick y se extiende hacia la izquierda: si el eje de valores no le da ese
  // espacio, el margen izquierdo crece lo que falta (hoy -16 para que el eje quede pegado al borde).
  const sobreSaliente = inclinar ? Math.ceil(largo * ANCHO_CARACTER * COSENO) : 0;
  return {
    ...base,
    inclinar,
    // Por periodo el eje es de fechas: Recharts decide cuales rotular; en categorias se rotulan todas.
    todasLasEtiquetas: !porPeriodo,
    altoEjeX,
    alto: ALTO_AREA_VERTICAL + altoEjeX + filasDeLeyenda * ALTO_FILA_LEYENDA,
    margenIzquierdo: -16 + Math.max(0, sobreSaliente - anchoEje),
  };
}
