// Prueba de RENDER de la tarjeta y del cuerpo del Dashboard de KPIs, con todas
// las combinaciones que importan. Existe por un error real: una constante usada
// antes de declararse dentro de KpiWidgetCard lanzaba ReferenceError al pintar
// CUALQUIER tarjeta con fechas, y como no habia ErrorBoundary la aplicacion
// entera quedaba en blanco. Ni el build ni el lint de entonces lo veian: solo
// se manifiesta cuando esa linea SE EJECUTA, y eso pasa unicamente al renderizar
// una tarjeta con un widget guardado (que llega de la API, no del codigo).
//
// Sin dependencias nuevas: esbuild ya viene con Vite; se empaqueta la entrada
// JSX, se importa el resultado y se renderiza con react-dom/server.
import assert from "node:assert/strict";
import test, { before } from "node:test";
import { cargarRender } from "./bundleRender.mjs";

let pintarTarjeta;
let pintarCuerpo;

before(async () => {
  ({ pintarTarjeta, pintarCuerpo } = await cargarRender());
});

// --- catalogo y widgets ---------------------------------------------------
const CATALOGO = [
  { id_kpi_definition: 3, clave: "incidentes_resueltos_por_empleado", etiqueta: "Incidentes resueltos", unidad: "numero", dimensiones: ["empleado"], direccion: "alto_es_mejor", modulo: "operaciones", modo: "snapshot", graficas_permitidas: ["numero", "barras", "linea", "area", "dona"] },
  { id_kpi_definition: 4, clave: "ingresos_totales", etiqueta: "Ingresos", unidad: "moneda", dimensiones: ["global"], direccion: "alto_es_mejor", modulo: "facturacion", modo: "snapshot", graficas_permitidas: ["numero", "barras", "linea", "area", "dona"] },
  { id_kpi_definition: 8, clave: "incidencias_abiertas_vs_cerradas", etiqueta: "Abiertas vs. cerradas", unidad: "numero", dimensiones: ["estado"], direccion: "neutral", modulo: "operaciones", modo: "snapshot", colores_categoria: { abierta: "#ef6f5c", cerrada: "#22b573" }, graficas_permitidas: ["numero", "barras", "dona"] },
  { id_kpi_definition: 11, clave: "material_prestado_actual", etiqueta: "Material prestado ahora", unidad: "piezas", dimensiones: ["empleado"], direccion: "neutral", modulo: "operaciones", modo: "vivo", graficas_permitidas: ["tabla"] },
];

const TIPOS = ["numero", "barras", "linea", "area", "dona", "tabla"];

