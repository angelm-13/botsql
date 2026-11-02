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

test("sin agregacion suma no hay total: promedio, vivo, sin declarar; una foto solo si es por estado y de conteo", () => {
  for (const agregacion of ["promedio_ponderado", null, undefined]) {
    assert.equal(totalCentroDeDona(DATOS, kpi({ agregacion }), formatNumber, TEXTOS), null, String(agregacion));
  }
  assert.equal(totalCentroDeDona(DATOS, undefined, formatNumber, TEXTOS), null);
  // Foto ("ultimo") por estado y en conteo: los estados son excluyentes, asi que sumarlos es el total de la foto.
  assert.equal(totalCentroDeDona(DATOS, kpi({ agregacion: "ultimo" }), formatNumber, TEXTOS).texto, "34");
  assert.equal(totalCentroDeDona(DATOS, kpi({ agregacion: "ultimo", unidad: "piezas" }), formatNumber, TEXTOS).detalle, "piezas");
  // Una foto por equipo, persona o producto no se suma (una persona en dos equipos contaria dos veces), ni una en pesos o minutos.
  for (const dimension of ["equipo", "empleado", "producto"]) {
    assert.equal(totalCentroDeDona(DATOS, kpi({ agregacion: "ultimo", dimensiones: [dimension] }), formatNumber, TEXTOS), null, dimension);
  }
  for (const unidad of ["moneda", "minutos", "porcentaje"]) assert.equal(totalCentroDeDona(DATOS, kpi({ agregacion: "ultimo", unidad }), formatNumber, TEXTOS), null, unidad);
});

// Valores REALES: lo que devuelve GET /kpi_definition/ (unidad, dimensiones, agregacion) y /kpi_snapshot/query en tu base local.
const REAL = {
  tareas_por_estado: { id_kpi_definition: 341, clave: "tareas_por_estado", unidad: "numero", dimensiones: ["estado"], agregacion: "ultimo", dimension_tipo: "categoria" },
  proyectos_por_estado_comercial: { id_kpi_definition: 339, clave: "proyectos_por_estado_comercial", unidad: "numero", dimensiones: ["estado"], agregacion: "ultimo", dimension_tipo: "categoria" },
  incidentes_resueltos_por_empleado: { id_kpi_definition: 5, clave: "incidentes_resueltos_por_empleado", unidad: "porcentaje", dimensiones: ["empleado"], agregacion: "promedio_ponderado", dimension_tipo: "persona" },
};
const snap = (porEmpleado) => ({ rango_a: { total: 0, por_empleado: porEmpleado, por_periodo: {}, etiquetas: {} } });
const dona = (kpiInfo, porEmpleado) => propsDona({ snapshot: snap(porEmpleado), kpiInfo, labelForId: (id) => id, agruparPorPeriodo: false, formatNumber, textos: TEXTOS });

test("con los datos reales: la dona de Tareas por estado muestra '24 registros' y la de Proyectos por estado comercial, su total", () => {
  const tareas = dona(REAL.tareas_por_estado, { bloqueada: 4, cancelada: 2, en_proceso: 5, en_revision: 2, pendiente: 5, sin_estado: 1, terminada: 5 });
  assert.equal(tareas.totalCentro.texto, "24");
  assert.equal(tareas.totalCentro.detalle, "registros");
  const proyectos = dona(REAL.proyectos_por_estado_comercial, { pendiente_orden_compra: 4, autorizado: 4, cancelado: 2, cobrado: 3 });
  assert.equal(proyectos.totalCentro.texto, "13");
});

test("con los datos reales: la dona de Incidentes resueltos por empleado (porcentaje, promedio) no muestra total", () => {
  const props = dona(REAL.incidentes_resueltos_por_empleado, { 28: 83.33, 29: 83.33, 30: 83.33, 31: 83.33, 32: 100, 33: 100, 34: 100, 35: 80, 36: 100, 37: 83.33, 38: 83.33, 39: 83.33 });
  assert.equal(props.totalCentro, null);
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
    snapshot: { rango_a: { total: 34, por_empleado: { abierta: 20, cerrada: 14 } } }, kpiInfo: kpi({ agregacion: "promedio_ponderado" }),
    labelForId: (id) => id, agruparPorPeriodo: false, formatNumber, textos: TEXTOS,
  });
  assert.equal(sinSuma.totalCentro, null);
});
