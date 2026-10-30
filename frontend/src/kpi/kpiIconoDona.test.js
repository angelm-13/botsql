import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), "utf8");

test("el icono de dona es un anillo propio, no la rebanada de lucide", () => {
  assert.doesNotMatch(leer("../pages/Dashboard.jsx"), /PieChartIcon/);
  assert.doesNotMatch(leer("../components/kpi-widgets/AgregarGraficoDemo.jsx"), /PieChartIcon/);
  assert.match(leer("../pages/Dashboard.jsx"), /dona: IconoDona/);
  assert.match(leer("../components/kpi-widgets/AgregarGraficoDemo.jsx"), /Icono: IconoDona/);
});

test("IconoDona pinta con currentColor, anillo tenue y tramo a color pleno", () => {
  const fuente = leer("../components/kpi-widgets/IconoDona.jsx");
  assert.match(fuente, /stroke="currentColor"/);
  assert.match(fuente, /opacity="0\.35"/);
  assert.match(fuente, /strokeDasharray/);
});
