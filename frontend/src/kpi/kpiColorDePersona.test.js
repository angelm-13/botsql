import test from "node:test";
import assert from "node:assert/strict";
import { CATEGORICAL, COLOR_OTHERS, colorDeKpi, colorDePersona, hayColoresRepetidos } from "./kpiDatos.js";
import { propsDona, propsSeries } from "./kpiAdaptadores.js";

const formatNumber = (valor) => String(valor);
const TEXTOS = { rangoA: "Periodo A", rangoB: "Periodo B", comparacionCorta: "comp" };
const POR_PERSONA = { id_kpi_definition: 3, clave: "x_por_empleado", unidad: "numero", dimensiones: ["empleado"], dimension_tipo: "persona" };
const POR_ESTADO = { id_kpi_definition: 8, clave: "y", unidad: "numero", dimensiones: ["estado"], dimension_tipo: "categoria", colores_categoria: { abierta: "#ef6f5c", cerrada: "#22b573" } };
const POR_PRODUCTO = { id_kpi_definition: 9, clave: "z", unidad: "numero", dimensiones: ["producto"], dimension_tipo: "catalogo" };
const snap = (porEmpleado) => ({ rango_a: { total: 0, por_empleado: porEmpleado }, rango_b: null });

test("la variante 0 es el color de siempre: el tono de `id % 8`, igual que colorDeKpi", () => {
  for (const id of [0, 1, 5, 7, 24, 25, 48, 55]) assert.equal(colorDePersona(id), colorDeKpi(id), `id ${id}`);
});

