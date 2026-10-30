// Prueba del SelectorDeKpi en un navegador de verdad (Chrome/Chromium sin
// interfaz): hace clic, escribe y mide, con el CSS real. El render en servidor
// (renderSelector.test.mjs) no puede cambiar de modulo ni escribir en el buscador,
// y jsdom no tiene layout; esto cubre las dos cosas.
//
// Sin dependencias nuevas: empaqueta con el esbuild de Vite y usa el Chrome que
// haya (o CHROME_BIN); sin ninguno, se SALTA. Igual que layoutTarjetas.test.mjs.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { build } from "esbuild";
import { CACHE_DIR } from "./bundleRender.mjs";

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

// El guion corre DENTRO de la pagina: cada paso es { nombre, ok, detalle }.
const GUION = `
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
const resultados = [];
const paso = (nombre, ok, detalle = "") => resultados.push({ nombre, ok: Boolean(ok), detalle: String(detalle) });
const KPI = (id, etiqueta, modulo, unidad, extra = {}) => ({ id_kpi_definition: id, etiqueta, clave: "k" + id, modulo, unidad, dimensiones: ["empleado"], modo: "snapshot", descripcion: "Descripcion de " + etiqueta, ...extra });
const CATALOGO = [
  KPI(1, "Incidencias abiertas", "operaciones", "numero"),
  KPI(2, "Incidentes resueltos", "operaciones", "porcentaje"),
  KPI(3, "Cancelaciones", "operaciones", "numero"),
  KPI(4, "Existencias", "inventario", "numero"),
  KPI(5, "Lotes por caducar", "inventario", "numero"),
  KPI(6, "Ordenes entregadas", "laboratorio", "numero"),
  KPI(7, "Documentos vencidos", "documentos", "numero"),
  KPI(8, "Ingresos totales", "facturacion", "moneda", { dimensiones: ["global"] }),
];
let contador = 0;
async function montar(config, ancho = 760) {
  contador += 1;
  const contenedor = document.createElement("div");
  contenedor.id = "escenario-" + contador;
  contenedor.style.cssText = "width:" + ancho + "px;margin:8px;font-family:system-ui,sans-serif";
  contenedor.className = "kpi-dashboard";
  document.body.appendChild(contenedor);
  window.montarSelector({ contenedor, catalogo: CATALOGO, ...config });
  await esperar(60);
  return contenedor;
}
const botones = (c) => [...c.querySelectorAll("[data-modulo]")];
const activo = (c) => botones(c).filter((b) => b.classList.contains("active")).map((b) => b.dataset.modulo);
const nombres = (c) => [...c.querySelectorAll(".kpi-selector-fila .kpi-editor-kpi-nombre")].map((n) => n.textContent.trim());
const grupos = (c) => [...c.querySelectorAll(".kpi-selector-grupo")].map((g) => g.dataset.grupo);
const click = async (el) => { el.click(); await esperar(60); };
const escribir = async (input, valor) => {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, valor);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  await esperar(60);
};
const fila = (c, nombre) => [...c.querySelectorAll(".kpi-selector-fila")].find((f) => f.textContent.includes(nombre));
const opcion = (c, nombre) => fila(c, nombre).querySelector(".kpi-editor-kpi-opcion");

async function todo() {
  // 1. Abre en el primer modulo, con boton por modulo y solo sus KPIs.
  let c = await montar({});
  paso("hay un boton por modulo (5: operaciones, inventario, facturacion, laboratorio, documentos) mas Variables", botones(c).map((b) => b.dataset.modulo).join() === "operaciones,inventario,facturacion,laboratorio,documentos,variables", botones(c).map((b) => b.dataset.modulo).join());
  paso("abre en el primer modulo", activo(c).join() === "operaciones", activo(c).join());
  paso("muestra SOLO los KPIs de ese modulo", nombres(c).join("|") === "Incidencias abiertas|Incidentes resueltos|Cancelaciones", nombres(c).join("|"));
  paso("cada boton dice cuantos KPIs tiene", botones(c).map((b) => b.querySelector(".kpi-selector-modulo-cuenta").textContent).join() === "3,2,1,1,1,1", botones(c).map((b) => b.querySelector(".kpi-selector-modulo-cuenta").textContent).join());
  paso("los iconos de los botones son distintos entre si", new Set(botones(c).map((b) => b.querySelector("svg").innerHTML)).size === botones(c).length);
  paso("el boton activo lleva check ademas del color y del borde", !!botones(c)[0].querySelector(".kpi-editor-tipo-check") && getComputedStyle(botones(c)[0]).borderColor !== getComputedStyle(botones(c)[1]).borderColor);
  paso("los botones en reposo son neutros (mismo fondo gris que los de tipo de grafica)", getComputedStyle(botones(c)[1]).backgroundColor === "rgb(244, 246, 249)", getComputedStyle(botones(c)[1]).backgroundColor);
  paso("el activo toma su color propio", getComputedStyle(botones(c)[0]).color === "rgb(235, 104, 52)", getComputedStyle(botones(c)[0]).color);

  // 2. Cambiar de modulo.
  await click(botones(c)[1]);
  paso("al elegir Inventario cambia el boton activo y la lista", activo(c).join() === "inventario" && nombres(c).join("|") === "Existencias|Lotes por caducar", activo(c).join() + " / " + nombres(c).join("|"));
  await click(botones(c).find((b) => b.dataset.modulo === "facturacion"));
  paso("Facturacion (solo sin desglose) es una pestana con su seccion «Combinables (sin desglose)»", activo(c).join() === "facturacion" && nombres(c).join("|") === "Ingresos totales" && !!c.querySelector('[data-seccion="combinables"]') && c.textContent.includes("Combinables (sin desglose)"), activo(c).join() + " / " + nombres(c).join("|"));
  paso("en la pestana de su modulo la tarjeta no lleva etiqueta de modulo", !c.querySelector(".kpi-selector-modulo-tag"));
  await click(botones(c).find((b) => b.dataset.modulo === "variables"));
  paso("Variables es un boton mas, muestra su ayuda y la tarjeta lleva la etiqueta de su modulo", nombres(c).length === 1 && nombres(c)[0].startsWith("Ingresos totales") && c.textContent.includes("sin desglose, de cualquier módulo") && c.querySelector(".kpi-selector-modulo-tag")?.textContent === "Facturación", nombres(c).join("|"));

  // 3. La seleccion se conserva al cambiar de modulo (varios KPIs de la misma unidad).
  c = await montar({ multiple: true });
  await click(opcion(c, "Incidencias abiertas"));
  await click(botones(c)[1]);
  await click(opcion(c, "Existencias"));
  const badge = (clave) => c.querySelector('[data-modulo="' + clave + '"] .kpi-selector-modulo-elegidos')?.textContent;
  paso("cada boton avisa cuantos KPIs elegidos tiene", badge("operaciones") === "1" && badge("inventario") === "1", badge("operaciones") + "/" + badge("inventario"));
  await click(botones(c)[0]);
  paso("al volver a Operaciones el KPI sigue elegido y con su numero", fila(c, "Incidencias abiertas").querySelector(".activo") && fila(c, "Incidencias abiertas").querySelector(".kpi-chip-badge").textContent === "1");
  await click(botones(c)[1]);
  paso("y el de Inventario conserva el orden 2", fila(c, "Existencias").querySelector(".kpi-chip-badge").textContent === "2");

  // 4. Regla de unidades: un porcentaje no se suma a una cantidad.
  await click(botones(c)[0]);
  const bloqueada = fila(c, "Incidentes resueltos");
  paso("un KPI de otra unidad sale deshabilitado con tooltip", bloqueada.querySelector("button").disabled && bloqueada.title.includes("No se puede combinar (unidad)"), bloqueada.title);
  paso("uno de la misma unidad sigue habilitado", !opcion(c, "Cancelaciones").disabled);

  // 5. Color por KPI y cierre al hacer clic fuera.
  const muestra = fila(c, "Incidencias abiertas").querySelector(".kpi-color-swatch");
  await click(muestra);
  paso("el circulo de color abre la paleta", !!c.querySelector(".kpi-color-popover"));
  document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  await esperar(60);
  paso("un clic fuera la cierra", !c.querySelector(".kpi-color-popover"));
  await click(muestra);
  await click(c.querySelector(".kpi-color-option"));
  paso("elegir un color la cierra y lo aplica al circulo", !c.querySelector(".kpi-color-popover") && getComputedStyle(fila(c, "Incidencias abiertas").querySelector(".kpi-color-swatch")).backgroundColor === "rgb(42, 120, 214)");

  // 6. Buscar recorre todos los modulos, agrupado; elegir un modulo borra la busqueda.
  c = await montar({ multiple: true, seleccionados: ["1"] });
  const buscador = c.querySelector("input[type=search]");
  await escribir(buscador, "existencias");
  paso("con texto se busca en TODOS los modulos y se agrupa por modulo", grupos(c).join() === "inventario" && nombres(c).join() === "Existencias", grupos(c).join());
  await escribir(buscador, "o");
  paso("una busqueda amplia muestra varios modulos, cada uno con su titulo", grupos(c).length >= 4 && c.querySelectorAll(".kpi-editor-grupo-titulo").length === grupos(c).length, grupos(c).join());
  paso("mientras hay texto ningun boton esta activo", activo(c).length === 0);
  await escribir(buscador, "existencias");
  paso("los modulos sin coincidencias se deshabilitan", botones(c).find((b) => b.dataset.modulo === "operaciones").disabled && !botones(c).find((b) => b.dataset.modulo === "inventario").disabled);
  paso("la seleccion se ve aun buscando (Operaciones marca 1 elegido)", c.querySelector('[data-modulo="operaciones"] .kpi-selector-modulo-elegidos')?.textContent === "1");
  await click(botones(c).find((b) => b.dataset.modulo === "inventario"));
  paso("elegir un modulo borra la busqueda y muestra ese modulo", buscador.value === "" && activo(c).join() === "inventario" && nombres(c).length === 2, buscador.value + "/" + activo(c).join());
  await escribir(buscador, "zzzz");
  paso("sin coincidencias avisa", c.textContent.includes("Ningún KPI coincide"));

  // 7. Modulo inicial = el del primer KPI ya elegido.
  c = await montar({ seleccionados: ["7"] });
  paso("con un KPI ya elegido abre en su modulo (Documentos)", activo(c).join() === "documentos" && nombres(c).join() === "Documentos vencidos", activo(c).join());

  // 8. Un solo modulo: sin fila de botones.
  const unSolo = CATALOGO.filter((k) => k.modulo === "operaciones");
  contador += 1;
  const solo = document.createElement("div");
  solo.style.cssText = "width:760px;margin:8px"; solo.className = "kpi-dashboard";
  document.body.appendChild(solo);
  window.montarSelector({ contenedor: solo, catalogo: unSolo });
  await esperar(60);
  paso("con un solo modulo no hay fila de botones", botones(solo).length === 0 && !solo.querySelector(".kpi-selector-modulos"));
  paso("pero se lista el modulo con su titulo", nombres(solo).length === 3 && solo.querySelectorAll(".kpi-editor-grupo-titulo").length === 1);

  // 9. Sin desbordes, en un ancho de telefono y en uno de escritorio.
  for (const ancho of [320, 760]) {
    const caja = await montar({ multiple: true, seleccionados: ["1", "4"] }, ancho);
    const raiz = caja.querySelector(".kpi-selector");
    paso("sin scroll horizontal a " + ancho + "px", raiz.scrollWidth <= raiz.clientWidth + 1 && caja.scrollWidth <= caja.clientWidth + 1, raiz.scrollWidth + ">" + raiz.clientWidth);
    const fuera = botones(caja).filter((b) => b.getBoundingClientRect().right > caja.getBoundingClientRect().right + 1);
    paso("ningun boton de modulo se sale a " + ancho + "px", fuera.length === 0, fuera.map((b) => b.dataset.modulo).join());
  }
  document.title = JSON.stringify({ resultados });
}
todo().catch((e) => { document.title = JSON.stringify({ resultados, error: String(e && e.stack || e) }); });
`;

