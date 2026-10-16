// Prueba de la vista previa con datos de EJEMPLO («Ver ejemplo» de un KPI permitido cuyo rango vuelve vacio):
// cuando se ofrece, y que el aviso y el sello "EJEMPLO" salen siempre con el texto acordado.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { before } from "node:test";
import { cargarRender } from "./bundleRender.mjs";
import { ofreceVerEjemplo } from "./vistaPreviaDeEjemplo.js";

let pintarMarcoEjemplo;

before(async () => {
  ({ pintarMarcoEjemplo } = await cargarRender());
});

const REAL = { id_kpi_definition: 4, clave: "ingresos_totales", etiqueta: "Ingresos", unidad: "moneda", dimensiones: ["global"], modulo: "facturacion", modo: "snapshot" };

test("«Ver ejemplo» solo se ofrece para un KPI REAL (permitido) cuya consulta del rango volvio vacia", () => {
  const vacio = { rango_a: { total: 0, por_empleado: {}, por_periodo: {} } };
  const conDatos = { rango_a: { total: 3, por_empleado: { a: 3 }, por_periodo: {} } };
  const listo = { kpiReal: REAL, esTablaVivo: false, loading: false, pendiente: false, error: null, snapshots: [vacio] };
  assert.equal(ofreceVerEjemplo(listo), true, "permitido y sin datos: el boton");
  assert.equal(ofreceVerEjemplo({ ...listo, snapshots: [conDatos] }), false, "con datos no hay nada que ejemplificar");
  assert.equal(ofreceVerEjemplo({ ...listo, snapshots: [null] }), true, "una respuesta sin rango tambien es vacia");
  assert.equal(ofreceVerEjemplo({ ...listo, kpiReal: null }), false, "sin KPI real (o con varios) no hay boton");
  assert.equal(ofreceVerEjemplo({ ...listo, loading: true }), false, "mientras carga no");
  assert.equal(ofreceVerEjemplo({ ...listo, pendiente: true }), false, "ni con el borrador sin asentar");
  assert.equal(ofreceVerEjemplo({ ...listo, error: "x" }), false, "ni con un error");
  assert.equal(ofreceVerEjemplo({ ...listo, esTablaVivo: true }), false, "una tabla en vivo no tiene rango vacio");
  assert.equal(ofreceVerEjemplo({ ...listo, snapshots: [vacio, vacio] }), false, "solo con un KPI");
  // El boton sigue cableado en la pantalla con esa decision y los textos de siempre.
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.ok(dashboard.includes("const sinDatos = ofreceVerEjemplo("), "el editor decide con ofreceVerEjemplo");
  assert.ok(dashboard.includes('tx("example_view", "Ver ejemplo")') && dashboard.includes("{sinDatos && ("));
});

test("el aviso lleva el texto acordado y el sello EJEMPLO, sin ninguna frase de motivo debajo", () => {
  const html = pintarMarcoEjemplo();
  assert.ok(html.includes("Vista previa con datos de ejemplo. Así se vería este KPI cuando tenga datos."));
  assert.ok(!html.includes("tu rol"), "el aviso ya no habla de permisos: solo aplica a un KPI permitido sin datos");
  assert.ok(html.includes("kpi-ejemplo-sello") && html.includes(">EJEMPLO<"));
  assert.ok(html.includes('data-marca="EJEMPLO"'), "la marca de agua toma el texto traducido");
  // La frase «Aún no tiene datos.» se quito: repetia el aviso, y ni siquiera era exacta (el rango esta vacio, no el KPI).
  assert.ok(!html.includes("Aún no tiene datos") && !html.includes("<em>"), "el aviso es una sola frase");
});

test("el reporte PDF solo captura las tarjetas del tablero, nunca la vista previa del editor", () => {
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.ok(dashboard.includes('nodoGrid.querySelectorAll(".kpi-widget-card")'), "el PDF recorre solo las tarjetas del tablero");
  assert.ok(!/kpi-ejemplo[^"]*kpi-widget-card|kpi-widget-card[^"]*kpi-ejemplo/.test(dashboard), "el marco de ejemplo no es una tarjeta");
});

test("Dashboard.jsx le pasa al selector TODOS los textos que este trae por omision", () => {
  // Un texto que el Dashboard no pasa se queda con su valor por omision (espanol) en cualquier idioma: asi se
  // quedaron sin traducir `modulos` (aria-label) y `elegidosEnModulo` (tooltip).
  const selector = readFileSync(new URL("../components/kpi-widgets/SelectorDeKpi.jsx", import.meta.url), "utf8");
  const porOmision = selector.slice(selector.indexOf("const TEXTOS_POR_OMISION = {"));
  const claves = (bloque) => [...bloque.matchAll(/^\s+([a-zA-Z]+): /gm)].map((m) => m[1]).sort();
  const declarados = claves(porOmision.slice(0, porOmision.indexOf("};")));
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  const desdeSelector = dashboard.slice(dashboard.indexOf("<SelectorDeKpi"));
  const inicio = desdeSelector.indexOf("textos={{");
  const pasados = claves(desdeSelector.slice(inicio + "textos={{".length, desdeSelector.indexOf("}}", inicio)));
  assert.ok(declarados.length >= 8, `no se leyeron los textos por omision del selector (${declarados})`);
  assert.deepEqual(pasados, declarados, "Dashboard.jsx debe pasar exactamente los textos que SelectorDeKpi declara por omision");
});

