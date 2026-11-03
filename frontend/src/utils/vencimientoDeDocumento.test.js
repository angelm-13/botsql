import test from "node:test";
import assert from "node:assert/strict";
import { errorDeVencimiento, reglaDeVencimiento } from "./vencimientoDeDocumento.js";

test("la regla por categoria: certification obligatoria; employee y supplier con salida; el resto opcional", () => {
  assert.equal(reglaDeVencimiento("certification"), "obligatorio");
  assert.equal(reglaDeVencimiento("employee"), "o_sin_vencimiento");
  assert.equal(reglaDeVencimiento("supplier"), "o_sin_vencimiento");
  for (const codigo of ["customer", "receipt", "internal_process", "warehouse_voucher", undefined, ""]) {
    assert.equal(reglaDeVencimiento(codigo), "opcional", String(codigo));
  }
});

test("certification: sin fecha es error, y marcar 'sin vencimiento' no la salva", () => {
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "certification", vencimiento: "" }), "obligatoria");
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "certification", vencimiento: "", sinVencimiento: true }), "obligatoria");
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "certification", vencimiento: "2030-01-01" }), null);
});

test("employee y supplier: la fecha o 'sin vencimiento'; las dos a la vez se contradicen", () => {
  for (const codigoDeCategoria of ["employee", "supplier"]) {
    assert.equal(errorDeVencimiento({ codigoDeCategoria, vencimiento: "" }), "obligatoria");
    assert.equal(errorDeVencimiento({ codigoDeCategoria, vencimiento: "", sinVencimiento: true }), null);
    assert.equal(errorDeVencimiento({ codigoDeCategoria, vencimiento: "2030-01-01" }), null);
    assert.equal(errorDeVencimiento({ codigoDeCategoria, vencimiento: "2030-01-01", sinVencimiento: true }), "contradiccion");
  }
});

test("las demas categorias: la fecha es opcional", () => {
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "customer", vencimiento: "" }), null);
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "receipt", vencimiento: "2030-01-01" }), null);
  assert.equal(errorDeVencimiento({ codigoDeCategoria: undefined, vencimiento: "" }), null);
});

test("la fecha de vencimiento no puede ser anterior a la de emision, en cualquier categoria", () => {
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "customer", emision: "2026-05-01", vencimiento: "2026-04-30" }), "orden");
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "customer", emision: "2026-05-01", vencimiento: "2026-05-01" }), null);
  assert.equal(errorDeVencimiento({ codigoDeCategoria: "certification", emision: "2026-05-01", vencimiento: "" }), "obligatoria");
});
