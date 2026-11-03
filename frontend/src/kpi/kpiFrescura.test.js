import test from "node:test";
import assert from "node:assert/strict";
import {
  RECIENTE_MS, UMBRAL_DATOS_ATRASADOS_HORAS, chipDeTarjeta, computedAtDeSnapshots, estadoGlobalDeDatos, etiquetaDeCuando, fechaCorta,
  frescuraDeWidget, paredDeInstante, paredDeTexto, ultimoCalculoEfectivo,
} from "./kpiFrescura.js";

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

test("la etiqueta trae la fecha formateada", () => {
  const frescura = frescuraDeWidget([snap("2026-10-29T00:22:00")]);
  assert.match(frescura.fecha, /2026/);
});

// 30 oct 2026, 10:00 en Mexico (UTC-6) = 16:00 UTC.
const AHORA = "2026-10-30T16:00:00Z";
const OPCIONES = { zona: ZONA, locale: "es-MX" };

test("el umbral de atraso es una sola constante de 36 horas", () => {
  assert.equal(UMBRAL_DATOS_ATRASADOS_HORAS, 36);
});

test("la linea global: hasta 36 horas esta al dia, pasadas 36 horas esta atrasada", () => {
  // 01:00 a.m. de hoy en Mexico = 07:00 UTC.
  assert.deepEqual(estadoGlobalDeDatos("2026-10-30T07:00:00Z", AHORA, OPCIONES).tipo, "al_dia");
  assert.match(estadoGlobalDeDatos("2026-10-30T07:00:00Z", AHORA, OPCIONES).cuando, /^hoy 1:00/);
  assert.equal(estadoGlobalDeDatos("2026-10-29T04:00:00Z", AHORA, OPCIONES).tipo, "al_dia", "36 h justas");
  const atrasado = estadoGlobalDeDatos("2026-10-29T03:59:00Z", AHORA, OPCIONES);
  assert.equal(atrasado.tipo, "atrasado");
  assert.equal(atrasado.dias, 1);
  assert.equal(estadoGlobalDeDatos("2026-10-25T07:00:00Z", AHORA, OPCIONES).dias, 5);
});

test("la linea global no existe sin ultimo calculo o con uno ilegible", () => {
  assert.equal(estadoGlobalDeDatos(null, AHORA, OPCIONES), null);
  assert.equal(estadoGlobalDeDatos("no es fecha", AHORA, OPCIONES), null);
});

test("un indicador sin eventos con fecha vieja NO apaga la linea global mientras otro este reciente", () => {
  // El ultimo calculo es el maximo de todos: lo que diga una tarjeta suelta no cambia la linea.
  const globalReciente = "2026-10-30T07:00:00Z";
  assert.equal(estadoGlobalDeDatos(globalReciente, AHORA, OPCIONES).tipo, "al_dia");
  assert.equal(chipDeTarjeta({ computedAt: "2026-10-28T10:00:00Z", ahora: AHORA, ...OPCIONES }).tipo, "ultimo_dato");
});

test("lo recalculado en la sesion adelanta el ultimo calculo aunque el servidor no haya escrito filas", () => {
  assert.equal(ultimoCalculoEfectivo("2026-10-25T07:00:00Z", { 1: "2026-10-30T15:50:00Z" }, ZONA), "2026-10-30T15:50:00Z");
  assert.equal(ultimoCalculoEfectivo("2026-10-30T07:00:00Z", { 1: "2026-10-29T15:50:00Z" }, ZONA), "2026-10-30T07:00:00Z");
  assert.equal(ultimoCalculoEfectivo(null, {}, ZONA), null);
  assert.equal(ultimoCalculoEfectivo(null, { 1: "2026-10-30T15:50:00Z" }, ZONA), "2026-10-30T15:50:00Z");
});

test("el chip de tarjeta solo aparece pasadas las 36 horas, con la fecha corta", () => {
  assert.equal(chipDeTarjeta({ computedAt: "2026-10-30T07:00:00Z", ahora: AHORA, ...OPCIONES }), null);
  assert.equal(chipDeTarjeta({ computedAt: "2026-10-29T04:00:00Z", ahora: AHORA, ...OPCIONES }), null, "36 h justas");
  const chip = chipDeTarjeta({ computedAt: "2026-10-28T10:00:00Z", ahora: AHORA, ...OPCIONES });
  assert.equal(chip.tipo, "ultimo_dato");
  assert.match(chip.cuando, /^28 oct/);
  assert.equal(chipDeTarjeta({ computedAt: null, ahora: AHORA, ...OPCIONES }), null);
});

test("el chip dice 'al dia' si se recalculo en la sesion, 'ahora' mientras sea reciente", () => {
  const ahoraNavegador = new Date("2026-10-30T16:00:00Z");
  const reciente = chipDeTarjeta({ computedAt: "2026-10-01T10:00:00Z", recalculadoEn: "2026-10-30T15:55:00Z", ahora: AHORA, ahoraNavegador, ...OPCIONES });
  assert.deepEqual({ tipo: reciente.tipo, reciente: reciente.reciente }, { tipo: "al_dia", reciente: true });
  const viejo = chipDeTarjeta({ computedAt: "2026-10-01T10:00:00Z", recalculadoEn: "2026-10-30T14:00:00Z", ahora: AHORA, ahoraNavegador, ...OPCIONES });
  assert.equal(viejo.reciente, false);
  assert.match(viejo.cuando, /^hoy 8:00/);
  assert.equal(RECIENTE_MS, 10 * 60 * 1000);
});

test("etiquetaDeCuando: hoy, ayer, fecha con y sin anio; palabras traducibles", () => {
  assert.match(etiquetaDeCuando("2026-10-30T07:00:00Z", AHORA, OPCIONES), /^hoy 1:00/);
  assert.match(etiquetaDeCuando("2026-10-29T20:00:00Z", AHORA, OPCIONES), /^ayer 2:00/);
  assert.match(etiquetaDeCuando("2026-10-25T07:00:00Z", AHORA, OPCIONES), /^25 oct/);
  assert.match(etiquetaDeCuando("2025-10-25T07:00:00Z", AHORA, OPCIONES), /2025/);
  assert.match(etiquetaDeCuando("2026-10-30T07:00:00Z", AHORA, { ...OPCIONES, palabras: { hoy: "today" } }), /^today /);
  assert.equal(etiquetaDeCuando("no es fecha", AHORA, OPCIONES), null);
  assert.match(fechaCorta("2026-10-28T10:00:00Z", AHORA, OPCIONES), /^28 oct/);
});
