// Adaptadores: de lo que devuelve la API (snapshots de /kpi_snapshot/query,
// filas de un KPI "vivo") a las props de los componentes de
// components/kpi-widgets/. Puros y sin React -- ver kpi.test.js.
//
// Regla de oro al moverlos desde Dashboard.jsx: un widget guardado antes de
// esta conexion (parametros con fechas absolutas, sin campos nuevos) tiene
// que producir exactamente los mismos datos que antes. Lo unico que cambia
// es QUIEN los pinta.
import {
  COLOR_OTHERS, CATEGORICAL, buildMultiSeriesData, buildPieData, buildSeriesData,
  colorDeCategoriaEstado, colorDePersona, colorEfectivoDeKpi, esKpiPorPersona, formatConUnidad, hayColoresRepetidos,
  kpiSeriesLabel, ordenarPorCategorias, unidadInfo,
} from "./kpiDatos.js";
import { anchoDelEje, ejeSoloEnteros, formatoDeEje, unidadDeLaGrafica } from "./kpiAccesibilidad.js";
import { etiquetasDePersonas } from "./kpiNombreCorto.js";

// Opacidad de la serie del periodo de comparacion (B): mismo color que la A,
// distinta opacidad -- no hay un segundo color fijo (ver colorDeKpi).
export const OPACIDAD_COMPARACION = 0.45;

/** `{ nombreCompleto: nombreCorto }` para el eje o la leyenda de una grafica POR PERSONA (null en cualquier otra dimension: productos,
 * estados y fechas no se acortan). Los datos conservan el nombre completo: solo cambia lo que se rotula. */
function etiquetasCortasDePersonas(nombres, esPorPersona) {
  return esPorPersona ? etiquetasDePersonas(nombres) : null;
}

/** Props de NumeroWidget para un widget "numero" de un solo KPI. */
export function propsNumero({ snapshot, kpiInfo, formatNumber, textos }) {
  const total = snapshot.rango_a.total;
  const hayComparacion = Boolean(snapshot?.rango_b);
  const totalB = snapshot.rango_b?.total;
  const delta = hayComparacion ? total - totalB : null;
  const deltaPct = hayComparacion && totalB ? (delta / Math.abs(totalB)) * 100 : null;
  const unidad = kpiInfo?.unidad;
  let variacionTexto = null;
  if (delta !== null) {
    const pct = deltaPct !== null && Number.isFinite(deltaPct)
      ? ` (${deltaPct >= 0 ? "+" : ""}${deltaPct.toFixed(1)}%)`
      : "";
    variacionTexto = `${formatConUnidad(formatNumber(Math.abs(delta)), unidad)}${pct}`;
  }
  return {
    valor: total,
    formatear: (valor) => formatConUnidad(formatNumber(valor), unidad),
    variacion: delta,
    variacionTexto,
    leyendaVariacion: textos.vsAnterior,
    textoSinVariacion: textos.sinComparacion,
    direccion: kpiInfo?.direccion || "neutral",
  };
}

/** "Artículos bajo stock": cuantos productos quedan por debajo del umbral. */
export function propsNumeroBajoStock({ snapshot, umbralBajoStock, textos }) {
  const porA = snapshot?.rango_a?.por_empleado || {};
  const cantidad = Object.values(porA).filter((valor) => valor < umbralBajoStock).length;
  return {
    valor: cantidad,
    variacion: null,
    textoSinVariacion: textos.bajoStock(umbralBajoStock),
    direccion: "neutral",
  };
}

/** Props de BarrasWidget / LineaAreaWidget (barras, linea, area).
 *
 * `tipo` decide solo el estilo de la serie de comparacion: barras la baja de
 * opacidad, linea/area la dibujan punteada.
 */
