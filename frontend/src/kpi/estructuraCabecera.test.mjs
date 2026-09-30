// Reglas de CSS de la cabecera de la tarjeta de KPI que, de volver, hacen que
// titulo y subtitulos se encimen (ver layoutTarjetas.test.mjs, que lo mide en un
// navegador). Esta version no necesita navegador y corre siempre.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

const CSS = readFileSync(fileURLToPath(new URL("../styles/kpi-dashboard.css", import.meta.url)), "utf8");

/** Todas las reglas cuyo selector menciona alguno de los nombres dados. */
function reglas(...nombres) {
  return [...CSS.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .map(([, selector, cuerpo]) => ({ selector: selector.trim(), cuerpo }))
    .filter(({ selector }) => nombres.some((n) => selector.includes(n)));
}

test("la cabecera de la tarjeta crece con su contenido: sin alturas fijas ni posicion absoluta", () => {
  const encontradas = reglas(".kpi-widget-card-header", ".kpi-widget-card-titulos", ".kpi-widget-meta");
  assert.ok(encontradas.length >= 4, "se encontraron las reglas de la cabecera");
  for (const { selector, cuerpo } of encontradas) {
    assert.doesNotMatch(cuerpo, /(^|;)\s*(min-|max-)?height\s*:/, `${selector}: altura fija`);
    assert.doesNotMatch(cuerpo, /position\s*:\s*(absolute|fixed)/, `${selector}: posicionamiento absoluto`);
    assert.doesNotMatch(cuerpo, /margin(-top|-bottom)?\s*:\s*-/, `${selector}: margen negativo`);
    assert.doesNotMatch(cuerpo, /overflow\s*:\s*hidden/, `${selector}: recorta el contenido`);
  }
});

test("no hay ninguna regla de hermanos con margen negativo entre subtitulos (el -6px que los montaba)", () => {
  for (const { selector, cuerpo } of reglas(".kpi-widget-meta+", ".kpi-widget-meta +")) {
    assert.doesNotMatch(cuerpo, /margin[^;]*-\d/, selector);
  }
});

test("titulo y subtitulos rompen palabras largas en vez de desbordar", () => {
  for (const nombre of [".kpi-widget-card-header h4", ".kpi-widget-meta"]) {
    const cuerpo = reglas(nombre).map((r) => r.cuerpo).join(";");
    assert.match(cuerpo, /overflow-wrap\s*:\s*anywhere/, nombre);
  }
  assert.match(reglas(".kpi-widget-card-titulos").map((r) => r.cuerpo).join(";"), /min-width\s*:\s*0/);
});
