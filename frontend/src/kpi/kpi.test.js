// Pruebas de la logica pura del Dashboard de KPIs. Se corren con
// `npm test` (node --test): sin dependencias nuevas, sin navegador.
//
// Los widgets "viejos" de aqui son los que ya existen guardados en
// tyakxa-dev: parametros con fechas ABSOLUTAS y ninguno de los campos que se
// fueron agregando despues (rango_relativo, etc.). Lo que se prueba es que
// pasar por los adaptadores nuevos produce exactamente los datos que el
// Dashboard pintaba antes de conectar los componentes de kpi-widgets/.
import test from "node:test";
import assert from "node:assert/strict";
import {
  CATEGORICAL, COLOR_OTHERS, buildMultiSeriesData, buildPieData, buildSeriesData,
  colorDeKpi, colorEfectivoDeKpi, formatConUnidad, labelForDimension,
} from "./kpiDatos.js";
import { armarParametros, widgetDeBorrador } from "./kpiParametros.js";
import {
  filasTablaPrestamo, propsDona, propsNumero, propsNumeroBajoStock, propsSeries,
  tendenciaDeSnapshot,
} from "./kpiAdaptadores.js";

const formatNumber = (valor) => new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(valor || 0);
const userLabel = (id) => ({ 5: "Ana", 7: "Beto", 9: "Carla" }[id] || `#${id}`);
const TEXTOS_SERIES = { rangoA: "Periodo A", rangoB: "Periodo B", comparacionCorta: "comparación" };

// --- fixtures de widgets viejos -------------------------------------------
const KPI_INCIDENTES = { id_kpi_definition: 3, etiqueta: "Incidentes resueltos", clave: "incidentes_resueltos_por_empleado", unidad: "numero", dimensiones: ["empleado"], direccion: "alto_es_mejor", modulo: "operaciones" };
const KPI_INGRESOS = { id_kpi_definition: 4, etiqueta: "Ingresos", clave: "ingresos_totales", unidad: "moneda", dimensiones: ["global"], direccion: "alto_es_mejor", modulo: "facturacion" };
const KPI_ESTADO = {
  id_kpi_definition: 8, clave: "incidencias_abiertas_vs_cerradas", unidad: "numero", dimensiones: ["estado"],
  colores_categoria: { abierta: "#ef6f5c", cerrada: "#22b573" }, modulo: "operaciones",
};
const WIDGET_VIEJO_BARRAS = {
  tipo_grafica: "barras", ids_kpi_definition: [3],
  parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" },
};
const SNAPSHOT_SIMPLE = { rango_a: { total: 14, por_empleado: { 5: 10, 7: 4 } }, rango_b: null };
const SNAPSHOT_COMPARADO = {
  rango_a: { total: 14, por_empleado: { 5: 10, 7: 4 } },
  rango_b: { total: 20, por_empleado: { 5: 8, 9: 12 } },
};

test("widget viejo de barras (un KPI, fechas absolutas): mismos datos que antes", () => {
  const props = propsSeries({
    tipo: WIDGET_VIEJO_BARRAS.tipo_grafica, snapshots: [SNAPSHOT_SIMPLE], kpiInfos: [KPI_INCIDENTES],
    labelForId: userLabel, empleados: undefined, agruparPorPeriodo: false,
    coloresOverride: undefined, formatNumber, textos: TEXTOS_SERIES,
  });
  // Lo mismo que devolvia buildSeriesData directo, fila por fila.
  assert.deepEqual(props.datos, [
    { id: "5", name: "Ana", a: 10, b: undefined },
    { id: "7", name: "Beto", a: 4, b: undefined },
  ]);
  assert.equal(props.campoEtiqueta, "name");
  assert.equal(props.series.length, 1);
  assert.equal(props.series[0].clave, "a");
  assert.equal(props.series[0].color, colorDeKpi(3));
  assert.equal(props.colorPorFila, null);
});

