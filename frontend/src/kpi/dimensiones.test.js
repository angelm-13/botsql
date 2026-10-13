// Pruebas de las dimensiones de KPI en el Dashboard: el backend manda los nombres, el filtro por
// empleados solo aplica a KPIs "por persona" y los widgets ya guardados no cambian.
import test from "node:test";
import assert from "node:assert/strict";
import {
  SIN_ASIGNAR, buildPieData, enriquecerCatalogo, etiquetasDeSnapshots, formatConUnidad, labelForDimension,
  muestraFiltroDePersonas, tipoDeDimension, unidadInfo,
} from "./kpiDatos.js";
import { armarParametros, estadoDeWidget } from "./kpiParametros.js";
import { propsDona } from "./kpiAdaptadores.js";

const DIMENSIONES = [
  { clave: "empleado", tipo: "persona", abierta: true },
  { clave: "estado", tipo: "categoria", abierta: false },
  { clave: "global", tipo: "global", abierta: false },
  { clave: "mesero", tipo: "catalogo", abierta: true },
];
const userLabel = (id) => `Usuario ${id}`;
const productLabel = (id) => `Producto ${id}`;

test("tipoDeDimension: el del catalogo del backend, o el de siempre si no hay catalogo", () => {
  assert.equal(tipoDeDimension("mesero", DIMENSIONES), "catalogo");
  assert.equal(tipoDeDimension("empleado", DIMENSIONES), "persona");
  // Sin catalogo (backend viejo): lo que el Dashboard asumia antes.
  assert.equal(tipoDeDimension("empleado"), "persona");
  assert.equal(tipoDeDimension("estado"), "categoria");
  assert.equal(tipoDeDimension("global", []), "global");
  // Una dimension desconocida NUNCA se trata como persona.
  assert.equal(tipoDeDimension("platillo"), "catalogo");
});

test("enriquecerCatalogo: agrega tipo y apertura sin quitar ni cambiar lo que ya traia el KPI", () => {
  const kpi = { id_kpi_definition: 7, clave: "ventas_por_mesero", dimensiones: ["mesero"], unidad: "moneda" };
  const [enriquecido] = enriquecerCatalogo([kpi], DIMENSIONES);
  assert.deepEqual(enriquecido, { ...kpi, dimension_tipo: "catalogo", dimension_abierta: true });
  const [legado] = enriquecerCatalogo([{ ...kpi, dimensiones: ["empleado"] }], undefined);
  assert.equal(legado.dimension_tipo, "persona");
  assert.equal("dimension_abierta" in legado, false);
});

test("el filtro de empleados se ofrece solo si algun KPI elegido desglosa por persona", () => {
  const catalogo = enriquecerCatalogo([
    { id_kpi_definition: 1, dimensiones: ["empleado"] },
    { id_kpi_definition: 2, dimensiones: ["mesero"] },
    { id_kpi_definition: 3, dimensiones: ["estado"] },
    { id_kpi_definition: 4, dimensiones: ["global"] },
  ], DIMENSIONES);
  assert.equal(muestraFiltroDePersonas([catalogo[0]]), true);
  assert.equal(muestraFiltroDePersonas([catalogo[1]]), false); // un mesero no es un usuario
  assert.equal(muestraFiltroDePersonas([catalogo[2]]), false);
  assert.equal(muestraFiltroDePersonas([catalogo[3]]), false);
  assert.equal(muestraFiltroDePersonas([catalogo[1], catalogo[0]]), true);
  assert.equal(muestraFiltroDePersonas([]), false);
  // Un KPI sin tipo enriquecido (catalogo cargado sin dimensiones) conserva el criterio de siempre.
  assert.equal(muestraFiltroDePersonas([{ dimensiones: ["empleado"] }]), true);
});