test("el selector de KPI en Chrome: cambiar de modulo, buscar, conservar la seleccion, un solo modulo", { skip: CHROME ? false : "no hay Chrome/Chromium (define CHROME_BIN)" }, async () => {
  const dir = `${CACHE_DIR}navegador/`;
  mkdirSync(dir, { recursive: true });
  const salida = `${dir}selector.js`;
  await build({
    entryPoints: [fileURLToPath(new URL("./selectorNavegador.entry.jsx", import.meta.url))],
    outfile: salida,
    bundle: true,
    platform: "browser",
    format: "iife",
    jsx: "automatic",
    loader: { ".js": "jsx", ".css": "empty" },
    define: { "process.env.NODE_ENV": '"production"', "import.meta.env": "{}" },
    logLevel: "silent",
  });
  const pagina = `${dir}selector.html`;
  writeFileSync(pagina, `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}${ESTILOS}</style></head><body><script>${readFileSync(salida, "utf8").replace(/<\/script/gi, "<\\/script")}</script><script>${GUION.replace(/<\/script/gi, "<\\/script")}</script></body></html>`);
  const corrida = spawnSync(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1000,2600", "--virtual-time-budget=20000", "--dump-dom", pathToFileURL(pagina).href], { encoding: "utf8", timeout: 90000 });
  const titulo = /<title>(.*?)<\/title>/s.exec(corrida.stdout || "");
  assert.ok(titulo, `Chrome no devolvio resultados (codigo ${corrida.status}): ${(corrida.stderr || "").slice(0, 300)}`);
  const medicion = JSON.parse(titulo[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"));
  assert.equal(medicion.error, undefined, medicion.error);
  const fallas = medicion.resultados.filter((r) => !r.ok).map((r) => `${r.nombre} -- ${r.detalle}`);
  assert.deepEqual(fallas, []);
  assert.ok(medicion.resultados.length >= 28, `se ejecutaron ${medicion.resultados.length} comprobaciones`);
});
