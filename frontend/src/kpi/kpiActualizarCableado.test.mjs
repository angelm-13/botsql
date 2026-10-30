import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), "utf8");

test("el boton Actualizar datos recalcula y las tarjetas se recargan con el contador", () => {
  const dashboard = leer("../pages/Dashboard.jsx");
  assert.match(dashboard, /onClick=\{actualizarDatos\}/);
  assert.doesNotMatch(dashboard, /onClick=\{\(\) => loadDashboards\(\)\}/);
  assert.match(dashboard, /refresco=\{refresco\}/);
  // El efecto que pide los datos de cada tarjeta depende del contador: sin esto el boton no refrescaba nada.
  assert.match(dashboard, /equiposKey, agruparPor, refresco\]\);/);
  assert.match(dashboard, /version: snapshot/);
});

test("el hook llama al endpoint una vez por indicador, en secuencia", () => {
  const hook = leer("../components/kpi-widgets/useActualizarDatos.js");
  assert.match(hook, /for \(const item of items\)/);
  assert.match(hook, /recalcularKpiDashboard\(idTablero, \{ items: \[item\] \}\)/);
  assert.match(leer("../api/index.js"), /\/kpi_dashboard\/\$\{id\}\/recalcular/);
});

test("la linea global reemplaza al aviso de 24 h y el chip de tarjeta usa la regla de 36 h", () => {
  const dashboard = leer("../pages/Dashboard.jsx");
  assert.match(dashboard, /estadoGlobalDeDatos\(ultimoCalculoEfectivo\(calculo\.ultimo, recalculados\)/);
  assert.match(dashboard, /chipDeTarjeta\(\{/);
  assert.doesNotMatch(dashboard, /kpi-aviso-datos-atrasados|avisoDeDatosAtrasados|data_stale_notice/);
  assert.doesNotMatch(leer("../kpi/kpiFrescura.js"), /avisoDeDatosAtrasados/);
});
