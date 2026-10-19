// Prueba de RENDER del selector de KPI del editor (SelectorDeKpi.jsx): que
// agrupe por modulo (cada pestana con TODOS los KPIs de su modulo, los sin desglose al final
// como "Combinables"), que "Variables" sea la vista transversal con la etiqueta del modulo de
// cada tarjeta, que el buscador filtre y que las opciones de otra unidad salgan deshabilitadas
// y con tooltip.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
  assert.deepEqual(botones.map((b) => b.clave), ["operaciones", "inventario", "facturacion", "variables"]);
  assert.match(botones[0].texto, /Modulo operaciones 4/, "operaciones tiene 4 KPIs (3 de serie y 1 en vivo)");
  assert.match(botones[1].texto, /Modulo inventario 1/);
  assert.match(botones[2].texto, /Modulo facturacion 2/, "facturacion solo tiene KPIs sin desglose y aun asi es una pestana con su total");
  assert.match(botones[3].texto, /Variables 2/);
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

test("los textos del selector se pueden traducir: el aria-label de los modulos y el tooltip de los elegidos", () => {
  // Por omision, en espanol.
  const porOmision = pintar({ seleccionados: ["1", "3", "4"], multiple: true });
  assert.ok(porOmision.includes('aria-label="Módulos"'));
  assert.ok(porOmision.includes('title="2 elegidos en este módulo"') && porOmision.includes('title="1 elegidos en este módulo"'));
  // Con los textos que manda el Dashboard en otro idioma.
  const textos = { modulos: "Modules", elegidosEnModulo: "selected in this module" };
  const traducido = pintar({ seleccionados: ["1", "3", "4"], multiple: true, textos });
  assert.ok(traducido.includes('aria-label="Modules"') && !traducido.includes('aria-label="Módulos"'));
  assert.ok(traducido.includes('title="2 selected in this module"') && traducido.includes('title="1 selected in this module"'));
  assert.ok(!traducido.includes("elegidos en este módulo"));
});

test("abre en el modulo del primer KPI ya elegido", () => {
  const enInventario = pintar({ seleccionados: ["4"] });
  assert.deepEqual(gruposVisibles(enInventario), ["inventario"]);
  const enFacturacion = pintar({ seleccionados: ["6", "1"] }); // el primero elegido manda; un sin desglose abre en SU modulo
  assert.deepEqual(gruposVisibles(enFacturacion), ["facturacion"]);
  assert.ok(enFacturacion.includes("Egresos totales") && enFacturacion.includes("Combinables (sin desglose)"));
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
  // Un catalogo que solo trae sin desglose de UN modulo tampoco: «Variables» es la vista transversal y con un solo
  // modulo no hay nada que cruzar (seria repetir sus combinables).
  const soloVariables = CATALOGO.filter((kpi) => kpi.dimensiones.includes("global"));
  const htmlSoloVariables = pintarSelector({ catalogo: soloVariables, seleccionados: [], multiple: false });
  assert.deepEqual(botonesDeModulo(htmlSoloVariables), []);
  assert.deepEqual(gruposVisibles(htmlSoloVariables), ["facturacion"]);
});

test("un modulo que no llega en el catalogo (plan o permiso) no tiene boton", () => {
  const sinInventario = CATALOGO.filter((kpi) => kpi.modulo !== "inventario");
  assert.deepEqual(botonesDeModulo(pintar({ catalogo: sinInventario })).map((b) => b.clave), ["operaciones", "facturacion", "variables"]);
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
  const varios = pintar({ busquedaInicial: "totales" }); // ingresos y egresos: su modulo y Variables
  assert.deepEqual(gruposVisibles(varios), ["facturacion", "variables"]);
  const cruza = pintar({ busquedaInicial: "de" }); // aparece en todos los modulos
  assert.deepEqual(gruposVisibles(cruza), ["operaciones", "inventario", "facturacion", "variables"]);
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

// --- cada pestana con TODOS sus KPIs; "Variables" transversal con etiqueta de modulo -------------------
// Un KPI sin desglose de operaciones, para tener un modulo con las dos clases.
const CON_COMBINABLE = [...CATALOGO, KPI(7, "Pendientes hoy", "operaciones", "numero", { dimensiones: ["global"] })];
const etiquetaDeModulo = (html, etiqueta) => /data-modulo-tag="([^"]+)"[^>]*>([^<]*)</.exec(filaDe(html, etiqueta) || "")?.slice(1);

