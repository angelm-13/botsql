// Prueba de RENDER de la vista previa de KPIs no disponibles: el selector marca los ejemplos y los bloquea al
// combinar, y el aviso y el sello "EJEMPLO" salen siempre con el texto acordado.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { before } from "node:test";
import { cargarRender } from "./bundleRender.mjs";
import {
  catalogoConEjemplos, esIdDeEjemplo, hayEjemploEnSeleccion, kpiDeEjemplo, ofreceVerEjemplo, sePuedeGuardar,
} from "./vistaPreviaDeEjemplo.js";
import { motivoParaNoCombinar, widgetDeBorrador } from "./kpiParametros.js";

let pintarSelector;
let pintarMarcoEjemplo;

before(async () => {
  ({ pintarSelector, pintarMarcoEjemplo } = await cargarRender());
});

const REAL = { id_kpi_definition: 4, clave: "ingresos_totales", etiqueta: "Ingresos", unidad: "moneda", dimensiones: ["global"], modulo: "facturacion", modo: "snapshot" };
const NO_DISPONIBLE = { clave: "mesas_ocupadas", etiqueta: "Mesas ocupadas", unidad: "numero", dimensiones: ["estado"], modulo: "restaurante", modo: "snapshot", motivo: "modulo_no_habilitado", descripcion: "Foto de hoy" };
const CATALOGO = catalogoConEjemplos([REAL], [NO_DISPONIBLE, { ...REAL, id_kpi_definition: undefined, motivo: "modulo_no_habilitado" }]);

test("un KPI no disponible entra al catalogo como ejemplo con un id que nunca es numerico", () => {
  const ejemplo = CATALOGO.find((k) => k.clave === "mesas_ocupadas");
  assert.equal(ejemplo.id_kpi_definition, "ejemplo:mesas_ocupadas");
  assert.equal(esIdDeEjemplo(ejemplo.id_kpi_definition), true);
  assert.equal(ejemplo.esEjemplo, true);
  assert.equal(ejemplo.motivo, "modulo_no_habilitado");
  assert.equal(CATALOGO.filter((k) => k.clave === "ingresos_totales").length, 1, "uno que SI esta disponible no se duplica");
  assert.equal(kpiDeEjemplo({ clave: "x" }, "sin_datos").motivo, "sin_datos");
});

test("un KPI sin permiso ya no se ofrece como ejemplo: un rol solo ve los suyos", () => {
  const sinPermiso = (clave) => ({ clave, etiqueta: clave, unidad: "numero", dimensiones: ["empleado"], modulo: "operaciones", modo: "snapshot", motivo: "sin_permiso" });
  const diez = Array.from({ length: 10 }, (_, i) => sinPermiso(`otro_${i}`));
  // El rol solo tiene REAL: un backend viejo que mande 10 sin_permiso no los destapa.
  assert.deepEqual(catalogoConEjemplos([REAL], diez), [REAL]);
  assert.equal(catalogoConEjemplos([REAL], diez).filter((k) => k.esEjemplo).length, 0, "ningun ejemplo de otros");
  // Un fuera-del-plan (candados apagados por omision) sigue entrando como ejemplo; uno sin permiso mezclado con el, no.
  const mezclado = catalogoConEjemplos([REAL], [NO_DISPONIBLE, ...diez]);
  assert.deepEqual(mezclado.filter((k) => k.esEjemplo).map((k) => k.clave), ["mesas_ocupadas"]);
});

test("«Ver ejemplo» solo se ofrece para un KPI REAL (permitido) cuya consulta del rango volvio vacia", () => {
  const vacio = { rango_a: { total: 0, por_empleado: {}, por_periodo: {} } };
  const conDatos = { rango_a: { total: 3, por_empleado: { a: 3 }, por_periodo: {} } };
  const listo = { kpiReal: REAL, esEjemplo: false, esTablaVivo: false, loading: false, pendiente: false, error: null, snapshots: [vacio] };
  assert.equal(ofreceVerEjemplo(listo), true, "permitido y sin datos: el boton");
  assert.equal(ofreceVerEjemplo({ ...listo, snapshots: [conDatos] }), false, "con datos no hay nada que ejemplificar");
  assert.equal(ofreceVerEjemplo({ ...listo, snapshots: [null] }), true, "una respuesta sin rango tambien es vacia");
  assert.equal(ofreceVerEjemplo({ ...listo, kpiReal: null }), false, "sin KPI real (o con varios) no hay boton");
  assert.equal(ofreceVerEjemplo({ ...listo, loading: true }), false, "mientras carga no");
  assert.equal(ofreceVerEjemplo({ ...listo, pendiente: true }), false, "ni con el borrador sin asentar");
  assert.equal(ofreceVerEjemplo({ ...listo, error: "x" }), false, "ni con un error");
  assert.equal(ofreceVerEjemplo({ ...listo, esTablaVivo: true }), false, "una tabla en vivo no tiene rango vacio");
  assert.equal(ofreceVerEjemplo({ ...listo, esEjemplo: true }), false, "un ejemplo no ofrece ejemplo");
  assert.equal(ofreceVerEjemplo({ ...listo, snapshots: [vacio, vacio] }), false, "solo con un KPI");
  // El boton sigue cableado en la pantalla con esa decision y los textos de siempre.
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.ok(dashboard.includes("const sinDatos = ofreceVerEjemplo("), "el editor decide con ofreceVerEjemplo");
  assert.ok(dashboard.includes('tx("example_view", "Ver ejemplo")') && dashboard.includes("{sinDatos && ("));
});

