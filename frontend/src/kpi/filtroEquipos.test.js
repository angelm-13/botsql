// El filtro por equipos del editor de graficos (paso 3, "Filtros"): se guarda en `parametros.id_teams`, sobrevive a
// editar y volver a guardar, y se manda en TODAS las consultas del Dashboard.
import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import { desglosaPorEquipo, enriquecerCatalogo, muestraFiltroDeEquipos } from "./kpiDatos.js";
import { armarParametros, estadoDeWidget, widgetDeBorrador } from "./kpiParametros.js";

const BORRADOR = {
  tipoGrafica: "barras", idsKpiSeleccionados: ["3"],
  fechaInicio: "2026-08-01", fechaFin: "2026-08-31", comparar: false, fechaInicioB: "", fechaFinB: "",
  empleadosSeleccionados: [], departamentosSeleccionados: [], equiposSeleccionados: [],
  coloresKpi: {}, agruparPor: "entidad", umbralBajoStock: "", rangoRelativo: "personalizado",
};
const HOY = new Date(2026, 8, 29);

const DIMENSIONES = [
  { clave: "empleado", tipo: "persona", abierta: true },
  { clave: "equipo", tipo: "catalogo", abierta: false },
  { clave: "estado", tipo: "categoria", abierta: false },
  { clave: "global", tipo: "global", abierta: false },
  { clave: "mesero", tipo: "catalogo", abierta: true },
];
const catalogo = enriquecerCatalogo([
  { id_kpi_definition: 1, dimensiones: ["empleado"] },
  { id_kpi_definition: 2, dimensiones: ["equipo"] },
  { id_kpi_definition: 3, dimensiones: ["estado"] },
  { id_kpi_definition: 4, dimensiones: ["global"] },
  { id_kpi_definition: 5, dimensiones: ["mesero"] },
], DIMENSIONES);

// --- se guarda y se conserva al editar ----------------------------------------------------

test("armarParametros: con equipos elegidos guarda id_teams como numeros", () => {
  const parametros = armarParametros({ ...BORRADOR, equiposSeleccionados: ["4", "9"] }, { hoy: HOY });
  assert.deepEqual(parametros.id_teams, [4, 9]);
});

test("armarParametros: sin equipos elegidos no guarda id_teams (un widget sin filtro sigue igual que antes)", () => {
  assert.equal("id_teams" in armarParametros(BORRADOR, { hoy: HOY }), false);
  // Un borrador de antes de que existiera el filtro (sin el campo) tampoco lo inventa ni revienta.
  const { equiposSeleccionados, ...viejo } = BORRADOR;
  assert.equal(equiposSeleccionados.length, 0);
  assert.equal("id_teams" in armarParametros(viejo, { hoy: HOY }), false);
});

test("guardar, editar y volver a guardar conserva el filtro de equipos", () => {
  const guardado = widgetDeBorrador({ ...BORRADOR, equiposSeleccionados: ["4", "9"] }, { hoy: HOY });
  assert.deepEqual(guardado.parametros.id_teams, [4, 9]);

  // El lapiz de la tarjeta: el widget guardado vuelve a ser un borrador...
  const editado = estadoDeWidget({ ...guardado, id_kpi_dashboard_widget: 12 }, [], HOY);
  assert.deepEqual(editado.equiposSeleccionados, ["4", "9"], "el borrador trae los equipos como texto, igual que los empleados");

  // ...y guardarlo SIN tocar nada no borra el filtro.
  const otraVez = widgetDeBorrador(editado, { hoy: HOY });
  assert.deepEqual(otraVez.parametros.id_teams, [4, 9]);
  assert.deepEqual(otraVez.parametros, guardado.parametros);
});

test("editar un widget sin equipos lo deja sin equipos", () => {
  const guardado = widgetDeBorrador(BORRADOR, { hoy: HOY });
  const editado = estadoDeWidget({ ...guardado, id_kpi_dashboard_widget: 12 }, [], HOY);
  assert.deepEqual(editado.equiposSeleccionados, []);
  assert.equal("id_teams" in widgetDeBorrador(editado, { hoy: HOY }).parametros, false);
});