test("la pestana de un modulo muestra todos sus KPIs: primero los de desglose y al final «Combinables (sin desglose)»", () => {
  const html = pintar({ catalogo: CON_COMBINABLE, moduloInicial: "operaciones" });
  assert.deepEqual(gruposVisibles(html), ["operaciones"]);
  assert.ok(html.includes('data-seccion="combinables"') && html.includes("Combinables (sin desglose)"));
  const posicion = (texto) => html.indexOf(texto);
  assert.ok(posicion("Cancelaciones por empleado") < posicion("Combinables (sin desglose)"), "los de desglose van antes de la seccion");
  assert.ok(posicion("Combinables (sin desglose)") < posicion("Pendientes hoy"), "el sin desglose va dentro de la seccion, al final");
  // Un modulo sin KPIs sin desglose no lleva la seccion.
  assert.ok(!pintar({ catalogo: CON_COMBINABLE, moduloInicial: "inventario" }).includes("Combinables"));
  // Un modulo con solo sin desglose (facturacion) la lleva y tambien su pestana.
  const facturacion = pintar({ moduloInicial: "facturacion" });
  assert.ok(facturacion.includes("Combinables (sin desglose)") && facturacion.includes("Ingresos totales") && facturacion.includes("Egresos totales"));
});

test("el contador de la pestana es el total del modulo, con sus combinables", () => {
  const botones = botonesDeModulo(pintar({ catalogo: CON_COMBINABLE }));
  assert.match(botones.find((b) => b.clave === "operaciones").texto, /Modulo operaciones 5/, "4 de siempre + 1 sin desglose");
  assert.match(botones.find((b) => b.clave === "variables").texto, /Variables 3/, "los 3 sin desglose, de dos modulos");
});

test("«Variables» junta los sin desglose de todos los modulos y cada tarjeta lleva la etiqueta de su modulo", () => {
  const variables = pintar({ catalogo: CON_COMBINABLE, moduloInicial: "variables" });
  assert.deepEqual(gruposVisibles(variables), ["variables"]);
  assert.deepEqual(etiquetaDeModulo(variables, "Ingresos totales"), ["facturacion", "Modulo facturacion"]);
  assert.deepEqual(etiquetaDeModulo(variables, "Egresos totales"), ["facturacion", "Modulo facturacion"]);
  assert.deepEqual(etiquetaDeModulo(variables, "Pendientes hoy"), ["operaciones", "Modulo operaciones"]);
  assert.equal(filas(variables).length, 3);
  assert.ok(!variables.includes("Cancelaciones por empleado"), "los que tienen desglose no son variables");
  // En la pestana de su modulo no hace falta la etiqueta.
  assert.ok(!pintar({ catalogo: CON_COMBINABLE, moduloInicial: "facturacion" }).includes("kpi-selector-modulo-tag"));
});

