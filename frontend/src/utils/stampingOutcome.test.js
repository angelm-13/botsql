import test from "node:test";
import assert from "node:assert/strict";
import { stampingOutcome } from "./stampingOutcome.js";

test("solo 'stamped' cuenta como timbrado", () => {
  assert.equal(stampingOutcome({ operation: { status: "stamped" } }).ok, true);
});

test("un rechazo del PAC muestra el mensaje de Facturama", () => {
  const result = {
    operation: {
      status: "rejected",
      error_code: "http_400",
      response_metadata: { provider_response: JSON.stringify({ Message: "El nombre del receptor no coincide." }) },
    },
  };
  const outcome = stampingOutcome(result);
  assert.equal(outcome.ok, false);
  assert.match(outcome.message, /El nombre del receptor no coincide\./);
});

test("un rechazo sin cuerpo cae al código de error", () => {
  const outcome = stampingOutcome({ operation: { status: "rejected", error_code: "http_500" } });
  assert.equal(outcome.ok, false);
  assert.match(outcome.message, /http_500/);
});

test("un timbrado incierto no se da por bueno", () => {
  const outcome = stampingOutcome({ operation: { status: "uncertain", error_code: "provider_timeout" } });
  assert.equal(outcome.ok, false);
  assert.match(outcome.message, /no confirm/i);
});

test("una respuesta sin operación no se da por timbrada", () => {
  assert.equal(stampingOutcome({}).ok, false);
});
