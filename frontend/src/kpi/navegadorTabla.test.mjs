// La tarjeta REAL de "Material prestado ahora" en un Chrome de verdad, con la respuesta
// REAL del backend (fixtures/material_prestado_actual.real.json), la misma cuadricula del
// Dashboard y recuadros "Agregar grafico" vecinos, a tres anchos.
//
// Existe por un error visto en el navegador: articulo, responsable y fecha salian
// VACIOS en modo tarjeta y los renglones se salian de la tarjeta, quedando bajo el
// recuadro vecino. Los datos llegaban bien; la causa era CSS (una regla global
// `table { min-width: 900px }`), asi que ninguna prueba en servidor ni con jsdom -sin
// layout- podia verlo.
//
// Sin dependencias nuevas: esbuild de Vite + el Chrome que haya (o CHROME_BIN); sin
// ninguno, se SALTA.
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

const ruta = (relativa) => fileURLToPath(new URL(relativa, import.meta.url));
const ESTILOS = ["app.css", "kpi-widgets.css", "kpi-editor.css", "kpi-dashboard.css"]
  .map((archivo) => readFileSync(ruta(`../styles/${archivo}`), "utf8").replace(/@import url\([^)]*\);?/g, ""))
  .join("\n");
const RESPUESTA_REAL = readFileSync(ruta("./fixtures/material_prestado_actual.real.json"), "utf8");

