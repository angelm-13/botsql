import test from "node:test";
import assert from "node:assert/strict";
import { rangoAnterior, rangoDe } from "./rangosDeAsistencia.js";

test("semana de lunes a domingo, aunque cruce de mes", () => {
  assert.deepEqual(rangoDe("week", new Date(2026, 10, 4)), { start: "2026-11-02", end: "2026-11-08" });
  assert.deepEqual(rangoDe("week", new Date(2026, 10, 1)), { start: "2026-10-26", end: "2026-11-01" });
  assert.deepEqual(rangoAnterior("week", new Date(2026, 10, 4)), { start: "2026-10-26", end: "2026-11-01" });
});

test("quincena 1-15 o 16-fin de mes, febrero incluido", () => {
  assert.deepEqual(rangoDe("biweekly", new Date(2026, 10, 15)), { start: "2026-11-01", end: "2026-11-15" });
  assert.deepEqual(rangoDe("biweekly", new Date(2026, 1, 20)), { start: "2026-02-16", end: "2026-02-28" });
  assert.deepEqual(rangoAnterior("biweekly", new Date(2026, 10, 4)), { start: "2026-10-16", end: "2026-10-31" });
  assert.deepEqual(rangoAnterior("biweekly", new Date(2026, 10, 20)), { start: "2026-11-01", end: "2026-11-15" });
});
