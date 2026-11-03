import test from "node:test";
import assert from "node:assert/strict";
import { RANGO_DIAS_MAX, idsAlDia, itemsAActualizar, resultadoFinal, sumarRespuestas } from "./kpiActualizar.js";

const HOY = new Date(2026, 9, 30); // 30 oct 2026
const CATALOGO = [
  { id_kpi_definition: 1, modo: "snapshot" },
  { id_kpi_definition: 2, modo: "snapshot" },
  { id_kpi_definition: 3, modo: "vivo" },
];
const widget = (ids, parametros, tipo = "barras") => ({ ids_kpi_definition: ids, tipo_grafica: tipo, parametros });

test("un item por indicador, con el rango que el widget muestra hoy", () => {
  const items = itemsAActualizar([widget([1], { rango_relativo: "30_dias", fecha_inicio: "2020-01-01", fecha_fin: "2020-01-30" })], CATALOGO, HOY);
  assert.equal(items.length, 1);
  assert.equal(items[0].id_kpi_definition, 1);
  assert.equal(items[0].fecha_fin, "2026-10-30");
  assert.notEqual(items[0].fecha_inicio, "2020-01-01");
});

test("un indicador en varios widgets pide la union de sus rangos", () => {
  const items = itemsAActualizar([
    widget([1], { fecha_inicio: "2026-10-01", fecha_fin: "2026-10-10" }),
    widget([1, 2], { fecha_inicio: "2026-09-20", fecha_fin: "2026-10-05" }),
  ], CATALOGO, HOY);
  assert.deepEqual(items, [
    { id_kpi_definition: 1, fecha_inicio: "2026-09-20", fecha_fin: "2026-10-10" },
    { id_kpi_definition: 2, fecha_inicio: "2026-09-20", fecha_fin: "2026-10-05" },
  ]);
});

test("el periodo de comparacion entra en la union", () => {
  const [item] = itemsAActualizar([widget([1], { fecha_inicio: "2026-10-01", fecha_fin: "2026-10-30", fecha_inicio_b: "2026-09-01", fecha_fin_b: "2026-09-30" })], CATALOGO, HOY);
  assert.deepEqual(item, { id_kpi_definition: 1, fecha_inicio: "2026-09-01", fecha_fin: "2026-10-30" });
});

test("si la union pasa del tope se queda con el rango principal", () => {
  const [item] = itemsAActualizar([widget([1], { fecha_inicio: "2026-10-01", fecha_fin: "2026-10-30", fecha_inicio_b: "2024-01-01", fecha_fin_b: "2024-01-30" })], CATALOGO, HOY);
  assert.deepEqual(item, { id_kpi_definition: 1, fecha_inicio: "2026-10-01", fecha_fin: "2026-10-30" });
  assert.equal(RANGO_DIAS_MAX, 365);
});

test("se omiten tablas, KPIs en vivo, KPIs sin permiso y widgets sin rango", () => {
  const items = itemsAActualizar([
    widget([3], { fecha_inicio: "2026-10-01", fecha_fin: "2026-10-30" }, "tabla"),
    widget([3], { fecha_inicio: "2026-10-01", fecha_fin: "2026-10-30" }),
    widget([99], { fecha_inicio: "2026-10-01", fecha_fin: "2026-10-30" }),
    widget([2], {}),
  ], CATALOGO, HOY);
  assert.deepEqual(items, []);
});

test("sumarRespuestas y idsAlDia cuentan indicadores", () => {
  const respuestas = [{ actualizados: [1], ya_al_dia: [], omitidos: [] }, { actualizados: [], ya_al_dia: [2], omitidos: [{ id_kpi_definition: 3 }] }];
  assert.deepEqual(sumarRespuestas(respuestas), { actualizados: 1, yaAlDia: 1, omitidos: 1 });
  assert.deepEqual(idsAlDia(respuestas), [1, 2]);
});

test("resultadoFinal distingue listo, ya al dia, nada, en curso y error", () => {
  const recalculado = [{ actualizados: [1], ya_al_dia: [2], omitidos: [] }];
  assert.deepEqual(resultadoFinal({ total: 2, respuestas: recalculado }), { tipo: "listo", actualizados: 1, yaAlDia: 1, omitidos: 0, alDia: 2 });
  assert.equal(resultadoFinal({ total: 1, respuestas: [{ actualizados: [], ya_al_dia: [1] }] }).tipo, "ya_al_dia");
  assert.equal(resultadoFinal({ total: 0, respuestas: [] }).tipo, "nada");
  assert.equal(resultadoFinal({ total: 2, respuestas: recalculado, fallo: "kpis.recalculation_in_progress" }).tipo, "en_curso");
  assert.equal(resultadoFinal({ total: 2, respuestas: recalculado, fallo: "errors.request_failed" }).tipo, "error");
});
