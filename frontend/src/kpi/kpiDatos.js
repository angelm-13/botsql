// Logica pura del Dashboard de KPIs: sin React, sin iconos, sin red -- para
// poder probarla con `node --test` (ver kpi.test.js) y para que los
// componentes de components/kpi-widgets/ reciban datos ya armados.
//
// Todo lo de aqui se movio tal cual desde pages/Dashboard.jsx: mismo
// comportamiento, distinto lugar.

// Orden categorico validado (dataviz skill): identidad, nunca ciclado.
export const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
export const COLOR_OTHERS = "#898781";

// "NUMERO"/"MONEDA" crudos nunca se le muestran a nadie: sufijo para pegar
// al VALOR ya formateado (widgets) y etiqueta corta para el selector de KPI
// del editor -- vocabulario cerrado, igual que el que ya valida el backend
// (ver UNIDADES en app/kpis/registry.py). Una unidad que el backend agregue
// y este mapa todavia no conozca cae en el mismo trato que "numero" (sin
// sufijo, "Cantidad" como etiqueta) en vez de imprimir la palabra cruda.
export const UNIDAD_INFO = {
  numero: { etiquetaSelector: "Cantidad", prefijo: "", sufijo: "" },
  porcentaje: { etiquetaSelector: "%", prefijo: "", sufijo: "%" },
  moneda: { etiquetaSelector: "$", prefijo: "$", sufijo: "" },
  dias: { etiquetaSelector: "Días", prefijo: "", sufijo: " días" },
  piezas: { etiquetaSelector: "Piezas", prefijo: "", sufijo: " piezas" },
};

export function unidadInfo(unidad) {
  return UNIDAD_INFO[unidad] || UNIDAD_INFO.numero;
}

export function formatConUnidad(valorFormateado, unidad) {
  const info = unidadInfo(unidad);
  return `${info.prefijo}${valorFormateado}${info.sufijo}`;
}

// Primera letra en mayuscula -- "abierta"/"cerrada" (los dos unicos valores
// que hoy trae la dimension "estado" de incidencias_abiertas_vs_cerradas)
// llegan en minuscula desde el backend; las de material_por_estado
// ("Entrada", "Salida"...) ya vienen capitalizadas, asi que esto no les hace
// nada -- es seguro aplicarlo siempre sin distinguir de cual KPI viene.
export function capitalizar(valor) {
  const texto = String(valor || "");
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : texto;
}

// Color de una categoria de dimension "estado": si el KPI declaro
// colores_categoria (backend, ver app/kpis/registry.py) se usa ESE color
// fijo por nombre de categoria -- nunca la paleta CATEGORICAL generica por
// posicion, que es para dimensiones ABIERTAS (empleado/producto), no para un
// catalogo cerrado y conocido de antemano.
export function colorDeCategoriaEstado(nombreCategoria, coloresCategoria, colorRespaldo) {
  if (coloresCategoria && nombreCategoria in coloresCategoria) return coloresCategoria[nombreCategoria];
  return colorRespaldo;
}

// Color fijo por KPI (no por posicion en un arreglo): el modulo (`%`) sobre
// el id real es determinista y estable entre widgets/tableros -mismo KPI,
// mismo color, siempre- sin necesitar guardar un mapeo aparte.
export function colorDeKpi(idKpiDefinition) {
  const id = Number(idKpiDefinition);
  if (!Number.isFinite(id)) return COLOR_OTHERS;
  return CATEGORICAL[((id % CATEGORICAL.length) + CATEGORICAL.length) % CATEGORICAL.length];
}

// Color EFECTIVO de un KPI dentro de un widget ya guardado: el override manual
// (`parametros.colores_kpi`, `{ [id_kpi_definition]: '#hex' }`) gana sobre el
// determinista de `colorDeKpi` cuando existe. Las llaves de un objeto JSON
// siempre llegan como string -- de ahi el `String(id)` al leer.
export function colorEfectivoDeKpi(idKpiDefinition, coloresOverride) {
  const override = (coloresOverride || {})[String(idKpiDefinition)];
  return override || colorDeKpi(idKpiDefinition);
}

// Como etiquetar una entidad segun la dimension real del KPI (empleado,
// producto o "global" -- sin desglose).
export function labelForDimension(dimension, userLabel, productLabel) {
  if (dimension === "producto") return productLabel;
  if (dimension === "global") return () => "Total";
  // "estado": el id YA es el nombre legible de la categoria (ej. "abierta",
  // "Entrada") -- no hay a quien buscarle nombre, solo capitalizar. Sin este
  // caso caia en userLabel, que trataba "abierta" como un id_user y lo
  // mostraba como "#abierta" al no encontrar a nadie con ese id.
  if (dimension === "estado") return (valor) => capitalizar(valor);
  return userLabel;
}

// El nombre de campo del backend (`por_empleado`) es historico -- se
// conserva tal cual aunque ahora tambien puede traer productos (KPIs con
// dimension "producto") o quedar vacio (KPIs "globales", ej. ingresos/
// egresos totales, o cuando el widget pidio `agrupar_por=periodo`). Este
// helper decide de que campo leer segun el modo de agrupacion elegido en el
// widget, sin que cada `build*Data` tenga que repetir la logica.
export function entradasPorModo(ladoDelRango, agruparPorPeriodo) {
  return agruparPorPeriodo ? (ladoDelRango?.por_periodo || {}) : (ladoDelRango?.por_empleado || {});
}

