import test from "node:test";
import assert from "node:assert/strict";
import {
  guardarTableroActivo, idDeUsuarioActual, leerTableroActivo, llaveDeTableroActivo, resolverTableroActivo,
} from "./kpiTableroActivo.js";

const memoria = (inicial = {}) => {
  const datos = { ...inicial };
  return { getItem: (k) => (k in datos ? datos[k] : null), setItem: (k, v) => { datos[k] = String(v); }, datos };
};
const lanza = { getItem() { throw new Error("bloqueado"); }, setItem() { throw new Error("bloqueado"); } };
const tableros = [{ id_kpi_dashboard: 4 }, { id_kpi_dashboard: 7 }, { id_kpi_dashboard: 9 }];

test("la llave es por usuario y sin usuario no hay llave", () => {
  assert.equal(llaveDeTableroActivo(12), "tyakxa-kpi-tablero:12");
  assert.equal(llaveDeTableroActivo(null), null);
  assert.equal(llaveDeTableroActivo(""), null);
});

test("guardar y leer: cada usuario tiene el suyo", () => {
  const storage = memoria();
  guardarTableroActivo(storage, 1, 7);
  guardarTableroActivo(storage, 2, 9);
  assert.equal(leerTableroActivo(storage, 1), "7");
  assert.equal(leerTableroActivo(storage, 2), "9");
  assert.equal(leerTableroActivo(storage, 3), null);
});

test("un storage que lanza o ausente no rompe nada", () => {
  assert.equal(leerTableroActivo(lanza, 1), null);
  assert.doesNotThrow(() => guardarTableroActivo(lanza, 1, 7));
  assert.equal(leerTableroActivo(undefined, 1), null);
  assert.doesNotThrow(() => guardarTableroActivo(undefined, 1, 7));
});

test("sin usuario o sin tablero no se escribe", () => {
  const storage = memoria();
  guardarTableroActivo(storage, null, 7);
  guardarTableroActivo(storage, 1, null);
  assert.deepEqual(storage.datos, {});
});

test("resolver: el guardado manda si existe y el id sale como viene en la lista", () => {
  assert.equal(resolverTableroActivo(tableros, null, "7"), 7);
});

test("resolver: un guardado que ya no existe cae al primero", () => {
  assert.equal(resolverTableroActivo(tableros, null, "99"), 4);
  assert.equal(resolverTableroActivo(tableros, null, null), 4);
});

test("resolver: el preferido vigente gana sobre el guardado; si desaparecio, el guardado", () => {
  assert.equal(resolverTableroActivo(tableros, 9, "7"), 9);
  assert.equal(resolverTableroActivo(tableros, 55, "7"), 7);
});

test("resolver: sin tableros es null", () => {
  assert.equal(resolverTableroActivo([], 4, "4"), null);
  assert.equal(resolverTableroActivo(undefined, null, null), null);
});

test("el id de usuario sale de localStorage.user y tolera basura", () => {
  assert.equal(idDeUsuarioActual(memoria({ user: JSON.stringify({ id_user: 5 }) })), 5);
  assert.equal(idDeUsuarioActual(memoria({ user: "{no json" })), null);
  assert.equal(idDeUsuarioActual(memoria()), null);
  assert.equal(idDeUsuarioActual(lanza), null);
});

test("cerrar sesion (borrar token, user y mfa_temp_token) no toca la llave del tablero", () => {
  const storage = memoria({ token: "t", user: JSON.stringify({ id_user: 5 }), mfa_temp_token: "m" });
  guardarTableroActivo(storage, 5, 7);
  ["token", "user", "mfa_temp_token"].forEach((k) => delete storage.datos[k]);
  assert.equal(leerTableroActivo(storage, 5), "7");
});