test("ids de 8 en adelante: mismo tono base pero distinto color (aclarado, oscurecido), y se repite cada 24", () => {
  const id = 3;
  const colores = [id, id + 8, id + 16].map(colorDePersona);
  assert.equal(new Set(colores).size, 3);
  assert.equal(colores[0], CATEGORICAL[3]);
  assert.match(colores[1], /^#[0-9a-f]{6}$/);
  assert.equal(colorDePersona(id + 24), colores[0]);
});

test("24 ids consecutivos dan 24 colores distintos", () => {
  assert.equal(new Set(Array.from({ length: 24 }, (_, i) => colorDePersona(i))).size, 24);
});

test("es estable y acepta el id como texto; lo que no es una persona va en gris", () => {
  assert.equal(colorDePersona("12"), colorDePersona(12));
  assert.equal(colorDePersona(null), COLOR_OTHERS);
  assert.equal(colorDePersona(""), COLOR_OTHERS);
  assert.equal(colorDePersona(undefined), COLOR_OTHERS);
  assert.equal(colorDePersona("sin_asignar"), COLOR_OTHERS);
});

test("hayColoresRepetidos ignora el gris de 'Otros' y 'Sin asignar'", () => {
  assert.equal(hayColoresRepetidos(["#111111", "#222222"]), false);
  assert.equal(hayColoresRepetidos(["#111111", "#222222", "#111111"]), true);
  assert.equal(hayColoresRepetidos([COLOR_OTHERS, COLOR_OTHERS]), false);
  assert.equal(hayColoresRepetidos(undefined), false);
});

test("barras por persona: cada barra con el color de su persona; 'Sin asignar' en gris; sin patrones si no chocan", () => {
  const props = propsSeries({
    tipo: "barras", snapshots: [snap({ 5: 10, 12: 4, sin_asignar: 1 })], kpiInfos: [POR_PERSONA],
    labelForId: (id) => `P${id}`, agruparPorPeriodo: false, formatNumber, textos: TEXTOS,
  });
  assert.deepEqual(props.datos.map((fila) => props.colorPorFila(fila)), [colorDePersona(5), colorDePersona(12), COLOR_OTHERS]);
  assert.equal(props.conPatrones, false);
  assert.equal(props.series[0].color, colorDeKpi(3));
});

test("barras por persona: dos personas con el mismo color (ids a 24 de distancia) llevan patron SOLO si el widget eligio texturas", () => {
  const barras = (relleno) => propsSeries({
    tipo: "barras", snapshots: [snap({ 5: 10, 29: 4 })], kpiInfos: [POR_PERSONA],
    labelForId: (id) => `P${id}`, agruparPorPeriodo: false, formatNumber, textos: TEXTOS, ...(relleno ? { relleno } : {}),
  });
  assert.equal(colorDePersona(5), colorDePersona(29), "el caso de la prueba: colores repetidos");
  assert.equal(barras().conPatrones, false, "sin la opcion (widget de antes) es solido");
  assert.equal(barras("solido").conPatrones, false);
  assert.equal(barras("textura").conPatrones, true);
  assert.equal(barras("textura").colorPorFila({ id: 5 }), colorDePersona(5), "con textura la barra conserva el color de su persona");
});

test("linea y area, por periodo y KPIs por estado o producto no cambian: color del KPI o de la categoria", () => {
  const base = { snapshots: [snap({ 5: 10 })], labelForId: (id) => `P${id}`, formatNumber, textos: TEXTOS };
  assert.equal(propsSeries({ ...base, tipo: "linea", kpiInfos: [POR_PERSONA], agruparPorPeriodo: false }).colorPorFila, null);
  assert.equal(propsSeries({ ...base, tipo: "area", kpiInfos: [POR_PERSONA], agruparPorPeriodo: false }).colorPorFila, null);
  assert.equal(propsSeries({ ...base, tipo: "barras", kpiInfos: [POR_PERSONA], agruparPorPeriodo: true }).colorPorFila, null);
  assert.equal(propsSeries({ ...base, tipo: "barras", kpiInfos: [POR_PRODUCTO], agruparPorPeriodo: false }).colorPorFila, null);
  const estado = propsSeries({ ...base, snapshots: [snap({ abierta: 5 })], tipo: "barras", kpiInfos: [POR_ESTADO], agruparPorPeriodo: false });
  assert.equal(estado.colorPorFila({ id: "abierta" }), "#ef6f5c");
});

test("dona por persona: color de cada persona, 'Otros' en gris y patrones solo con relleno textura", () => {
  const dona = (porEmpleado, relleno) => propsDona({
    snapshot: snap(porEmpleado), kpiInfo: POR_PERSONA, labelForId: (id) => `P${id}`,
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" }, ...(relleno ? { relleno } : {}),
  });
  const sinChoque = dona({ 5: 10, 6: 4 });
  assert.deepEqual(sinChoque.datos.map((d) => d.color), [colorDePersona(5), colorDePersona(6)]);
  assert.equal(sinChoque.conPatrones, false);

  const muchos = {};
  for (let id = 1; id <= 12; id += 1) muchos[id] = 100 - id;
  const conOtros = dona(muchos);
  assert.equal(conOtros.datos.at(-1).color, COLOR_OTHERS);
  assert.equal(conOtros.conPatrones, false);

  assert.equal(dona({ 5: 10, 29: 4 }).conPatrones, false, "colores repetidos ya no fuerzan patrones: lo decide el relleno");
  assert.equal(dona({ 5: 10, 6: 4 }, "textura").conPatrones, true);
  assert.equal(dona({ 5: 10, 6: 4 }, "solido").conPatrones, false);
});

test("dona por estado conserva colores_categoria y por producto la paleta por posicion", () => {
  const estado = propsDona({
    snapshot: snap({ abierta: 5, cerrada: 2 }), kpiInfo: POR_ESTADO, labelForId: (id) => id,
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.deepEqual(estado.datos.map((d) => d.color), ["#ef6f5c", "#22b573"]);
  const producto = propsDona({
    snapshot: snap({ 1: 5, 2: 2 }), kpiInfo: POR_PRODUCTO, labelForId: (id) => `P${id}`,
    agruparPorPeriodo: false, formatNumber, textos: { otros: "Otros" },
  });
  assert.deepEqual(producto.datos.map((d) => d.color), [CATEGORICAL[0], CATEGORICAL[1]]);
});
