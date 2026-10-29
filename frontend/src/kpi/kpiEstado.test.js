import test from "node:test";
import assert from "node:assert/strict";
import { CON_DATOS, NO_CALCULADO, SIN_DATOS, estadoDeDatos } from "./kpiEstado.js";

const rango = (extra) => ({ rango_a: { total: 0, por_empleado: {}, por_periodo: {}, ...extra } });

test("un 0 con filas es un 0: con datos", () => {
  assert.equal(estadoDeDatos([rango({ n_filas: 3, calculado: true })]), CON_DATOS);
});

test("sin filas en el rango pero con el KPI calculado en otras fechas: sin datos en el periodo", () => {
  assert.equal(estadoDeDatos([rango({ n_filas: 0, calculado: true })]), SIN_DATOS);
});

test("un KPI que nunca se calculo: no calculado", () => {
  assert.equal(estadoDeDatos([rango({ n_filas: 0, calculado: false })]), NO_CALCULADO);
});

test("con varios KPIs: solo es 'sin datos' o 'no calculado' si NINGUNO trae filas", () => {
  assert.equal(estadoDeDatos([rango({ n_filas: 0, calculado: true }), rango({ n_filas: 5, calculado: true })]), CON_DATOS);
  assert.equal(estadoDeDatos([rango({ n_filas: 0, calculado: false }), rango({ n_filas: 0, calculado: true })]), SIN_DATOS);
  assert.equal(estadoDeDatos([rango({ n_filas: 0, calculado: false }), rango({ n_filas: 0, calculado: false })]), NO_CALCULADO);
});

test("un servidor sin los campos nuevos se muestra como siempre", () => {
  assert.equal(estadoDeDatos([rango({})]), CON_DATOS);
  assert.equal(estadoDeDatos([]), CON_DATOS);
  assert.equal(estadoDeDatos(undefined), CON_DATOS);
});
