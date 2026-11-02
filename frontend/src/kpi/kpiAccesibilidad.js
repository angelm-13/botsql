// Lo que hace que una grafica no dependa SOLO del color: patrones por categoria, unidad en el eje y una descripcion
// para lectores de pantalla. Puro y sin React -- ver kpiAccesibilidad.test.js.
import { formatConUnidad, unidadInfo } from "./kpiDatos.js";

// Un patron por categoria, en el orden en que se leen (el color rojo/verde de `colores_categoria` ya no es lo unico
// que las distingue). Son los trazos que dibuja `components/kpi-widgets/PatronesSvg.jsx` y `patronesDeRelleno.jsx`.
export const PATRONES = ["diagonal", "puntos", "horizontal", "cruz", "diagonal_inversa", "vertical"];

export function patronDeIndice(indice) {
  return PATRONES[((indice % PATRONES.length) + PATRONES.length) % PATRONES.length];
}

// El relleno (`fill`) de la categoria `indice`: el patron `${idBase}-${indice}` que define `patronesDeRelleno`.
export function rellenoConPatron(idBase, indice) {
  return `url(#${idBase}-${indice})`;
}

// La unidad que comparten los KPIs de una grafica, o null si no hay una sola (varios KPIs con unidades distintas).
export function unidadDeLaGrafica(kpiInfos) {
  const unidades = new Set((kpiInfos || []).map((info) => info?.unidad || "numero"));
  return unidades.size === 1 ? [...unidades][0] : null;
}

// Formato de las marcas del eje Y con la unidad ("50%", "$1,200", "30 min"), o null cuando no hay unidad que mostrar
// ("numero", o varias unidades en un mismo eje).
export function formatoDeEje(unidad, formatNumber) {
  if (!unidad || unidad === "numero") return null;
  return (valor) => formatConUnidad(formatNumber(valor), unidad);
}

// Una unidad con sufijo largo (" piezas") pide mas ancho en el eje para no recortarse.
export function anchoDelEje(unidad) {
  const { prefijo, sufijo } = unidadInfo(unidad);
  return 60 + Math.max(0, `${prefijo}${sufijo}`.trim().length - 1) * 6;
}

// "Barras: Incidentes resueltos. 5 puntos de datos. Mayor: Ana (12)." -- lo que lee un lector de pantalla (y el
// tooltip del navegador) en lugar de una imagen sin nombre. `textos`: { tipo, puntos, mayor, sinDatos }.
export function descripcionDeGrafica({ nombres, datos, claveValor = "a", campoEtiqueta = "name", formatear, textos }) {
  const partes = [`${textos.tipo}: ${nombres}.`];
  const filas = Array.isArray(datos) ? datos : [];
  partes.push(`${filas.length} ${textos.puntos}.`);
  const conValor = filas.filter((fila) => Number.isFinite(Number(fila?.[claveValor])));
  if (conValor.length > 0) {
    const mayor = conValor.reduce((m, fila) => (Number(fila[claveValor]) > Number(m[claveValor]) ? fila : m));
    const valor = formatear ? formatear(mayor[claveValor]) : String(mayor[claveValor]);
    partes.push(`${textos.mayor}: ${mayor[campoEtiqueta]} (${valor}).`);
  }
  return partes.join(" ");
}