test("un widget guardado antes de que existiera el filtro se abre sin equipos", () => {
  const viejo = { id_kpi_dashboard_widget: 3, tipo_grafica: "barras", ids_kpi_definition: [3], parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" } };
  assert.deepEqual(estadoDeWidget(viejo, [], HOY).equiposSeleccionados, []);
});

test("un id_teams guardado que no es una lista se ignora en vez de romper el editor", () => {
  const raro = { id_kpi_dashboard_widget: 3, tipo_grafica: "barras", ids_kpi_definition: [3], parametros: { id_teams: "4" } };
  assert.deepEqual(estadoDeWidget(raro, [], HOY).equiposSeleccionados, []);
});

test("conservar el filtro no pisa los otros: empleados, departamentos y equipos conviven", () => {
  const parametros = armarParametros({
    ...BORRADOR, empleadosSeleccionados: ["5"], departamentosSeleccionados: ["2"], equiposSeleccionados: ["4"],
  }, { hoy: HOY });
  assert.deepEqual([parametros.empleados, parametros.id_departments, parametros.id_teams], [[5], [2], [4]]);
});

test("una tabla (KPI vivo) son datos de ahora: no guarda ni inventa un filtro de equipos", () => {
  assert.equal("id_teams" in armarParametros({ ...BORRADOR, equiposSeleccionados: ["4"] }, { esTabla: true }), false);
});

// --- cuando se ofrece el filtro ------------------------------------------------------------

test("el filtro de equipos se ofrece con KPIs por equipo y por persona, y con ningun otro", () => {
  const [persona, equipo, estado, global, mesero] = catalogo;
  assert.equal(muestraFiltroDeEquipos([persona]), true, "un KPI por persona: deja a quienes estaban en esos equipos");
  assert.equal(muestraFiltroDeEquipos([equipo]), true, "un KPI por equipo: filtra los equipos que se pintan");
  assert.equal(muestraFiltroDeEquipos([estado]), false);
  assert.equal(muestraFiltroDeEquipos([global]), false);
  assert.equal(muestraFiltroDeEquipos([mesero]), false, "un mesero no es un usuario ni un equipo");
  assert.equal(muestraFiltroDeEquipos([estado, equipo]), true);
  assert.equal(muestraFiltroDeEquipos([]), false);
  assert.equal(muestraFiltroDeEquipos(undefined), false);
  // Sin el catalogo de dimensiones del backend (uno viejo) el KPI por persona conserva su criterio de siempre.
  assert.equal(muestraFiltroDeEquipos([{ dimensiones: ["empleado"] }]), true);
});

test("la ayuda de «Sin equipo» aplica solo a los KPIs que desglosan por equipo", () => {
  const [persona, equipo, estado] = catalogo;
  assert.equal(desglosaPorEquipo([equipo]), true);
  assert.equal(desglosaPorEquipo([persona]), false);
  assert.equal(desglosaPorEquipo([estado, equipo]), true);
  assert.equal(desglosaPorEquipo([]), false);
});

// --- se manda en todas las consultas ---------------------------------------------------------

test("Dashboard.jsx manda id_teams en cada llamada a /kpi_snapshot/query", () => {
  const fuente = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  const consultas = (fuente.match(/queryKpiSnapshot\(/g) || []).length;
  const conEquipos = (fuente.match(/\.id_teams = /g) || []).length;
  assert.ok(consultas >= 2, "la tarjeta del widget y la mini-tendencia del numero");
  // Si alguien agrega una consulta nueva sin el filtro, un widget con equipos mostraria cifras de TODOS: esta cuenta lo avisa.
  assert.equal(conEquipos, consultas, `hay ${consultas} consultas a queryKpiSnapshot y ${conEquipos} asignaciones de id_teams`);
  assert.match(fuente, /paramsComunes\.id_teams = equiposKey/);
  assert.match(fuente, /params\.id_teams = idTeamsKey/);
  // El efecto de la tarjeta se vuelve a correr si cambia el filtro.
  assert.match(fuente, /departamentosKey, equiposKey, agruparPor\]/);
});

// --- textos en los cuatro idiomas -----------------------------------------------------------

const IDIOMAS = ["es", "en", "pt", "de"];
const LLAVES_DEL_FILTRO = ["teams_filter", "teams_selected", "teams_filter_help", "teams_filter_history_help", "no_filters"];
const locale = (idioma) => readFileSync(new URL(`../i18n/locales/${idioma}.json`, import.meta.url), "utf8");

// `JSON.parse` se queda con la ultima de dos llaves repetidas y no avisa: se cuentan en el texto, dentro de la seccion.
function llavesDeLaSeccion(texto, seccion) {
  const inicio = texto.indexOf(`\n  "${seccion}": {\n`);
  assert.ok(inicio >= 0, `no encuentro la seccion ${seccion}`);
  const fin = texto.indexOf("\n  }", inicio + 1);
  return [...texto.slice(inicio, fin).matchAll(/^ {4}"([^"]+)":/gm)].map((m) => m[1]);
}

test("los textos del filtro de equipos existen en es, en, pt y de, y son distintos de un idioma a otro", () => {
  const textos = Object.fromEntries(IDIOMAS.map((idioma) => [idioma, JSON.parse(locale(idioma)).kpi_dashboard]));
  for (const llave of LLAVES_DEL_FILTRO) {
    for (const idioma of IDIOMAS) {
      assert.equal(typeof textos[idioma][llave], "string", `${idioma}.kpi_dashboard.${llave}`);
      assert.ok(textos[idioma][llave].trim().length > 0, `${idioma}.kpi_dashboard.${llave} esta vacio`);
    }
    assert.equal(new Set(IDIOMAS.map((idioma) => textos[idioma][llave])).size, IDIOMAS.length, `${llave}: dos idiomas tienen el mismo texto`);
  }
});

test("agregar los textos del filtro no duplico ninguna llave de kpi_dashboard", () => {
  for (const idioma of IDIOMAS) {
    const llaves = llavesDeLaSeccion(locale(idioma), "kpi_dashboard");
    const repetidas = llaves.filter((llave, i) => llaves.indexOf(llave) !== i);
    assert.deepEqual(repetidas, [], `${idioma}: llaves repetidas en kpi_dashboard`);
    for (const llave of LLAVES_DEL_FILTRO) assert.ok(llaves.includes(llave), `${idioma}: falta ${llave}`);
  }
});

test("la ayuda en español nombra la fila «Sin equipo» tal como la rotula el backend", () => {
  // «Sin equipo» es la `etiqueta_sin_asignar` de la dimension equipo. Las otras traducciones no se contrastan con el backend.
  assert.match(JSON.parse(locale("es")).kpi_dashboard.teams_filter_help, /«Sin equipo»/);
});
