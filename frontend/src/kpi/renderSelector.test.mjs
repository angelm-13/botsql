// Prueba de RENDER del selector de KPI del editor (SelectorDeKpi.jsx): que
// agrupe por modulo, que "Variables" sea un grupo mas, que el buscador filtre y
// que las opciones de otra unidad salgan deshabilitadas y con tooltip.
import assert from "node:assert/strict";
import test, { before } from "node:test";
import { cargarRender } from "./bundleRender.mjs";

let pintarSelector;

before(async () => {
  ({ pintarSelector } = await cargarRender());
});

const KPI = (id, etiqueta, modulo, unidad, extra = {}) => ({
  id_kpi_definition: id, etiqueta, clave: `k${id}`, modulo, unidad, dimensiones: ["empleado"], modo: "snapshot",
  descripcion: `Descripcion de ${etiqueta}`, ...extra,
});
const CATALOGO = [
  KPI(1, "Incidencias abiertas por responsable", "operaciones", "numero"),
  KPI(2, "Incidentes resueltos por empleado", "operaciones", "porcentaje"),
  KPI(3, "Cancelaciones por empleado", "operaciones", "numero"),
  KPI(4, "Existencias en almacén", "inventario", "piezas"),
  KPI(5, "Ingresos totales", "facturacion", "moneda", { dimensiones: ["global"] }),
  KPI(6, "Egresos totales", "facturacion", "moneda", { dimensiones: ["global"] }),
  KPI(11, "Material prestado ahora", "operaciones", "piezas", { modo: "vivo" }),
];

const pintar = (props) => pintarSelector({ catalogo: CATALOGO, seleccionados: [], multiple: false, ...props });
// Las filas del selector, para revisar una por una.
const filas = (html) => [...html.matchAll(/<div class="kpi-selector-fila[^"]*"[^>]*>.*?<\/button>/gs)].map((m) => m[0]);
const filaDe = (html, etiqueta) => filas(html).find((fila) => fila.includes(etiqueta));

test("agrupa por modulo y pone las variables como un grupo mas, al final", () => {
  const html = pintar({});
  const grupos = [...html.matchAll(/data-grupo="([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(grupos, ["operaciones", "inventario", "variables"]);
  assert.ok(html.includes("Modulo operaciones") && html.includes("Modulo inventario"));
  assert.ok(html.includes("Variables"), "titulo del grupo Variables");
  // Las variables NO aparecen dentro de su modulo (facturacion no es un grupo).
  assert.ok(!html.includes("Modulo facturacion"));
  const variables = html.slice(html.indexOf('data-grupo="variables"'));
  assert.ok(variables.includes("Ingresos totales") && variables.includes("Egresos totales"));
});

test("cada opcion muestra nombre, unidad con su etiqueta y descripcion", () => {
  const fila = filaDe(pintar({}), "Incidentes resueltos por empleado");
  assert.ok(fila.includes("Descripcion de Incidentes resueltos por empleado"));
  assert.ok(fila.includes(">%<"), "unidad porcentaje -> %");
  assert.ok(filaDe(pintar({}), "Existencias en almacén").includes(">Piezas<"));
});

test("el buscador filtra por nombre y descripcion, sin acentos ni mayusculas, y quita los grupos vacios", () => {
  const porNombre = pintar({ busquedaInicial: "EXISTENCIAS" });
  assert.deepEqual([...porNombre.matchAll(/data-grupo="([^"]+)"/g)].map((m) => m[1]), ["inventario"]);
  const sinAcento = pintar({ busquedaInicial: "almacen" });
  assert.ok(sinAcento.includes("Existencias en almacén"), "'almacen' encuentra 'almacén'");
  const porDescripcion = pintar({ busquedaInicial: "descripcion de egresos" });
  assert.ok(porDescripcion.includes("Egresos totales") && !porDescripcion.includes("Ingresos totales"));
  assert.ok(pintar({ busquedaInicial: "zzzz" }).includes("Ningún KPI coincide"));
});

test("con un solo KPI por grafico nada se bloquea: elegir otro simplemente lo reemplaza", () => {
  const html = pintar({ seleccionados: ["1"], multiple: false });
  assert.ok(!html.includes("disabled"));
  assert.ok(!html.includes("BLOQUEADO"));
});

test("al combinar varios, los de otra unidad salen deshabilitados y con tooltip; los de la misma no", () => {
  const html = pintar({ seleccionados: ["1"], multiple: true });
  const bloqueada = filaDe(html, "Incidentes resueltos por empleado"); // porcentaje vs numero
  assert.ok(bloqueada.includes("disabled"), "deshabilitada");
  assert.ok(bloqueada.includes('title="BLOQUEADO(unidad): Incidentes resueltos por empleado"'), "tooltip en la fila");
  const libre = filaDe(html, "Cancelaciones por empleado"); // numero, igual
  assert.ok(!libre.includes("disabled") && !libre.includes("BLOQUEADO"));
  // Un KPI en vivo no se mezcla con uno de serie.
  assert.ok(filaDe(html, "Material prestado ahora").includes("BLOQUEADO(modo)"));
});

test("un KPI ya elegido nunca se bloquea, lleva su numero de orden y su color", () => {
  const html = pintar({ seleccionados: ["1", "3"], multiple: true, onElegirColor: () => {}, coloresKpi: { 3: "#123456" } });
  const primera = filaDe(html, "Incidencias abiertas por responsable");
  const segunda = filaDe(html, "Cancelaciones por empleado");
  assert.ok(primera.includes("kpi-chip-badge") && primera.includes(">1<"));
  assert.ok(segunda.includes(">2<"));
  assert.ok(!primera.includes("disabled") && !segunda.includes("disabled"));
  assert.ok(html.includes("kpi-color-swatch") && html.includes("background:#123456"), "el circulo de color usa el override");
  assert.ok(primera.includes("activo") && primera.includes('aria-pressed="true"'));
});