export function propsSeries({
  tipo, snapshots, kpiInfos, labelForId, empleados, agruparPorPeriodo,
  coloresOverride, umbralBajoStock, esBajoStock, formatNumber, textos,
}) {
  const hayComparacion = Boolean(snapshots[0]?.rango_b);
  const esBarras = tipo === "barras";
  const estiloB = esBarras ? { opacidad: OPACIDAD_COMPARACION } : { punteada: true, opacidad: 0.1 };

  if (kpiInfos.length <= 1) {
    const kpiInfo = kpiInfos[0];
    let datos = buildSeriesData(snapshots[0], labelForId, empleados, agruparPorPeriodo);
    if (esBajoStock) datos = datos.filter((fila) => fila.a < umbralBajoStock);
    // Un KPI de categorias ordinales declara su orden de lectura; por periodo las llaves son fechas.
    if (!agruparPorPeriodo) datos = ordenarPorCategorias(datos, kpiInfo?.orden_categorias);
    const colorKpi = colorEfectivoDeKpi(kpiInfo?.id_kpi_definition, coloresOverride);
    const formatear = (valor) => formatConUnidad(formatNumber(valor), kpiInfo?.unidad);
    const series = [{ clave: "a", nombre: textos.rangoA, color: colorKpi, formatear }];
    if (hayComparacion) series.push({ clave: "b", nombre: textos.rangoB, color: colorKpi, formatear, ...estiloB });
    // Dimension "estado" (catalogo fijo, ej. incidencias_abiertas_vs_cerradas):
    // cada categoria lleva SU color declarado (colores_categoria), no el
    // color unico del KPI para todas las barras.
    const coloresPorCategoria = kpiInfo?.dimensiones?.[0] === "estado" ? kpiInfo?.colores_categoria : null;
    // Dimension "persona": cada barra lleva el color de SU persona (`colorDePersona`), no el del KPI. Por periodo las
    // filas son fechas, no personas. Una linea o un area siguen con el color del KPI: una serie no tiene color por persona.
    const porPersona = esBarras && !agruparPorPeriodo && !coloresPorCategoria && esKpiPorPersona(kpiInfo);
    let colorPorFila = null;
    let conPatrones = false;
    if (esBarras && coloresPorCategoria) {
      colorPorFila = (fila) => colorDeCategoriaEstado(fila.id, coloresPorCategoria, colorKpi);
      conPatrones = true;
    } else if (porPersona) {
      colorPorFila = (fila) => colorDePersona(fila.id);
      // Dos personas con el mismo color en esta grafica: patron por barra, para que el color no sea la unica senal.
      conPatrones = hayColoresRepetidos(datos.map((fila) => colorDePersona(fila.id)));
    }
    const unidad = unidadDeLaGrafica([kpiInfo]);
    return {
      datos, series, campoEtiqueta: "name", colorPorFila, porPeriodo: Boolean(agruparPorPeriodo),
      etiquetasCortas: etiquetasCortasDePersonas(datos.map((fila) => fila.name), !agruparPorPeriodo && esKpiPorPersona(kpiInfo)),
      conPatrones, formatearEje: formatoDeEje(unidad, formatNumber), anchoEje: anchoDelEje(unidad), soloEnteros: ejeSoloEnteros(unidad),
    };
  }

  // Varios KPIs combinados: una serie por KPI, coloreada por identidad del
  // KPI y no por su posicion. El eje X sigue siendo por empleado. La serie de
  // comparacion de cada KPI reusa SU color -distingue por opacidad/trazo-
  // porque con N KPIs ya no hay solo dos roles (A/B) que colorear aparte.
  const datos = buildMultiSeriesData(snapshots, labelForId, empleados, agruparPorPeriodo);
  const sufijoComparacion = ` (${textos.comparacionCorta})`;
  const series = kpiInfos.map((info, indice) => ({
    clave: `kpi_${indice}_a`,
    nombre: kpiSeriesLabel(info, indice),
    color: colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride),
    formatear: formatNumber,
  }));
  if (hayComparacion) {
    kpiInfos.forEach((info, indice) => {
      series.push({
        clave: `kpi_${indice}_b`,
        nombre: `${kpiSeriesLabel(info, indice)}${sufijoComparacion}`,
        color: colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride),
        formatear: formatNumber,
        ...estiloB,
      });
    });
  }
  const unidadComun = unidadDeLaGrafica(kpiInfos);
  return {
    datos, series, campoEtiqueta: "name", colorPorFila: null, porPeriodo: Boolean(agruparPorPeriodo),
    etiquetasCortas: etiquetasCortasDePersonas(datos.map((fila) => fila.name), !agruparPorPeriodo && kpiInfos.every(esKpiPorPersona)),
    conPatrones: false, formatearEje: formatoDeEje(unidadComun, formatNumber), anchoEje: anchoDelEje(unidadComun), soloEnteros: ejeSoloEnteros(unidadComun),
  };
}

// Ancho util (px) del hueco de la dona (radio interior 50): el total tiene que caber dentro.
const ANCHO_DEL_HUECO_DE_DONA = 84;
const FUENTE_MAXIMA_DEL_TOTAL = 26;
const FUENTE_MINIMA_DEL_TOTAL = 11;

/** Tamano de letra (px) para que `texto` quepa en el hueco de la dona: el maximo para un numero corto y menos conforme
 * crece (cada caracter ocupa cerca de 0.62 de la letra). */
