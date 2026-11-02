// La dona de un KPI que no se suma dice "Mostrando N de M" cuando hay mas rebanadas de las que caben (ver donaSinOtros.test.js).
import assert from "node:assert/strict";
import test, { before } from "node:test";
import { cargarGraficas } from "./bundleGraficas.mjs";

let pintarDona;
before(async () => { ({ pintarDona } = await cargarGraficas()); });
const datos = Array.from({ length: 3 }, (_, i) => ({ categoria: `P${i}`, valor: 90 - i, color: `#00${i}000` }));

test("con recorte la dona lo dice, con el texto que pone la pantalla; sin recorte no dice nada", () => {
  const con = pintarDona({ datos, recorte: { mostradas: 12, total: 15 }, textoRecorte: (n, t) => `Mostrando ${n} de ${t}` });
  assert.match(con, /<p class="kpi-barras-recorte">Mostrando 12 de 15<\/p>/);
  assert.equal(pintarDona({ datos }).includes("kpi-barras-recorte"), false);
  assert.match(pintarDona({ datos, recorte: { mostradas: 12, total: 15 } }), /Mostrando 12 de 15/, "con el texto por omision");
});
