import test from "node:test";
import assert from "node:assert/strict";
import { detallesDePersonas, nombreDePersona } from "./kpiPersonas.js";

test("el nombre es el completo; sin el, el usuario; sin ninguno, el id", () => {
  assert.equal(nombreDePersona({ id_user: 1, full_name: "Ana Maria Lopez", username: "ana" }), "Ana Maria Lopez");
  assert.equal(nombreDePersona({ id_user: 2, username: "beto" }), "beto");
  assert.equal(nombreDePersona({ id_user: 3 }), "#3");
});

test("quien no se confunde con nadie no lleva texto secundario", () => {
  const usuarios = [{ id_user: 1, full_name: "Ana Lopez", role: "Supervisor" }, { id_user: 2, full_name: "Beto Ruiz", role: "Almacen" }];
  assert.equal(detallesDePersonas(usuarios).size, 0);
  assert.equal(detallesDePersonas(undefined).size, 0);
});

test("dos personas con el mismo nombre se distinguen por el rol, sin importar mayusculas ni acentos", () => {
  const detalles = detallesDePersonas([
    { id_user: 1, full_name: "José Pérez", role: "Supervisor" },
    { id_user: 2, full_name: "JOSE PEREZ", role: "Almacenista" },
    { id_user: 3, full_name: "Ana Lopez", role: "Supervisor" },
  ]);
  assert.equal(detalles.get("1"), "Supervisor");
  assert.equal(detalles.get("2"), "Almacenista");
  assert.equal(detalles.has("3"), false);
});

test("un nombre que es el principio de otro (cortado en otra pantalla) tambien se distingue", () => {
  const detalles = detallesDePersonas([
    { id_user: 1, full_name: "Juan Perez", role: "Supervisor" },
    { id_user: 2, full_name: "Juan Perez Lopez", role: "Almacenista" },
    { id_user: 3, full_name: "Juana Perez", role: "Almacenista" },
  ]);
  assert.equal(detalles.get("1"), "Supervisor");
  assert.equal(detalles.get("2"), "Almacenista");
  assert.equal(detalles.has("3"), false, "Juana no empieza con 'Juan ' como palabra completa");
});

test("mismo nombre y mismo rol: se agrega el usuario, y si tambien coincide, el id; nunca dos chips identicos", () => {
  const detalles = detallesDePersonas([
    { id_user: 1, full_name: "Luis Gil", role: "Supervisor", username: "lgil" },
    { id_user: 2, full_name: "Luis Gil", role: "Supervisor", username: "lgil2" },
    { id_user: 3, full_name: "Mario Paz", role: "Supervisor", username: "mp" },
    { id_user: 4, full_name: "Mario Paz", role: "Supervisor", username: "mp" },
    { id_user: 5, full_name: "Sin Rol", username: "sr1" },
    { id_user: 6, full_name: "Sin Rol", username: "sr2" },
  ]);
  assert.equal(detalles.get("1"), "Supervisor · @lgil");
  assert.equal(detalles.get("2"), "Supervisor · @lgil2");
  assert.equal(detalles.get("3"), "Supervisor · #3");
  assert.equal(detalles.get("4"), "Supervisor · #4");
  assert.equal(detalles.get("5"), "@sr1");
  assert.equal(detalles.get("6"), "@sr2");
});
