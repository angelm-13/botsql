// Un conteo no tiene marcas con decimales: un eje con 0, 0.5, 1, 1.5 ("1,5 tareas bloqueadas") confunde. Las unidades de conteo
// (`numero`, que el selector rotula "Cantidad", y `piezas`) piden eje entero; porcentajes y pesos no. Se pinta con tamano fijo
// (ver bundleGraficas.mjs) y se leen las marcas del eje del SVG.
import assert from "node:assert/strict";
import test, { before } from "node:test";
import { cargarGraficas } from "./bundleGraficas.mjs";
import { ejeSoloEnteros } from "./kpiAccesibilidad.js";
import { propsSeries } from "./kpiAdaptadores.js";
import { UNIDAD_INFO } from "./kpiDatos.js";

let pintarBarras;
let pintarLineaArea;
before(async () => { ({ pintarBarras, pintarLineaArea } = await cargarGraficas()); });

const formatNumber = (valor) => String(valor);
const textos = { rangoA: "A", rangoB: "B", comparacionCorta: "comp" };
const snapshot = (porEmpleado) => ({ rango_a: { total: 0, por_empleado: porEmpleado, por_periodo: {}, etiquetas: {} } });

/** Las marcas del eje numerico: los <text> de las ticks del eje que tiene numeros. */
function marcas(html) {
  return [...html.matchAll(/<tspan[^>]*>([^<]*)<\/tspan>/g)].map((m) => m[1]).filter((texto) => /^-?[\d.,]+[^\d]*$/.test(texto));
}

test("ejeSoloEnteros: numero y piezas si; porcentaje, moneda, dias, minutos y una mezcla (null) no", () => {
  assert.equal(ejeSoloEnteros("numero"), true);
  assert.equal(ejeSoloEnteros("piezas"), true);
  for (const unidad of ["porcentaje", "moneda", "dias", "minutos", null, undefined]) assert.equal(ejeSoloEnteros(unidad), false, String(unidad));
  // Todas las unidades que existen estan decididas: una nueva obliga a decidir si es conteo.
  assert.deepEqual(Object.keys(UNIDAD_INFO).sort(), ["dias", "minutos", "moneda", "numero", "piezas", "porcentaje"]);
});

test("propsSeries pasa soloEnteros segun la unidad del KPI (y no en un eje con unidades mezcladas)", () => {
  const props = (unidad, extra = {}) => propsSeries({
    tipo: "barras", snapshots: [snapshot({ 5: 2, 7: 1 })], kpiInfos: [{ id_kpi_definition: 3, dimensiones: ["empleado"], unidad, ...extra }],
    labelForId: (id) => `P${id}`, agruparPorPeriodo: false, formatNumber, textos,
  });
  assert.equal(props("numero").soloEnteros, true);
  assert.equal(props("piezas").soloEnteros, true);
  assert.equal(props("porcentaje").soloEnteros, false);
  assert.equal(props("moneda").soloEnteros, false);
  const mezcla = propsSeries({
    tipo: "barras", snapshots: [snapshot({ 5: 2 }), snapshot({ 5: 1 })], labelForId: (id) => `P${id}`, agruparPorPeriodo: false, formatNumber, textos,
    kpiInfos: [{ id_kpi_definition: 3, dimensiones: ["empleado"], unidad: "numero" }, { id_kpi_definition: 4, dimensiones: ["empleado"], unidad: "moneda" }],
  });
  assert.equal(mezcla.soloEnteros, false);
});

test("barras (verticales) con valores 2, 1, 1: con soloEnteros el eje no tiene decimales; sin el, si", () => {
  const datos = [{ id: "a", name: "A", a: 2 }, { id: "b", name: "B", a: 1 }, { id: "c", name: "C", a: 1 }];
  const series = [{ clave: "a", nombre: "A", color: "#2f8fe0" }];
  const sin = marcas(pintarBarras({ datos, series, campoEtiqueta: "name" }));
  assert.ok(sin.some((m) => m.includes(".")), `sin el arreglo el eje trae decimales: ${sin}`);
  const con = marcas(pintarBarras({ datos, series, campoEtiqueta: "name", soloEnteros: true }));
  assert.ok(con.length > 0 && con.every((m) => !m.includes(".")), `eje entero: ${con}`);
  assert.equal(con[0], "0", "arranca en 0");
  // El tope no es el maximo exacto (88, 19...) sino un numero redondo: con valores 70 y 88 salen marcas de 25 en 25.
  const grandes = marcas(pintarBarras({ datos: [{ id: "a", name: "A", a: 70 }, { id: "b", name: "B", a: 88 }], series, campoEtiqueta: "name", soloEnteros: true }));
  assert.ok(grandes.every((m) => !m.includes(".")) && !grandes.includes("88"), `tope redondo, no el maximo: ${grandes}`);
});

test("barras horizontales (desde 13 categorias): el eje numerico X tambien es entero", () => {
  const datos = Array.from({ length: 14 }, (_, i) => ({ id: i, name: `Persona ${i}`, a: i % 2 ? 1 : 2 }));
  const series = [{ clave: "a", nombre: "A", color: "#2f8fe0" }];
  const con = marcas(pintarBarras({ datos, series, campoEtiqueta: "name", soloEnteros: true })).filter((m) => !m.startsWith("Persona"));
  assert.ok(con.length > 0 && con.every((m) => !m.includes(".")), `eje entero: ${con}`);
});

test("linea y area: el eje Y es entero con soloEnteros", () => {
  const datos = [{ name: "d1", a: 2 }, { name: "d2", a: 1 }, { name: "d3", a: 1 }];
  const series = [{ clave: "a", nombre: "A", color: "#2f8fe0" }];
  for (const tipo of ["linea", "area"]) {
    const sin = marcas(pintarLineaArea({ tipo, datos, series, campoEtiqueta: "name" }));
    assert.ok(sin.some((m) => m.includes(".")), `${tipo} sin el arreglo: ${sin}`);
    const con = marcas(pintarLineaArea({ tipo, datos, series, campoEtiqueta: "name", soloEnteros: true }));
    assert.ok(con.length > 0 && con.every((m) => !m.includes(".")), `${tipo} entero: ${con}`);
  }
});