test("un KPI que sale en dos pestanas se elige y se comporta igual: mismo id, mismo orden, mismo bloqueo", () => {
  for (const moduloInicial of ["facturacion", "variables"]) {
    const elegido = pintar({ catalogo: CON_COMBINABLE, seleccionados: ["5"], multiple: true, moduloInicial });
    const fila = filaDe(elegido, "Ingresos totales");
    assert.ok(fila.includes('aria-pressed="true"') && fila.includes("kpi-chip-badge") && fila.includes(">1<"), `${moduloInicial}: elegido y con su numero`);
    // Con un KPI de otra unidad elegido (numero vs moneda), se bloquea igual en las dos pestanas.
    const bloqueado = filaDe(pintar({ catalogo: CON_COMBINABLE, seleccionados: ["1"], multiple: true, moduloInicial }), "Ingresos totales");
    assert.ok(bloqueado.includes("disabled") && bloqueado.includes('title="BLOQUEADO(unidad): Ingresos totales"'), `${moduloInicial}: bloqueado por unidad`);
    // Y uno de la misma unidad (moneda: Egresos) sigue libre en las dos.
    const libre = filaDe(pintar({ catalogo: CON_COMBINABLE, seleccionados: ["5"], multiple: true, moduloInicial }), "Egresos totales");
    assert.ok(!libre.includes("disabled") && !libre.includes("BLOQUEADO"), `${moduloInicial}: misma unidad, sin bloqueo`);
  }
  // El contador "elegidos" de las dos pestanas refleja la misma seleccion.
  const botones = Object.fromEntries(botonesDeModulo(pintar({ catalogo: CON_COMBINABLE, seleccionados: ["5"], multiple: true })).map((b) => [b.clave, b.html]));
  assert.ok(botones.facturacion.includes("kpi-selector-modulo-elegidos") && botones.variables.includes("kpi-selector-modulo-elegidos"));
  assert.ok(!botones.operaciones.includes("kpi-selector-modulo-elegidos"));
});

test("al buscar un sin desglose sale en su modulo y en Variables (con etiqueta solo en Variables)", () => {
  const html = pintar({ busquedaInicial: "ingresos" });
  assert.deepEqual(gruposVisibles(html), ["facturacion", "variables"]);
  const apariciones = filas(html).filter((fila) => fila.includes("Ingresos totales"));
  assert.equal(apariciones.length, 2);
  assert.equal(apariciones.filter((fila) => fila.includes("kpi-selector-modulo-tag")).length, 1, "solo la de Variables lleva la etiqueta");
});

// --- con los 40 KPIs del registry ----------------------------------------------------------------
const REGISTRY = JSON.parse(readFileSync(new URL("./fixtures/catalogo_del_registry.json", import.meta.url), "utf8"))
  .map((kpi) => ({ ...kpi, descripcion: `Descripcion de ${kpi.etiqueta}` }));
const SIN_DESGLOSE_DE_RESTAURANTE = ["Ventas del restaurante", "Ticket promedio", "Propinas del restaurante", "Propina como % de la venta", "Tiempo de entrega", "Cuentas sin cobrar"];

test("con los 40 KPIs del registry: conteos por pestana y los 6 sin desglose de restaurante dentro de Restaurante", () => {
  const botones = botonesDeModulo(pintarSelector({ catalogo: REGISTRY, seleccionados: [], multiple: false }));
  assert.deepEqual(botones.map((b) => [b.clave, b.texto.match(/(\d+)$/)[1]]), [
    ["operaciones", "14"], ["inventario", "4"], ["facturacion", "4"], ["laboratorio", "3"], ["documentos", "1"], ["restaurante", "14"], ["variables", "9"],
  ]);
  const restaurante = pintarSelector({ catalogo: REGISTRY, seleccionados: [], multiple: false, moduloInicial: "restaurante" });
  assert.equal(filas(restaurante).length, 14, "la pestana Restaurante trae TODOS sus KPIs");
  for (const etiqueta of SIN_DESGLOSE_DE_RESTAURANTE) assert.ok(filaDe(restaurante, etiqueta), `${etiqueta} esta en Restaurante`);
  assert.ok(restaurante.includes('data-seccion="combinables"') && restaurante.includes("Combinables (sin desglose)"));
  const combinables = restaurante.slice(restaurante.indexOf('data-seccion="combinables"'));
  assert.equal(filas(combinables).length, 6, "los 6 sin desglose, juntos al final");
  assert.ok(!filas(combinables).some((fila) => fila.includes("Mesas ocupadas")), "los de desglose quedan arriba");
  const variables = pintarSelector({ catalogo: REGISTRY, seleccionados: [], multiple: false, moduloInicial: "variables" });
  assert.equal(filas(variables).length, 9);
  assert.ok(filas(variables).every((fila) => fila.includes("kpi-selector-modulo-tag")), "las 9 tarjetas de Variables llevan su modulo");
  assert.deepEqual(etiquetaDeModulo(variables, "Ticket promedio"), ["restaurante", "Modulo restaurante"]);
  assert.deepEqual(etiquetaDeModulo(variables, "Incidencias pendientes"), ["operaciones", "Modulo operaciones"]);
});