test("todos los textos de la vista previa y del selector existen en es, en, pt y de", () => {
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  // 1) `example_*`: la vista previa con datos de ejemplo; `selector_*`: los textos nuevos del selector de KPI.
  const porPrefijo = [...dashboard.matchAll(/tx\("((?:example|selector)_[a-z_]+)"/g)].map((m) => m[1]);
  // 2) TODO lo que el Dashboard le pasa al selector en `textos={{ ... }}` (buscador, "Variables", color...): un texto
  // nuevo ahi queda exigido solo, sin tener que acordarse de agregarle un prefijo a la lista de arriba.
  const desdeSelector = dashboard.slice(dashboard.indexOf("<SelectorDeKpi"));
  const textosDelSelector = desdeSelector.slice(desdeSelector.indexOf("textos={{"), desdeSelector.indexOf("}}", desdeSelector.indexOf("textos={{")));
  const pares = [...textosDelSelector.matchAll(/tx\("([a-z_]+)",\s*"((?:[^"\\]|\\.)*)"\)/g)].map((m) => ({ clave: m[1], respaldo: m[2] }));
  const delSelector = pares.map((par) => par.clave);
  for (const clave of [
    "kpi_search_placeholder", "kpi_search_empty", "kpi_variables_group", "kpi_color_choose", "selector_combinables",
    "selector_variables_ayuda", "selector_modulos", "selector_elegidos_en_modulo",
  ]) {
    assert.ok(delSelector.includes(clave), `el selector recibe ${clave}: la prueba tiene que vigilarlo`);
  }
  for (const clave of ["example_banner", "example_badge", "example_view", "example_hide", "example_no_data_hint"]) {
    assert.ok(porPrefijo.includes(clave), `la vista previa usa ${clave}: la prueba tiene que vigilarlo`);
  }
  assert.ok(!porPrefijo.includes("example_reason_sin_datos"), "esa frase se quito del aviso");
  const claves = [...new Set([...porPrefijo, ...delSelector])];

  const catalogos = {};
  for (const idioma of ["es", "en", "pt", "de"]) {
    catalogos[idioma] = JSON.parse(readFileSync(new URL(`../i18n/locales/${idioma}.json`, import.meta.url), "utf8")).kpi_dashboard;
    for (const clave of claves) {
      assert.equal(typeof catalogos[idioma]?.[clave], "string", `${idioma}: falta kpi_dashboard.${clave}`);
      assert.ok(catalogos[idioma][clave].trim(), `${idioma}: kpi_dashboard.${clave} esta vacio`);
    }
  }
  // El catalogo en espanol dice lo mismo que el texto de respaldo del codigo: no se desfasan.
  for (const { clave, respaldo } of pares) assert.equal(catalogos.es[clave], respaldo, `es: ${clave} difiere del texto de respaldo de Dashboard.jsx`);
  // El aviso acordado, tal cual, en espanol; y los demas idiomas no se quedan con el texto en espanol.
  assert.equal(catalogos.es.example_banner, "Vista previa con datos de ejemplo. Así se vería este KPI cuando tenga datos.");
  // Ya no habla de permisos ni de modulos no habilitados, en ningun idioma.
  const PALABRAS_DE_PERMISO = { es: /\brol\b/i, en: /\brole\b/i, pt: /perfil/i, de: /Rolle/i };
  for (const idioma of Object.keys(PALABRAS_DE_PERMISO)) {
    assert.ok(!PALABRAS_DE_PERMISO[idioma].test(catalogos[idioma].example_banner), `${idioma}: el aviso no debe hablar de permisos`);
  }
  assert.equal(catalogos.es.selector_combinables, "Combinables (sin desglose)");
  // Traducidos de verdad: ninguno de en/pt/de repite el texto en espanol. Unicas excepciones, palabras que se escriben
  // igual (no una traduccion que falte): "Variables" en ingles y "Módulos" en portugues.
  const IGUAL_QUE_EN_ESPANOL = { kpi_variables_group: ["en"], selector_modulos: ["pt"] };
  for (const idioma of ["en", "pt", "de"]) {
    for (const clave of claves) {
      if (IGUAL_QUE_EN_ESPANOL[clave]?.includes(idioma)) continue;
      assert.notEqual(catalogos[idioma][clave], catalogos.es[clave], `${idioma}: ${clave} sin traducir`);
    }
  }
});
