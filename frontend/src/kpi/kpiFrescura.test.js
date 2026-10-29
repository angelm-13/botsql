import test from "node:test";
import assert from "node:assert/strict";
import { computedAtDeSnapshots, frescuraDeWidget, paredDeInstante, paredDeTexto } from "./kpiFrescura.js";

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
  assert.equal(frescuraDeWidget([{ rango_a: { total: 1 } }], new Date("2026-10-29T18:00:00Z"), ZONA), null);
});

test("hasta 24 horas no es atraso; mas de 24 horas si", () => {
  // Ahora: 2026-10-29 12:00 en Mexico (18:00 UTC).
  const ahora = new Date("2026-10-29T18:00:00Z");
  assert.equal(frescuraDeWidget([snap("2026-10-29T00:22:00")], ahora, ZONA).atrasado, false);
  assert.equal(frescuraDeWidget([snap("2026-10-28T12:00:00")], ahora, ZONA).atrasado, false, "justo 24 h");
  assert.equal(frescuraDeWidget([snap("2026-10-28T11:59:00")], ahora, ZONA).atrasado, true);
  assert.equal(frescuraDeWidget([snap("2026-10-02T12:07:57")], ahora, ZONA).atrasado, true);
});

test("el atraso cuenta en hora del negocio: a las 20:00 locales (02:00 UTC) un dato de las 19:00 no esta atrasado", () => {
  const ahora = new Date("2026-10-29T02:00:00Z");
  assert.equal(frescuraDeWidget([snap("2026-10-28T19:00:00")], ahora, ZONA).atrasado, false);
});

test("la etiqueta trae la fecha formateada", () => {
  const frescura = frescuraDeWidget([snap("2026-10-29T00:22:00")], new Date("2026-10-29T18:00:00Z"), ZONA);
  assert.match(frescura.fecha, /2026/);
});