test("labelForDimension: el nombre que manda el backend gana, y 'Sin asignar' sale en cualquier dimension", () => {
  const etiquetas = etiquetasDeSnapshots([{ rango_a: { etiquetas: { 3: "Rosa", [SIN_ASIGNAR]: "Sin asignar" } } }]);
  // Un mesero jamas se busca entre los usuarios.
  const mesero = labelForDimension("mesero", userLabel, productLabel, etiquetas);
  assert.equal(mesero("3"), "Rosa");
  assert.equal(mesero("99"), "#99");
  assert.equal(mesero(SIN_ASIGNAR), "Sin asignar");
  // Empleado: el nombre del backend; sin el, el respaldo de usuarios de siempre.
  const empleado = labelForDimension("empleado", userLabel, productLabel, etiquetas);
  assert.equal(empleado("3"), "Rosa");
  assert.equal(empleado("5"), "Usuario 5");
  assert.equal(labelForDimension("empleado", userLabel, productLabel)("5"), "Usuario 5");
  // Producto igual.
  assert.equal(labelForDimension("producto", userLabel, productLabel, { 8: "Pulidor" })("8"), "Pulidor");
  assert.equal(labelForDimension("producto", userLabel, productLabel)("8"), "Producto 8");
  // Sin etiquetas del backend, la fila sin entidad se llama igual.
  assert.equal(labelForDimension("empleado", userLabel, productLabel)(SIN_ASIGNAR), "Sin asignar");
  assert.equal(labelForDimension("estado", userLabel, productLabel)(SIN_ASIGNAR), "Sin asignar");
  // Lo que ya funcionaba no cambia.
  assert.equal(labelForDimension("global", userLabel, productLabel)("x"), "Total");
  assert.equal(labelForDimension("estado", userLabel, productLabel)("abierta"), "Abierta");
});

test("buildPieData: 'Otros' se agrupa solo en dimensiones abiertas, segun lo declare el backend", () => {
  const muchas = {};
  for (let i = 1; i <= 12; i += 1) muchas[i] = 100 - i;
  const snapshot = { rango_a: { por_empleado: muchas } };
  const etiqueta = (id) => `M${id}`;
  // Declarada abierta (mesero): agrupa.
  assert.equal(buildPieData(snapshot, etiqueta, "Otros", false, "mesero", true).at(-1).name, "Otros");
  // Declarada cerrada: las 12 entran.
  assert.equal(buildPieData(snapshot, etiqueta, "Otros", false, "mesero", false).length, 12);
  // Sin declaracion, el criterio de siempre.
  assert.equal(buildPieData(snapshot, etiqueta, "Otros", false, "empleado").at(-1).name, "Otros");
  assert.equal(buildPieData(snapshot, etiqueta, "Otros", false, "estado").length, 12);
  // Via el adaptador de la dona.
  const props = propsDona({
    snapshot, kpiInfo: { dimensiones: ["mesero"], dimension_abierta: false }, labelForId: etiqueta,
    agruparPorPeriodo: false, formatNumber: String, textos: { otros: "Otros" },
  });
  assert.equal(props.datos.length, 12);
});

test("un widget guardado con parametros.empleados sigue igual: se lee y se vuelve a guardar identico", () => {
  const widget = {
    id_kpi_dashboard_widget: 1, tipo_grafica: "barras", ids_kpi_definition: [1],
    parametros: { fecha_inicio: "2026-09-01", fecha_fin: "2026-09-30", empleados: [7, 9], id_departments: [2] },
  };
  const estado = estadoDeWidget(widget, [{ id_kpi_definition: 1, dimensiones: ["empleado"] }]);
  assert.deepEqual(estado.empleadosSeleccionados, ["7", "9"]);
  assert.deepEqual(estado.departamentosSeleccionados, ["2"]);
  const guardado = armarParametros(estado, {});
  assert.deepEqual(guardado.empleados, [7, 9]);
  assert.deepEqual(guardado.id_departments, [2]);
});

test("la unidad 'minutos' se muestra con su sufijo y tiene etiqueta en el selector", () => {
  assert.equal(formatConUnidad("12.5", "minutos"), "12.5 min");
  assert.equal(unidadInfo("minutos").etiquetaSelector, "Min");
  // Una unidad desconocida sigue cayendo en "numero", sin imprimir la palabra cruda.
  assert.equal(formatConUnidad("7", "kilos"), "7");
});
