// Regresion: una marca con `fill="url(#id)"` necesita su `<pattern id>` DENTRO de su propio <svg>. Recharts descarta un
// componente envoltorio que devuelva `<defs>` (solo conserva el `<defs>` literal), asi que las donas por estado, las barras por
// estado y las barras por persona con colores repetidos salian sin barras ni aro: el relleno apuntaba a un patron que no existia
// y el navegador lo pinta como "none". Se pinta con tamano fijo (ver bundleGraficas.mjs) y se lee el SVG resultante.
import assert from "node:assert/strict";
import test, { before } from "node:test";
import { cargarGraficas } from "./bundleGraficas.mjs";
import { propsDona, propsSeries } from "./kpiAdaptadores.js";
import { colorDePersona } from "./kpiDatos.js";

let pintarDona;
let pintarBarras;
before(async () => { ({ pintarDona, pintarBarras } = await cargarGraficas()); });

const formatNumber = (valor) => String(valor);
const textos = { rangoA: "A", rangoB: "B", comparacionCorta: "comp", otros: "Otros", registros: "registros", total: "total" };

/** Cada <svg> del HTML (no se anidan) con los ids de sus <pattern> y los de sus fill="url(#...)". */
function svgs(html) {
  return [...html.matchAll(/<svg[\s\S]*?<\/svg>/g)].map(([svg]) => ({
    svg,
    patrones: new Set([...svg.matchAll(/<pattern[^>]*\sid="([^"]+)"/g)].map((m) => m[1])),
    referencias: [...svg.matchAll(/fill="url\(#([^)]+)\)"/g)].map((m) => m[1]),
  }));
}

function assertCadaRellenoTienePatron(html, minimoDeMarcas) {
  const todas = svgs(html);
  const referencias = todas.flatMap((s) => s.referencias);
  assert.ok(referencias.length >= minimoDeMarcas, `se esperaban al menos ${minimoDeMarcas} rellenos con patron y hay ${referencias.length}`);
  todas.forEach(({ patrones, referencias: refs }) => refs.forEach((id) => assert.ok(patrones.has(id), `fill="url(#${id})" sin <pattern id="${id}" en su mismo <svg>`)));
}

function snapshot(porEmpleado) {
  return { rango_a: { total: 0, por_empleado: porEmpleado, por_periodo: {}, etiquetas: {} } };
}

test("dona por estado (colores fijos): cada sector tiene su patron dentro de la grafica", () => {
  const kpiInfo = { dimensiones: ["estado"], unidad: "numero", colores_categoria: { pendiente: "#f0a93b", en_proceso: "#2f8fe0", bloqueada: "#ef6f5c" }, orden_categorias: ["pendiente", "en_proceso", "bloqueada"] };
  const props = propsDona({ snapshot: snapshot({ pendiente: 5, en_proceso: 5, bloqueada: 4 }), kpiInfo, labelForId: (id) => id, agruparPorPeriodo: false, formatNumber, textos });
  assert.equal(props.conPatrones, true);
  const html = pintarDona(props);
  assert.equal((html.match(/recharts-sector/g) || []).length >= 3, true, "la dona no pinto sus sectores");
  assertCadaRellenoTienePatron(html, 3);
});

test("barras por estado (colores fijos): cada barra tiene su patron dentro de la grafica", () => {
  const kpiInfo = { id_kpi_definition: 8, dimensiones: ["estado"], unidad: "numero", colores_categoria: { abierta: "#ef6f5c", cerrada: "#22b573" } };
  const props = propsSeries({
    tipo: "barras", snapshots: [snapshot({ abierta: 70, cerrada: 88 })], kpiInfos: [kpiInfo], labelForId: (id) => id,
    agruparPorPeriodo: false, formatNumber, textos,
  });
  assert.equal(props.conPatrones, true);
  const html = pintarBarras(props);
  assert.equal((html.match(/recharts-rectangle/g) || []).length >= 2, true, "las barras no se pintaron");
  assertCadaRellenoTienePatron(html, 2);
});

test("barras por persona con colores repetidos (horizontales desde 13): cada barra tiene su patron", () => {
  // Los ids 13 y 37 comparten color: la grafica agrega patrones para que el color no sea la unica senal.
  const ids = [13, 14, 15, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39];
  assert.equal(colorDePersona(13), colorDePersona(37));
  const kpiInfo = { id_kpi_definition: 17, dimensiones: ["empleado"], unidad: "numero" };
  const porEmpleado = Object.fromEntries(ids.map((id, i) => [String(id), 20 - i]));
  const props = propsSeries({
    tipo: "barras", snapshots: [snapshot(porEmpleado)], kpiInfos: [kpiInfo], labelForId: (id) => `Persona ${id}`,
    agruparPorPeriodo: false, formatNumber, textos,
  });
  assert.equal(props.conPatrones, true);
  const html = pintarBarras(props);
  assert.equal((html.match(/recharts-rectangle/g) || []).length >= ids.length, true, "las barras no se pintaron");
  assertCadaRellenoTienePatron(html, ids.length);
});

test("sin patrones el relleno es el color plano y no hay <pattern> en la grafica", () => {
  const html = pintarDona({ datos: [{ categoria: "a", valor: 1, color: "#f0a93b" }, { categoria: "b", valor: 2, color: "#2f8fe0" }], conPatrones: false });
  assert.equal(html.includes("<pattern"), false);
  assert.ok(html.includes('fill="#f0a93b"'));
});
