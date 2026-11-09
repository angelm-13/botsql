import test from "node:test";
import assert from "node:assert/strict";
import { anioDelRangoPrincipal, etiquetaDeRangoComparado, rangoComparadoDe, textoVsRango } from "./kpiComparacion.js";
import { formatoDeRangoCorto } from "./kpiRango.js";
import { propsNumero, propsSeries } from "./kpiAdaptadores.js";

test("formatoDeRangoCorto omite el año solo si todo el rango es del año de referencia", () => {
  assert.equal(formatoDeRangoCorto("2026-09-06", "2026-10-05", { anioDeReferencia: 2026 }), "6 sep – 5 oct");
  assert.equal(formatoDeRangoCorto("2026-10-05", "2026-10-05", { anioDeReferencia: 2026 }), "5 oct");
  assert.equal(formatoDeRangoCorto("2026-10-01", "2026-10-30", { anioDeReferencia: 2026 }), "1 – 30 oct");
  assert.equal(formatoDeRangoCorto("2025-07-01", "2025-07-31", { anioDeReferencia: 2026 }), "1 – 31 jul 2025");
  assert.equal(formatoDeRangoCorto("2025-12-28", "2026-01-03", { anioDeReferencia: 2026 }), "28 dic 2025 – 3 ene 2026");
  assert.equal(formatoDeRangoCorto("2026-09-06", "2026-10-05"), "6 sep – 5 oct 2026", "sin referencia: completo");
  assert.equal(formatoDeRangoCorto("", "2026-10-05", { anioDeReferencia: 2026 }), "");
});

test("rangoComparadoDe prefiere lo que devolvio el servidor y cae en los parametros", () => {
  const snapshot = { rango_b: { inicio: "2026-09-06", fin: "2026-10-05" } };
  const parametros = { fecha_inicio_b: "2026-08-01", fecha_fin_b: "2026-08-31" };
  assert.deepEqual(rangoComparadoDe({ snapshot, parametros }), { inicio: "2026-09-06", fin: "2026-10-05", origen: "servidor" });
  assert.deepEqual(rangoComparadoDe({ snapshot: { rango_b: null }, parametros }), { inicio: "2026-08-01", fin: "2026-08-31", origen: "cliente" });
  assert.equal(rangoComparadoDe({ snapshot: { rango_b: null }, parametros: {} }), null);
  assert.equal(rangoComparadoDe(), null);
});

test("anioDelRangoPrincipal sale del rango A del servidor o de los parametros", () => {
  assert.equal(anioDelRangoPrincipal({ snapshot: { rango_a: { fin: "2026-11-04" } } }), 2026);
  assert.equal(anioDelRangoPrincipal({ parametros: { fecha_fin: "2025-01-02" } }), 2025);
  assert.equal(anioDelRangoPrincipal({}), null);
});

test("etiquetaDeRangoComparado y textoVsRango", () => {
  const rango = { inicio: "2026-09-06", fin: "2026-10-05" };
  assert.equal(etiquetaDeRangoComparado(rango, { anioDeReferencia: 2026 }), "6 sep – 5 oct");
  assert.equal(etiquetaDeRangoComparado(rango, { completa: true }), "6 sep – 5 oct 2026");
  assert.equal(etiquetaDeRangoComparado(null), "");
  assert.equal(textoVsRango("vs. {rango}", "6 sep – 5 oct"), "vs. 6 sep – 5 oct");
  assert.equal(textoVsRango(undefined, "x"), "vs. x");
});

const KPI = { id_kpi_definition: 1, unidad: "conteo", direccion: "bajo_mejor", dimensiones: ["empleado"] };
const TEXTOS = {
  vsAnterior: "vs. periodo anterior", sinComparacion: "Activa Comparar",
  vsRango: (r) => `vs. ${r}`, comparacionNoDisponible: (r) => (r ? `Sin datos para comparar vs. ${r}` : "Sin datos para comparar"),
};
const SNAP = { rango_a: { total: 6, por_empleado: {}, por_periodo: {} }, rango_b: { total: 5, por_empleado: {}, por_periodo: {} } };

