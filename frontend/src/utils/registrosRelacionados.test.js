import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mensajeDeBorradoBloqueado } from "./registrosRelacionados.js";

const es = JSON.parse(readFileSync(new URL("../i18n/locales/es.json", import.meta.url), "utf8"));
const t = (key, fallback = key) => key.split(".").reduce((acc, part) => acc?.[part], es) || fallback;

test("sin detalle del servidor queda el mensaje de siempre", () => {
  assert.equal(mensajeDeBorradoBloqueado(t, {}), es.errors.delete_has_related_records);
  assert.equal(mensajeDeBorradoBloqueado(t, { related: [] }), es.errors.delete_has_related_records);
  assert.equal(mensajeDeBorradoBloqueado(t, undefined), es.errors.delete_has_related_records);
});

test("nombra cada grupo de registros con su nombre legible y cuantos son", () => {
  const mensaje = mensajeDeBorradoBloqueado(t, {
    related: [
      { table: "incident", count: 3, deleted_count: 0 },
      { table: "nm_team_user", count: 1, deleted_count: 0 },
    ],
  });
  assert.match(mensaje, /Vales \/ incidencias: 3; Membresías en equipos: 1\./);
  assert.doesNotMatch(mensaje, /nm_team_user|incident\b/);
});

test("avisa cuantos ya estan dados de baja, porque no se ven pero siguen bloqueando", () => {
  const mensaje = mensajeDeBorradoBloqueado(t, { related: [{ table: "incident", count: 4, deleted_count: 4 }] });
  assert.match(mensaje, /Vales \/ incidencias: 4 \(4 ya dados de baja\)/);
  assert.match(mensaje, /historial/);
});

test("una tabla sin nombre en el catalogo sale con su nombre tecnico legible", () => {
  const mensaje = mensajeDeBorradoBloqueado(t, { related: [{ table: "logistics_rack", count: 2, deleted_count: 0 }] });
  assert.match(mensaje, /Logistics rack: 2/);
});
