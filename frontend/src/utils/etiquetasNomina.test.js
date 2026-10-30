import test from "node:test";
import assert from "node:assert/strict";

import { crearEtiquetas, etiquetaConcepto, etiquetaPeriodo } from "./etiquetasNomina.js";

const periodos = [{ id_payroll_period: 2, period_start: "2026-10-12", period_end: "2026-10-16" }];
const usuarios = [{ id_user: 5, full_name: "Empleado Demo KPI 1", username: "kpi1" }];
const detalles = [{ id_payroll_detail: 9, id_user: 5, id_payroll_period: 2 }];
const conceptos = [{ id_payroll_concept: 3, payroll_concept_description: "Cuota obrera IMSS", payroll_code: "IMSS" }];

test("un periodo se nombra con su numero y sus fechas", () => {
  assert.equal(etiquetaPeriodo(periodos[0]), "#2 · 2026-10-12 al 2026-10-16");
});

test("un concepto lleva su codigo", () => {
  assert.equal(etiquetaConcepto(conceptos[0]), "Cuota obrera IMSS (IMSS)");
});

test("un detalle es el empleado en un periodo", () => {
  const e = crearEtiquetas({ periodos, usuarios, detalles, conceptos });
  assert.equal(e.detalle(9), "Empleado Demo KPI 1 · #2 · 2026-10-12 al 2026-10-16");
  assert.equal(e.usuario(5), "Empleado Demo KPI 1");
  assert.equal(e.concepto(3), "Cuota obrera IMSS (IMSS)");
});

test("si no se encuentra el registro se muestra el numero tal cual", () => {
  const e = crearEtiquetas({});
  assert.equal(e.usuario(77), "77");
  assert.equal(e.detalle(null), "");
});