test("propsNumero: la leyenda lleva las fechas; sin fechas conserva el texto de siempre", () => {
  const f = (n) => String(n);
  assert.equal(propsNumero({ snapshot: SNAP, kpiInfo: KPI, formatNumber: f, textos: TEXTOS, etiquetaRangoB: "6 sep – 5 oct" }).leyendaVariacion, "vs. 6 sep – 5 oct");
  assert.equal(propsNumero({ snapshot: SNAP, kpiInfo: KPI, formatNumber: f, textos: TEXTOS }).leyendaVariacion, "vs. periodo anterior");
  // Los textos viejos (sin vsRango) siguen funcionando.
  assert.equal(propsNumero({ snapshot: SNAP, kpiInfo: KPI, formatNumber: f, textos: { vsAnterior: "vs. periodo anterior", sinComparacion: "x" }, etiquetaRangoB: "6 sep" }).leyendaVariacion, "vs. periodo anterior");
});

test("propsNumero: sin periodo B, un widget que NO compara invita a activar y uno que SI compara lo dice", () => {
  const f = (n) => String(n);
  const sinB = { ...SNAP, rango_b: null };
  assert.equal(propsNumero({ snapshot: sinB, kpiInfo: KPI, formatNumber: f, textos: TEXTOS }).textoSinVariacion, "Activa Comparar");
  assert.equal(propsNumero({ snapshot: sinB, kpiInfo: KPI, formatNumber: f, textos: TEXTOS, comparacionActiva: true, etiquetaRangoB: "6 sep – 5 oct" }).textoSinVariacion, "Sin datos para comparar vs. 6 sep – 5 oct");
  assert.equal(propsNumero({ snapshot: sinB, kpiInfo: KPI, formatNumber: f, textos: TEXTOS, comparacionActiva: true }).textoSinVariacion, "Sin datos para comparar");
  assert.equal(propsNumero({ snapshot: sinB, kpiInfo: KPI, formatNumber: f, textos: TEXTOS, comparacionActiva: true }).variacion, null);
});

test("propsSeries: las series A y B se llaman por sus fechas", () => {
  const snap = { rango_a: { total: 3, por_empleado: { 1: 3 }, por_periodo: {} }, rango_b: { total: 2, por_empleado: { 1: 2 }, por_periodo: {} } };
  const props = propsSeries({
    tipo: "barras", snapshots: [snap], kpiInfos: [KPI], labelForId: (id) => `P${id}`, empleados: [], agruparPorPeriodo: false, coloresOverride: {},
    umbralBajoStock: 0, esBajoStock: false, formatNumber: String,
    textos: { rangoA: "6 oct – 4 nov 2026", rangoB: "6 sep – 5 oct 2026", comparacionCorta: "vs. 6 sep – 5 oct 2026" },
  });
  assert.deepEqual(props.series.map((s) => s.nombre), ["6 oct – 4 nov 2026", "6 sep – 5 oct 2026"]);
});

import { diasDeRango, formatoDeRangoConDias } from "./kpiRango.js";

test("diasDeRango cuenta ambos extremos y tolera lo invalido", () => {
  assert.equal(diasDeRango("2026-10-06", "2026-11-04"), 30);
  assert.equal(diasDeRango("2026-10-06", "2026-10-06"), 1);
  assert.equal(diasDeRango("2026-01-01", "2026-12-31"), 365);
  assert.equal(diasDeRango("2026-02-27", "2026-03-02"), 4, "cruza febrero");
  assert.equal(diasDeRango("2026-11-04", "2026-10-06"), 0, "al reves");
  assert.equal(diasDeRango("", "2026-10-06"), 0);
});

test("formatoDeRangoConDias arma '6 oct – 4 nov 2026 (30 días)' y '(1 día)' para un solo dia", () => {
  assert.equal(formatoDeRangoConDias("2026-10-06", "2026-11-04"), "6 oct – 4 nov 2026 (30 días)");
  assert.equal(formatoDeRangoConDias("2026-11-04", "2026-11-04"), "4 nov 2026 (1 día)");
  assert.equal(formatoDeRangoConDias("2026-11-04", "2026-11-04", { textos: { uno: "1 day", otros: "{n} days" } }), "4 nov 2026 (1 day)");
  assert.equal(formatoDeRangoConDias("2026-10-06", "2026-11-04", { textos: { uno: "1 day", otros: "{n} days" } }), "6 oct – 4 nov 2026 (30 days)");
  assert.equal(formatoDeRangoConDias("", ""), "");
});
