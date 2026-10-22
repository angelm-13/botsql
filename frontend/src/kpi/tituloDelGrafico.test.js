// El titulo propio de un grafico: `parametros.titulo`, hasta 80 caracteres, que la tarjeta (y con ella el PDF, que captura las
// tarjetas) y la vista previa muestran en lugar del nombre del KPI.
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import {
  TITULO_MAX, armarParametros, estadoDeWidget, normalizarTitulo, tituloConHtml, tituloDeWidget, widgetDeBorrador,
} from "./kpiParametros.js";

const BORRADOR = {
  tipoGrafica: "barras", idsKpiSeleccionados: ["3"],
  fechaInicio: "2026-08-01", fechaFin: "2026-08-31", comparar: false, fechaInicioB: "", fechaFinB: "",
  empleadosSeleccionados: [], departamentosSeleccionados: [], equiposSeleccionados: [],
  coloresKpi: {}, agruparPor: "entidad", umbralBajoStock: "", rangoRelativo: "personalizado", titulo: "",
};
const HOY = new Date(2026, 8, 29);

// --- normalizar -----------------------------------------------------------------------------

test("normalizarTitulo: recorta los espacios de los lados y no toca los de dentro", () => {
  assert.equal(normalizarTitulo("  Entradas  de Manzanillo  "), "Entradas  de Manzanillo");
});

test("normalizarTitulo: lo vacio, lo que no es texto y undefined son «sin titulo»", () => {
  for (const valor of ["", "   ", null, undefined, 7, ["x"], {}]) assert.equal(normalizarTitulo(valor), "", String(valor));
});

test("normalizarTitulo: el limite es de 80 caracteres, y se cuentan caracteres y no unidades UTF-16", () => {
  assert.equal(TITULO_MAX, 80);
  assert.equal(normalizarTitulo("a".repeat(80)), "a".repeat(80));
  assert.equal(normalizarTitulo("a".repeat(81)), "a".repeat(80));
  // 80 emojis son 160 unidades UTF-16 pero 80 caracteres: el servidor los cuenta como 80 y los acepta.
  assert.equal(Array.from(normalizarTitulo("😀".repeat(80))).length, 80);
  assert.equal(Array.from(normalizarTitulo("😀".repeat(100))).length, 80);
  assert.ok(!normalizarTitulo("😀".repeat(100)).includes("�"), "no parte un emoji por la mitad");
});

test("tituloConHtml: etiquetas y comentarios si; un «menor que» de texto no", () => {
  for (const valor of ["<b>x</b>", "</div>", "x <!-- y -->", "<script>", "<?xml", "a<b"]) assert.equal(tituloConHtml(valor), true, valor);
  for (const valor of ["Menos de <12 h", "a < b", "x<", "", "Entradas", null, 7]) assert.equal(tituloConHtml(valor), false, String(valor));
});

// --- guardar, editar y volver a guardar --------------------------------------------------------

test("armarParametros: con titulo lo guarda recortado", () => {
  assert.equal(armarParametros({ ...BORRADOR, titulo: "  Entradas por parque " }, { hoy: HOY }).titulo, "Entradas por parque");
});

test("armarParametros: sin titulo, o con solo espacios, no guarda la llave", () => {
  assert.equal("titulo" in armarParametros(BORRADOR, { hoy: HOY }), false);
  assert.equal("titulo" in armarParametros({ ...BORRADOR, titulo: "   " }, { hoy: HOY }), false);
  // Un borrador de antes de que existiera el campo (sin `titulo`) tampoco lo inventa ni revienta.
  const { titulo, ...viejo } = BORRADOR;
  assert.equal(titulo, "");
  assert.equal("titulo" in armarParametros(viejo, { hoy: HOY }), false);
});

test("armarParametros: lo que guarda cabe en el limite del servidor aunque el campo trajera mas", () => {
  assert.equal(Array.from(armarParametros({ ...BORRADOR, titulo: "x".repeat(200) }, { hoy: HOY }).titulo).length, 80);
});

test("guardar, editar y volver a guardar conserva el titulo", () => {
  const guardado = widgetDeBorrador({ ...BORRADOR, titulo: "Entradas por parque" }, { hoy: HOY });
  assert.equal(guardado.parametros.titulo, "Entradas por parque");

  const editado = estadoDeWidget({ ...guardado, id_kpi_dashboard_widget: 12 }, [], HOY);
  assert.equal(editado.titulo, "Entradas por parque", "el lapiz de la tarjeta trae el titulo al campo");

  const otraVez = widgetDeBorrador(editado, { hoy: HOY });
  assert.deepEqual(otraVez.parametros, guardado.parametros, "guardar sin tocar nada no lo pierde");

  // Y se puede cambiar, o quitar.
  assert.equal(widgetDeBorrador({ ...editado, titulo: "Salidas" }, { hoy: HOY }).parametros.titulo, "Salidas");
  assert.equal("titulo" in widgetDeBorrador({ ...editado, titulo: "" }, { hoy: HOY }).parametros, false);
});

