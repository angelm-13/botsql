import test from "node:test";
import assert from "node:assert/strict";
import { avisoDeDatosAtrasados, computedAtDeSnapshots, frescuraDeWidget, paredDeInstante, paredDeTexto } from "./kpiFrescura.js";

const ZONA = "America/Mexico_City";
const snap = (computedAt) => ({ rango_a: { total: 1, computed_at: computedAt } });

test("la hora de pared de un instante es la de Mexico, no la del navegador ni la UTC", () => {
  // 02:00 UTC del 29 son las 20:00 del 28 en Mexico (UTC-6).
  assert.equal(paredDeInstante(new Date("2026-10-29T02:00:00Z"), ZONA), Date.UTC(2026, 9, 28, 20, 0, 0));
});

test("un computed_at sin zona se lee como hora de pared; con zona, convertido a la del negocio", () => {
  assert.equal(paredDeTexto("2026-10-28T20:00:00", ZONA), Date.UTC(2026, 9, 28, 20, 0, 0));
  assert.equal(paredDeTexto("2026-10-29T02:00:00Z", ZONA), Date.UTC(2026, 9, 28, 20, 0, 0));
  assert.equal(paredDeTexto("no es fecha", ZONA), null);
  assert.equal(paredDeTexto(undefined, ZONA), null);
});

test("de varios KPIs se toma el computed_at mas reciente", () => {
  assert.equal(computedAtDeSnapshots([snap("2026-10-01T10:00:00"), snap("2026-10-02T12:07:57.421494"), snap(null)]), "2026-10-02T12:07:57.421494");
  assert.equal(computedAtDeSnapshots([snap(null)]), null);
  assert.equal(computedAtDeSnapshots([{ rango_a: { total: 1 } }]), null);
});

test("sin computed_at no hay etiqueta", () => {
  assert.equal(frescuraDeWidget([{ rango_a: { total: 1 } }]), null);
});

test("la etiqueta de un KPI es neutra: no juzga el atraso", () => {
  const frescura = frescuraDeWidget([snap("2026-10-02T12:07:57")]);
  assert.deepEqual(Object.keys(frescura), ["fecha"]);
});

test("el aviso global: hasta 24 horas no avisa; mas de 24 horas si", () => {
  const ahora = "2026-10-29T18:00:00Z";
  assert.equal(avisoDeDatosAtrasados("2026-10-29T06:22:00Z", ahora, ZONA), null);
  assert.equal(avisoDeDatosAtrasados("2026-10-28T18:00:00Z", ahora, ZONA), null, "justo 24 h");
  assert.match(avisoDeDatosAtrasados("2026-10-28T17:59:00Z", ahora, ZONA).fecha, /2026/);
  assert.ok(avisoDeDatosAtrasados("2026-10-02T12:07:57Z", ahora, ZONA));
});

test("el aviso global no avisa sin ultimo calculo ni con una fecha ilegible", () => {
  assert.equal(avisoDeDatosAtrasados(null, "2026-10-29T18:00:00Z", ZONA), null);
  assert.equal(avisoDeDatosAtrasados("no es fecha", "2026-10-29T18:00:00Z", ZONA), null);
  assert.equal(avisoDeDatosAtrasados(undefined, undefined, ZONA), null);
});

test("el aviso global usa el reloj del servidor, y sin el, el del navegador", () => {
  assert.equal(avisoDeDatosAtrasados("2026-10-29T10:00:00Z", "2026-10-29T12:00:00Z", ZONA), null);
  const haceTresDias = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
  assert.ok(avisoDeDatosAtrasados(haceTresDias, null, ZONA));
});

test("la etiqueta trae la fecha formateada", () => {
  const frescura = frescuraDeWidget([snap("2026-10-29T00:22:00")]);
  assert.match(frescura.fecha, /2026/);
});