test("un ejemplo nunca se puede guardar: ni el borrador ni la barrera final", () => {
  assert.equal(sePuedeGuardar(["4"]), true);
  assert.equal(sePuedeGuardar(["4", "7"]), true);
  assert.equal(sePuedeGuardar(["ejemplo:mesas_ocupadas"]), false);
  assert.equal(sePuedeGuardar(["4", "ejemplo:mesas_ocupadas"]), false);
  assert.equal(sePuedeGuardar([]), false);
  assert.equal(sePuedeGuardar([Number.NaN]), false);
  assert.equal(hayEjemploEnSeleccion(["4", "ejemplo:x"]), true);
  const borrador = {
    tipoGrafica: "dona", idsKpiSeleccionados: ["ejemplo:mesas_ocupadas"], rangoRelativo: "personalizado", fechaInicio: "2026-09-01",
    fechaFin: "2026-09-30", comparar: false, empleadosSeleccionados: [], departamentosSeleccionados: [], coloresKpi: {}, agruparPor: "entidad",
  };
  assert.deepEqual(widgetDeBorrador(borrador, {}).ids_kpi_definition, ["ejemplo:mesas_ocupadas"], "el id textual se conserva, nunca NaN");
  assert.deepEqual(widgetDeBorrador({ ...borrador, idsKpiSeleccionados: ["4"] }, {}).ids_kpi_definition, [4]);
});

test("un ejemplo no se mezcla con KPIs reales ni con otros ejemplos", () => {
  const ejemplo = CATALOGO.find((k) => k.esEjemplo);
  assert.equal(motivoParaNoCombinar([REAL], ejemplo), "ejemplo");
  assert.equal(motivoParaNoCombinar([ejemplo], REAL), "ejemplo");
  assert.equal(motivoParaNoCombinar([ejemplo], { ...ejemplo, clave: "otro" }), "ejemplo");
  assert.equal(motivoParaNoCombinar([], ejemplo), null, "solo, se puede elegir");
  assert.equal(motivoParaNoCombinar([REAL], { ...REAL, id_kpi_definition: 5 }), null, "dos reales de la misma unidad siguen combinandose");
});

test("el selector marca los ejemplos con una etiqueta y los bloquea al combinar con uno real", () => {
  const sinElegir = pintarSelector({ catalogo: CATALOGO, seleccionados: [], multiple: true, moduloInicial: "restaurante" });
  assert.ok(sinElegir.includes("kpi-editor-kpi-ejemplo"), "el ejemplo lleva su etiqueta");
  assert.ok(sinElegir.includes("Mesas ocupadas"));
  const combinando = pintarSelector({ catalogo: CATALOGO, seleccionados: ["4"], multiple: true, moduloInicial: "restaurante" });
  assert.ok(combinando.includes("BLOQUEADO(ejemplo): Mesas ocupadas"), "con un KPI real elegido, el ejemplo sale bloqueado");
  const alReves = pintarSelector({ catalogo: CATALOGO, seleccionados: ["ejemplo:mesas_ocupadas"], multiple: true, moduloInicial: "variables" });
  assert.ok(alReves.includes("BLOQUEADO(ejemplo): Ingresos"), "y con el ejemplo elegido, los reales salen bloqueados");
});

test("el aviso lleva el texto acordado y el sello EJEMPLO, con su motivo", () => {
  const html = pintarMarcoEjemplo({ motivo: "sin_datos" });
  assert.ok(html.includes("Vista previa con datos de ejemplo. Así se vería este KPI; no está disponible para tu rol o aún no tiene datos"));
  assert.ok(html.includes("kpi-ejemplo-sello") && html.includes(">EJEMPLO<"));
  assert.ok(html.includes('data-marca="EJEMPLO"'), "la marca de agua toma el texto traducido");
  assert.ok(html.includes("Aún no tiene datos."));
  assert.ok(pintarMarcoEjemplo({ motivo: "modulo_no_habilitado" }).includes("Módulo no habilitado."));
  // El motivo «sin permiso» ya no existe: no hay texto "No disponible para tu rol." en el motivo.
  assert.ok(!pintarMarcoEjemplo({ motivo: "sin_permiso" }).includes("No disponible para tu rol."));
});

test("el reporte PDF solo captura las tarjetas del tablero, nunca la vista previa del editor", () => {
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.ok(dashboard.includes('nodoGrid.querySelectorAll(".kpi-widget-card")'), "el PDF recorre solo las tarjetas del tablero");
  assert.ok(!/kpi-ejemplo[^"]*kpi-widget-card|kpi-widget-card[^"]*kpi-ejemplo/.test(dashboard), "el marco de ejemplo no es una tarjeta");
  // Y un widget con un ejemplo no llega a la API: el guardado lo rechaza dos veces.
  assert.ok(dashboard.includes('throw new Error("kpi_example_not_saved")'));
  assert.ok(dashboard.includes("if (hayEjemplo) rechazar("));
  assert.ok(dashboard.includes("|| hayEjemplo"), "Terminar queda deshabilitado");
});

test("todos los textos nuevos de la vista previa y del selector existen en es, en, pt y de", () => {
  const dashboard = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  // `example_*`: la vista previa de KPIs no disponibles; `selector_*`: los textos nuevos del selector de KPI.
  const claves = [...new Set([...dashboard.matchAll(/tx\("((?:example|selector)_[a-z_]+)"/g)].map((m) => m[1]))];
  assert.ok(claves.length >= 14, `se esperaban los textos de ejemplo en Dashboard.jsx (hay ${claves.length})`);
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
    assert.notEqual(catalogos[idioma].example_cannot_save, catalogos.es.example_cannot_save, `${idioma}: aviso de guardado sin traducir`);
  }
});
