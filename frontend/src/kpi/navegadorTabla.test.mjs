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
  const envoltura = contenedor.querySelector("[data-tarjeta]");
  const tarjeta = envoltura.querySelector(".kpi-widget-card");
  const caja = tarjeta.getBoundingClientRect();
  const filas = [...tarjeta.querySelectorAll("tbody tr")];
  paso(nombre + ": se pintaron los 15 renglones", filas.length === 15, filas.length);
  // 1. Ninguna parte de la tarjeta se sale de ella por los lados.
  const fuera = [...tarjeta.querySelectorAll("*")].filter((el) => !dentro(el, caja) && getComputedStyle(el).display !== "none");
  paso(nombre + ": nada se sale de la tarjeta", fuera.length === 0, fuera.slice(0, 3).map((el) => el.tagName + "." + (el.className || "").toString().slice(0, 30) + " " + Math.round(el.getBoundingClientRect().right - caja.right) + "px").join(", "));
  paso(nombre + ": la tarjeta no tiene scroll horizontal", tarjeta.scrollWidth <= tarjeta.clientWidth + 1, tarjeta.scrollWidth + ">" + tarjeta.clientWidth);
  // 2. Ningun renglon queda bajo un recuadro vecino.
  const tapados = filas.filter((fila) => { const r = fila.getBoundingClientRect(); if (!r.width) return false; const punto = document.elementFromPoint(Math.min(r.left + r.width / 2, window.innerWidth - 1), r.top + Math.min(r.height / 2, 8)); return punto && !tarjeta.contains(punto); });
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

async function todo() {
  // 420: una columna. 760: dos columnas de ~372 (tarjeta angosta). 1120: dos de ~552.
  await escenario("420px (1 columna)", 420);
  await escenario("760px (2 columnas angostas)", 760);
  await escenario("1120px (2 columnas anchas)", 1120);
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
  const corrida = spawnSync(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1300,3000", "--virtual-time-budget=30000", "--dump-dom", pathToFileURL(pagina).href], { encoding: "utf8", timeout: 120000, maxBuffer: 64 * 1024 * 1024 });
  const titulo = /<title>(.*?)<\/title>/s.exec(corrida.stdout || "");
  assert.ok(titulo, `Chrome no devolvio resultados (codigo ${corrida.status}): ${(corrida.stderr || "").slice(0, 300)}`);
  const medicion = JSON.parse(titulo[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"));
  assert.equal(medicion.error, undefined, medicion.error);
  const fallas = medicion.resultados.filter((r) => !r.ok).map((r) => `${r.nombre} -- ${r.detalle}`);
  assert.deepEqual(fallas, []);
  assert.ok(medicion.resultados.length >= 15, `se ejecutaron ${medicion.resultados.length} comprobaciones`);
});
