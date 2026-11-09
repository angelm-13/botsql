// Adaptadores: de lo que devuelve la API (snapshots de /kpi_snapshot/query,
// filas de un KPI "vivo") a las props de los componentes de
// components/kpi-widgets/. Puros y sin React -- ver kpi.test.js.
//
// Regla de oro al moverlos desde Dashboard.jsx: un widget guardado antes de
// esta conexion (parametros con fechas absolutas, sin campos nuevos) tiene
// que producir exactamente los mismos datos que antes. Lo unico que cambia
// es QUIEN los pinta.
import {
  COLOR_OTHERS, CATEGORICAL, DIMENSIONES_ABIERTAS, buildMultiSeriesData, buildPieData, buildSeriesData, entradasPorModo,
  colorDeCategoriaEstado, colorDePersona, colorEfectivoDeKpi, esKpiPorPersona, esUnidadDeConteo, formatConUnidad,
  kpiSeriesLabel, ordenarPorCategorias, unidadInfo, valoresNoSumables,
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
export function propsNumero({ snapshot, kpiInfo, formatNumber, textos, etiquetaRangoB = "", comparacionActiva = false }) {
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
    // La leyenda dice CONTRA QUE FECHAS se compara ("vs. 6 sep – 5 oct"); solo sin fechas conocidas cae en el texto generico.
    leyendaVariacion: etiquetaRangoB && textos.vsRango ? textos.vsRango(etiquetaRangoB) : textos.vsAnterior,
    // Se pidio comparar pero la respuesta no trae el periodo B: no se promete una variacion que no hay, ni se pide "Activa Comparar".
    textoSinVariacion: comparacionActiva && !hayComparacion && textos.comparacionNoDisponible
      ? textos.comparacionNoDisponible(etiquetaRangoB)
      : textos.sinComparacion,
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
 *
 * `relleno` ("solido" por omision, o "textura"): lo elige el usuario por widget. Las texturas (`conPatrones`) salen SOLO con "textura"
 * y en barras por categoria; ya no dependen de que el KPI tenga colores fijos ni de que haya colores repetidos.
 */
export function propsSeries({
  tipo, snapshots, kpiInfos, labelForId, empleados, agruparPorPeriodo,
  coloresOverride, umbralBajoStock, esBajoStock, formatNumber, textos, relleno = "solido",
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
    // Con textura cada barra lleva un patron sobre su color; por periodo las filas son fechas, no categorias: no aplica.
    const textura = esBarras && relleno === "textura" && !agruparPorPeriodo;
    let conPatrones = false;
    if (esBarras && coloresPorCategoria) {
      colorPorFila = (fila) => colorDeCategoriaEstado(fila.id, coloresPorCategoria, colorKpi);
      conPatrones = textura;
    } else if (porPersona) {
      colorPorFila = (fila) => colorDePersona(fila.id);
      conPatrones = textura;
    } else if (textura) {
      // Una dimension sin color por categoria (producto, familia...): las barras llevan el color del KPI, ahora con textura.
      colorPorFila = () => colorKpi;
      conPatrones = true;
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

/** Si las rebanadas de una dona SUMAN un total con sentido. Dos casos:
 * - el KPI declara `agregacion: "suma"` (flujos: tareas creadas, ventas...), salvo un porcentaje;
 * - una foto de HOY (`agregacion: "ultimo"`) por ESTADO y en unidades de conteo: los estados son excluyentes (cada tarea o proyecto
 *   esta en uno solo), asi que sumarlos es el total de la foto ("24 tareas"). Una foto por equipo, persona o producto no: una persona en
 *   dos equipos contaria dos veces.
 * Un promedio o un porcentaje (`promedio_ponderado`) no se suma jamas: 4 personas al 83 % no son un 333 %. */
export function sumaConSentido(kpiInfo) {
  if (!kpiInfo || kpiInfo.unidad === "porcentaje") return false;
  if (kpiInfo.agregacion === "suma") return true;
  return kpiInfo.agregacion === "ultimo" && kpiInfo.dimensiones?.[0] === "estado" && esUnidadDeConteo(kpiInfo.unidad);
}

/** El total al centro de la dona, o `null` cuando no tiene sentido (`sumaConSentido`). Incluye "Otros".
 * `texto` es el numero (con el prefijo de su unidad, "$1,200"), `detalle` lo que cuenta: el sufijo de la unidad
 * ("piezas", "min") y, para una cantidad sin unidad, "registros". `textos`: { registros, total }. */
export function totalCentroDeDona(datos, kpiInfo, formatNumber, textos = {}) {
  if (!sumaConSentido(kpiInfo)) return null;
  const total = (datos || []).reduce((suma, entrada) => suma + (Number(entrada.valor) || 0), 0);
  if (!Number.isFinite(total)) return null;
  const { prefijo, sufijo } = unidadInfo(kpiInfo?.unidad);
  const detalle = sufijo.trim() || (prefijo ? (textos.total ?? "total") : (textos.registros ?? "registros"));
  const texto = `${prefijo}${formatNumber(total)}`;
  return { texto, detalle, fuente: fuenteDelTotalDeDona(texto) };
}

/** Props de DonaWidget. */
export function propsDona({ snapshot, kpiInfo, labelForId, agruparPorPeriodo, formatNumber, textos, relleno = "solido" }) {
  const dimension = kpiInfo?.dimensiones?.[0];
  const noSumable = valoresNoSumables(kpiInfo);
  const crudas = buildPieData(snapshot, labelForId, textos.otros, agruparPorPeriodo, dimension, kpiInfo?.dimension_abierta, noSumable);
  // Un KPI que no se suma no agrupa el sobrante en "Otros": si hay mas rebanadas de las que caben, se dice cuantas se muestran.
  const totalDeRebanadas = Object.keys(entradasPorModo(snapshot?.rango_a, agruparPorPeriodo)).length;
  const recorte = noSumable && (kpiInfo?.dimension_abierta ?? DIMENSIONES_ABIERTAS.has(dimension)) && totalDeRebanadas > crudas.length
    ? { mostradas: crudas.length, total: totalDeRebanadas }
    : null;
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
  // Las texturas salen solo si el usuario las eligio (`relleno`), en cualquier dona por categorias.
  const conPatrones = relleno === "textura" && datos.length > 0;
  return {
    datos, conPatrones, recorte, formatearValor: (valor) => formatConUnidad(formatNumber(valor), kpiInfo?.unidad),
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