test("barras con comparacion: serie B con el MISMO color y menos opacidad", () => {
  const props = propsSeries({
    tipo: "barras", snapshots: [SNAPSHOT_COMPARADO], kpiInfos: [KPI_INCIDENTES],
    labelForId: userLabel, empleados: undefined, agruparPorPeriodo: false, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.series.map((s) => s.clave), ["a", "b"]);
  assert.equal(props.series[1].color, props.series[0].color);
  assert.equal(props.series[1].opacidad, 0.45);
  // Ordenado por el valor del periodo A, y las filas que solo existen en B entran con a = 0.
  assert.deepEqual(props.datos.map((f) => [f.name, f.a, f.b]), [["Ana", 10, 8], ["Beto", 4, undefined], ["Carla", 0, 12]]);
});

test("linea/area con comparacion: la serie B va punteada, no en otro color", () => {
  const props = propsSeries({
    tipo: "linea", snapshots: [SNAPSHOT_COMPARADO], kpiInfos: [KPI_INCIDENTES],
    labelForId: userLabel, empleados: undefined, agruparPorPeriodo: false, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.equal(props.series[1].punteada, true);
  assert.equal(props.series[1].color, props.series[0].color);
});

test("varios KPIs combinados: una serie por KPI, color por identidad, sufijo de comparacion", () => {
  const snapshotB = { rango_a: { total: 5, por_empleado: { 5: 3, 7: 2 } }, rango_b: { total: 1, por_empleado: { 5: 1 } } };
  const props = propsSeries({
    tipo: "barras", snapshots: [SNAPSHOT_COMPARADO, snapshotB], kpiInfos: [KPI_INCIDENTES, KPI_INGRESOS],
    labelForId: userLabel, empleados: undefined, agruparPorPeriodo: false,
    coloresOverride: { 4: "#123456" }, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.series.map((s) => s.clave), ["kpi_0_a", "kpi_1_a", "kpi_0_b", "kpi_1_b"]);
  assert.equal(props.series[0].color, colorDeKpi(3));
  assert.equal(props.series[1].color, "#123456"); // el override manual gana
  assert.equal(props.series[2].nombre, "Incidentes resueltos (Cantidad) (comparación)");
  assert.equal(props.series[3].nombre, "Ingresos ($) (comparación)");
  assert.deepEqual(props.datos, buildMultiSeriesData([SNAPSHOT_COMPARADO, snapshotB], userLabel, undefined, false));
});

test("KPI de categorias fijas (estado): cada barra con SU color declarado", () => {
  const snapshot = { rango_a: { total: 7, por_empleado: { abierta: 5, cerrada: 2 } }, rango_b: null };
  const props = propsSeries({
    tipo: "barras", snapshots: [snapshot], kpiInfos: [KPI_ESTADO],
    labelForId: labelForDimension("estado", userLabel, userLabel), empleados: undefined,
    agruparPorPeriodo: false, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.datos.map((f) => f.name), ["Abierta", "Cerrada"]);
  assert.deepEqual(props.datos.map((f) => props.colorPorFila(f)), ["#ef6f5c", "#22b573"]);
});

test("artículos bajo stock: solo quedan los que estan por debajo del umbral", () => {
  const kpi = { id_kpi_definition: 1, clave: "articulos_bajo_stock", unidad: "piezas", dimensiones: ["producto"] };
  const snapshot = { rango_a: { total: 0, por_empleado: { 10: 2, 11: 50, 12: 9 } }, rango_b: null };
  const props = propsSeries({
    tipo: "barras", snapshots: [snapshot], kpiInfos: [kpi], labelForId: (id) => `P${id}`,
    agruparPorPeriodo: false, umbralBajoStock: 10, esBajoStock: true, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.datos.map((f) => f.id), ["12", "10"]);
  const numero = propsNumeroBajoStock({ snapshot, umbralBajoStock: 10, textos: { bajoStock: (u) => `bajo ${u}` } });
  assert.equal(numero.valor, 2);
  assert.equal(numero.textoSinVariacion, "bajo 10");
});

test("agrupar por periodo: el eje X son las fechas, ordenadas", () => {
  const snapshot = { rango_a: { total: 3, por_periodo: { "2026-08-03": 1, "2026-08-01": 2 } }, rango_b: null };
  const props = propsSeries({
    tipo: "linea", snapshots: [snapshot], kpiInfos: [KPI_INCIDENTES], labelForId: (id) => id,
    agruparPorPeriodo: true, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.datos.map((f) => f.name), ["2026-08-01", "2026-08-03"]);
  assert.deepEqual(tendenciaDeSnapshot(snapshot), [2, 1]);
});

test("numero sin comparacion: valor con unidad y sin variacion", () => {
  const snapshot = { rango_a: { total: 1234.5, por_empleado: {} }, rango_b: null };
  const props = propsNumero({ snapshot, kpiInfo: KPI_INGRESOS, formatNumber, textos: { vsAnterior: "vs. anterior", sinComparacion: "Activa Comparar" } });
  assert.equal(props.valor, 1234.5);
  assert.equal(props.formatear(1234.5), "$1,234.5");
  assert.equal(props.variacion, null);
  assert.equal(props.variacionTexto, null);
  assert.equal(props.textoSinVariacion, "Activa Comparar");
});

test("numero con comparacion: delta, porcentaje y direccion del KPI", () => {
  const snapshot = { rango_a: { total: 150, por_empleado: {} }, rango_b: { total: 100, por_empleado: {} } };
  const props = propsNumero({ snapshot, kpiInfo: KPI_INGRESOS, formatNumber, textos: { vsAnterior: "vs. anterior", sinComparacion: "x" } });
  assert.equal(props.variacion, 50);
  assert.equal(props.variacionTexto, "$50 (+50.0%)");
  assert.equal(props.direccion, "alto_es_mejor");
  // Base en cero: hay delta pero no porcentaje (no se divide entre 0).
  const desdeCero = propsNumero({ snapshot: { rango_a: { total: 5 }, rango_b: { total: 0 } }, kpiInfo: KPI_INGRESOS, formatNumber, textos: { vsAnterior: "", sinComparacion: "" } });
  assert.equal(desdeCero.variacionTexto, "$5");
});

test("dona: categorias fijas con su color, abiertas con la paleta y 'Otros' al final", () => {
  const estado = propsDona({
    snapshot: { rango_a: { total: 7, por_empleado: { abierta: 5, cerrada: 2 } } },
    kpiInfo: KPI_ESTADO, labelForId: labelForDimension("estado", userLabel, userLabel),
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.deepEqual(estado.datos, [
    { categoria: "Abierta", valor: 5, color: "#ef6f5c" },
    { categoria: "Cerrada", valor: 2, color: "#22b573" },
  ]);
  const muchos = {};
  for (let i = 1; i <= CATEGORICAL.length + 2; i += 1) muchos[i] = 100 - i;
  const abierta = propsDona({
    snapshot: { rango_a: { total: 0, por_empleado: muchos } }, kpiInfo: KPI_INCIDENTES,
    labelForId: (id) => `E${id}`, agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.equal(abierta.datos.length, CATEGORICAL.length + 1);
  assert.deepEqual(abierta.datos.at(-1), { categoria: "Otros", valor: (100 - 9) + (100 - 10), color: COLOR_OTHERS });
  assert.equal(abierta.datos[0].color, CATEGORICAL[0]);
});

test("tabla de material prestado: id, responsable por omision y columnas", () => {
  const filas = filasTablaPrestamo([
    { id_nm_incident_product: 11, articulo: "Taladro", responsable: null, fecha_prestamo: "2026-08-01", dias_prestado: 30 },
    { id_nm_incident_product: 12, articulo: "Sierra", responsable: "Ana", fecha_prestamo: "2026-09-20", dias_prestado: 9 },
  ], "Sin asignar");
  assert.deepEqual(filas, [
    { id: 11, articulo: "Taladro", responsable: "Sin asignar", fecha_prestamo: "2026-08-01", dias_prestado: 30 },
    { id: 12, articulo: "Sierra", responsable: "Ana", fecha_prestamo: "2026-09-20", dias_prestado: 9 },
  ]);
  assert.deepEqual(filasTablaPrestamo(undefined, "x"), []);
});

test("funciones de datos: el mismo KPI siempre el mismo color, unidades sin palabra cruda", () => {
  assert.equal(colorDeKpi(3), colorDeKpi(3 + CATEGORICAL.length));
  assert.equal(colorDeKpi("no-es-un-id"), COLOR_OTHERS);
  assert.equal(colorEfectivoDeKpi(3, { 3: "#abcdef" }), "#abcdef");
  assert.equal(colorEfectivoDeKpi("3", { 3: "#abcdef" }), "#abcdef");
  assert.equal(formatConUnidad("12", "piezas"), "12 piezas");
  assert.equal(formatConUnidad("12", "porcentaje"), "12%");
  assert.equal(formatConUnidad("12", "unidad-desconocida"), "12");
  assert.deepEqual(buildPieData({ rango_a: { por_empleado: { a: 1 } } }, (x) => x, "Otros", false, "estado"), [{ id: "a", name: "a", value: 1 }]);
  assert.deepEqual(buildSeriesData({ rango_a: { por_empleado: { 1: 1, 2: 2 } } }, (x) => x, ["2", "1"], false).map((f) => f.id), ["2", "1"]);
});

// --- parametros del borrador del editor -------------------------------------
const BORRADOR = {
  tipoGrafica: "barras", idsKpiSeleccionados: ["3", "4"],
  fechaInicio: "2026-08-01", fechaFin: "2026-08-31",
  comparar: true, fechaInicioB: "2026-07-01", fechaFinB: "2026-07-31",
  empleadosSeleccionados: ["5", "7"], departamentosSeleccionados: ["2"],
  coloresKpi: { 3: "#111111", 99: "#222222" }, agruparPor: "periodo", umbralBajoStock: "12",
};

test("armarParametros: lo mismo que guardaba el editor antes (numeros, colores vigentes, umbral)", () => {
  assert.deepEqual(armarParametros(BORRADOR, { tieneBajoStock: true }), {
    fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31",
    fecha_inicio_b: "2026-07-01", fecha_fin_b: "2026-07-31",
    empleados: [5, 7], id_departments: [2],
    colores_kpi: { 3: "#111111" }, // el 99 ya no esta seleccionado: no se guarda huerfano
    agrupar_por: "periodo", umbral_bajo_stock: 12,
  });
  // Sin bajo stock el umbral no se guarda; sin comparar no hay rango B.
  const simple = armarParametros({ ...BORRADOR, comparar: false, agruparPor: "entidad", empleadosSeleccionados: [], departamentosSeleccionados: [], coloresKpi: {} }, {});
  assert.deepEqual(simple, { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" });
});

test("armarParametros: una tabla (KPI vivo) no guarda periodo ni filtros", () => {
  assert.deepEqual(armarParametros(BORRADOR, { esTabla: true }), {});
  const widget = widgetDeBorrador({ ...BORRADOR, tipoGrafica: "tabla", idsKpiSeleccionados: ["11"] }, { esTabla: true });
  assert.deepEqual(widget, { tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: {} });
});
