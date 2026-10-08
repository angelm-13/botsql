import test from "node:test";
import assert from "node:assert/strict";
import {
  agruparPorProyecto, esXml, excedeLoAutorizado, estadoDeOrden, requiereReferencia,
  totalDeRenglones,
} from "./ordenDeCompra.js";

test("suma cantidad por costo sin errores de coma flotante", () => {
  assert.equal(totalDeRenglones([
    { quantity: 3, unit_cost: "0.1" }, { quantity: 3, unit_cost: "0.2" },
  ]), 0.9);
  assert.equal(totalDeRenglones([
    { quantity: 10, unit_cost: 400 }, { quantity: 40, unit_cost: 150 },
  ]), 10000);
});

test("un total con un costo que falta no es un total", () => {
  assert.equal(totalDeRenglones([
    { quantity: 10, unit_cost: 400 }, { quantity: 40, unit_cost: "" },
  ]), null);
  assert.equal(totalDeRenglones([{ quantity: 1, unit_cost: null }]), null);
});

test("avisa cuando lo comprado se pasa de lo autorizado mas la tolerancia", () => {
  assert.equal(excedeLoAutorizado(10000, 10900, 10), false);
  assert.equal(excedeLoAutorizado(10000, 11000, 10), false);
  assert.equal(excedeLoAutorizado(10000, 11000.01, 10), true);
  assert.equal(excedeLoAutorizado(10000, 8000, 10), false);
  assert.equal(excedeLoAutorizado(null, 8000, 10), false);
});

test("transferencia, cheque y tarjeta piden su referencia; efectivo no", () => {
  assert.deepEqual(
    ["transfer", "check", "card", "cash", "credit", "other"].filter(requiereReferencia),
    ["transfer", "check", "card"]);
});

test("reconoce el XML por su extension", () => {
  assert.equal(esXml("factura.XML"), true);
  assert.equal(esXml("factura.pdf"), false);
  assert.equal(esXml(""), false);
});

test("un estado que no conoce no rompe la pantalla", () => {
  assert.equal(estadoDeOrden("pending_authorization").etiqueta, "Por autorizar");
  assert.equal(estadoDeOrden("inventado").etiqueta, "inventado");
});

test("agrupa los renglones por proyecto y deja los sueltos al final", () => {
  const grupos = agruparPorProyecto([
    { id_proyect: null, description: "guantes" },
    { id_proyect: 20, description: "cemento", project: { folio: "PRJ-20" } },
    { id_proyect: 10, description: "soldadura", project: { folio: "PRJ-10" } },
    { id_proyect: 20, description: "arena", project: { folio: "PRJ-20" } },
  ]);
  assert.deepEqual(grupos.map((g) => g.renglones.map((r) => r.description)),
    [["soldadura"], ["cemento", "arena"], ["guantes"]]);
});
