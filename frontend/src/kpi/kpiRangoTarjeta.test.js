import test from "node:test";
import assert from "node:assert/strict";
import { ETIQUETA_DE_RANGO_EN_TARJETA, RANGOS_RELATIVOS, formatoDeRango, formatoDeRangoLargo, textoDeRango } from "./kpiRango.js";

test("formatoDeRango: mismo mes, mismo anio, otro anio y un solo dia", () => {
  assert.match(formatoDeRango("2026-10-01", "2026-10-30"), /^1 – 30 oct 2026$/);
  assert.match(formatoDeRango("2026-09-28", "2026-10-30"), /^28 sep – 30 oct 2026$/);
  assert.match(formatoDeRango("2025-12-28", "2026-01-03"), /^28 dic 2025 – 3 ene 2026$/);
  assert.match(formatoDeRango("2026-10-30", "2026-10-30"), /^30 oct 2026$/);
});

test("formatoDeRango nunca devuelve ISO ni flechas, y es vacio con fechas invalidas", () => {
  const texto = formatoDeRango("2026-10-01", "2026-10-30");
  assert.doesNotMatch(texto, /\d{4}-\d{2}-\d{2}|→/);
  assert.equal(formatoDeRango("", "2026-10-30"), "");
  assert.equal(formatoDeRango("no", "2026-10-30"), "");
});

test("formatoDeRangoLargo para el tooltip", () => {
  assert.equal(formatoDeRangoLargo("2026-10-01", "2026-10-30"), "1 de octubre de 2026 al 30 de octubre de 2026");
  assert.match(formatoDeRangoLargo("2026-10-01", "2026-10-30", { locale: "en-US", al: "to" }), /October 1, 2026 to October 30, 2026/);
});

test("un widget relativo dice 'Ultimos 30 dias' y deja las fechas exactas en el detalle", () => {
  const rango = textoDeRango({ inicio: "2026-10-01", fin: "2026-10-30", etiquetaRelativa: ETIQUETA_DE_RANGO_EN_TARJETA["30_dias"] });
  assert.equal(rango.texto, "Últimos 30 días");
  assert.equal(rango.detalle, "1 de octubre de 2026 al 30 de octubre de 2026");
});

test("uno de fechas fijas dice las fechas cortas; con comparacion el detalle nombra el otro periodo", () => {
  const rango = textoDeRango({ inicio: "2026-10-01", fin: "2026-10-30", inicioB: "2026-09-01", finB: "2026-09-30", palabras: { vs: "vs." } });
  assert.match(rango.texto, /^1 – 30 oct 2026$/);
  assert.match(rango.detalle, /\(vs\. 1 de septiembre de 2026 al 30 de septiembre de 2026\)$/);
});

test("todos los rangos relativos tienen texto de tarjeta", () => {
  for (const clave of RANGOS_RELATIVOS) assert.ok(ETIQUETA_DE_RANGO_EN_TARJETA[clave], clave);
});
