import test from "node:test";
import assert from "node:assert/strict";
import {
  costoDeRenta, diasDelPeriodo, etapaDeRenta, periodosDeRenta,
} from "./rentaDeMaquinaria.js";

test("el periodo cuenta el dia de inicio y el de fin", () => {
  assert.equal(diasDelPeriodo("2026-11-01", "2026-11-03"), 3);
  assert.equal(diasDelPeriodo("2026-11-01", "2026-11-01"), 1);
  assert.equal(diasDelPeriodo("2026-11-03", "2026-11-01"), null);
  assert.equal(diasDelPeriodo("", "2026-11-01"), null);
});

test("semanas y meses redondean hacia arriba, como el servidor", () => {
  assert.equal(periodosDeRenta("2026-11-01", "2026-11-03", "day"), 3);
  assert.equal(periodosDeRenta("2026-11-01", "2026-11-07", "week"), 1);
  assert.equal(periodosDeRenta("2026-11-01", "2026-11-09", "week"), 2);
  assert.equal(periodosDeRenta("2026-11-01", "2026-12-01", "month"), 2);
  assert.equal(periodosDeRenta("2026-11-01", "2026-11-09", "año"), null);
});

test("el costo es tarifa por periodos, y sin tarifa no hay costo", () => {
  assert.equal(costoDeRenta(1500, "2026-11-01", "2026-11-03", "day"), 4500);
  assert.equal(costoDeRenta("3000", "2026-11-01", "2026-11-14", "week"), 6000);
  assert.equal(costoDeRenta("", "2026-11-01", "2026-11-03"), null);
  assert.equal(costoDeRenta(0, "2026-11-01", "2026-11-03"), null);
  assert.equal(costoDeRenta(100, "2026-11-03", "2026-11-01"), null);
});

test("la etapa avisa cuando la renta esta por vencer", () => {
  assert.equal(etapaDeRenta({ stage: "on_site", days_left: 10 }).clave, "rental.stage.on_site");
  assert.equal(etapaDeRenta({ stage: "on_site", days_left: 2 }).clave, "rental.stage.due_soon");
  assert.equal(etapaDeRenta({ stage: "overdue", days_left: -1 }).clase, "vencida");
  assert.equal(etapaDeRenta({ stage: "returned" }).clase, "devuelta");
  assert.equal(etapaDeRenta(null), null);
});
