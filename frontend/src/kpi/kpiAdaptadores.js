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
  colorDeCategoriaEstado, colorEfectivoDeKpi, formatConUnidad, kpiSeriesLabel,
} from "./kpiDatos.js";

// Dias desde los que un prestamo se considera atrasado (mismo umbral que
// tenia TablaMaterialPrestado en Dashboard.jsx).
export const UMBRAL_ATRASO_PRESTAMO_DIAS = 14;

// Opacidad de la serie del periodo de comparacion (B): mismo color que la A,
// distinta opacidad -- no hay un segundo color fijo (ver colorDeKpi).
export const OPACIDAD_COMPARACION = 0.45;

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
    const colorKpi = colorEfectivoDeKpi(kpiInfo?.id_kpi_definition, coloresOverride);
    const formatear = (valor) => formatConUnidad(formatNumber(valor), kpiInfo?.unidad);
    const series = [{ clave: "a", nombre: textos.rangoA, color: colorKpi, formatear }];
    if (hayComparacion) series.push({ clave: "b", nombre: textos.rangoB, color: colorKpi, formatear, ...estiloB });
    // Dimension "estado" (catalogo fijo, ej. incidencias_abiertas_vs_cerradas):
    // cada categoria lleva SU color declarado (colores_categoria), no el
    // color unico del KPI para todas las barras.
    const coloresPorCategoria = kpiInfo?.dimensiones?.[0] === "estado" ? kpiInfo?.colores_categoria : null;
    const colorPorFila = esBarras && coloresPorCategoria
      ? (fila) => colorDeCategoriaEstado(fila.id, coloresPorCategoria, colorKpi)
      : null;
    return { datos, series, campoEtiqueta: "name", colorPorFila };
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
  return { datos, series, campoEtiqueta: "name", colorPorFila: null };
}

/** Props de DonaWidget. */
export function propsDona({ snapshot, kpiInfo, labelForId, agruparPorPeriodo, formatNumber, textos }) {
  const dimension = kpiInfo?.dimensiones?.[0];
  const rebanadas = buildPieData(snapshot, labelForId, textos.otros, agruparPorPeriodo, dimension);
  const coloresCategoria = kpiInfo?.colores_categoria;
  const datos = rebanadas.map((entrada, indice) => ({
    categoria: entrada.name,
    valor: entrada.value,
    color: coloresCategoria
      ? colorDeCategoriaEstado(entrada.id, coloresCategoria, COLOR_OTHERS)
      : (indice < CATEGORICAL.length ? CATEGORICAL[indice] : COLOR_OTHERS),
  }));
  return { datos, formatearValor: (valor) => formatConUnidad(formatNumber(valor), kpiInfo?.unidad) };
}

/** Filas de TablaWidget a partir de los renglones del KPI "vivo". */
export function filasTablaPrestamo(items, textoSinAsignar) {
  return (items || []).map((fila) => ({
    id: fila.id_nm_incident_product,
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
