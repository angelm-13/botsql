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

const botonesDeModulo = (html) => [...html.matchAll(/<button[^>]*data-modulo="([^"]+)"[^>]*>(.*?)<\/button>/gs)]
  .map((m) => ({ clave: m[1], html: m[0], texto: m[2].replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim() }));
const gruposVisibles = (html) => [...html.matchAll(/data-grupo="([^"]+)"/g)].map((m) => m[1]);

test("arriba hay un boton por modulo, con su conteo, y las variables son un boton mas al final", () => {
  const botones = botonesDeModulo(pintar({}));
  assert.deepEqual(botones.map((b) => b.clave), ["operaciones", "inventario", "variables"]);
  assert.match(botones[0].texto, /Modulo operaciones 4/, "operaciones tiene 4 KPIs (3 de serie y 1 en vivo)");
  assert.match(botones[1].texto, /Modulo inventario 1/);
  assert.match(botones[2].texto, /Variables 2/);
  // Facturacion solo aporta variables: no es un modulo aparte.
  assert.ok(!botones.some((b) => b.clave === "facturacion"));
});

test("abre en el primer modulo y muestra SOLO sus KPIs, no la lista completa", () => {
  const html = pintar({});
  assert.deepEqual(gruposVisibles(html), ["operaciones"]);
  assert.ok(html.includes("Cancelaciones por empleado"));
  assert.ok(!html.includes("Existencias en almacén"), "los de inventario no se ven");
  assert.ok(!html.includes("Ingresos totales"), "ni las variables");
  const activo = botonesDeModulo(html).filter((b) => b.html.includes('aria-pressed="true"'));
  assert.deepEqual(activo.map((b) => b.clave), ["operaciones"]);
  assert.ok(activo[0].html.includes("kpi-editor-tipo-check"), "el elegido lleva check ademas del color");
  assert.ok(activo[0].html.includes("--tinte"), "y su color propio");
});

test("abre en el modulo del primer KPI ya elegido", () => {
  const enInventario = pintar({ seleccionados: ["4"] });
  assert.deepEqual(gruposVisibles(enInventario), ["inventario"]);
  const enVariables = pintar({ seleccionados: ["6", "1"] }); // el primero elegido manda
  assert.deepEqual(gruposVisibles(enVariables), ["variables"]);
  assert.ok(enVariables.includes("Egresos totales") && enVariables.includes("Sin desglose"));
});

test("cada boton de modulo dice cuantos de sus KPIs estan elegidos (la seleccion se conserva al cambiar)", () => {
  const html = pintar({ seleccionados: ["1", "3", "4"], multiple: true });
  const botones = Object.fromEntries(botonesDeModulo(html).map((b) => [b.clave, b.html]));
  assert.ok(botones.operaciones.includes('class="kpi-selector-modulo-elegidos"') && botones.operaciones.includes(">2<"));
  assert.ok(botones.inventario.includes("kpi-selector-modulo-elegidos") && botones.inventario.includes(">1<"));
  assert.ok(!botones.variables.includes("kpi-selector-modulo-elegidos"));
  // Cambiar de modulo (aqui: abrir en otro) tampoco altera el orden: sigue siendo el de eleccion.
  const enInventario = pintar({ seleccionados: ["1", "3", "4"], multiple: true, moduloInicial: "inventario" });
  assert.ok(filaDe(enInventario, "Existencias en almacén").includes(">3<"), "el 3ro elegido conserva su numero");
});

test("con un solo modulo en el catalogo no hay fila de botones, pero si el titulo del grupo", () => {
  const soloOperaciones = CATALOGO.filter((kpi) => kpi.modulo === "operaciones" && !kpi.dimensiones.includes("global"));
  const html = pintarSelector({ catalogo: soloOperaciones, seleccionados: [], multiple: false });
  assert.deepEqual(botonesDeModulo(html), []);
  assert.ok(!html.includes("kpi-selector-modulos"));
  assert.deepEqual(gruposVisibles(html), ["operaciones"]);
  assert.ok(html.includes("Modulo operaciones"), "sin botones, el titulo dice en que modulo se esta");
  // Un catalogo que solo trae variables tampoco muestra botones.
  const soloVariables = CATALOGO.filter((kpi) => kpi.dimensiones.includes("global"));
  assert.deepEqual(botonesDeModulo(pintarSelector({ catalogo: soloVariables, seleccionados: [], multiple: false })), []);
});

test("un modulo que no llega en el catalogo (plan o permiso) no tiene boton", () => {
  const sinInventario = CATALOGO.filter((kpi) => kpi.modulo !== "inventario");
  assert.deepEqual(botonesDeModulo(pintar({ catalogo: sinInventario })).map((b) => b.clave), ["operaciones", "variables"]);
});

test("cada opcion muestra nombre, unidad con su etiqueta y descripcion", () => {
  const fila = filaDe(pintar({}), "Incidentes resueltos por empleado");
  assert.ok(fila.includes("Descripcion de Incidentes resueltos por empleado"));
  assert.ok(fila.includes(">%<"), "unidad porcentaje -> %");
  assert.ok(filaDe(pintar({ moduloInicial: "inventario" }), "Existencias en almacén").includes(">Piezas<"));
});

test("con texto, el buscador recorre TODOS los modulos y muestra los resultados agrupados por modulo", () => {
  const html = pintar({ busquedaInicial: "por empleado" }); // 3 de operaciones; nada de inventario
  assert.deepEqual(gruposVisibles(html), ["operaciones"]);
  const varios = pintar({ busquedaInicial: "totales" }); // ingresos y egresos: variables
  assert.deepEqual(gruposVisibles(varios), ["variables"]);
  const cruza = pintar({ busquedaInicial: "de" }); // aparece en todos los modulos
  assert.deepEqual(gruposVisibles(cruza), ["operaciones", "inventario", "variables"]);
  assert.ok(cruza.includes("Modulo operaciones") && cruza.includes("Modulo inventario"), "cada grupo con su titulo");
});

test("mientras hay texto ningun boton esta activo, cuentan coincidencias y los que no tienen se deshabilitan", () => {
  const html = pintar({ busquedaInicial: "EXISTENCIAS" });
  const botones = botonesDeModulo(html);
  assert.ok(botones.every((b) => !b.html.includes('aria-pressed="true"')));
  const porClave = Object.fromEntries(botones.map((b) => [b.clave, b]));
  assert.match(porClave.inventario.texto, /Modulo inventario 1/);
  assert.ok(!porClave.inventario.html.includes("disabled"));
  assert.match(porClave.operaciones.texto, /Modulo operaciones 0/);
  assert.ok(porClave.operaciones.html.includes("disabled"), "sin coincidencias no se puede elegir");
});

test("el buscador filtra por nombre y descripcion, sin acentos ni mayusculas, y quita los grupos vacios", () => {
  const porNombre = pintar({ busquedaInicial: "EXISTENCIAS" });
  assert.deepEqual(gruposVisibles(porNombre), ["inventario"]);
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
