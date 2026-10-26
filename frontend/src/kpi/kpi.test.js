// Pruebas de la logica pura del Dashboard de KPIs. Se corren con
// `npm test` (node --test): sin dependencias nuevas, sin navegador.
//
// Los widgets "viejos" de aqui son los que ya existen guardados en
// tyakxa-dev: parametros con fechas ABSOLUTAS y ninguno de los campos que se
// fueron agregando despues (rango_relativo, etc.). Lo que se prueba es que
// pasar por los adaptadores nuevos produce exactamente los datos que el
// Dashboard pintaba antes de conectar los componentes de kpi-widgets/.
import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import {
  CATEGORICAL, COLOR_OTHERS, buildMultiSeriesData, etiquetasDeDimension, buildPieData, buildSeriesData,
  colorDeKpi, colorEfectivoDeKpi, etiquetasDeSnapshots, formatConUnidad, labelForDimension, ordenarPorCategorias,
} from "./kpiDatos.js";
import {
  agruparPorResponsable, duracionLegible, etiquetaDeDias, filtrarPorResponsable, gravedadDeDias, ordenarFilas,
  anchoDeBarra, buscarEnFilas, escalaDeBarras, filtrarPorUsuario, recortar, recortarGrupos, resumenDePrestamos, responsablesDe,
  ORDEN_POR_OMISION, normalizarOrdenTabla,
} from "./kpiPrestamos.js";
import {
  agruparKpis, claveDeGrupo, colorDeModulo, COLOR_DE_MODULO, estadoDeOpcion, esVariable, grupoInicial, resumenDeModulos,
} from "./kpiSelector.js";
import {
  armarParametros, columnasDeWidget, estadoDeWidget, filasDeWidget, mezclaUnidades, motivoParaNoCombinar, rangoInicialDelBorrador,
  tiposDeGraficaPermitidos, unidadDeKpi, widgetDeBorrador,
} from "./kpiParametros.js";
import {
  fechaLocalIso, parametrosEfectivos, periodoAnterior, rangoDesfasado, resolverRangoRelativo,
} from "./kpiRango.js";
import { colorDeAvatar } from "../components/kpi-widgets/avatar.js";
import { datosDeEjemplo, rangoVacio } from "./datosDeEjemplo.js";
import { filasQueOcupa } from "../components/kpi-widgets/useMasonry.js";
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

test("estado: usa el nombre que manda el backend (etiquetas) y, sin el, la clave capitalizada", () => {
  const etiquetas = { por_liberar: "Pagada, aún ocupada" };
  const conNombre = labelForDimension("estado", userLabel, userLabel, etiquetas);
  assert.equal(conNombre("por_liberar"), "Pagada, aún ocupada");
  assert.equal(conNombre("libre"), "Libre");
  assert.equal(labelForDimension("estado", userLabel, userLabel)("abierta"), "Abierta");
});

// --- datos de ejemplo («Ver ejemplo» de un KPI permitido sin datos) ---

const HOY_EJEMPLO = new Date(2026, 9, 13);
const KPI_EJEMPLO_GLOBAL = { clave: "ventas_restaurante", unidad: "moneda", dimensiones: ["global"], direccion: "alto_es_mejor" };
const KPI_EJEMPLO_ESTADO = {
  clave: "mesas_ocupadas", unidad: "numero", dimensiones: ["estado"], dimension_tipo: "categoria",
  orden_categorias: ["libre", "ocupada_con_cuenta_pendiente", "por_liberar"],
  etiquetas_categoria: { libre: "Libre", ocupada_con_cuenta_pendiente: "Ocupada con cuenta pendiente", por_liberar: "Pagada, aún ocupada" },
  colores_categoria: { libre: "#22b573", ocupada_con_cuenta_pendiente: "#ef6f5c", por_liberar: "#2f8fe0" },
};

test("datos de ejemplo: el mismo KPI da siempre los mismos numeros y otro KPI da otros", () => {
  const uno = datosDeEjemplo(KPI_EJEMPLO_GLOBAL, { hoy: HOY_EJEMPLO });
  assert.deepEqual(uno, datosDeEjemplo(KPI_EJEMPLO_GLOBAL, { hoy: HOY_EJEMPLO }));
  assert.deepEqual(
    Object.values(uno.rango_a.por_periodo),
    Object.values(datosDeEjemplo(KPI_EJEMPLO_GLOBAL, { hoy: new Date(2027, 0, 5) }).rango_a.por_periodo),
    "cambiar el dia de hoy mueve las fechas, no los valores",
  );
  assert.notDeepEqual(
    Object.values(uno.rango_a.por_periodo),
    Object.values(datosDeEjemplo({ ...KPI_EJEMPLO_GLOBAL, clave: "otro_kpi" }, { hoy: HOY_EJEMPLO }).rango_a.por_periodo),
  );
});

test("datos de ejemplo: forma de /kpi_snapshot/query, 14 dias y total coherente con la unidad", () => {
  const { rango_a: a, rango_b: b } = datosDeEjemplo(KPI_EJEMPLO_GLOBAL, { hoy: HOY_EJEMPLO });
  assert.equal(b, null);
  assert.equal(Object.keys(a.por_periodo).length, 14);
  assert.equal(Object.keys(a.por_periodo).at(-1), "2026-10-13");
  assert.deepEqual(a.por_empleado, {});
  assert.equal(a.total, Object.values(a.por_periodo).reduce((x, y) => x + y, 0), "moneda: se suma");
  const porcentaje = datosDeEjemplo({ clave: "p", unidad: "porcentaje", dimensiones: ["global"] }, { hoy: HOY_EJEMPLO }).rango_a;
  assert.ok(porcentaje.total >= 20 && porcentaje.total <= 90, "porcentaje: se promedia, queda entre 20 y 90");
});