test("un widget guardado antes de que existiera el titulo se abre sin titulo y se guarda igual", () => {
  const viejo = { id_kpi_dashboard_widget: 3, tipo_grafica: "barras", ids_kpi_definition: [3], parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" } };
  const estado = estadoDeWidget(viejo, [], HOY);
  assert.equal(estado.titulo, "");
  assert.equal("titulo" in armarParametros(estado, { hoy: HOY }), false);
});

test("un titulo guardado que no es texto se ignora en vez de romper el editor", () => {
  const raro = { id_kpi_dashboard_widget: 3, tipo_grafica: "barras", ids_kpi_definition: [3], parametros: { titulo: 7 } };
  assert.equal(estadoDeWidget(raro, [], HOY).titulo, "");
});

test("una tabla (KPI vivo) tambien guarda y conserva su titulo", () => {
  const widget = { id_kpi_dashboard_widget: 7, tipo_grafica: "tabla", ids_kpi_definition: [11], parametros: { columnas: 2, titulo: "Material afuera" } };
  const estado = estadoDeWidget(widget, []);
  assert.equal(estado.titulo, "Material afuera");
  assert.deepEqual(armarParametros(estado, { esTabla: true }), { columnas: 2, titulo: "Material afuera" });
  assert.deepEqual(armarParametros({ ...estado, titulo: "" }, { esTabla: true }), { columnas: 2 });
});

test("el titulo convive con los demas parametros sin pisarlos", () => {
  const parametros = armarParametros({ ...BORRADOR, empleadosSeleccionados: ["5"], equiposSeleccionados: ["4"], titulo: "Mi grafico" }, { hoy: HOY });
  assert.deepEqual([parametros.empleados, parametros.id_teams, parametros.titulo], [[5], [4], "Mi grafico"]);
});

// --- lo que dice la tarjeta ---------------------------------------------------------------------

test("tituloDeWidget: el titulo propio gana y, sin el, el nombre del KPI", () => {
  assert.equal(tituloDeWidget({ titulo: "Entradas por parque" }, "Entradas por equipo"), "Entradas por parque");
  assert.equal(tituloDeWidget({}, "Entradas por equipo"), "Entradas por equipo");
  assert.equal(tituloDeWidget(undefined, "Entradas por equipo"), "Entradas por equipo");
  assert.equal(tituloDeWidget({ titulo: "   " }, "Entradas por equipo"), "Entradas por equipo");
  assert.equal(tituloDeWidget({ titulo: 7 }, "Entradas por equipo"), "Entradas por equipo");
});

test("tituloDeWidget: en un grafico de varios KPIs el titulo propio reemplaza los nombres unidos", () => {
  assert.equal(tituloDeWidget({ titulo: "Asistencia" }, "Entradas por equipo + Salidas por equipo"), "Asistencia");
  assert.equal(tituloDeWidget({}, "Entradas por equipo + Salidas por equipo"), "Entradas por equipo + Salidas por equipo");
});

test("la tarjeta y la vista previa del editor usan tituloDeWidget, la unica regla", () => {
  const fuente = readFileSync(new URL("../pages/Dashboard.jsx", import.meta.url), "utf8");
  assert.match(fuente, /const titulo = tituloDeWidget\(widget\.parametros, nombreDeLosKpis\)/, "el encabezado de la tarjeta");
  assert.match(fuente, /<h4>\{titulo\}<\/h4>/, "y lo pinta");
  assert.match(fuente, /<strong>\{tituloDeWidget\(\{ titulo \}, /, "la vista previa del editor");
  // El PDF no arma titulos aparte: captura las tarjetas con html2canvas (solo el nombre del tablero va como titulo de seccion).
  assert.match(fuente, /tituloSeccion: dashboard\.nombre/);
});

// --- el limite es el mismo que el del servidor -----------------------------------------------------

test("el limite de 80 caracteres es el que valida el servidor", (t) => {
  const ruta = new URL("../../../backend/app/services/kpi_dashboard_widget_service.py", import.meta.url);
  if (!existsSync(ruta)) { t.skip("no esta el backend junto al front: no se puede contrastar el limite"); return; }
  const servidor = readFileSync(ruta, "utf8");
  assert.equal(Number(/^TITULO_MAX = (\d+)$/m.exec(servidor)?.[1]), TITULO_MAX);
});

// --- textos en los cuatro idiomas ---------------------------------------------------------------

const IDIOMAS = ["es", "en", "pt", "de"];
const LLAVES = ["chart_title", "chart_title_placeholder", "chart_title_html"];
const locale = (idioma) => readFileSync(new URL(`../i18n/locales/${idioma}.json`, import.meta.url), "utf8");

function llavesDeLaSeccion(texto, seccion) {
  const inicio = texto.indexOf(`\n  "${seccion}": {\n`);
  assert.ok(inicio >= 0, `no encuentro la seccion ${seccion}`);
  const fin = texto.indexOf("\n  }", inicio + 1);
  return [...texto.slice(inicio, fin).matchAll(/^ {4}"([^"]+)":/gm)].map((m) => m[1]);
}

test("los textos del titulo existen en es, en, pt y de, distintos de un idioma a otro, y sin llaves repetidas", () => {
  const textos = Object.fromEntries(IDIOMAS.map((idioma) => [idioma, JSON.parse(locale(idioma)).kpi_dashboard]));
  for (const llave of LLAVES) {
    for (const idioma of IDIOMAS) assert.ok(String(textos[idioma][llave] || "").trim(), `${idioma}.kpi_dashboard.${llave}`);
    assert.equal(new Set(IDIOMAS.map((idioma) => textos[idioma][llave])).size, IDIOMAS.length, `${llave}: dos idiomas tienen el mismo texto`);
  }
  for (const idioma of IDIOMAS) {
    const llaves = llavesDeLaSeccion(locale(idioma), "kpi_dashboard");
    assert.deepEqual(llaves.filter((llave, i) => llaves.indexOf(llave) !== i), [], `${idioma}: llaves repetidas`);
  }
});