// Parametros como los guardaba el editor en cada epoca.
const PARAMETROS = {
  "viejo, fechas absolutas": { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" },
  "viejo, con comparacion": { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31", fecha_inicio_b: "2026-07-01", fecha_fin_b: "2026-07-31" },
  "rango relativo": { rango_relativo: "30_dias", fecha_inicio: "2026-08-31", fecha_fin: "2026-09-29" },
  "rango relativo con comparar el periodo anterior": { rango_relativo: "este_mes", comparar_anterior: true, fecha_inicio: "2026-09-01", fecha_fin: "2026-09-29", fecha_inicio_b: "2026-08-03", fecha_fin_b: "2026-08-31" },
  "rango relativo \"hoy\" comparado con hace 30 dias": { rango_relativo: "hoy", comparar_desfase_dias: 30, fecha_inicio: "2026-09-29", fecha_fin: "2026-09-29", fecha_inicio_b: "2026-08-30", fecha_fin_b: "2026-08-30" },
  "sin fechas": {},
  "sin parametros": undefined,
  "rango relativo desconocido (version futura)": { rango_relativo: "trimestre_pasado", fecha_inicio: "2026-06-01", fecha_fin: "2026-08-31" },
};

function idsDe(tipo) {
  if (tipo === "tabla") return [11];
  if (tipo === "dona") return [8];
  return [3];
}

function widgetDe(tipo, parametros) {
  return { id_kpi_dashboard_widget: 1, tipo_grafica: tipo, ids_kpi_definition: idsDe(tipo), parametros };
}

test("la tarjeta se pinta para los 6 tipos de grafica en toda combinacion de parametros", () => {
  let combinaciones = 0;
  for (const tipo of TIPOS) {
    for (const [nombre, parametros] of Object.entries(PARAMETROS)) {
      const html = pintarTarjeta({ widget: widgetDe(tipo, parametros), kpiCatalog: CATALOGO });
      const donde = `${tipo} / ${nombre}`;
      assert.match(html, /kpi-widget-card/, donde);
      const titulo = tipo === "tabla" ? "Material prestado ahora" : tipo === "dona" ? "Abiertas vs. cerradas" : "Incidentes resueltos";
      assert.ok(html.includes(titulo), `${donde}: falta el titulo del KPI`);
      combinaciones += 1;
    }
  }
  assert.equal(combinaciones, TIPOS.length * Object.keys(PARAMETROS).length);
});

test("el encabezado dice el rango: fechas tal cual en un widget viejo, y el nombre del rango en uno relativo", () => {
  const viejo = pintarTarjeta({ widget: widgetDe("barras", PARAMETROS["viejo, fechas absolutas"]), kpiCatalog: CATALOGO });
  assert.ok(viejo.includes("2026-08-01 → 2026-08-31"), "un widget viejo muestra SUS fechas");
  assert.ok(!viejo.includes(" · 20"), "y sin nombre de rango");

  const comparado = pintarTarjeta({ widget: widgetDe("barras", PARAMETROS["viejo, con comparacion"]), kpiCatalog: CATALOGO });
  assert.ok(comparado.includes("vs.") && comparado.includes("2026-07-01 → 2026-07-31"));

  // Un rango relativo se recalcula al dia de hoy: el nombre legible + fechas de hoy.
  const relativo = pintarTarjeta({ widget: widgetDe("barras", PARAMETROS["rango relativo"]), kpiCatalog: CATALOGO });
  assert.match(relativo, /30 días · \d{4}-\d{2}-\d{2} → \d{4}-\d{2}-\d{2}/, "nombre del rango, no la clave cruda");
  assert.ok(!relativo.includes("30_dias"), "la clave interna no se le muestra a nadie");

  const sinFechas = pintarTarjeta({ widget: widgetDe("barras", PARAMETROS["sin fechas"]), kpiCatalog: CATALOGO });
  assert.ok(sinFechas.includes("Sin rango de fechas configurado"));

  // Una tabla de un KPI vivo no tiene periodo: dice que es en vivo.
  const tabla = pintarTarjeta({ widget: widgetDe("tabla", {}), kpiCatalog: CATALOGO });
  assert.ok(tabla.includes("En vivo"));
});

// --- cuerpo con datos ---------------------------------------------------
const SNAPSHOT = { rango_a: { total: 14, por_empleado: { 5: 10, 7: 4 }, por_periodo: {} }, rango_b: null };
const SNAPSHOT_COMPARADO = { rango_a: { total: 14, por_empleado: { 5: 10, 7: 4 }, por_periodo: {} }, rango_b: { total: 20, por_empleado: { 5: 8, 9: 12 }, por_periodo: {} } };
const SNAPSHOT_ESTADO = { rango_a: { total: 7, por_empleado: { abierta: 5, cerrada: 2 }, por_periodo: {} }, rango_b: null };
const SNAPSHOT_VACIO = { rango_a: { total: 0, por_empleado: {}, por_periodo: {} }, rango_b: null };

function datosDe(widget, { snapshot, items = [], total = 0, error = "", loading = false }) {
  const kpiInfos = widget.ids_kpi_definition.map((id) => CATALOGO.find((k) => k.id_kpi_definition === id));
  return {
    snapshots: snapshot ? [snapshot] : [],
    loading, error, vivoItems: items, vivoTotal: total, kpiInfos,
    idsUsados: widget.ids_kpi_definition,
    esTablaVivo: widget.tipo_grafica === "tabla" && kpiInfos[0]?.modo === "vivo",
  };
}

test("el cuerpo se pinta con datos, con comparacion y vacio para cada tipo de grafica", () => {
  for (const tipo of ["numero", "barras", "linea", "area", "dona"]) {
    const widget = widgetDe(tipo, PARAMETROS["viejo, fechas absolutas"]);
    const conDatos = tipo === "dona" ? SNAPSHOT_ESTADO : SNAPSHOT;
    const html = pintarCuerpo({ widget, datos: datosDe(widget, { snapshot: conDatos }) });
    assert.ok(html.length > 0, `${tipo} con datos`);

    const comparado = pintarCuerpo({ widget: widgetDe(tipo, PARAMETROS["viejo, con comparacion"]), datos: datosDe(widget, { snapshot: tipo === "dona" ? SNAPSHOT_ESTADO : SNAPSHOT_COMPARADO }) });
    assert.ok(comparado.length > 0, `${tipo} con comparacion`);

    const vacio = pintarCuerpo({ widget, datos: datosDe(widget, { snapshot: SNAPSHOT_VACIO }) });
    // "numero" con total 0 se pinta como un 0; el resto dice que no hay datos.
    if (tipo === "numero") assert.ok(vacio.includes("0"), "numero vacio");
    else assert.ok(vacio.includes("Sin datos en el rango seleccionado."), `${tipo} vacio`);
  }
});

test("el numero muestra la unidad, la comparacion y la ayuda cuando no se compara", () => {
  const widget = widgetDe("numero", PARAMETROS["viejo, con comparacion"]);
  const sinComparar = pintarCuerpo({ widget, datos: datosDe(widget, { snapshot: SNAPSHOT }) });
  assert.ok(sinComparar.includes("Activa"), "invita a activar Comparar");
  const comparado = pintarCuerpo({ widget, datos: datosDe(widget, { snapshot: SNAPSHOT_COMPARADO }) });
  assert.ok(comparado.includes("vs. periodo anterior"));
});

test("la tabla en vivo: con filas, vacia, y una tabla sobre un KPI que no es vivo", () => {
  const widget = widgetDe("tabla", {});
  const items = [
    { id_nm_incident_product: 1, articulo: "Taladro", responsable: "Ana", fecha_prestamo: "2026-08-01", dias_prestado: 30 },
    { id_nm_incident_product: 2, articulo: "Sierra", responsable: null, fecha_prestamo: "2026-09-20", dias_prestado: 9 },
  ];
  const conFilas = pintarCuerpo({ widget, datos: datosDe(widget, { items, total: 2 }) });
  assert.ok(conFilas.includes("Taladro") && conFilas.includes("Sierra") && conFilas.includes("Sin asignar"));
  const paginada = pintarCuerpo({ widget, datos: datosDe(widget, { items, total: 50 }) });
  assert.ok(paginada.includes("Mostrando 2 de 50"));
  const vacia = pintarCuerpo({ widget, datos: datosDe(widget, { items: [], total: 0 }) });
  assert.ok(vacia.includes("No hay artículos prestados"));

  // Una tabla apuntando a un KPI que no es "vivo" (widget viejo o mal armado).
  const rara = { ...widgetDe("tabla", {}), ids_kpi_definition: [3] };
  const noVivo = pintarCuerpo({ widget: rara, datos: { ...datosDe(rara, {}), error: "tabla_no_soportada" } });
  assert.ok(noVivo.includes("próximamente"));
});

test("estados de carga y de error del cuerpo", () => {
  const widget = widgetDe("barras", PARAMETROS["viejo, fechas absolutas"]);
  assert.ok(pintarCuerpo({ widget, datos: datosDe(widget, { loading: true }) }).includes("kpi-skeleton"));
  assert.ok(pintarCuerpo({ widget, datos: datosDe(widget, { error: "missing_range" }) }).includes("le falta un rango"));
  assert.ok(pintarCuerpo({ widget, datos: datosDe(widget, { error: "missing_kpi" }) }).includes("le falta un KPI"));
  assert.ok(pintarCuerpo({ widget, datos: datosDe(widget, { error: "errors.rango_excede_limite" }) }).includes("excede el máximo"));
  assert.ok(pintarCuerpo({ widget, datos: datosDe(widget, { error: "errors.request_failed" }) }).includes("errors.request_failed"));
});

test("un widget guardado con unidades mezcladas (porcentaje + cantidad) se sigue pintando", () => {
  const catalogo = [
    { ...CATALOGO[0], id_kpi_definition: 3, unidad: "porcentaje", etiqueta: "Incidentes resueltos" },
    { ...CATALOGO[0], id_kpi_definition: 5, unidad: "numero", etiqueta: "Cancelaciones" },
  ];
  const widget = { id_kpi_dashboard_widget: 1, tipo_grafica: "barras", ids_kpi_definition: [3, 5], parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" } };
  const tarjeta = pintarTarjeta({ widget, kpiCatalog: catalogo });
  assert.ok(tarjeta.includes("Incidentes resueltos + Cancelaciones"));
  const snapshot = { rango_a: { total: 14, por_empleado: { 5: 10, 7: 4 }, por_periodo: {} }, rango_b: null };
  const datos = { snapshots: [snapshot, snapshot], loading: false, error: "", vivoItems: [], vivoTotal: 0, kpiInfos: catalogo, idsUsados: [3, 5], esTablaVivo: false };
  assert.ok(pintarCuerpo({ widget, datos }).length > 0);
});