export function fuenteDelTotalDeDona(texto) {
  const largo = Math.max(1, String(texto ?? "").length);
  return Math.max(FUENTE_MINIMA_DEL_TOTAL, Math.min(FUENTE_MAXIMA_DEL_TOTAL, Math.floor(ANCHO_DEL_HUECO_DE_DONA / (0.62 * largo))));
}

/** El total al centro de la dona, o `null` cuando no tiene sentido. Solo si las rebanadas SUMAN un total: el KPI declara
 * `agregacion: "suma"` (un promedio, un porcentaje o una foto "ultimo" no se suman entre categorias). Incluye "Otros".
 * `texto` es el numero (con el prefijo de su unidad, "$1,200"), `detalle` lo que cuenta: el sufijo de la unidad
 * ("piezas", "min") y, para una cantidad sin unidad, "registros". `textos`: { registros, total }. */
export function totalCentroDeDona(datos, kpiInfo, formatNumber, textos = {}) {
  if (kpiInfo?.agregacion !== "suma" || kpiInfo?.unidad === "porcentaje") return null;
  const total = (datos || []).reduce((suma, entrada) => suma + (Number(entrada.valor) || 0), 0);
  if (!Number.isFinite(total)) return null;
  const { prefijo, sufijo } = unidadInfo(kpiInfo?.unidad);
  const detalle = sufijo.trim() || (prefijo ? (textos.total ?? "total") : (textos.registros ?? "registros"));
  const texto = `${prefijo}${formatNumber(total)}`;
  return { texto, detalle, fuente: fuenteDelTotalDeDona(texto) };
}

/** Props de DonaWidget. */
export function propsDona({ snapshot, kpiInfo, labelForId, agruparPorPeriodo, formatNumber, textos }) {
  const dimension = kpiInfo?.dimensiones?.[0];
  const crudas = buildPieData(snapshot, labelForId, textos.otros, agruparPorPeriodo, dimension, kpiInfo?.dimension_abierta);
  const rebanadas = agruparPorPeriodo ? crudas : ordenarPorCategorias(crudas, kpiInfo?.orden_categorias);
  const coloresCategoria = kpiInfo?.colores_categoria;
  // Dimension "persona": cada rebanada lleva el color de SU persona; "Otros" (id null) y "Sin asignar" en gris.
  const porPersona = !agruparPorPeriodo && !coloresCategoria && esKpiPorPersona(kpiInfo);
  const cortas = etiquetasCortasDePersonas(rebanadas.filter((entrada) => entrada.id !== null).map((entrada) => entrada.name), porPersona);
  const datos = rebanadas.map((entrada, indice) => {
    let color;
    if (coloresCategoria) color = colorDeCategoriaEstado(entrada.id, coloresCategoria, COLOR_OTHERS);
    else if (porPersona) color = colorDePersona(entrada.id);
    else color = indice < CATEGORICAL.length ? CATEGORICAL[indice] : COLOR_OTHERS;
    // `categoria` sigue siendo el nombre completo (tooltip, descripcion, clave); `etiqueta` (solo si es distinta) es lo que rotula la leyenda.
    const etiqueta = cortas?.[entrada.name];
    return { categoria: entrada.name, ...(etiqueta && etiqueta !== entrada.name ? { etiqueta } : {}), valor: entrada.value, color };
  });
  const conPatrones = Boolean(coloresCategoria) || (porPersona && hayColoresRepetidos(datos.map((entrada) => entrada.color)));
  return {
    datos, conPatrones, formatearValor: (valor) => formatConUnidad(formatNumber(valor), kpiInfo?.unidad),
    totalCentro: totalCentroDeDona(datos, kpiInfo, formatNumber, textos),
  };
}

/** Filas de TablaWidget a partir de los renglones del KPI "vivo". */
export function filasTablaPrestamo(items, textoSinAsignar) {
  return (items || []).map((fila) => ({
    id: fila.id_nm_incident_product,
    id_user: fila.id_user,
    articulo: fila.articulo,
    responsable: fila.responsable || textoSinAsignar,
    fecha_prestamo: fila.fecha_prestamo,
    dias_prestado: fila.dias_prestado,
  }));
}

/** Serie de valores (ordenada por fecha) para la mini-tendencia del numero. */
export function tendenciaDeSnapshot(resultado) {
  const porPeriodo = resultado?.rango_a?.por_periodo || {};
  return Object.entries(porPeriodo)
    .sort(([periodoA], [periodoB]) => (periodoA < periodoB ? -1 : periodoA > periodoB ? 1 : 0))
    .map(([, valor]) => valor);
}
