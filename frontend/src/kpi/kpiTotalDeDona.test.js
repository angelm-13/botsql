import test from "node:test";
import assert from "node:assert/strict";
import { fuenteDelTotalDeDona, propsDona, totalCentroDeDona } from "./kpiAdaptadores.js";

const formatNumber = (valor) => new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(valor || 0);
const TEXTOS = { otros: "Otros", registros: "registros", total: "total" };
const DATOS = [{ categoria: "A", valor: 20, color: "#111111" }, { categoria: "B", valor: 14, color: "#222222" }];
const kpi = (extra) => ({ id_kpi_definition: 1, clave: "k", unidad: "numero", dimensiones: ["estado"], agregacion: "suma", ...extra });

test("cantidad con agregacion suma: el total y 'registros'", () => {
  const total = totalCentroDeDona(DATOS, kpi(), formatNumber, TEXTOS);
  assert.equal(total.texto, "34");
  assert.equal(total.detalle, "registros");
});

test("la unidad aporta su prefijo o su sufijo: moneda '$' + 'total'; piezas 'piezas'; minutos 'min'", () => {
  assert.deepEqual(totalCentroDeDona(DATOS, kpi({ unidad: "moneda" }), formatNumber, TEXTOS), { texto: "$34", detalle: "total", fuente: fuenteDelTotalDeDona("$34") });
  assert.equal(totalCentroDeDona(DATOS, kpi({ unidad: "piezas" }), formatNumber, TEXTOS).detalle, "piezas");
  assert.equal(totalCentroDeDona(DATOS, kpi({ unidad: "minutos" }), formatNumber, TEXTOS).detalle, "min");
});

test("sin agregacion suma no hay total: promedio, ultimo, vivo, sin declarar", () => {
  for (const agregacion of ["promedio_ponderado", "ultimo", null, undefined]) {
    assert.equal(totalCentroDeDona(DATOS, kpi({ agregacion }), formatNumber, TEXTOS), null, String(agregacion));
  }
  assert.equal(totalCentroDeDona(DATOS, undefined, formatNumber, TEXTOS), null);
});

test("un porcentaje no se suma entre categorias, aunque el KPI sume", () => {
  assert.equal(totalCentroDeDona(DATOS, kpi({ unidad: "porcentaje" }), formatNumber, TEXTOS), null);
});

test("el total incluye 'Otros' y respeta el formato del idioma", () => {
  const total = totalCentroDeDona([{ categoria: "A", valor: 1200.5, color: "#1" }, { categoria: "Otros", valor: 99.25, color: "#2" }], kpi(), formatNumber, TEXTOS);
  assert.equal(total.texto, formatNumber(1299.75));
});

test("la letra se ajusta: grande con pocas cifras, menor con muchas, con piso", () => {
  assert.equal(fuenteDelTotalDeDona("34"), 26);
  assert.ok(fuenteDelTotalDeDona("1,234,567") < fuenteDelTotalDeDona("1,234"));
  assert.ok(fuenteDelTotalDeDona("1,234") < fuenteDelTotalDeDona("34") || fuenteDelTotalDeDona("1,234") === 26);
  assert.equal(fuenteDelTotalDeDona("$12,345,678,901.55"), 11);
  assert.equal(fuenteDelTotalDeDona(""), 26);
});

test("propsDona trae el total al centro; por periodo tambien suma", () => {
  const props = propsDona({
    snapshot: { rango_a: { total: 34, por_empleado: { abierta: 20, cerrada: 14 } } }, kpiInfo: kpi(),
    labelForId: (id) => id, agruparPorPeriodo: false, formatNumber, textos: TEXTOS,
  });
  assert.equal(props.totalCentro.texto, "34");
  const sinSuma = propsDona({
    snapshot: { rango_a: { total: 34, por_empleado: { abierta: 20, cerrada: 14 } } }, kpiInfo: kpi({ agregacion: "ultimo" }),
    labelForId: (id) => id, agruparPorPeriodo: false, formatNumber, textos: TEXTOS,
  });
  assert.equal(sinSuma.totalCentro, null);
});
