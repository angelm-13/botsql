import test from "node:test";
import assert from "node:assert/strict";
import { accionDeEnter, kpiAdmiteFiltros, puedeAgregar, puedeIrAlPaso } from "./kpiPasos.js";

test("hacia atras y el paso actual siempre se puede", () => {
  assert.equal(puedeIrAlPaso({ indice: 0, pasoActual: 2, puedeAvanzar: false }), true);
  assert.equal(puedeIrAlPaso({ indice: 1, pasoActual: 1, puedeAvanzar: false }), true);
});

test("hacia adelante solo el siguiente, y solo si se puede avanzar", () => {
  assert.equal(puedeIrAlPaso({ indice: 1, pasoActual: 0, puedeAvanzar: true }), true);
  assert.equal(puedeIrAlPaso({ indice: 1, pasoActual: 0, puedeAvanzar: false }), false);
});

test("desde 'Que medir' no se salta al paso 'Filtros' tocando su pestana", () => {
  assert.equal(puedeIrAlPaso({ indice: 2, pasoActual: 0, puedeAvanzar: true }), false);
});

test("el paso 'Filtros' se alcanza desde 'Periodo'", () => {
  assert.equal(puedeIrAlPaso({ indice: 2, pasoActual: 1, puedeAvanzar: true }), true);
});

test("Dashboard.jsx usa la regla de orden en las pestanas del asistente", async () => {
  const { readFileSync } = await import("node:fs");
  const fuente = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.match(fuente, /puedeIrAlPaso\(\{ indice, pasoActual, puedeAvanzar \}\)/);
  assert.doesNotMatch(fuente, /indice <= pasoActual \|\| puedeAvanzar/);
});

test("el paso Filtros solo existe si hay filtros aplicables y no es tabla", () => {
  assert.equal(kpiAdmiteFiltros({ hayAlgunFiltro: true, tipo: "barras" }), true);
  assert.equal(kpiAdmiteFiltros({ hayAlgunFiltro: false, tipo: "barras" }), false);
  assert.equal(kpiAdmiteFiltros({ hayAlgunFiltro: true, tipo: "tabla" }), false);
});

test("no se agrega sin haber visitado Filtros cuando el indicador los admite", () => {
  assert.equal(puedeAgregar({ admiteFiltros: true, visitados: ["medir", "periodo"] }), false);
  assert.equal(puedeAgregar({ admiteFiltros: true, visitados: [] }), false);
  assert.equal(puedeAgregar({ admiteFiltros: true, visitados: ["medir", "periodo", "filtros"] }), true);
  assert.equal(puedeAgregar({ admiteFiltros: true }), false);
});

test("sin filtros aplicables (o tabla) se puede agregar sin visitar Filtros", () => {
  assert.equal(puedeAgregar({ admiteFiltros: false, visitados: [] }), true);
});

test("Enter avanza en pasos intermedios, nunca guarda y no actua en el buscador", () => {
  assert.equal(accionDeEnter({ esUltimoPaso: false, puedeAvanzar: true, enBuscador: false }), "avanzar");
  assert.equal(accionDeEnter({ esUltimoPaso: false, puedeAvanzar: false, enBuscador: false }), "nada");
  assert.equal(accionDeEnter({ esUltimoPaso: false, puedeAvanzar: true, enBuscador: true }), "nada");
  assert.equal(accionDeEnter({ esUltimoPaso: true, puedeAvanzar: true, enBuscador: false }), "nada");
});

test("Siguiente y Agregar son botones distintos para React (key) y Enter se filtra", async () => {
  const { readFileSync } = await import("node:fs");
  const fuente = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.match(fuente, /key="paso-siguiente"/);
  assert.match(fuente, /key="paso-agregar"/);
  assert.match(fuente, /accionDeEnter\(/);
  assert.match(fuente, /puedeAgregar\(\{ admiteFiltros, visitados \}\)/);
});