export function buildSeriesData(snapshot, labelForId, entidadesFiltro, agruparPorPeriodo) {
  const porA = entradasPorModo(snapshot?.rango_a, agruparPorPeriodo);
  const porB = entradasPorModo(snapshot?.rango_b, agruparPorPeriodo);
  let ids = Array.from(new Set([...Object.keys(porA), ...Object.keys(porB)]));
  if (agruparPorPeriodo) {
    // Las llaves son fechas ISO (`AAAA-MM-DD`): ordenan bien como texto.
    ids.sort();
  } else if (Array.isArray(entidadesFiltro) && entidadesFiltro.length) {
    const orden = entidadesFiltro.map(String);
    ids = orden.filter((id) => ids.includes(id));
  } else {
    ids.sort((x, y) => (porA[y] ?? 0) - (porA[x] ?? 0));
  }
  return ids.map((id) => ({
    id,
    name: labelForId(id),
    a: porA[id] ?? 0,
    b: id in porB ? porB[id] : undefined,
  }));
}

// Un widget con varios KPIs hace una llamada a `/kpi_snapshot/query` POR CADA
// id (ver KpiWidgetCard) -- `snapshots[i]` corresponde a `kpiInfos[i]`. Cada
// fila resultante trae una columna `kpi_<indice>_a`/`kpi_<indice>_b` por KPI,
// para que Recharts pinte una serie por cada uno sin tocar el eje X (que
// sigue siendo por empleado, igual que con un solo KPI).
export function buildMultiSeriesData(snapshots, labelForId, entidadesFiltro, agruparPorPeriodo) {
  const ids = new Set();
  snapshots.forEach((snapshot) => {
    Object.keys(entradasPorModo(snapshot?.rango_a, agruparPorPeriodo)).forEach((id) => ids.add(id));
    Object.keys(entradasPorModo(snapshot?.rango_b, agruparPorPeriodo)).forEach((id) => ids.add(id));
  });
  let ordenados = Array.from(ids);
  if (agruparPorPeriodo) {
    ordenados.sort();
  } else if (Array.isArray(entidadesFiltro) && entidadesFiltro.length) {
    const orden = entidadesFiltro.map(String);
    ordenados = orden.filter((id) => ordenados.includes(id));
  } else {
    const totalPorId = (id) => snapshots.reduce(
      (suma, snapshot) => suma + (entradasPorModo(snapshot?.rango_a, agruparPorPeriodo)[id] ?? 0), 0,
    );
    ordenados.sort((x, y) => totalPorId(y) - totalPorId(x));
  }
  return ordenados.map((id) => {
    const fila = { name: labelForId(id) };
    snapshots.forEach((snapshot, index) => {
      const porA = entradasPorModo(snapshot?.rango_a, agruparPorPeriodo);
      const porB = entradasPorModo(snapshot?.rango_b, agruparPorPeriodo);
      fila[`kpi_${index}_a`] = porA[id] ?? 0;
      fila[`kpi_${index}_b`] = id in porB ? porB[id] : undefined;
    });
    return fila;
  });
}

// Nombre real del KPI (no "Periodo A/B" generico) con su unidad al lado --
// para que el tooltip/leyenda no confundan KPIs de distinta naturaleza (ej.
// moneda vs. porcentaje) combinados en la misma grafica.
export function kpiSeriesLabel(kpiInfo, index) {
  const etiqueta = kpiInfo?.etiqueta || `KPI #${index + 1}`;
  return kpiInfo?.unidad ? `${etiqueta} (${unidadInfo(kpiInfo.unidad).etiquetaSelector})` : etiqueta;
}

// "Otros" agrupa el sobrante SOLO en dimensiones ABIERTAS (empleado,
// producto: catalogos que pueden crecer sin limite). Una dimension "estado"
// es un catalogo CERRADO y conocido de antemano (5 categorias como mucho,
// ver material_por_estado) -- agruparla no tiene sentido y le escondería a
// alguien una categoria real detras de un "Otros" que nunca hacia falta.
export const DIMENSIONES_ABIERTAS = new Set(["empleado", "producto"]);

export function buildPieData(snapshot, labelForId, othersLabel, agruparPorPeriodo, dimension) {
  const porA = entradasPorModo(snapshot?.rango_a, agruparPorPeriodo);
  const entradas = agruparPorPeriodo
    ? Object.entries(porA).sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0))
    : Object.entries(porA).sort((x, y) => y[1] - x[1]);
  if (!DIMENSIONES_ABIERTAS.has(dimension)) {
    return entradas.map(([id, valor]) => ({ id, name: labelForId(id), value: valor }));
  }
  const principales = entradas.slice(0, CATEGORICAL.length);
  const restoTotal = entradas.slice(CATEGORICAL.length).reduce((suma, [, valor]) => suma + valor, 0);
  const data = principales.map(([id, valor]) => ({ id, name: labelForId(id), value: valor }));
  if (restoTotal > 0) data.push({ id: null, name: othersLabel, value: restoTotal });
  return data;
}