test("datos de ejemplo: un KPI de estado usa sus categorias y sus nombres declarados", () => {
  const { rango_a: a } = datosDeEjemplo(KPI_EJEMPLO_ESTADO, { hoy: HOY_EJEMPLO });
  assert.deepEqual(Object.keys(a.por_empleado).sort(), [...KPI_EJEMPLO_ESTADO.orden_categorias].sort());
  assert.equal(a.etiquetas.por_liberar, "Pagada, aún ocupada");
  const props = propsDona({
    snapshot: { rango_a: a }, kpiInfo: KPI_EJEMPLO_ESTADO, labelForId: labelForDimension("estado", userLabel, userLabel, a.etiquetas),
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.deepEqual(props.datos.map((d) => d.categoria).sort(), ["Libre", "Ocupada con cuenta pendiente", "Pagada, aún ocupada"]);
  assert.deepEqual(props.datos.map((d) => d.color).sort(), ["#22b573", "#2f8fe0", "#ef6f5c"]);
});

test("datos de ejemplo: persona/catalogo usan entidades genericas, nunca nombres reales", () => {
  const { rango_a: a } = datosDeEjemplo({ clave: "x", unidad: "numero", dimensiones: ["empleado"] }, { hoy: HOY_EJEMPLO });
  assert.equal(Object.keys(a.por_empleado).length, 5);
  assert.deepEqual(Object.values(a.etiquetas), ["Ejemplo 1", "Ejemplo 2", "Ejemplo 3", "Ejemplo 4", "Ejemplo 5"]);
  const recortado = datosDeEjemplo({ clave: "x", unidad: "numero", dimensiones: ["platillo"], limite_categorias: 3 }, { hoy: HOY_EJEMPLO });
  assert.equal(Object.keys(recortado.rango_a.por_empleado).length, 3);
  const traducido = datosDeEjemplo({ clave: "x", unidad: "numero", dimensiones: ["empleado"] }, { hoy: HOY_EJEMPLO, textos: { entidad: "Example" } });
  assert.equal(traducido.rango_a.etiquetas["1"], "Example 1");
});

test("rangoVacio detecta una respuesta sin datos", () => {
  assert.equal(rangoVacio({ rango_a: { total: 0, por_empleado: {}, por_periodo: {} } }), true);
  assert.equal(rangoVacio(null), true);
  assert.equal(rangoVacio({ rango_a: { total: 3, por_empleado: { a: 3 }, por_periodo: {} } }), false);
  assert.equal(rangoVacio({ rango_a: datosDeEjemplo(KPI_EJEMPLO_GLOBAL).rango_a }), false);
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

// --- categorias ORDINALES: prestamos_abiertos_por_antiguedad ---------------------------------------
const ORDEN_ANTIGUEDAD = ["0-30", "31-60", "61-90", "+90"];
const KPI_ANTIGUEDAD = {
  id_kpi_definition: 30, clave: "prestamos_abiertos_por_antiguedad", unidad: "numero", dimensiones: ["estado"],
  colores_categoria: { "0-30": "#22b573", "31-60": "#f0a93b", "61-90": "#f58a3c", "+90": "#e5484d" },
  orden_categorias: ORDEN_ANTIGUEDAD, modulo: "operaciones",
};
// Los valores estan puestos para que ordenar por valor (lo normal) los dejara al reves: +90 primero.
const SNAPSHOT_ANTIGUEDAD = { rango_a: { total: 15, por_empleado: { "+90": 9, "61-90": 4, "31-60": 2, "0-30": 0 } }, rango_b: null };
const SNAPSHOT_ESTADOS = { rango_a: { total: 15, por_empleado: { Dañado: 3, Entrada: 9, Salida: 1, Extraviado: 2 } }, rango_b: null };

test("ordenarPorCategorias: sigue el orden declarado, lo desconocido va al final y no altera la entrada", () => {
  const filas = [{ id: "+90" }, { id: "raro" }, { id: "0-30" }, { id: "61-90" }, { id: "31-60" }];
  const copia = filas.map((f) => ({ ...f }));
  assert.deepEqual(ordenarPorCategorias(filas, ORDEN_ANTIGUEDAD).map((f) => f.id), ["0-30", "31-60", "61-90", "+90", "raro"]);
  assert.deepEqual(filas, copia);
  // Sin orden declarado: las mismas filas, sin tocarlas.
  assert.equal(ordenarPorCategorias(filas, undefined), filas);
  assert.equal(ordenarPorCategorias(filas, null), filas);
  assert.equal(ordenarPorCategorias(filas, []), filas);
});

test("barras de antiguedad: siempre 0-30, 31-60, 61-90, +90, aunque el valor las pida al reves", () => {
  const props = propsSeries({
    tipo: "barras", snapshots: [SNAPSHOT_ANTIGUEDAD], kpiInfos: [KPI_ANTIGUEDAD],
    labelForId: (id) => id, empleados: undefined, agruparPorPeriodo: false,
    coloresOverride: undefined, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.datos.map((fila) => fila.id), ORDEN_ANTIGUEDAD);
  assert.deepEqual(props.datos.map((fila) => fila.a), [0, 2, 4, 9]);
  // Cada barra con SU color declarado.
  assert.equal(props.colorPorFila(props.datos[0]), "#22b573");
  assert.equal(props.colorPorFila(props.datos[3]), "#e5484d");
});

test("dona de antiguedad: mismo orden fijo, no por valor", () => {
  const dona = propsDona({
    snapshot: SNAPSHOT_ANTIGUEDAD, kpiInfo: KPI_ANTIGUEDAD, labelForId: (id) => id,
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.deepEqual(dona.datos.map((d) => d.categoria), ORDEN_ANTIGUEDAD);
  assert.deepEqual(dona.datos.map((d) => d.color), ["#22b573", "#f0a93b", "#f58a3c", "#e5484d"]);
});

test("por periodo (llaves = fechas) el orden declarado no se toca", () => {
  const snapshot = { rango_a: { total: 3, por_periodo: { "2026-09-02": 1, "2026-09-01": 2 } }, rango_b: null };
  const props = propsSeries({
    tipo: "barras", snapshots: [snapshot], kpiInfos: [KPI_ANTIGUEDAD], labelForId: (id) => id,
    empleados: undefined, agruparPorPeriodo: true, coloresOverride: undefined, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.datos.map((fila) => fila.id), ["2026-09-01", "2026-09-02"]);
});

test("los demas KPIs de estado (sin orden declarado) siguen ordenados por valor, de mayor a menor", () => {
  const KPI_MATERIAL = {
    id_kpi_definition: 9, clave: "material_por_estado", unidad: "numero", dimensiones: ["estado"],
    colores_categoria: { Entrada: "#22b573", Salida: "#2f8fe0", Dañado: "#f0a93b", Extraviado: "#ef6f5c" }, modulo: "operaciones",
  };
  const barras = propsSeries({
    tipo: "barras", snapshots: [SNAPSHOT_ESTADOS], kpiInfos: [KPI_MATERIAL], labelForId: (id) => id,
    empleados: undefined, agruparPorPeriodo: false, coloresOverride: undefined, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(barras.datos.map((fila) => fila.id), ["Entrada", "Dañado", "Extraviado", "Salida"]);
  const dona = propsDona({
    snapshot: SNAPSHOT_ESTADOS, kpiInfo: KPI_MATERIAL, labelForId: (id) => id,
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.deepEqual(dona.datos.map((d) => d.categoria), ["Entrada", "Dañado", "Extraviado", "Salida"]);
});

// --- dimension "familia": perdidas_por_familia ------------------------------------------------------
const KPI_FAMILIA = {
  id_kpi_definition: 31, clave: "perdidas_por_familia", unidad: "piezas", dimensiones: ["familia"],
  etiqueta_dimension: "Familia", limite_categorias: 10, modulo: "operaciones",
};
// La API ya manda el top 10 cortado, con los nombres aparte (el snapshot solo guarda el id).
const SNAPSHOT_FAMILIA = {
  rango_a: { total: 181, por_empleado: { 7: 12, 1: 101, 0: 3 }, etiquetas: { 7: "Taladros", 1: "Sierras", 0: "Sin familia" } },
  rango_b: { total: 20, por_empleado: { 7: 5, 9: 1 }, etiquetas: { 7: "Taladros", 9: "Brocas" } },
};

test("etiquetasDeSnapshots junta los nombres de los dos lados del rango y de todos los snapshots", () => {
  assert.deepEqual(etiquetasDeSnapshots([SNAPSHOT_FAMILIA]), { 7: "Taladros", 1: "Sierras", 0: "Sin familia", 9: "Brocas" });
  assert.deepEqual(etiquetasDeSnapshots([{ rango_a: { total: 1, por_empleado: {} }, rango_b: null }]), {});
  assert.deepEqual(etiquetasDeSnapshots(undefined), {});
});

test("labelForDimension familia: el nombre que mando la API, o #id si no hay", () => {
  const etiquetas = etiquetasDeSnapshots([SNAPSHOT_FAMILIA]);
  const label = labelForDimension("familia", userLabel, userLabel, etiquetas);
  assert.equal(label("1"), "Sierras");
  assert.equal(label("0"), "Sin familia");
  assert.equal(label("404"), "#404");
  assert.equal(labelForDimension("familia", userLabel, userLabel)("5"), "#5");
});

test("barras de perdidas por familia: nombres de familia, de mayor a menor y sin 'Otros'", () => {
  const props = propsSeries({
    tipo: "barras", snapshots: [SNAPSHOT_FAMILIA], kpiInfos: [KPI_FAMILIA],
    labelForId: labelForDimension("familia", userLabel, userLabel, etiquetasDeSnapshots([SNAPSHOT_FAMILIA])),
    empleados: undefined, agruparPorPeriodo: false, coloresOverride: undefined, formatNumber, textos: TEXTOS_SERIES,
  });
  assert.deepEqual(props.datos.map((fila) => fila.name), ["Sierras", "Taladros", "Sin familia", "Brocas"]);
  assert.deepEqual(props.datos.map((fila) => fila.a), [101, 12, 3, 0]);
  // Un solo color del KPI: una familia no es una categoria fija con color propio.
  assert.equal(props.colorPorFila, null);
  assert.equal(etiquetasDeDimension([KPI_FAMILIA])[0], "Familia");
});

test("tabla de material prestado: id, responsable por omision y columnas", () => {
  const filas = filasTablaPrestamo([
    { id_nm_incident_product: 11, id_user: 5, articulo: "Taladro", responsable: null, fecha_prestamo: "2026-08-01", dias_prestado: 30 },
    { id_nm_incident_product: 12, id_user: 6, articulo: "Sierra", responsable: "Ana", fecha_prestamo: "2026-09-20", dias_prestado: 9 },
  ], "Sin asignar");
  assert.deepEqual(filas, [
    { id: 11, id_user: 5, articulo: "Taladro", responsable: "Sin asignar", fecha_prestamo: "2026-08-01", dias_prestado: 30 },
    { id: 12, id_user: 6, articulo: "Sierra", responsable: "Ana", fecha_prestamo: "2026-09-20", dias_prestado: 9 },
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
  rangoRelativo: "personalizado",
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
  assert.deepEqual(armarParametros({ ...BORRADOR, columnas: 1 }, { esTabla: true }), {});
  assert.deepEqual(armarParametros({ ...BORRADOR, columnas: 2 }, { esTabla: true }), { columnas: 2 });
  assert.deepEqual(armarParametros({ ...BORRADOR, columnas: 2, filas: 2 }, { esTabla: true }), { columnas: 2, filas: 2 });
  assert.deepEqual(armarParametros({ ...BORRADOR, columnas: 1, filas: 1 }, { esTabla: true }), {});
  const widget = widgetDeBorrador({ ...BORRADOR, tipoGrafica: "tabla", idsKpiSeleccionados: ["11"] }, { esTabla: true });
  assert.deepEqual(widget, { tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: {} });
});

// --- rangos relativos -----------------------------------------------------
const HOY = new Date(2026, 8, 29); // martes 29 de septiembre de 2026

test("cada chip de rango relativo da las fechas esperadas (contando hoy)", () => {
  const esperado = {
    hoy: ["2026-09-29", "2026-09-29"],
    "7_dias": ["2026-09-23", "2026-09-29"],
    "30_dias": ["2026-08-31", "2026-09-29"],
    "90_dias": ["2026-07-02", "2026-09-29"],
    este_mes: ["2026-09-01", "2026-09-29"],
    mes_anterior: ["2026-08-01", "2026-08-31"],
    este_anio: ["2026-01-01", "2026-09-29"],
  };
  for (const [clave, [inicio, fin]] of Object.entries(esperado)) {
    assert.deepEqual(resolverRangoRelativo(clave, HOY), { fecha_inicio: inicio, fecha_fin: fin }, clave);
  }
  assert.equal(resolverRangoRelativo("personalizado", HOY), null);
  assert.equal(resolverRangoRelativo("de_una_version_futura", HOY), null);
});

test("mes anterior en los bordes: enero, marzo y ano bisiesto", () => {
  assert.deepEqual(resolverRangoRelativo("mes_anterior", new Date(2026, 0, 15)), { fecha_inicio: "2025-12-01", fecha_fin: "2025-12-31" });
  assert.deepEqual(resolverRangoRelativo("mes_anterior", new Date(2026, 2, 1)), { fecha_inicio: "2026-02-01", fecha_fin: "2026-02-28" });
  assert.deepEqual(resolverRangoRelativo("mes_anterior", new Date(2028, 2, 5)), { fecha_inicio: "2028-02-01", fecha_fin: "2028-02-29" });
});

test("la fecha es LOCAL: a las 23:30 sigue siendo hoy (toISOString en UTC-6 daria manana)", () => {
  assert.equal(fechaLocalIso(new Date(2026, 8, 29, 23, 30)), "2026-09-29");
  assert.deepEqual(resolverRangoRelativo("hoy", new Date(2026, 8, 29, 23, 30)), { fecha_inicio: "2026-09-29", fecha_fin: "2026-09-29" });
});

test("periodo anterior: misma duracion, pegado al inicio", () => {
  assert.deepEqual(periodoAnterior({ fecha_inicio: "2026-09-01", fecha_fin: "2026-09-29" }), { fecha_inicio_b: "2026-08-03", fecha_fin_b: "2026-08-31" });
  assert.deepEqual(periodoAnterior({ fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" }), { fecha_inicio_b: "2026-07-01", fecha_fin_b: "2026-07-31" });
});

// Widgets como los que ya estan guardados en tyakxa-dev: fechas absolutas y
// ninguno de los campos que llegaron despues.
const WIDGETS_VIEJOS = [
  { id_kpi_dashboard_widget: 1, tipo_grafica: "barras", ids_kpi_definition: [3], parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" } },
  {
    id_kpi_dashboard_widget: 2, tipo_grafica: "linea", ids_kpi_definition: [3, 4],
    parametros: {
      fecha_inicio: "2026-06-01", fecha_fin: "2026-06-30", fecha_inicio_b: "2026-05-01", fecha_fin_b: "2026-05-31",
      empleados: [5, 7], id_departments: [2], colores_kpi: { 3: "#2a78d6", 4: "#eb6834" }, agrupar_por: "periodo",
    },
  },
  { id_kpi_dashboard_widget: 3, tipo_grafica: "numero", ids_kpi_definition: [1], parametros: { fecha_inicio: "2026-09-01", fecha_fin: "2026-09-15", umbral_bajo_stock: 10 } },
  { id_kpi_dashboard_widget: 4, tipo_grafica: "dona", ids_kpi_definition: [8], parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" } },
];
const CATALOGO = [
  { id_kpi_definition: 3, clave: "incidentes_resueltos_por_empleado", modulo: "operaciones" },
  { id_kpi_definition: 4, clave: "ingresos_totales", modulo: "facturacion" },
  { id_kpi_definition: 1, clave: "articulos_bajo_stock", modulo: "inventario" },
  { id_kpi_definition: 8, clave: "incidencias_abiertas_vs_cerradas", modulo: "operaciones" },
];

test("widgets viejos: las fechas efectivas son EXACTAMENTE las guardadas", () => {
  for (const widget of WIDGETS_VIEJOS) {
    assert.equal(parametrosEfectivos(widget.parametros, HOY), widget.parametros, `widget ${widget.id_kpi_dashboard_widget}`);
  }
  assert.deepEqual(parametrosEfectivos(undefined, HOY), {});
});

test("widgets viejos: abrir en el editor y volver a guardar no cambia nada", () => {
  for (const widget of WIDGETS_VIEJOS) {
    const estado = estadoDeWidget(widget, CATALOGO, HOY);
    assert.equal(estado.rangoRelativo, "personalizado", "entra como personalizado");
    const tieneBajoStock = widget.ids_kpi_definition.includes(1);
    assert.deepEqual(armarParametros(estado, { tieneBajoStock, hoy: HOY }), widget.parametros, `widget ${widget.id_kpi_dashboard_widget}`);
  }
});

test("un widget con rango relativo: se guarda la instruccion Y la foto de hoy, y se recalcula al mirarlo", () => {
  const estado = {
    ...estadoDeWidget(WIDGETS_VIEJOS[0], CATALOGO, HOY),
    rangoRelativo: "30_dias", comparar: true,
  };
  const guardado = armarParametros(estado, { hoy: HOY });
  assert.deepEqual(guardado, {
    fecha_inicio: "2026-08-31", fecha_fin: "2026-09-29", rango_relativo: "30_dias",
    comparar_anterior: true, fecha_inicio_b: "2026-08-01", fecha_fin_b: "2026-08-30",
  });
  // Mirado 10 dias despues, las fechas se corrieron; lo demas no.
  const despues = parametrosEfectivos(guardado, new Date(2026, 9, 9));
  assert.equal(despues.fecha_inicio, "2026-09-10");
  assert.equal(despues.fecha_fin, "2026-10-09");
  assert.equal(despues.fecha_inicio_b, "2026-08-11");
  assert.equal(despues.rango_relativo, "30_dias");
  // Abierto en el editor vuelve a ser el chip, con las fechas de hoy.
  const reabierto = estadoDeWidget({ ...WIDGETS_VIEJOS[0], parametros: guardado }, CATALOGO, new Date(2026, 9, 9));
  assert.equal(reabierto.rangoRelativo, "30_dias");
  assert.equal(reabierto.fechaInicio, "2026-09-10");
});

test("un rango relativo desconocido (version futura) cae a las fechas guardadas", () => {
  const parametros = { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31", rango_relativo: "trimestre_pasado" };
  assert.equal(parametrosEfectivos(parametros, HOY), parametros);
  assert.equal(estadoDeWidget({ ...WIDGETS_VIEJOS[0], parametros }, CATALOGO, HOY).rangoRelativo, "personalizado");
});

test("un borrador nuevo arranca en los ultimos 30 dias como chip", () => {
  assert.deepEqual(rangoInicialDelBorrador(HOY), { rangoRelativo: "30_dias", fechaInicio: "2026-08-31", fechaFin: "2026-09-29" });
});

// --- paleta: ni marrones, ni grafitos, ni vinos ----------------------------
function hsl(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  const sat = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
  }
  return { h: (h * 60 + 360) % 360, s: sat, l };
}

/** Por que un color NO es "vivo y claro", o null si lo es. */
function motivoNoVivo(hex) {
  const { h, s, l } = hsl(hex);
  if (s < 0.18 && l > 0.08 && l < 0.5) return "grafito";
  if (h >= 10 && h <= 50 && s >= 0.18 && l < 0.5 && (s < 0.6 || l < 0.35)) return "marron";
  if ((h >= 320 || h <= 8) && l < 0.4 && s > 0.2) return "vino";
  return null;
}

test("la paleta categorica y el gris de 'Otros' son vivos y claros", () => {
  assert.equal(CATEGORICAL.length, 8);
  for (const retirado of ["#4a3aa7", "#008300", "#898781"]) {
    assert.ok(!CATEGORICAL.includes(retirado) && COLOR_OTHERS !== retirado, `${retirado} ya no debe estar`);
  }
  for (const color of [...CATEGORICAL, COLOR_OTHERS]) assert.equal(motivoNoVivo(color), null, color);
  // "Otros" es gris azulado claro: apagado a proposito, pero nunca oscuro.
  const otros = hsl(COLOR_OTHERS);
  assert.ok(otros.h > 190 && otros.h < 240 && otros.l > 0.6, "gris azulado claro");
  assert.equal(new Set(CATEGORICAL).size, CATEGORICAL.length, "sin repetidos");
});

test("los avatares tambien: nada de tonos tierra", () => {
  for (let id = 0; id < 8; id += 1) assert.equal(motivoNoVivo(colorDeAvatar(id)), null, colorDeAvatar(id));
});

test("los tokens de tema (claro y oscuro) no traen marrones, grafitos ni vinos", () => {
  const css = readFileSync(new URL("../styles/kpi-widgets.css", import.meta.url), "utf8");
  // Grises azulados de TEXTO secundario (no de graficos, bordes ni franjas).
  const textoPizarra = new Set(["#526273", "#64748b"]);
  const tokens = [...css.matchAll(/(--kpi-[a-z-]+):\s*(#[0-9a-fA-F]{6})/g)];
  assert.ok(tokens.length > 20, "se encontraron los tokens");
  for (const [, nombre, color] of tokens) {
    if (textoPizarra.has(color.toLowerCase())) continue;
    assert.equal(motivoNoVivo(color.toLowerCase()), null, `${nombre}: ${color}`);
  }
});

// --- tipos de grafica que ofrece el editor -----------------------------------
const TODOS = ["numero", "barras", "linea", "area", "dona", "tabla"];
const SERIE = { graficas_permitidas: ["numero", "barras", "linea", "area", "dona"], modo: "snapshot" };

test("sin KPI elegido el editor ofrece todo menos Tabla", () => {
  assert.deepEqual(tiposDeGraficaPermitidos([], TODOS), ["numero", "barras", "linea", "area", "dona"]);
});

test("un KPI en vivo solo admite Tabla", () => {
  assert.deepEqual(tiposDeGraficaPermitidos([{ graficas_permitidas: ["tabla"], modo: "vivo" }], TODOS), ["tabla"]);
});

test("un KPI de serie que lista 'tabla' en el registry NO la ofrece (no hay tabla para snapshots)", () => {
  // material_por_estado e incidencias_abiertas_por_empleado lo declaran asi.
  const conTabla = { graficas_permitidas: ["dona", "tabla"], modo: "snapshot" };
  assert.deepEqual(tiposDeGraficaPermitidos([conTabla], TODOS), ["dona"]);
  assert.deepEqual(tiposDeGraficaPermitidos([{ graficas_permitidas: ["barras", "tabla"], modo: "snapshot" }], TODOS), ["barras"]);
});

test("varios KPIs: la interseccion; uno en vivo con uno de serie no comparten nada", () => {
  assert.deepEqual(tiposDeGraficaPermitidos([SERIE, { graficas_permitidas: ["barras", "linea"], modo: "snapshot" }], TODOS), ["barras", "linea"]);
  assert.deepEqual(tiposDeGraficaPermitidos([SERIE, { graficas_permitidas: ["tabla"], modo: "vivo" }], TODOS), []);
});

test("un KPI sin lista de graficas no restringe (menos Tabla)", () => {
  assert.deepEqual(tiposDeGraficaPermitidos([{ modo: "snapshot" }], TODOS), ["numero", "barras", "linea", "area", "dona"]);
});

// --- comparar contra "hace N dias" --------------------------------------------
test("rango desfasado: el mismo rango N dias atras (hoy contra hace 30 dias es un dia contra otro dia)", () => {
  assert.deepEqual(rangoDesfasado({ fecha_inicio: "2026-09-29", fecha_fin: "2026-09-29" }, 30), { fecha_inicio_b: "2026-08-30", fecha_fin_b: "2026-08-30" });
  assert.deepEqual(rangoDesfasado({ fecha_inicio: "2026-09-01", fecha_fin: "2026-09-29" }, 365), { fecha_inicio_b: "2025-09-01", fecha_fin_b: "2025-09-29" });
});

test("un widget con comparar_desfase_dias recalcula su B cada dia; guardar y reabrir no lo pierde", () => {
  const estado = { ...estadoDeWidget(WIDGETS_VIEJOS[0], CATALOGO, HOY), rangoRelativo: "hoy", comparar: true, desfaseComparacion: 30 };
  const guardado = armarParametros(estado, { hoy: HOY });
  assert.deepEqual(guardado, {
    fecha_inicio: "2026-09-29", fecha_fin: "2026-09-29", rango_relativo: "hoy",
    comparar_desfase_dias: 30, fecha_inicio_b: "2026-08-30", fecha_fin_b: "2026-08-30",
  });
  assert.ok(!("comparar_anterior" in guardado), "es una u otra");
  const manana = parametrosEfectivos(guardado, new Date(2026, 8, 30));
  assert.deepEqual([manana.fecha_inicio, manana.fecha_inicio_b], ["2026-09-30", "2026-08-31"]);
  const reabierto = estadoDeWidget({ ...WIDGETS_VIEJOS[0], parametros: guardado }, CATALOGO, HOY);
  assert.equal(reabierto.desfaseComparacion, 30);
  assert.equal(reabierto.comparar, true);
  assert.deepEqual(armarParametros(reabierto, { hoy: HOY }), guardado);
});

test("sin desfase, comparar sigue siendo contra el periodo anterior (lo de antes)", () => {
  const estado = { ...estadoDeWidget(WIDGETS_VIEJOS[0], CATALOGO, HOY), rangoRelativo: "30_dias", comparar: true, desfaseComparacion: null };
  const guardado = armarParametros(estado, { hoy: HOY });
  assert.equal(guardado.comparar_anterior, true);
  assert.ok(!("comparar_desfase_dias" in guardado));
});

// --- unidades: solo se combinan KPIs de la misma unidad ----------------------
const PORCENTAJE = { id_kpi_definition: 3, clave: "incidentes_resueltos_por_empleado", unidad: "porcentaje", modo: "snapshot" };
const CANTIDAD = { id_kpi_definition: 5, clave: "cancelaciones_por_empleado", unidad: "numero", modo: "snapshot" };
const OTRA_CANTIDAD = { id_kpi_definition: 6, clave: "incidencias_abiertas_por_empleado", unidad: "numero", modo: "snapshot" };
const SIN_UNIDAD = { id_kpi_definition: 7, clave: "sin_unidad", modo: "snapshot" };
const VIVO = { id_kpi_definition: 11, clave: "material_prestado_actual", unidad: "piezas", modo: "vivo" };

test("un porcentaje y una cantidad NO se combinan (el caso que dejaba una barra invisible)", () => {
  assert.equal(motivoParaNoCombinar([PORCENTAJE], CANTIDAD), "unidad");
  assert.equal(motivoParaNoCombinar([CANTIDAD], PORCENTAJE), "unidad");
});

test("dos KPIs de la misma unidad si; y sin nada elegido todo se puede elegir", () => {
  assert.equal(motivoParaNoCombinar([CANTIDAD], OTRA_CANTIDAD), null);
  assert.equal(motivoParaNoCombinar([], PORCENTAJE), null);
  // Un KPI sin unidad declarada cuenta como "numero", igual que al mostrarlo.
  assert.equal(unidadDeKpi(SIN_UNIDAD), "numero");
  assert.equal(motivoParaNoCombinar([CANTIDAD], SIN_UNIDAD), null);
});

test("la regla mira TODOS los ya elegidos, y un KPI en vivo no se mezcla con uno de serie", () => {
  assert.equal(motivoParaNoCombinar([CANTIDAD, OTRA_CANTIDAD], PORCENTAJE), "unidad");
  assert.equal(motivoParaNoCombinar([CANTIDAD], VIVO), "modo");
  assert.equal(motivoParaNoCombinar([VIVO], CANTIDAD), "modo");
});

test("un widget viejo con unidades mezcladas se detecta, pero no se le cambia nada", () => {
  const viejo = { id_kpi_dashboard_widget: 9, tipo_grafica: "barras", ids_kpi_definition: [3, 5], parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" } };
  assert.equal(mezclaUnidades([PORCENTAJE, CANTIDAD]), true);
  assert.equal(mezclaUnidades([CANTIDAD, OTRA_CANTIDAD]), false);
  // Abrirlo y guardarlo tal cual no altera los KPIs ni los parametros.
  const estado = estadoDeWidget(viejo, [PORCENTAJE, CANTIDAD], HOY);
  assert.deepEqual(estado.idsKpiSeleccionados, ["3", "5"]);
  assert.deepEqual(armarParametros(estado, { hoy: HOY }), viejo.parametros);
});

// --- logica del selector de KPI -------------------------------------------
const SEL = [
  { id_kpi_definition: 1, etiqueta: "Incidencias abiertas", clave: "a", modulo: "operaciones", unidad: "numero", dimensiones: ["empleado"], descripcion: "Cuántas siguen abiertas" },
  { id_kpi_definition: 2, etiqueta: "Ingresos totales", clave: "b", modulo: "facturacion", unidad: "moneda", dimensiones: ["global"] },
  { id_kpi_definition: 3, etiqueta: "Existencias", clave: "c", modulo: "inventario", unidad: "piezas", dimensiones: ["producto"] },
  { id_kpi_definition: 4, etiqueta: "Cancelaciones", clave: "d", modulo: "operaciones", unidad: "numero", dimensiones: ["empleado"] },
];

test("selector: agrupa por modulo en un orden fijo (no el del catalogo) y deja 'Variables' al final", () => {
  const grupos = agruparKpis(SEL);
  assert.deepEqual(grupos.map((g) => g.clave), ["operaciones", "inventario", "facturacion", "variables"]);
  assert.deepEqual(grupos[0].kpis.map((k) => k.etiqueta), ["Incidencias abiertas", "Cancelaciones"]);
  assert.equal(esVariable(SEL[1]), true);
  assert.equal(grupos[3].esVariables, true);
  // Un modulo cuyos KPIs son todos sin desglose (facturacion aqui) tiene su propia pestana.
  assert.deepEqual(grupos[2].combinables.map((k) => k.etiqueta), ["Ingresos totales"]);
  assert.deepEqual(grupos[3].kpis.map((k) => k.etiqueta), ["Ingresos totales"], "y el mismo KPI sale tambien en Variables");
});

test("selector: la busqueda mira nombre, descripcion y clave, sin acentos, y quita grupos vacios", () => {
  assert.deepEqual(agruparKpis(SEL, "cuantas").map((g) => g.clave), ["operaciones"], "por descripcion, sin acento");
  assert.deepEqual(agruparKpis(SEL, "INGRESOS").map((g) => g.clave), ["facturacion", "variables"], "un sin desglose sale en su modulo y en Variables");
  assert.deepEqual(agruparKpis(SEL, "").length, 4);
  assert.deepEqual(agruparKpis(SEL, "nada de esto"), []);
  assert.deepEqual(agruparKpis([], "x"), []);
});

test("selector: una opcion se bloquea solo al combinar, y una ya elegida nunca", () => {
  const catalogo = [...SEL, { id_kpi_definition: 5, etiqueta: "Resueltos %", clave: "e", modulo: "operaciones", unidad: "porcentaje", dimensiones: ["empleado"] }];
  const porcentaje = catalogo[4];
  assert.deepEqual(estadoDeOpcion({ kpi: porcentaje, seleccionados: ["1"], catalogo, multiple: true }), { elegida: false, motivo: "unidad" });
  assert.deepEqual(estadoDeOpcion({ kpi: porcentaje, seleccionados: ["1"], catalogo, multiple: false }), { elegida: false, motivo: null });
  assert.deepEqual(estadoDeOpcion({ kpi: SEL[3], seleccionados: ["1"], catalogo, multiple: true }), { elegida: false, motivo: null });
  assert.deepEqual(estadoDeOpcion({ kpi: SEL[0], seleccionados: ["1", "5"], catalogo, multiple: true }), { elegida: true, motivo: null });
  assert.deepEqual(estadoDeOpcion({ kpi: porcentaje, seleccionados: [], catalogo, multiple: true }), { elegida: false, motivo: null });
});

// --- etiqueta de la dimension en "Agrupar por" ---------------------------------
test("Agrupar por usa la etiqueta que declara el KPI (Responsable, no Empleado)", () => {
  const responsable = { dimensiones: ["empleado"], etiqueta_dimension: "Responsable" };
  assert.deepEqual(etiquetasDeDimension([responsable]), ["Responsable"]);
});

test("sin etiqueta propia (backend viejo, fila huerfana) cae a la de la dimension", () => {
  assert.deepEqual(etiquetasDeDimension([{ dimensiones: ["empleado"] }]), ["Empleado"]);
  assert.deepEqual(etiquetasDeDimension([{ dimensiones: ["producto"], etiqueta_dimension: "" }]), ["Producto"]);
  assert.deepEqual(etiquetasDeDimension([{ dimensiones: ["desconocida"] }]), []);
  assert.deepEqual(etiquetasDeDimension([]), []);
});

test("con varios KPIs salen las etiquetas distintas, sin repetir y en el orden elegido", () => {
  const a = { dimensiones: ["empleado"], etiqueta_dimension: "Responsable" };
  const b = { dimensiones: ["empleado"], etiqueta_dimension: "Responsable" };
  const c = { dimensiones: ["empleado"] };
  assert.deepEqual(etiquetasDeDimension([a, b]), ["Responsable"]);
  assert.deepEqual(etiquetasDeDimension([a, c]), ["Responsable", "Empleado"]);
});

// --- botones de modulo del selector -----------------------------------------
test("modulo inicial: el del primer KPI ya elegido; si no hay, el primero de la lista", () => {
  const grupos = agruparKpis(SEL);
  assert.equal(grupoInicial(grupos, SEL, []), "operaciones");
  assert.equal(grupoInicial(grupos, SEL, ["3"]), "inventario");
  assert.equal(grupoInicial(grupos, SEL, ["2", "1"]), "facturacion", "manda el PRIMERO elegido, no el de menor id; un sin desglose abre en su modulo");
  assert.equal(grupoInicial(grupos, SEL, ["999"]), "operaciones", "un id que ya no existe no rompe nada");
  assert.equal(grupoInicial([], [], []), null);
  assert.equal(claveDeGrupo(SEL[1]), "facturacion", "un sin desglose abre en su modulo (ahi estan todos sus KPIs)");
  assert.equal(claveDeGrupo(SEL[0]), "operaciones");
});

test("resumen de modulos: total, coincidencias con la busqueda y elegidos por modulo", () => {
  const sinBuscar = resumenDeModulos(SEL, "", ["1", "4"]);
  assert.deepEqual(sinBuscar.map((m) => [m.clave, m.total, m.coincidencias, m.elegidos]), [
    ["operaciones", 2, 2, 2], ["inventario", 1, 1, 0], ["facturacion", 1, 1, 0], ["variables", 1, 1, 0],
  ]);
  const buscando = resumenDeModulos(SEL, "cancel", ["1"]);
  assert.deepEqual(buscando.map((m) => [m.clave, m.total, m.coincidencias]), [
    ["operaciones", 2, 1], ["inventario", 1, 0], ["facturacion", 1, 0], ["variables", 1, 0],
  ], "el total no cambia al buscar; las coincidencias si");
  assert.equal(buscando[0].elegidos, 1, "la seleccion se conserva mientras se busca");
});

test("un modulo sin KPIs en el catalogo (plan o permiso) no aparece en el resumen", () => {
  const sinInventario = SEL.filter((kpi) => kpi.modulo !== "inventario");
  assert.deepEqual(resumenDeModulos(sinInventario, "", []).map((m) => m.clave), ["operaciones", "facturacion", "variables"]);
  assert.deepEqual(resumenDeModulos([], "", []), []);
});

test("cada modulo tiene su color, distinto, estable y vivo", () => {
  const conocidos = Object.keys(COLOR_DE_MODULO);
  assert.equal(new Set(Object.values(COLOR_DE_MODULO)).size, conocidos.length, "sin repetidos");
  assert.equal(colorDeModulo("operaciones"), colorDeModulo("operaciones"));
  const desconocido = colorDeModulo("un_modulo_nuevo");
  assert.ok(CATEGORICAL.includes(desconocido) && desconocido === colorDeModulo("un_modulo_nuevo"));
});

test("el orden de los modulos no depende del orden en que llegue el catalogo", () => {
  const mezclado = [
    { id_kpi_definition: 1, etiqueta: "a", modulo: "documentos", dimensiones: ["empleado"] },
    { id_kpi_definition: 2, etiqueta: "b", modulo: "zeta_nuevo", dimensiones: ["empleado"] },
    { id_kpi_definition: 3, etiqueta: "c", modulo: "facturacion", dimensiones: ["empleado"] },
    { id_kpi_definition: 4, etiqueta: "d", modulo: "operaciones", dimensiones: ["empleado"] },
    { id_kpi_definition: 5, etiqueta: "e", modulo: "alfa_nuevo", dimensiones: ["empleado"] },
    { id_kpi_definition: 6, etiqueta: "f", modulo: "inventario", dimensiones: ["global"] },
  ];
  const orden = agruparKpis(mezclado).map((g) => g.clave);
  assert.deepEqual(orden, ["operaciones", "inventario", "facturacion", "documentos", "alfa_nuevo", "zeta_nuevo", "variables"]);
  assert.deepEqual(agruparKpis([...mezclado].reverse()).map((g) => g.clave), orden);
});

// --- tabla de material prestado: gravedad, duracion, resumen, filtro y agrupado ----
test("gravedad por dias: hasta 30 verde, 31 a 90 ambar, mas de 90 coral (los bordes)", () => {
  assert.deepEqual([0, 1, 30].map(gravedadDeDias), ["ok", "ok", "ok"]);
  assert.deepEqual([31, 60, 90].map(gravedadDeDias), ["atencion", "atencion", "atencion"]);
  assert.deepEqual([91, 456, 512].map(gravedadDeDias), ["critico", "critico", "critico"]);
});

test("512 y 456 dias son GRAVES y se leen distinto: '1 año, 5 meses' y '1 año, 3 meses'", () => {
  assert.equal(duracionLegible(512), "1 año, 5 meses");
  assert.equal(duracionLegible(456), "1 año, 3 meses");
  assert.equal(etiquetaDeDias(512), "512 días · 1 año, 5 meses");
  assert.notEqual(etiquetaDeDias(512), etiquetaDeDias(456));
});

test("duracion legible: nada bajo un mes, meses hasta un año, y los plurales en singular", () => {
  assert.equal(duracionLegible(0), "");
  assert.equal(duracionLegible(29), "");
  assert.equal(etiquetaDeDias(1), "1 día");
  assert.equal(etiquetaDeDias(12), "12 días");
  assert.equal(duracionLegible(45), "1 mes");
  assert.equal(duracionLegible(75), "2 meses");
  assert.equal(duracionLegible(364), "12 meses", "casi un año: aun no es un año");
  assert.equal(duracionLegible(365), "1 año");
  assert.equal(duracionLegible(730), "2 años");
  assert.equal(duracionLegible(365 + 182), "1 año, 6 meses");
  assert.equal(duracionLegible(365 + 360), "2 años", "12 meses redondeados pasan a un año mas");
  assert.equal(duracionLegible(Number.NaN), "");
});

const PRESTAMOS = [
  { id: 1, articulo: "Taladro", responsable: "Ana", fecha_prestamo: "2025-05-05", dias_prestado: 512 },
  { id: 2, articulo: "Sierra", responsable: "Beto", fecha_prestamo: "2026-08-15", dias_prestado: 45 },
  { id: 3, articulo: "Martillo", responsable: "Ana", fecha_prestamo: "2026-09-17", dias_prestado: 12 },
  { id: 4, articulo: "Nivel", responsable: "Carla", fecha_prestamo: "2026-07-08", dias_prestado: 83 },
  { id: 5, articulo: "Llave", responsable: "Beto", fecha_prestamo: "2026-08-15", dias_prestado: 45 },
];

test("resumen: renglones, responsables distintos y el mas antiguo", () => {
  assert.deepEqual(resumenDePrestamos(PRESTAMOS), {
    renglones: 5, cargados: 5, responsables: 3,
    masAntiguo: { dias: 512, articulo: "Taladro", responsable: "Ana" },
  });
  // Cuando llego solo la primera pagina, los renglones son los del servidor.
  assert.equal(resumenDePrestamos(PRESTAMOS, 120).renglones, 120);
  assert.equal(resumenDePrestamos(PRESTAMOS, 120).cargados, 5);
  assert.deepEqual(resumenDePrestamos([]), { renglones: 0, cargados: 0, responsables: 0, masAntiguo: null });
});

test("filtro por responsable y lista de responsables (alfabetica)", () => {
  assert.deepEqual(responsablesDe(PRESTAMOS), ["Ana", "Beto", "Carla"]);
  assert.deepEqual(filtrarPorResponsable(PRESTAMOS, "Ana").map((f) => f.id), [1, 3]);
  assert.equal(filtrarPorResponsable(PRESTAMOS, "").length, 5, "vacio = todos");
  assert.deepEqual(filtrarPorResponsable(PRESTAMOS, "Nadie"), []);
});

test("el orden por dias es estable y determinista, y no altera la lista original", () => {
  const copia = JSON.stringify(PRESTAMOS);
  assert.deepEqual(ordenarFilas(PRESTAMOS).map((f) => f.id), [1, 4, 5, 2, 3], "empate de 45 dias: por fecha y luego por articulo (Llave antes que Sierra)");
  assert.deepEqual(ordenarFilas(PRESTAMOS, "dias_prestado", "asc").map((f) => f.id), [3, 5, 2, 4, 1].map((n) => n), "ascendente");
  assert.deepEqual(ordenarFilas(PRESTAMOS, "articulo", "asc").map((f) => f.articulo), ["Llave", "Martillo", "Nivel", "Sierra", "Taladro"]);
  assert.equal(JSON.stringify(PRESTAMOS), copia);
});

test("agrupado por responsable: el grupo con el prestamo mas viejo primero, y sus renglones por dias", () => {
  const grupos = agruparPorResponsable(PRESTAMOS);
  assert.deepEqual(grupos.map((g) => [g.responsable, g.masAntiguo, g.filas.map((f) => f.id)]), [
    ["Ana", 512, [1, 3]], ["Carla", 83, [4]], ["Beto", 45, [5, 2]],
  ]);
  assert.deepEqual(agruparPorResponsable([]), []);
});

test("agrupado por responsable: la direccion elegida ordena los renglones DENTRO de cada grupo", () => {
  const masDias = agruparPorResponsable(PRESTAMOS, { campo: "dias_prestado", direccion: "desc" });
  const menosDias = agruparPorResponsable(PRESTAMOS, { campo: "dias_prestado", direccion: "asc" });
  // Los grupos no se mueven (el prestamo mas viejo primero)...
  assert.deepEqual(menosDias.map((g) => g.responsable), masDias.map((g) => g.responsable));
  // ...y lo que cambia es el orden de adentro. Ana: 512 dias (id 1) y otro (id 3).
  assert.deepEqual(masDias[0].filas.map((f) => f.id), [1, 3]);
  assert.deepEqual(menosDias[0].filas.map((f) => f.id), [3, 1]);
  assert.equal(menosDias[0].masAntiguo, 512, "el renglon mas antiguo del grupo no depende del sentido");
  assert.deepEqual(agruparPorResponsable(PRESTAMOS).map((g) => g.responsable), masDias.map((g) => g.responsable), "sin orden = por omision");
});

test("agrupado por responsable: ordenando por responsable, los GRUPOS van de la A a la Z o al reves", () => {
  const az = agruparPorResponsable(PRESTAMOS, { campo: "responsable", direccion: "asc" });
  const za = agruparPorResponsable(PRESTAMOS, { campo: "responsable", direccion: "desc" });
  assert.deepEqual(az.map((g) => g.responsable), ["Ana", "Beto", "Carla"]);
  assert.deepEqual(za.map((g) => g.responsable), ["Carla", "Beto", "Ana"]);
});

test("con todo igual, el orden se desempata por el id del renglon (los dos sentidos)", () => {
  const iguales = [9, 3, 5].map((id) => ({ id, articulo: "Taladro", responsable: "Ana", fecha_prestamo: "2026-05-01", dias_prestado: 40 }));
  for (const direccion of ["asc", "desc"]) {
    for (const campo of ["dias_prestado", "fecha_prestamo", "articulo", "responsable"]) {
      assert.deepEqual(ordenarFilas(iguales, campo, direccion).map((f) => f.id), [3, 5, 9], `${campo} ${direccion}`);
    }
  }
});

test("normalizarOrdenTabla: un orden guardado valido se respeta y cualquier otra cosa vuelve a mas dias primero", () => {
  assert.deepEqual(ORDEN_POR_OMISION, { campo: "dias_prestado", direccion: "desc" });
  assert.deepEqual(normalizarOrdenTabla({ campo: "articulo", direccion: "asc" }), { campo: "articulo", direccion: "asc" });
  assert.deepEqual(normalizarOrdenTabla({ campo: "fecha_prestamo", direccion: "desc" }), { campo: "fecha_prestamo", direccion: "desc" });
  for (const raro of [undefined, null, "articulo", 7, [], {}, { campo: "id_user", direccion: "asc" }, { campo: "articulo", direccion: "arriba" }, { campo: "articulo" }]) {
    assert.deepEqual(normalizarOrdenTabla(raro), { campo: "dias_prestado", direccion: "desc" }, JSON.stringify(raro));
  }
  const guardado = { campo: "articulo", direccion: "asc" };
  assert.notEqual(normalizarOrdenTabla(guardado), guardado, "devuelve una copia, no el objeto guardado");
});

test("armarParametros: guardar el editor de una tabla CONSERVA el orden que el usuario eligio", () => {
  const widget = {
    id_kpi_dashboard_widget: 7, tipo_grafica: "tabla", ids_kpi_definition: [11],
    parametros: { columnas: 2, orden_tabla: { campo: "responsable", direccion: "desc" } },
  };
  const estado = estadoDeWidget(widget, []);
  assert.deepEqual(estado.ordenTabla, { campo: "responsable", direccion: "desc" });
  assert.deepEqual(armarParametros(estado, { esTabla: true }), {
    columnas: 2, orden_tabla: { campo: "responsable", direccion: "desc" },
  });
  // Un widget sin orden guardado sigue guardando lo de siempre, sin inventar uno.
  const sinOrden = estadoDeWidget({ ...widget, parametros: { columnas: 2 } }, []);
  assert.equal(sinOrden.ordenTabla, null);
  assert.deepEqual(armarParametros(sinOrden, { esTabla: true }), { columnas: 2 });
  // Un orden basura guardado no se manda al servidor (que lo rechazaria): se vuelve el de por omision.
  const basura = estadoDeWidget({ ...widget, parametros: { orden_tabla: { campo: "x", direccion: "y" } } }, []);
  assert.deepEqual(armarParametros(basura, { esTabla: true }), { orden_tabla: { campo: "dias_prestado", direccion: "desc" } });
});

test("armarParametros: un widget que deja de ser tabla no arrastra el orden de la tabla", () => {
  const estado = { ...BORRADOR, ordenTabla: { campo: "articulo", direccion: "asc" } };
  assert.equal("orden_tabla" in armarParametros(estado, {}), false);
});

test("solo se ven 10 renglones hasta pedir 'Ver todos'", () => {
  const muchas = Array.from({ length: 25 }, (_, i) => ({ id: i, dias_prestado: 100 - i }));
  assert.equal(recortar(muchas, false).length, 10);
  assert.equal(recortar(muchas, true).length, 25);
  assert.equal(recortar(muchas.slice(0, 4), false).length, 4);
});

test("agrupado: el limite de renglones se reparte entre grupos y cada uno dice cuantos oculta", () => {
  const grupo = (responsable, n) => ({ responsable, filas: Array.from({ length: n }, (_, i) => ({ id: i })) });
  const grupos = [grupo("Ana", 7), grupo("Beto", 6), grupo("Carla", 2)];
  const vistos = recortarGrupos(grupos, false, 10);
  assert.deepEqual(vistos.map((g) => [g.responsable, g.filas.length, g.ocultos]), [["Ana", 7, 0], ["Beto", 3, 3]]);
  assert.equal(recortarGrupos(grupos, true, 10), grupos);
});

test("la barra de dias es proporcional al maximo, con minimo visible y tope de 100", () => {
  assert.equal(anchoDeBarra(512, 512), 100);
  assert.equal(anchoDeBarra(256, 512), 50);
  assert.equal(anchoDeBarra(0, 512), 4);
  assert.equal(anchoDeBarra(600, 512), 100);
  assert.equal(anchoDeBarra(10, 0), 4);
});

test("columnasDeWidget: solo una tabla guardada con columnas 2 ocupa dos; lo demas (y lo anterior) ocupa una", () => {
  assert.equal(columnasDeWidget({ tipo_grafica: "tabla", parametros: { columnas: 2 } }), 2);
  assert.equal(columnasDeWidget({ tipo_grafica: "tabla", parametros: {} }), 1);
  assert.equal(columnasDeWidget({ tipo_grafica: "tabla", parametros: { columnas: 7 } }), 1);
  assert.equal(columnasDeWidget({ tipo_grafica: "tabla" }), 1);
  assert.equal(columnasDeWidget({ tipo_grafica: "barras", parametros: { columnas: 2 } }), 1);
  assert.equal(estadoDeWidget({ tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: { columnas: 2 } }, []).columnas, 2);
  assert.equal(estadoDeWidget({ tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: {} }, []).columnas, 1);
});

test("filasDeWidget: solo una tabla guardada con filas 2 ocupa dos filas; lo anterior ocupa una", () => {
  assert.equal(filasDeWidget({ tipo_grafica: "tabla", parametros: { columnas: 2, filas: 2 } }), 2);
  assert.equal(filasDeWidget({ tipo_grafica: "tabla", parametros: { columnas: 2 } }), 1);
  assert.equal(filasDeWidget({ tipo_grafica: "tabla", parametros: { filas: 3 } }), 1);
  assert.equal(filasDeWidget({ tipo_grafica: "barras", parametros: { filas: 2 } }), 1);
  assert.equal(filasDeWidget({ tipo_grafica: "tabla" }), 1);
  assert.equal(estadoDeWidget({ tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: { filas: 2 } }, []).filas, 2);
  assert.equal(estadoDeWidget({ tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: {} }, []).filas, 1);
});

test("filtrarPorUsuario filtra por id_user (no por nombre) y sin id no filtra", () => {
  const filas = [{ id: 1, id_user: 5, responsable: "Ana" }, { id: 2, id_user: "6", responsable: "Ana" }, { id: 3, id_user: 5, responsable: "Ana" }];
  assert.deepEqual(filtrarPorUsuario(filas, "5").map((f) => f.id), [1, 3]);
  assert.deepEqual(filtrarPorUsuario(filas, 6).map((f) => f.id), [2]);
  assert.equal(filtrarPorUsuario(filas, null), filas);
  assert.deepEqual(filtrarPorUsuario(filas, 99), []);
});

test("buscarEnFilas: todas las palabras, sin importar mayusculas ni acentos, en cualquier columna", () => {
  const filas = [
    { id: 1, articulo: "Taladro Bosch", responsable: "José Pérez", fecha_prestamo: "2026-08-01", dias_prestado: 512 },
    { id: 2, articulo: "Sierra circular", responsable: "Ana", fecha_prestamo: "2026-09-20", dias_prestado: 9 },
  ];
  assert.deepEqual(buscarEnFilas(filas, "jose").map((f) => f.id), [1]);
  assert.deepEqual(buscarEnFilas(filas, "BOSCH taladro").map((f) => f.id), [1]);
  assert.deepEqual(buscarEnFilas(filas, "2026-09").map((f) => f.id), [2]);
  assert.deepEqual(buscarEnFilas(filas, "512").map((f) => f.id), [1]);
  assert.deepEqual(buscarEnFilas(filas, "taladro ana"), []);
  assert.equal(buscarEnFilas(filas, "  "), filas);
});

test("escalaDeBarras: el renglon mas antiguo, pero nunca menos de un ano", () => {
  assert.equal(escalaDeBarras([{ dias_prestado: 512 }, { dias_prestado: 45 }]), 512);
  assert.equal(escalaDeBarras([{ dias_prestado: 20 }, { dias_prestado: 3 }]), 365);
  assert.equal(escalaDeBarras([]), 365);
  assert.equal(anchoDeBarra(45, escalaDeBarras([{ dias_prestado: 45 }])), 12);
});

test("masonry: una tarjeta ocupa las filas de 4px que mide, mas el hueco de abajo", () => {
  assert.equal(filasQueOcupa(193), 53); // (193 + 16) / 4 = 52.25 -> 53
  assert.equal(filasQueOcupa(676), 173);
  assert.equal(filasQueOcupa(48), 16); // justo 64 / 4
  assert.equal(filasQueOcupa(0), 1);
  assert.equal(filasQueOcupa(NaN), 1);
  // La tarjeta siempre cabe en lo que ocupa, y sobra menos de una fila.
  for (const alto of [1, 50, 193, 324, 350, 799]) {
    const ocupado = filasQueOcupa(alto) * 4 - 16;
    assert.ok(ocupado >= alto && ocupado - alto < 4, `alto ${alto} -> ${ocupado}`);
  }
});