// --- un rol solo ve los KPIs que tiene permitidos ------------------------------------------------------
// El catalogo del selector es `GET /kpi_definition/`: solo lo permitido, sin nada mas que ofrecer.
const UN_KPI = [KPI(21, "Asistencias del mes", "operaciones", "numero")];

test("un rol con UN solo KPI ve una pestana y una tarjeta", () => {
  const html = pintarSelector({ catalogo: UN_KPI, seleccionados: [], multiple: false });
  assert.deepEqual(gruposVisibles(html), ["operaciones"], "una sola pestana (un solo modulo: sin fila de botones, con su titulo)");
  assert.deepEqual(botonesDeModulo(html), []);
  assert.equal(filas(html).length, 1, "una tarjeta");
  assert.ok(filas(html)[0].includes("Asistencias del mes"));
  assert.ok(html.includes("Modulo operaciones"), "el titulo del modulo con su conteo");
  assert.match(html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " "), /Modulo operaciones 1/);
  // Un solo KPI sin desglose: su modulo, sin una segunda pestana «Variables» que repita lo mismo.
  const global = pintarSelector({ catalogo: [KPI(22, "Pendientes hoy", "operaciones", "numero", { dimensiones: ["global"] })], seleccionados: [], multiple: false });
  assert.deepEqual(gruposVisibles(global), ["operaciones"]);
  assert.equal(filas(global).length, 1);
  assert.ok(global.includes("Combinables (sin desglose)"));
});

test("las pestanas sin KPIs permitidos no aparecen y los contadores son solo de lo permitido", () => {
  // Un rol con 3 KPIs en 2 modulos: dos pestanas (+ Variables) y nada de inventario ni restaurante.
  const rol = [
    KPI(31, "Asistencias del mes", "operaciones", "numero"),
    KPI(32, "Retardos", "operaciones", "numero"),
    KPI(33, "Ventas del restaurante", "restaurante", "moneda", { dimensiones: ["global"] }),
  ];
  const html = pintarSelector({ catalogo: rol, seleccionados: [], multiple: false });
  const botones = botonesDeModulo(html);
  assert.deepEqual(botones.map((b) => b.clave), ["operaciones", "restaurante", "variables"]);
  assert.match(botones[0].texto, /Modulo operaciones 2/);
  assert.match(botones[1].texto, /Modulo restaurante 1/, "cuenta solo el KPI que SI tiene");
  assert.match(botones[2].texto, /Variables 1/);
  assert.ok(!botones.some((b) => b.clave === "inventario"), "sin KPIs permitidos de inventario no hay pestana");
});

test("el superusuario ve todo como antes: los 40 KPIs, 7 pestanas", () => {
  // Un superusuario lo tiene todo permitido: el catalogo es el registry completo.
  const html = pintarSelector({ catalogo: REGISTRY, seleccionados: [], multiple: false });
  assert.deepEqual(botonesDeModulo(html).map((b) => b.clave), ["operaciones", "inventario", "facturacion", "laboratorio", "documentos", "restaurante", "variables"]);
});