// app.css se carga a proposito: la regla global `table { min-width: 900px }` esta ahi.
const GUION = `
const RESPUESTA = ${RESPUESTA_REAL};
window.fetch = async () => new Response(JSON.stringify(RESPUESTA), { status: 200, headers: { "content-type": "application/json" } });
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
const resultados = [];
const paso = (nombre, ok, detalle = "") => resultados.push({ nombre, ok: Boolean(ok), detalle: String(detalle) });
const dentro = (el, caja) => { const r = el.getBoundingClientRect(); return r.width === 0 || (r.left >= caja.left - 1 && r.right <= caja.right + 1); };

async function escenario(nombre, anchoCuadricula, config = {}) {
  const contenedor = document.createElement("div");
  contenedor.className = "kpi-dashboard";
  contenedor.style.cssText = "width:" + anchoCuadricula + "px;margin:8px 0;font-family:'IBM Plex Sans',system-ui,sans-serif";
  document.body.appendChild(contenedor);
  window.montarTabla({ contenedor, ...config });
  await esperar(700);
  window.remedirMasonry();
  await esperar(50);
  const envoltura = contenedor.querySelector("[data-tarjeta]");
  const tarjeta = envoltura.querySelector(".kpi-widget-card");
  const caja = tarjeta.getBoundingClientRect();
  const filas = [...tarjeta.querySelectorAll("tbody tr")];
  paso(nombre + ": se pintaron los 10 primeros renglones (el resto, tras 'Ver todos')", filas.length === 10, filas.length);
  // 1. Ninguna parte de la tarjeta se sale de ella por los lados.
  const fuera = [...tarjeta.querySelectorAll("*")].filter((el) => !dentro(el, caja) && getComputedStyle(el).display !== "none");
  paso(nombre + ": nada se sale de la tarjeta", fuera.length === 0, fuera.slice(0, 3).map((el) => el.tagName + "." + (el.className || "").toString().slice(0, 30) + " " + Math.round(el.getBoundingClientRect().right - caja.right) + "px").join(", "));
  paso(nombre + ": la tarjeta no tiene scroll horizontal", tarjeta.scrollWidth <= tarjeta.clientWidth + 1, tarjeta.scrollWidth + ">" + tarjeta.clientWidth);
  // 2. Ningun renglon queda bajo un recuadro vecino.
  const areaLista = (tarjeta.querySelector(".kpi-prestamos-lista") || tarjeta).getBoundingClientRect();
  // Un renglon que la lista recorta (queda por scroll) no esta "tapado": esta fuera de la vista de su propia lista.
  const tapados = filas.filter((fila) => { const r = fila.getBoundingClientRect(); if (!r.width || r.bottom > areaLista.bottom || r.top < areaLista.top) return false; const punto = document.elementFromPoint(Math.min(r.left + r.width / 2, window.innerWidth - 1), r.top + Math.min(r.height / 2, 8)); return punto && !tarjeta.contains(punto); });
  paso(nombre + ": ningun renglon queda tapado por otro recuadro", tapados.length === 0, tapados.length + " tapados");
  const vecinos = [...contenedor.querySelectorAll("[data-vecino]")].filter((v) => { const r = v.getBoundingClientRect(); return r.left < caja.right - 1 && r.right > caja.left + 1 && r.top < caja.bottom - 1 && r.bottom > caja.top + 1; });
  paso(nombre + ": los vecinos no se enciman con la tarjeta", vecinos.length === 0, vecinos.length);
  // 3. Articulo, responsable, fecha y dias tienen texto VISIBLE (con ancho) dentro de la tarjeta.
  const primera = filas[0];
  // El elemento MAS PROFUNDO cuyo texto contiene lo buscado (un valor puede venir partido
  // en varios nodos de texto: "512" + "días").
  const visibles = ["Empleado demo", "sample_descripcion", "2025-", "512 días"].map((texto) => {
    const candidatos = [...primera.querySelectorAll("*")].filter((el) => el.textContent.replace(/\\s+/g, " ").includes(texto) && ![...el.children].some((hijo) => hijo.textContent.replace(/\\s+/g, " ").includes(texto)));
    const caja1 = candidatos[0]?.getBoundingClientRect();
    return { texto, ok: !!caja1 && caja1.width > 4 && caja1.height > 4 && caja1.left >= caja.left && caja1.right <= caja.right + 1, rect: caja1 ? [Math.round(caja1.left), Math.round(caja1.right), Math.round(caja1.width), Math.round(caja1.height)].join("/") + " tarjeta " + Math.round(caja.left) + "-" + Math.round(caja.right) + " <" + candidatos[0].tagName + ">" : "sin elemento" };
  });
  paso(nombre + ": articulo, responsable, fecha y dias se ven en el primer renglon", visibles.every((v) => v.ok), visibles.filter((v) => !v.ok).map((v) => v.texto + " " + v.rect).join("; "));
  return { contenedor, tarjeta, filas };
}

const click = async (el) => { el.click(); await esperar(120); };
const seleccionar = async (select, valor) => { select.value = valor; select.dispatchEvent(new Event("change", { bubbles: true })); await esperar(120); };
const escribir = async (input, valor) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, valor); input.dispatchEvent(new Event("input", { bubbles: true })); await esperar(120); };
const filasDe = (tarjeta) => [...tarjeta.querySelectorAll("tbody tr")];
const textoPlano = (el) => el.textContent.replace(/\\s+/g, " ").trim();
const boton = (tarjeta, re) => [...tarjeta.querySelectorAll("button")].find((b) => re.test(b.textContent));

async function diseno(nombre, ancho, esTabla) {
  const { tarjeta } = await escenario(nombre, ancho);
  const filas = filasDe(tarjeta);
  const resumen = textoPlano(tarjeta.querySelector(".kpi-prestamos-resumen"));
  paso(nombre + ": el resumen dice renglones, responsables y el mas antiguo", /^15 renglones\\s*2 responsables\\s*el más antiguo: 512 días · 1 año, 5 meses/.test(resumen), resumen);
  paso(nombre + ": la tarjeta dice 'En vivo · actualizado ahora' (sin doble guion)", textoPlano(tarjeta).includes("En vivo · actualizado ahora") && !textoPlano(tarjeta).includes("--"));
  // Solo 10 renglones hasta pedir "Ver todos".
  const visiblesAntes = filas.filter((f) => f.getBoundingClientRect().height > 0).length;
  paso(nombre + ": solo se ven 10 renglones al principio", visiblesAntes === 10, visiblesAntes);
  const verTodos = boton(tarjeta, /Ver todos \\(15\\)/);
  paso(nombre + ": hay un 'Ver todos (15)'", !!verTodos);
  // Gravedad: 512 y 456 son coral, 45 ambar, 12 verde, con icono y texto; 512 y 456 NO se distinguen por color pero si por texto.
  const chips = (f) => f.querySelector(".kpi-prestamos-chip");
  // Chrome devuelve color-mix() como color(srgb r g b / a) con canales de 0 a 1.
  const esCoral = (valor) => { const n = (valor.match(/[\\d.]+/g) || []).slice(-4, -1).map(Number); return n.length === 3 && Math.abs(n[0] * 255 - 239) < 3 && Math.abs(n[1] * 255 - 111) < 3 && Math.abs(n[2] * 255 - 92) < 3; };
  const niveles = filas.map((f) => [...f.classList].find((c) => c.startsWith("nivel-")));
  paso(nombre + ": 512, 456 y 100 dias son criticos; 83 dias es ambar", niveles.slice(0, 4).join() === "nivel-critico,nivel-critico,nivel-critico,nivel-atencion", niveles.slice(0, 4).join());
  const color = (f) => getComputedStyle(chips(f)).borderColor;
  paso(nombre + ": el chip critico es coral, no oscuro ni cafe", color(filas[0]) !== color(filas[3]) && esCoral(color(filas[0])), color(filas[0]));
  paso(nombre + ": cada chip lleva icono y texto (la duracion), no solo color", !!chips(filas[0]).querySelector("svg") && textoPlano(chips(filas[0])).includes("512 días · 1 año, 5 meses") && textoPlano(chips(filas[1])).includes("456 días · 1 año, 3 meses"));
  if (esTabla) {
    const th = tarjeta.querySelector("th");
    paso(nombre + ": tabla ancha con encabezado de columnas y encabezado fijo", getComputedStyle(th).display !== "none" && getComputedStyle(th).position === "sticky");
    paso(nombre + ": el selector de orden del modo compacto no se ve", getComputedStyle(tarjeta.querySelector(".kpi-preview-orden-movil")).display === "none");
  } else {
    paso(nombre + ": modo compacto: sin encabezado ni etiquetas repetidas", getComputedStyle(tarjeta.querySelector("thead")).display === "none" && getComputedStyle(filas[0].querySelector(".kpi-prestamos-articulo"), "::before").content === "none");
    const art = filas[0].querySelector(".kpi-prestamos-articulo").getBoundingClientRect();
    const resp = filas[0].querySelector(".kpi-prestamos-responsable").getBoundingClientRect();
    const fecha = filas[0].querySelector(".kpi-prestamos-fecha").getBoundingClientRect();
    const dias = filas[0].querySelector(".kpi-prestamos-dias").getBoundingClientRect();
    paso(nombre + ": articulo arriba, luego responsable y fecha en una linea, y abajo los dias", art.bottom <= resp.top + 1 && Math.abs(resp.top - fecha.top) < 4 && resp.bottom <= dias.top + 1, [art.top, resp.top, fecha.top, dias.top].map(Math.round).join("/"));
    const chipCaja = filas[0].querySelector(".kpi-prestamos-chip").getBoundingClientRect();
    const barraCaja = filas[0].querySelector(".kpi-prestamos-barra").getBoundingClientRect();
    paso(nombre + ": el chip y la barra van en la MISMA linea y la barra es delgada", Math.abs((chipCaja.top + chipCaja.height / 2) - (barraCaja.top + barraCaja.height / 2)) < 4 && barraCaja.height <= 8 && barraCaja.width > 30, "barra " + Math.round(barraCaja.width) + "x" + Math.round(barraCaja.height) + " chip@" + Math.round(chipCaja.top) + " barra@" + Math.round(barraCaja.top));
    const marca = getComputedStyle(filas[0].querySelector(".kpi-prestamos-articulo")).boxShadow;
    paso(nombre + ": el articulo no lleva la marca lateral de la tabla ancha (esa es solo de la tabla)", marca === "none", marca);
    paso(nombre + ": el articulo va en negritas", +getComputedStyle(filas[0].querySelector(".kpi-prestamos-articulo")).fontWeight >= 700);
    const antesFecha = getComputedStyle(filas[0].querySelector(".kpi-prestamos-fecha"), "::before").content;
    paso(nombre + ": la fecha dice 'vale del'", /vale del/.test(antesFecha), antesFecha);
    paso(nombre + ": el orden se elige con un selector propio", getComputedStyle(tarjeta.querySelector(".kpi-preview-orden-movil")).display !== "none");
  }
  // Ver todos: abre una ventana con los 15 renglones, sin agrandar la tarjeta.
  const alto0 = tarjeta.getBoundingClientRect().height;
  verTodos.focus();
  await click(verTodos);
  const dlg = document.querySelector('[role="dialog"]');
  paso(nombre + ": 'Ver todos' abre una ventana", !!dlg && dlg.getAttribute("aria-modal") === "true");
  const todas = filasDe(dlg);
  paso(nombre + ": la ventana muestra los 15", todas.length === 15, todas.length);
  const verde = todas.find((f) => f.classList.contains("nivel-ok"));
  paso(nombre + ": hay renglones verdes (hasta 30 dias) con otro icono que el coral", !!verde && chips(verde).querySelector("svg").innerHTML !== chips(todas[0]).querySelector("svg").innerHTML);
  paso(nombre + ": la tarjeta no crece al abrir la ventana", Math.abs(tarjeta.getBoundingClientRect().height - alto0) < 2, Math.round(alto0) + " -> " + Math.round(tarjeta.getBoundingClientRect().height));
  const cajaDlg = dlg.getBoundingClientRect();
  paso(nombre + ": la ventana cabe en la pantalla", cajaDlg.left >= -1 && cajaDlg.right <= innerWidth + 1 && cajaDlg.bottom <= innerHeight + 1, Math.round(cajaDlg.left) + "-" + Math.round(cajaDlg.right));
  paso(nombre + ": la ventana tiene busqueda, filtro por responsable y orden", !!dlg.querySelector('input[type="search"]') && !!dlg.querySelector(".kpi-prestamos-control select") && !!dlg.querySelector(".kpi-prestamos-tabla th, .kpi-preview-orden-movil"));
  paso(nombre + ": el foco entra a la ventana", dlg.contains(document.activeElement), document.activeElement && document.activeElement.tagName);
  const buscador = dlg.querySelector('input[type="search"]');
  await escribir(buscador, "2025-05");
  paso(nombre + ": buscar por fecha deja solo ese renglon", filasDe(dlg).length === 1, filasDe(dlg).length);
  await escribir(buscador, "zzz");
  paso(nombre + ": una busqueda sin resultados lo dice", /Ningún renglón coincide/.test(textoPlano(dlg)));
  await escribir(buscador, "");
  const lista = dlg.querySelector(".kpi-prestamos-lista");
  paso(nombre + ": en la ventana la lista se desplaza por dentro, sin salirse", getComputedStyle(lista).overflowY === "auto" && lista.getBoundingClientRect().bottom <= cajaDlg.bottom + 1);
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await esperar(200);
  paso(nombre + ": Escape cierra la ventana y devuelve el foco al boton", !document.querySelector('[role="dialog"]') && document.activeElement === verTodos);
  paso(nombre + ": la tarjeta sigue con sus 10 renglones", filasDe(tarjeta).length === 10, filasDe(tarjeta).length);
  paso(nombre + ": nada se sale de la tarjeta", [...tarjeta.querySelectorAll("*")].every((el) => dentro(el, tarjeta.getBoundingClientRect())));
  // Filtro por responsable.
  const filtro = tarjeta.querySelector(".kpi-prestamos-control select");
  const opciones = [...filtro.options].map((o) => o.value).filter(Boolean);
  paso(nombre + ": el filtro lista los responsables", opciones.length === 2 && filtro.options[0].textContent.includes("(15)"), opciones.join("|"));
  await seleccionar(filtro, opciones[0]);
  const solo = filasDe(tarjeta).filter((f) => f.getBoundingClientRect().height > 0);
  paso(nombre + ": filtrar deja solo los renglones de ese responsable, con el orden por dias", solo.length > 0 && solo.every((f) => f.querySelector(".kpi-prestamos-responsable").textContent === opciones[0]) && solo.map((f) => +f.querySelector(".kpi-prestamos-chip-texto").textContent.split(" ")[0]).every((d, i, arr) => i === 0 || arr[i - 1] >= d));
  paso(nombre + ": el resumen se ajusta al filtro (1 responsable)", /1 responsable/.test(textoPlano(tarjeta.querySelector(".kpi-prestamos-resumen"))));
  await seleccionar(filtro, "");
  // Vista agrupada por responsable.
  await click(boton(tarjeta, /Por responsable/));
  const grupos = [...tarjeta.querySelectorAll(".kpi-prestamos-grupo")];
  paso(nombre + ": la vista agrupada tiene un grupo por responsable, el del prestamo mas viejo primero", grupos.length === 2 && textoPlano(grupos[0].querySelector("header")).includes("512 días"), grupos.map((g) => g.querySelector("header strong").textContent).join("|"));
  paso(nombre + ": el boton de la vista activa esta marcado", boton(tarjeta, /Por responsable/).getAttribute("aria-pressed") === "true" && boton(tarjeta, /Lista/).getAttribute("aria-pressed") === "false");
  paso(nombre + ": agrupada tambien limita a 10 renglones", filasDe(tarjeta).filter((f) => f.getBoundingClientRect().height > 0).length === 10);
  paso(nombre + ": agrupada, nada se sale de la tarjeta", [...tarjeta.querySelectorAll("*")].every((el) => dentro(el, tarjeta.getBoundingClientRect())));
  await click(boton(tarjeta, /Lista/));
  // Orden.
  if (esTabla) {
    await click(tarjeta.querySelector("th button"));
    paso(nombre + ": pulsar el encabezado ordena por esa columna", filasDe(tarjeta)[0].querySelector(".kpi-prestamos-articulo").textContent === "sample_descripcion");
  }
}

async function estadoVacio() {
  const original = window.fetch;
  window.fetch = async () => new Response(JSON.stringify({ items: [], limit: 50, offset: 0, total: 0 }), { status: 200, headers: { "content-type": "application/json" } });
  const contenedor = document.createElement("div");
  contenedor.className = "kpi-dashboard"; contenedor.style.cssText = "width:420px;margin:8px 0";
  document.body.appendChild(contenedor);
  window.montarTabla({ contenedor });
  await esperar(700);
  const vacio = contenedor.querySelector(".kpi-prestamos-vacio");
  paso("estado vacio: dice claro que todo esta en el almacen, con icono", !!vacio && !!vacio.querySelector("svg") && /Todo el material está en el almacén/.test(vacio.textContent) && /No hay artículos prestados/.test(vacio.textContent), vacio && vacio.textContent);
  paso("estado vacio: sin tabla, sin controles y sin 'Ver todos'", !contenedor.querySelector("table") && !contenedor.querySelector(".kpi-prestamos-controles") && !/Ver todos/.test(contenedor.textContent));
  paso("estado vacio: cabe en la tarjeta", dentro(vacio, contenedor.querySelector(".kpi-widget-card").getBoundingClientRect()));
  window.fetch = original;
}

function movimientoReducido() {
  const reducido = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const relleno = document.querySelector(".kpi-prestamos-barra-relleno");
  const duracion = getComputedStyle(relleno).transitionDuration;
  paso("movimiento reducido: " + (reducido ? "las barras no se animan" : "las barras se animan"), reducido ? parseFloat(duracion) === 0 : parseFloat(duracion) > 0, "reducido=" + reducido + " duracion=" + duracion);
}

// Ancho doble (columnas = 2): ocupa dos pistas de la cuadricula, y donde solo cabe una
// vuelve a ocupar una (un span 2 crearia una columna implicita fuera de la pantalla).
async function anchoDoble(nombre, ancho, pistasEsperadas) {
  const { contenedor, tarjeta } = await escenario(nombre, ancho, { columnas: 2, vecinos: 4 });
  const grid = contenedor.querySelector(".kpi-widget-grid");
  const pistas = getComputedStyle(grid).gridTemplateColumns.trim().split(/\\s+/).length;
  const envoltura = contenedor.querySelector("[data-tarjeta]");
  const caja = envoltura.getBoundingClientRect();
  const cajaGrid = grid.getBoundingClientRect();
  const unaPista = (cajaGrid.width - 16 * (pistas - 1)) / pistas;
  const ocupa = pistasEsperadas === 1 ? 1 : 2;
  paso(nombre + ": la cuadricula tiene " + pistasEsperadas + " columna(s)", pistas === pistasEsperadas, pistas);
  paso(nombre + ": la tabla ocupa " + ocupa + " columna(s)", Math.abs(caja.width - (unaPista * ocupa + 16 * (ocupa - 1))) < 2, Math.round(caja.width) + "px de " + Math.round(unaPista) + "px por columna");
  paso(nombre + ": no crea columnas implicitas (sin scroll horizontal de la cuadricula)", grid.scrollWidth <= grid.clientWidth + 1, grid.scrollWidth + ">" + grid.clientWidth);
  paso(nombre + ": el modo depende del ancho real de la tarjeta", (getComputedStyle(tarjeta.querySelector("thead")).display !== "none") === (caja.width > 560), Math.round(caja.width));
}

async function todo() {
  // La cuadricula es repeat(auto-fill, minmax(340px, 1fr)):
  //   420 -> 1 columna de 420 (tarjeta angosta: renglones compactos)
  //   680 -> 1 columna de 680 (tarjeta ancha: tabla de cuatro columnas)
  //   760 -> 2 columnas de ~372 (tarjeta angosta)
  await diseno("420px (1 columna)", 420, false);
  await diseno("680px (1 columna ancha)", 680, true);
  await diseno("760px (2 columnas angostas)", 760, false);
  // Ancho doble: 500 -> 1 pista (vuelve a una), 900 -> 2 pistas, 1200 -> 3 pistas (la tabla ocupa 2).
  await anchoDoble("doble a 500px", 500, 1);
  await anchoDoble("doble a 900px", 900, 2);
  await anchoDoble("doble a 1200px", 1200, 3);
  await estadoVacio();
  movimientoReducido();
  document.title = JSON.stringify({ resultados });
}
todo().catch((e) => { document.title = JSON.stringify({ resultados, error: String(e && e.stack || e) }); });
`;

