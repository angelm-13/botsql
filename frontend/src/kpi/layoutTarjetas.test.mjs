// Prueba de LAYOUT de la cabecera de la tarjeta de KPI, en un navegador de
// verdad (Chrome/Chromium sin interfaz): pinta las tarjetas reales -mismo
// marcado que el Dashboard, mismos estilos- en varios anchos y mide que
// titulo y subtitulos no se encimen ni se salgan de la cabecera.
//
// Existe por un error visto en produccion: con un titulo de dos renglones, o un
// rango que se partia en dos, las lineas de la cabecera se montaban unas sobre
// otras (un margen negativo). Eso no lo ve ningun render en servidor: solo se
// nota cuando hay layout.
//
// Sin dependencias nuevas: usa el Chrome que haya en la maquina y, si no hay
// ninguno (CI sin navegador), la prueba se SALTA en lugar de fallar. La parte
// que no necesita navegador -las reglas de CSS que hacen posible el problema-
// esta en estructuraCabecera.test.mjs y corre siempre.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import test, { before } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { CACHE_DIR, cargarRender } from "./bundleRender.mjs";

const CANDIDATOS = [
  process.env.CHROME_BIN,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);
const CHROME = CANDIDATOS.find((ruta) => existsSync(ruta));

const ESTILOS = ["kpi-widgets.css", "kpi-editor.css", "kpi-dashboard.css"]
  .map((archivo) => readFileSync(fileURLToPath(new URL(`../styles/${archivo}`, import.meta.url)), "utf8"))
  .join("\n");

const KPI = (id, etiqueta) => ({ id_kpi_definition: id, etiqueta, clave: `k${id}`, unidad: "numero", dimensiones: ["empleado"], direccion: "neutral", modulo: "operaciones", modo: "snapshot", graficas_permitidas: ["barras"] });
// Los titulos reales que se vieron encimados en sistema-test, y uno absurdamente largo.
const CATALOGO = [
  KPI(1, "Vales vencidos por responsable"),
  KPI(2, "Incidentes resueltos por empleado"),
  KPI(3, "Cancelaciones por empleado"),
  KPI(4, "Desarrollo por empleado"),
  KPI(5, "Un titulo extraordinariamente largo de KPI que sigue y sigue para probar el ajuste de linea de la cabecera"),
  KPI(6, "PalabraSinEspaciosExtremadamenteLargaQueNoCabeEnNingunaTarjetaEstrechaDelTablero"),
];
const w = (id, parametros) => ({ id_kpi_dashboard_widget: id, tipo_grafica: "barras", ids_kpi_definition: [id], parametros });
const WIDGETS = [
  w(1, { fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31" }),
  w(2, { rango_relativo: "90_dias", fecha_inicio: "2026-07-02", fecha_fin: "2026-09-29" }),
  // El caso de Cancelaciones: rango relativo largo + linea "vs." de comparacion.
  w(3, { rango_relativo: "este_mes", comparar_anterior: true, fecha_inicio: "2026-09-01", fecha_fin: "2026-09-29", fecha_inicio_b: "2026-08-03", fecha_fin_b: "2026-08-31" }),
  w(4, { fecha_inicio: "2026-06-01", fecha_fin: "2026-08-31", fecha_inicio_b: "2026-03-01", fecha_fin_b: "2026-05-31" }),
  w(5, { rango_relativo: "mes_anterior", comparar_anterior: true, fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31", fecha_inicio_b: "2026-07-01", fecha_fin_b: "2026-07-31" }),
  w(6, { rango_relativo: "este_anio", comparar_anterior: true, fecha_inicio: "2026-01-01", fecha_fin: "2026-09-29", fecha_inicio_b: "2025-04-05", fecha_fin_b: "2025-12-31" }),
];
// 320 = telefono; 340 = minimo de la cuadricula; el resto, tarjetas holgadas.
const ANCHOS = [280, 320, 340, 420, 640];

const MEDIDOR = `<script>
addEventListener("load", () => {
  const solapa = (a, b) => a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
  const fallas = [];
  document.querySelectorAll(".kpi-widget-card").forEach((card, i) => {
    const n = "tarjeta " + (i + 1);
    const cab = card.querySelector(".kpi-widget-card-header");
    const cabR = cab.getBoundingClientRect();
    const cardR = card.getBoundingClientRect();
    const partes = [...cab.querySelectorAll("h4, .kpi-widget-meta")].map((el) => ({ el, r: el.getBoundingClientRect() }));
    for (let a = 0; a < partes.length; a += 1) for (let b = a + 1; b < partes.length; b += 1) {
      if (solapa(partes[a].r, partes[b].r)) fallas.push(n + ": se encima <" + partes[a].el.tagName.toLowerCase() + "." + (partes[a].el.className || "") + "> con <" + partes[b].el.tagName.toLowerCase() + "." + (partes[b].el.className || "") + ">");
    }
    partes.forEach(({ el, r }) => {
      if (r.bottom > cabR.bottom + 0.5) fallas.push(n + ": " + el.tagName.toLowerCase() + " se sale por debajo de la cabecera");
      if (r.right > cardR.right + 0.5) fallas.push(n + ": " + el.tagName.toLowerCase() + " se sale de la tarjeta por la derecha");
    });
    const acciones = card.querySelector(".kpi-widget-card-actions").getBoundingClientRect();
    partes.forEach(({ el, r }) => { if (solapa(r, acciones)) fallas.push(n + ": " + el.tagName.toLowerCase() + " se encima con los botones"); });
    if (card.querySelector(".kpi-chart-box").getBoundingClientRect().top < cabR.bottom - 0.5) fallas.push(n + ": el cuerpo sube sobre la cabecera");
    if (card.scrollWidth > card.clientWidth + 1) fallas.push(n + ": la tarjeta tiene scroll horizontal");
  });
  document.title = JSON.stringify({ fallas, tarjetas: document.querySelectorAll(".kpi-widget-card").length });
});
</script>`;

let tarjetas = [];

before(async () => {
  if (!CHROME) return;
  const { pintarTarjeta } = await cargarRender();
  tarjetas = WIDGETS.map((widget) => pintarTarjeta({ widget, kpiCatalog: CATALOGO }));
});

for (const ancho of ANCHOS) {
  test(`cabecera de la tarjeta a ${ancho}px: titulo y subtitulos no se encriman`, { skip: CHROME ? false : "no hay Chrome/Chromium (define CHROME_BIN)" }, () => {
    const dir = `${CACHE_DIR}layout/`;
    mkdirSync(dir, { recursive: true });
    const archivo = `${dir}ancho-${ancho}.html`;
    writeFileSync(archivo, `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;font-family:system-ui,sans-serif}${ESTILOS}</style></head><body><div class="kpi-dashboard"><div style="display:grid;grid-template-columns:${ancho}px;gap:16px;width:${ancho}px">${tarjetas.join("")}</div></div>${MEDIDOR}</body></html>`);
    const corrida = spawnSync(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=900,2400", "--virtual-time-budget=3000", "--dump-dom", pathToFileURL(archivo).href], { encoding: "utf8", timeout: 60000 });
    const titulo = /<title>(.*?)<\/title>/s.exec(corrida.stdout || "");
    assert.ok(titulo, `Chrome no devolvio la medicion (codigo ${corrida.status}): ${(corrida.stderr || "").slice(0, 300)}`);
    const medicion = JSON.parse(titulo[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"));
    assert.equal(medicion.tarjetas, WIDGETS.length);
    assert.deepEqual(medicion.fallas, []);
  });
}
