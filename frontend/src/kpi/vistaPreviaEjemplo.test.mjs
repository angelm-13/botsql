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

test("el aviso lleva el texto acordado y el sello EJEMPLO, con su motivo", () => {
  const html = pintarMarcoEjemplo({ motivo: "sin_datos" });
  assert.ok(html.includes("Vista previa con datos de ejemplo. Así se vería este KPI; no está disponible para tu rol o aún no tiene datos"));
  assert.ok(html.includes("kpi-ejemplo-sello") && html.includes(">EJEMPLO<"));
  assert.ok(html.includes('data-marca="EJEMPLO"'), "la marca de agua toma el texto traducido");
  assert.ok(html.includes("Aún no tiene datos."));
});

test("el reporte PDF solo captura las tarjetas del tablero, nunca la vista previa del editor", () => {
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.ok(dashboard.includes('nodoGrid.querySelectorAll(".kpi-widget-card")'), "el PDF recorre solo las tarjetas del tablero");
  assert.ok(!/kpi-ejemplo[^"]*kpi-widget-card|kpi-widget-card[^"]*kpi-ejemplo/.test(dashboard), "el marco de ejemplo no es una tarjeta");
});

test("todos los textos de la vista previa y del selector existen en es, en, pt y de", () => {
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  // `example_*`: la vista previa con datos de ejemplo; `selector_*`: los textos nuevos del selector de KPI.
  const claves = [...new Set([...dashboard.matchAll(/tx\("((?:example|selector)_[a-z_]+)"/g)].map((m) => m[1]))];
  assert.ok(claves.length >= 10, `se esperaban los textos de ejemplo en Dashboard.jsx (hay ${claves.length})`);
  assert.ok(claves.includes("selector_combinables") && claves.includes("selector_variables_ayuda"), "los textos nuevos del selector se revisan aqui");
  const catalogos = {};
  for (const idioma of ["es", "en", "pt", "de"]) {
    catalogos[idioma] = JSON.parse(readFileSync(new URL(`../i18n/locales/${idioma}.json`, import.meta.url), "utf8")).kpi_dashboard;
    for (const clave of claves) assert.ok(catalogos[idioma]?.[clave], `${idioma}: falta kpi_dashboard.${clave}`);
  }
  // El aviso acordado, tal cual, en espanol; y los demas idiomas no se quedan con el texto en espanol.
  assert.equal(catalogos.es.example_banner, "Vista previa con datos de ejemplo. Así se vería este KPI; no está disponible para tu rol o aún no tiene datos");
  assert.equal(catalogos.es.selector_combinables, "Combinables (sin desglose)");
  for (const idioma of ["en", "pt", "de"]) {
    for (const clave of ["selector_combinables", "selector_variables_ayuda"]) {
      assert.notEqual(catalogos[idioma][clave], catalogos.es[clave], `${idioma}: ${clave} sin traducir`);
    }
    assert.notEqual(catalogos[idioma].example_banner, catalogos.es.example_banner, `${idioma}: banner sin traducir`);
  }
});
