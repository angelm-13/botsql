// BarrasWidget no se puede pintar con medidas reales en Node (ResponsiveContainer mide 0), asi que se fija el cableado
// del componente con el helper y que el adaptador avise cuando el eje es de fechas.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { propsSeries } from "./kpiAdaptadores.js";

const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), "utf8");

test("BarrasWidget decide modo, etiquetas y recorte con disenoDeBarras", () => {
  const barras = leer("../components/kpi-widgets/BarrasWidget.jsx");
  assert.match(barras, /disenoDeBarras\(/);
  assert.match(barras, /layout=\{horizontal \? "vertical" : "horizontal"\}/);
  assert.match(barras, /type="category"/);
  assert.match(barras, /tickFormatter=\{recortar\}/);
  assert.match(barras, /interval=\{diseno\.todasLasEtiquetas \? 0 : undefined\}/);
  assert.match(barras, /textoRecorte\(diseno\.mostradas, diseno\.total\)/);
  // Solo se dibujan las categorias visibles, tambien las celdas de color/patron.
  assert.match(barras, /data=\{visibles\}/);
  assert.match(barras, /visibles\.map\(\(fila, indice\)/);
  // El tooltip sigue leyendo el nombre completo: la etiqueta recortada es solo del eje.
  assert.match(barras, /<strong>\{label\}<\/strong>/);
});

test("el Dashboard pasa el texto traducible de 'Mostrando n de total'", () => {
  const dashboard = leer("../pages/Dashboard.jsx");
  assert.match(dashboard, /tx\("showing_n_of_total", "Mostrando \{n\} de \{total\}"\)/);
});

const CATALOGO_UN_KPI = [{ id_kpi_definition: 3, clave: "x", etiqueta: "X", unidad: "numero", dimensiones: ["empleado"] }];
const snapshot = { rango_a: { por_empleado: { 1: 5 }, por_periodo: { "2026-10-01": 2 } } };
const base = {
  tipo: "barras", snapshots: [snapshot], kpiInfos: CATALOGO_UN_KPI, labelForId: (id) => `E${id}`, empleados: [],
  coloresOverride: {}, umbralBajoStock: null, esBajoStock: false, formatNumber: (n) => String(n),
  textos: { rangoA: "A", rangoB: "B", comparacionCorta: "comp" },
};

test("propsSeries avisa porPeriodo solo cuando el eje es de fechas, con uno o varios indicadores", () => {
  assert.equal(propsSeries({ ...base, agruparPorPeriodo: false }).porPeriodo, false);
  assert.equal(propsSeries({ ...base, agruparPorPeriodo: true }).porPeriodo, true);
  const dos = { ...base, kpiInfos: [...CATALOGO_UN_KPI, { ...CATALOGO_UN_KPI[0], id_kpi_definition: 4, clave: "y" }], snapshots: [snapshot, snapshot] };
  assert.equal(propsSeries({ ...dos, agruparPorPeriodo: false }).porPeriodo, false);
  assert.equal(propsSeries({ ...dos, agruparPorPeriodo: true }).porPeriodo, true);
});
