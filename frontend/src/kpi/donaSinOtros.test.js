// Un KPI que no se suma (porcentaje, promedio) no agrupa el sobrante en "Otros": sumar 4 personas al 83 % da un "Otros 333 %" sin sentido,
// y la API no manda el peso de cada una para promediarlas bien. Salen todas las rebanadas (hasta 12) y, si hay mas, "Mostrando N de M".
import test from "node:test";
import assert from "node:assert/strict";
import { propsDona } from "./kpiAdaptadores.js";
import { MAXIMO_DE_REBANADAS_SIN_OTROS, buildPieData, valoresNoSumables } from "./kpiDatos.js";

const formatNumber = (valor) => new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(valor || 0);
const TEXTOS = { otros: "Otros", registros: "registros", total: "total" };
const snap = (porEmpleado) => ({ rango_a: { total: 0, por_empleado: porEmpleado, por_periodo: {}, etiquetas: {} } });

// Valores REALES: GET /kpi_definition/ y /kpi_snapshot/query de incidentes_resueltos_por_empleado (12 personas) en tu base local.
const INCIDENTES_RESUELTOS = { id_kpi_definition: 5, clave: "incidentes_resueltos_por_empleado", unidad: "porcentaje", dimensiones: ["empleado"], agregacion: "promedio_ponderado", dimension_tipo: "persona", dimension_abierta: true };
const REAL = { 28: 83.33, 29: 83.33, 30: 83.33, 31: 83.33, 32: 100, 33: 100, 34: 100, 35: 80, 36: 100, 37: 83.33, 38: 83.33, 39: 83.33 };
const dona = (kpiInfo, porEmpleado) => propsDona({ snapshot: snap(porEmpleado), kpiInfo, labelForId: (id) => `P${id}`, agruparPorPeriodo: false, formatNumber, textos: TEXTOS });

test("valoresNoSumables: un porcentaje o un promedio si; un conteo o una suma no", () => {
  assert.equal(valoresNoSumables(INCIDENTES_RESUELTOS), true);
  assert.equal(valoresNoSumables({ unidad: "dias", agregacion: "promedio_ponderado" }), true);
  assert.equal(valoresNoSumables({ unidad: "porcentaje", agregacion: "suma" }), true);
  assert.equal(valoresNoSumables({ unidad: "numero", agregacion: "suma" }), false);
  assert.equal(valoresNoSumables({ unidad: "numero", agregacion: "ultimo" }), false);
  assert.equal(valoresNoSumables(undefined), false);
});

test("con los datos reales (12 personas, porcentaje): las 12 rebanadas, sin 'Otros', sin recorte y sin total al centro", () => {
  const props = dona(INCIDENTES_RESUELTOS, REAL);
  assert.equal(props.datos.length, 12);
  assert.ok(props.datos.every((d) => d.categoria !== "Otros"));
  assert.deepEqual(props.datos.slice(0, 4).map((d) => d.valor), [100, 100, 100, 100]);
  assert.equal(props.recorte, null);
  assert.equal(props.totalCentro, null);
  // Antes de este cambio el 9.o en adelante se sumaba: 83.33 x 3 + 80 = 330 (el "Otros 330 %").
  assert.ok(!props.datos.some((d) => d.valor > 100), "ninguna rebanada supera el 100 %");
});

test("con mas de 12 personas salen las 12 primeras y el recorte dice 'N de M'; el valor de cada una es el suyo", () => {
  const muchas = Object.fromEntries(Array.from({ length: 15 }, (_, i) => [String(i + 1), 100 - i]));
  const props = dona(INCIDENTES_RESUELTOS, muchas);
  assert.equal(MAXIMO_DE_REBANADAS_SIN_OTROS, 12);
  assert.equal(props.datos.length, 12);
  assert.deepEqual(props.recorte, { mostradas: 12, total: 15 });
  assert.deepEqual(props.datos.map((d) => d.valor), Array.from({ length: 12 }, (_, i) => 100 - i), "de mayor a menor");
  assert.equal(props.totalCentro, null);
});

test("un conteo con mas de 8 personas SIGUE agrupando 'Otros' (ahi si se puede sumar) y no trae recorte", () => {
  const conteo = { id_kpi_definition: 17, clave: "x", unidad: "numero", dimensiones: ["empleado"], agregacion: "suma", dimension_abierta: true };
  const muchas = Object.fromEntries(Array.from({ length: 12 }, (_, i) => [String(i + 1), 20 - i]));
  const props = dona(conteo, muchas);
  assert.equal(props.datos.length, 9);
  assert.equal(props.datos.at(-1).categoria, "Otros");
  assert.equal(props.datos.at(-1).valor, 12 + 11 + 10 + 9);
  assert.equal(props.recorte, null);
});

test("buildPieData: sin la bandera se comporta como siempre (Otros desde la 9.a)", () => {
  const porA = Object.fromEntries(Array.from({ length: 10 }, (_, i) => [String(i + 1), 10 - i]));
  const datos = buildPieData(snap(porA), (id) => id, "Otros", false, "empleado");
  assert.equal(datos.at(-1).name, "Otros");
  assert.equal(buildPieData(snap(porA), (id) => id, "Otros", false, "empleado", undefined, true).length, 10);
});

test("una dimension cerrada (estado) no se recorta aunque no se sume: nunca hubo 'Otros' ahi", () => {
  const estado = { unidad: "porcentaje", dimensiones: ["estado"], agregacion: "promedio_ponderado", dimension_abierta: false };
  const props = dona(estado, Object.fromEntries(Array.from({ length: 14 }, (_, i) => [`e${i}`, 50])));
  assert.equal(props.recorte, null);
});
