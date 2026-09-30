// CONTRATO entre el backend y la tabla de "Material prestado ahora".
//
// fixtures/material_prestado_actual.real.json NO es un fixture escrito a mano: es la
// respuesta de `GET /kpi_definition/<id>/vivo` del backend local, guardada tal cual (con
// datos del seed demo y fechas de 512, 456, 100, 45 y 12 dias). Para regenerarla:
//
//   TOKEN=$(curl -s -X POST localhost:5001/auth/login -H 'Content-Type: application/json' \
//     -d '{"username":"admin1","password":"test password"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
//   curl -s "localhost:5001/kpi_definition/<id de material_prestado_actual>/vivo?limit=50&offset=0" \
//     -H "Authorization: Bearer $TOKEN" > frontend/src/kpi/fixtures/material_prestado_actual.real.json
//
// El otro lado del contrato esta en el backend (test_kpi_material_prestado_actual.py):
// fija los MISMOS campos con CAMPOS_RENGLON_PRESTADO_ACTUAL. Si el backend renombra un
// campo, esa prueba falla; si esta lista o el archivo real se desalinean, falla esta.
//
// Un renglon con otro nombre de campo no revienta: la tabla se pinta VACIA. Por eso la
// prueba comprueba que cada valor de la respuesta real llega a la pantalla.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { before } from "node:test";
import { fileURLToPath } from "node:url";
import { cargarRender } from "./bundleRender.mjs";

const REAL = JSON.parse(readFileSync(fileURLToPath(new URL("./fixtures/material_prestado_actual.real.json", import.meta.url)), "utf8"));
// Debe coincidir con CAMPOS_RENGLON_PRESTADO_ACTUAL en backend/app/kpis/registry.py.
const CAMPOS_DEL_BACKEND = ["articulo", "dias_prestado", "fecha_prestamo", "id_nm_incident_product", "id_user", "responsable"];

let pintarCuerpo;
before(async () => {
  ({ pintarCuerpo } = await cargarRender());
});

const WIDGET = { id_kpi_dashboard_widget: 1, tipo_grafica: "tabla", ids_kpi_definition: [57], parametros: {} };
const KPI = { id_kpi_definition: 57, clave: "material_prestado_actual", etiqueta: "Material prestado ahora", modo: "vivo", unidad: "piezas", dimensiones: ["empleado"], graficas_permitidas: ["tabla"] };
const datos = (items, total) => ({ snapshots: [], loading: false, error: "", vivoItems: items, vivoTotal: total, kpiInfos: [KPI], idsUsados: [57], esTablaVivo: true });
const texto = (html) => html.replace(/<[^>]*>/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ");

test("la respuesta real trae exactamente los campos del contrato y cada uno con su tipo", () => {
  assert.deepEqual(Object.keys(REAL).sort(), ["items", "limit", "offset", "total"]);
  assert.ok(REAL.items.length >= 10, "la respuesta guardada trae renglones de verdad");
  for (const renglon of REAL.items) {
    assert.deepEqual(Object.keys(renglon).sort(), CAMPOS_DEL_BACKEND);
    assert.equal(typeof renglon.articulo, "string");
    assert.equal(typeof renglon.responsable, "string");
    assert.match(renglon.fecha_prestamo, /^\d{4}-\d{2}-\d{2}$/);
    assert.ok(Number.isInteger(renglon.dias_prestado) && Number.isInteger(renglon.id_nm_incident_product) && Number.isInteger(renglon.id_user));
  }
  const dias = REAL.items.map((r) => r.dias_prestado);
  assert.deepEqual(dias, [...dias].sort((a, b) => b - a), "el backend entrega primero lo que lleva mas dias");
});

test("con la respuesta real, articulo, responsable, fecha del vale y dias llegan a la pantalla", () => {
  const html = pintarCuerpo({ widget: WIDGET, datos: datos(REAL.items, REAL.total) });
  const plano = texto(html);
  // Solo se ven 10 renglones hasta pulsar "Ver todos" (eso lo prueba navegadorTabla.test.mjs);
  // los 10 primeros, que son los que llevan mas dias, tienen que estar completos.
  const visibles = REAL.items.slice(0, 10);
  for (const renglon of visibles) {
    assert.ok(plano.includes(renglon.articulo), `articulo ${renglon.articulo}`);
    assert.ok(plano.includes(renglon.responsable), `responsable ${renglon.responsable}`);
    assert.ok(plano.includes(renglon.fecha_prestamo), `fecha ${renglon.fecha_prestamo}`);
    assert.ok(new RegExp(`${renglon.dias_prestado}\\s+días`).test(plano), `dias ${renglon.dias_prestado}`);
  }
  assert.equal([...html.matchAll(/<tr[ >]/g)].length - 1, visibles.length, "un <tr> por renglon visible, mas el de encabezado");
  assert.ok(plano.includes(`Ver todos (${REAL.items.length})`), "el resto queda tras 'Ver todos'");
  // El resumen sale de los datos reales.
  const responsables = new Set(REAL.items.map((r) => r.responsable)).size;
  assert.ok(plano.includes(`${REAL.items.length} renglones`) && plano.includes(`${responsables} responsables`));
  assert.ok(plano.includes(`${REAL.items[0].dias_prestado} días`), "el mas antiguo va en el resumen");
});

test("la gravedad sale de los dias reales: 512 y 456 coral, 45 ambar, 12 verde, cada una con su icono y texto", () => {
  const html = pintarCuerpo({ widget: WIDGET, datos: datos(REAL.items, REAL.total) });
  const clases = [...html.matchAll(/kpi-prestamos-fila nivel-(\w+)/g)].map((m) => m[1]);
  assert.deepEqual(clases.slice(0, 3), ["critico", "critico", "critico"], "512, 456 y 100 dias");
  assert.ok(clases.includes("atencion"));
  const plano = texto(html);
  assert.ok(plano.includes("512 días · 1 año, 5 meses") && plano.includes("456 días · 1 año, 3 meses"), "los dias legibles");
  assert.ok(plano.includes("Atrasado") && plano.includes("Requiere atención"), "el nivel tambien esta escrito, no solo pintado");
});

test("un renglon sin responsable dice 'Sin asignar' en vez de quedar vacio", () => {
  const sinResponsable = REAL.items.map((r, i) => (i === 0 ? { ...r, responsable: null } : r));
  const plano = texto(pintarCuerpo({ widget: WIDGET, datos: datos(sinResponsable, REAL.total) }));
  assert.ok(plano.includes("Sin asignar"));
});

test("si el backend limita la lista, la tabla dice 'Mostrando N de M'; si llegaron todos, no lo dice", () => {
  const limitada = texto(pintarCuerpo({ widget: WIDGET, datos: datos(REAL.items, 73) }));
  assert.match(limitada, new RegExp(`Mostrando ${REAL.items.length} de 73`));
  assert.ok(limitada.includes(`${REAL.items.length} de 73 renglones`), "el resumen tambien dice cuantos hay de mas");
  const completa = texto(pintarCuerpo({ widget: WIDGET, datos: datos(REAL.items, REAL.items.length) }));
  assert.doesNotMatch(completa, /Mostrando/);
});