async function construir(nombrePagina) {
  const dir = `${CACHE_DIR}navegador/`;
  mkdirSync(dir, { recursive: true });
  const salida = `${dir}tabla.js`;
  await build({
    entryPoints: [ruta("./tablaNavegador.entry.jsx")],
    outfile: salida,
    bundle: true,
    platform: "browser",
    format: "iife",
    jsx: "automatic",
    loader: { ".js": "jsx", ".css": "empty" },
    define: { "process.env.NODE_ENV": '"production"', "import.meta.env": '{"VITE_API_BASE_URL":"/api"}' },
    logLevel: "silent",
  });
  const pagina = `${dir}${nombrePagina}.html`;
  const escapar = (codigo) => codigo.replace(/<\/script/gi, "<\\/script");
  writeFileSync(pagina, `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}${ESTILOS}</style></head><body><script>${escapar(readFileSync(salida, "utf8"))}</script><script>${escapar(GUION)}</script></body></html>`);
  return pagina;
}

test("la tabla de material prestado en Chrome, con la respuesta REAL del backend, a tres anchos", { skip: CHROME ? false : "no hay Chrome/Chromium (define CHROME_BIN)" }, async () => {
  const pagina = await construir("tabla");
  for (const [modo, banderas] of [["normal", []], ["con movimiento reducido", ["--force-prefers-reduced-motion"]]]) {
    const corrida = spawnSync(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", ...banderas, "--window-size=1500,4000", "--virtual-time-budget=60000", "--dump-dom", pathToFileURL(pagina).href], { encoding: "utf8", timeout: 180000, maxBuffer: 64 * 1024 * 1024 });
    const titulo = /<title>(.*?)<\/title>/s.exec(corrida.stdout || "");
    assert.ok(titulo, `Chrome (${modo}) no devolvio resultados (codigo ${corrida.status}): ${(corrida.stderr || "").slice(0, 300)}`);
    const medicion = JSON.parse(titulo[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"));
    assert.equal(medicion.error, undefined, medicion.error);
    const fallas = medicion.resultados.filter((r) => !r.ok).map((r) => `${r.nombre} -- ${r.detalle}`);
    assert.deepEqual(fallas, [], `Chrome ${modo}`);
    assert.ok(medicion.resultados.length >= 60, `se ejecutaron ${medicion.resultados.length} comprobaciones`);
  }
});
