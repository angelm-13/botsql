import test from "node:test";
import assert from "node:assert/strict";

// El navegador del usuario puede estar en cualquier zona: se prueba en una muy
// lejana para demostrar que lo que se ve no depende de ella.
process.env.TZ = "Asia/Tokyo";

const { formatearFechaHora, ZONA_DE_NEGOCIO } = await import("./fechas.js");

test("la zona del negocio es America/Mexico_City (UTC-6)", () => {
  assert.equal(ZONA_DE_NEGOCIO, "America/Mexico_City");
});

test("una fecha de auditoria en UTC se muestra en hora del negocio", () => {
  // Es el caso de la tabla de incidencias: 20:33 UTC son las 2:33 p.m. en Mexico.
  const texto = formatearFechaHora("2026-10-14T20:33:16.049979Z", "es-MX");
  assert.match(texto, /14 oct 2026/);
  assert.match(texto, /2:33/);
});

test("una fecha con desfase explicito se convierte igual", () => {
  assert.match(formatearFechaHora("2026-10-14T14:33:00-06:00", "es-MX"), /2:33/);
  assert.match(formatearFechaHora("2026-10-14T21:33:00+01:00", "es-MX"), /2:33/);
});

test("una fecha de negocio sin zona se muestra tal cual, sin moverla", () => {
  const texto = formatearFechaHora("2026-10-14T14:33:12", "es-MX");
  assert.match(texto, /14 oct 2026/);
  assert.match(texto, /2:33/);
});

test("una fecha de auditoria que cruza la medianoche cambia de dia al convertir", () => {
  // 03:00 UTC del 15 son las 9:00 p.m. del 14 en Mexico.
  const texto = formatearFechaHora("2026-10-15T03:00:00Z", "es-MX");
  assert.match(texto, /14 oct 2026/);
  assert.match(texto, /9:00/);
});

test("medianoche sin zona es una fecha sin hora", () => {
  const texto = formatearFechaHora("2026-10-14T00:00:00", "es-MX");
  assert.match(texto, /14 oct 2026/);
  assert.doesNotMatch(texto, /:/);
});

test("lo que no es fecha devuelve vacio para que quien llama use su formato", () => {
  assert.equal(formatearFechaHora("hola"), "");
  assert.equal(formatearFechaHora(null), "");
  assert.equal(formatearFechaHora(42), "");
});
