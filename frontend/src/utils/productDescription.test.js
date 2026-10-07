import assert from "node:assert/strict";
import { test } from "node:test";
import { descripcionValida, sugerirDescripcion } from "./productDescription.js";

test("acepta formato de oracion con numeros, fracciones y siglas", () => {
  for (const t of ["Pulidor chico 3/4", "Cemento gris 50kg", "Codo PVC 90", "PVC codo 90", "Broca 1/4 - larga"]) {
    assert.equal(descripcionValida(t), true, t);
  }
});

test("rechaza lo que no es formato de oracion", () => {
  for (const t of ["pulidor chico", "PULIDOR CHICO 3/4", "Pulidor Chico", "Pulidor  chico", " Pulidor chico", "3/4 pulidor", "Pulidor_chico"]) {
    assert.equal(descripcionValida(t), false, t);
  }
});

test("vacia se acepta porque el campo es opcional", () => {
  assert.equal(descripcionValida(""), true);
  assert.equal(descripcionValida(null), true);
});

test("letras sueltas y codigos de modelo conservan su mayuscula", () => {
  assert.equal(sugerirDescripcion('PRENSA C 3"'), 'Prensa C 3"');
  assert.equal(sugerirDescripcion("PISTOLA CAFETATEADORA B26T600"), "Pistola cafetateadora B26T600");
  assert.equal(sugerirDescripcion("ROMPEDOR 18KG"), "Rompedor 18kg");
  assert.equal(sugerirDescripcion("TUERCA Y TORNILLO"), "Tuerca y tornillo");
});

test("la sugerencia corrige y siempre es valida", () => {
  assert.equal(sugerirDescripcion("PULIDOR CHICO 3/4"), "Pulidor chico 3/4");
  assert.equal(sugerirDescripcion("codo PVC 90"), "Codo PVC 90");
  assert.equal(sugerirDescripcion("TALADRO XYZ"), "Taladro xyz");
  for (const t of ["PULIDOR CHICO 3/4", "pulidor Chico", "CODO PVC 90"]) {
    assert.equal(descripcionValida(sugerirDescripcion(t)), true, t);
  }
});

test("la x de una medida no se queda en mayuscula", () => {
  assert.equal(sugerirDescripcion("PERFIL 4 X 4"), "Perfil 4 x 4");
});
