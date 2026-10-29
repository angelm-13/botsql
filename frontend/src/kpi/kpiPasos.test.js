import test from "node:test";
import assert from "node:assert/strict";
import { puedeIrAlPaso } from "./kpiPasos.js";

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
