import test from "node:test";
import assert from "node:assert/strict";
import { PATRONES, anchoDelEje, rellenoConPatron, descripcionDeGrafica, formatoDeEje, patronDeIndice, unidadDeLaGrafica } from "./kpiAccesibilidad.js";

const formatNumber = (valor) => String(valor);

test("cada categoria recibe un patron distinto, y se repiten solo al pasar de la lista", () => {
  assert.equal(new Set(PATRONES).size, PATRONES.length);
  assert.deepEqual([0, 1, 2, 3].map(patronDeIndice), PATRONES.slice(0, 4));
  assert.equal(patronDeIndice(PATRONES.length), PATRONES[0]);
  assert.equal(patronDeIndice(-1), PATRONES[PATRONES.length - 1]);
});

test("la unidad del eje es la de los KPIs si es una sola; con unidades mezcladas no hay", () => {
  assert.equal(unidadDeLaGrafica([{ unidad: "minutos" }]), "minutos");
  assert.equal(unidadDeLaGrafica([{ unidad: "minutos" }, { unidad: "minutos" }]), "minutos");
  assert.equal(unidadDeLaGrafica([{ unidad: "minutos" }, { unidad: "moneda" }]), null);
  assert.equal(unidadDeLaGrafica([{}]), "numero");
});

test("las marcas del eje llevan la unidad; 'numero' no lleva nada", () => {
  assert.equal(formatoDeEje("porcentaje", formatNumber)(50), "50%");
  assert.equal(formatoDeEje("moneda", formatNumber)(1200), "$1200");
  assert.equal(formatoDeEje("minutos", formatNumber)(30), "30 min");
  assert.equal(formatoDeEje("numero", formatNumber), null);
  assert.equal(formatoDeEje(null, formatNumber), null);
});

test("el eje se ensancha con una unidad de sufijo largo", () => {
  assert.equal(anchoDelEje("numero"), 60);
  assert.equal(anchoDelEje("porcentaje"), 60);
  assert.ok(anchoDelEje("piezas") > anchoDelEje("minutos"));
});

test("la descripcion dice el tipo, el KPI, cuantos puntos hay y el mayor", () => {
  const texto = descripcionDeGrafica({
    nombres: "Incidentes resueltos",
    datos: [{ name: "Ana", a: 3 }, { name: "Beto", a: 12 }],
    formatear: (v) => `${v} min`,
    textos: { tipo: "Barras", puntos: "puntos de datos", mayor: "Mayor" },
  });
  assert.equal(texto, "Barras: Incidentes resueltos. 2 puntos de datos. Mayor: Beto (12 min).");
});

test("sin filas la descripcion no inventa un mayor", () => {
  const texto = descripcionDeGrafica({ nombres: "X", datos: [], textos: { tipo: "Dona", puntos: "puntos de datos", mayor: "Mayor" } });
  assert.equal(texto, "Dona: X. 0 puntos de datos.");
});

test("el relleno de una categoria apunta a su patron", () => {
  assert.equal(rellenoConPatron("w1", 2), "url(#w1-2)");
});
