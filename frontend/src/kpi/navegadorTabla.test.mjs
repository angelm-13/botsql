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
// La tabla pide sus renglones al servidor por paginas, ya filtrados, buscados y ordenados (ver
// kpiPrestamosServidor.js). Aqui el `fetch` SIMULA ese endpoint (GET .../vivo) sobre las filas de la
// respuesta real: filtro por id_user, busqueda, orden, paginas, resumen y conteo por responsable. La semantica
// REAL de esas consultas la prueban las pruebas de Postgres del backend
// (test_kpi_material_prestado_actual_servidor.py); esto prueba el cableado y el aspecto en un Chrome de verdad.
//
// OPT-IN: esta prueba NO corre por omision. Hay que pedirla con `KPI_CHROME_TESTS=1` (y tener Chrome/Chromium o
// CHROME_BIN); sin la variable se SALTA con un mensaje y `node --test src/kpi/` / `npm test` ya no la ejecutan.
//
//   KPI_CHROME_TESTS=1 node --test --test-concurrency=1 src/kpi/navegadorTabla.test.mjs
//
// Por que: es INTERMITENTE. Medido el 2026-10-16 en un Chromium 149 headless dentro de un contenedor: falla entre
// el 10 % y el 40 % de las corridas (una comparacion intercalada de 25 rondas dio 6 y 10 fallas segun la version del
// codigo, y otra tanda 8 de 20 contra 2 de 20: la tasa cambia con la carga de la maquina), siempre en las mismas dos
// comprobaciones del escenario de "mas de 50 renglones": «al abrir 'Ver todos' solo se carga la primera pagina»
// (llegan 100 renglones en vez de 50) y «'Mostrar mas' trae otra pagina del servidor» (100 -> 113). Fallaba igual
// antes de los cambios de ese dia, asi que no es una regresion de ellos.
//
// Lo que NO es: la sospecha anterior (procesos de Chromium que se acumulan y cuelgan las corridas siguientes) no se
// confirmo -- despues de cada corrida no quedaba ningun Chromium vivo, y la falla es una asercion de la propia prueba
// con Chrome devolviendo datos. La CAUSA DE FONDO no se ha investigado: puede ser de la prueba, del tiempo virtual
// (`--virtual-time-budget`) o de la propia tabla. Hasta saberlo, el escenario se verifica tambien A MANO en el navegador.
//
// Antes este comentario decia "no correrla en automatico", pero `node --test src/kpi/` la corria sola en cualquier
// maquina con Chrome; por eso ahora lo impide la propia prueba.
//
// Sin dependencias nuevas: esbuild de Vite + el Chrome que haya (o CHROME_BIN). Correr los archivos de Chrome EN
// SERIE (`node --test --test-concurrency=1`): dos Chrome a la vez pelean por el mismo perfil.
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
// Las filas que "tiene" el servidor; una prueba puede cambiarlas (window.__FILAS).
const sinAcentos = (s) => String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
function servir(url) {
  const q = new URL(url, location.href).searchParams;
  const todas = window.__FILAS || RESPUESTA.items;
  const ambito = q.get("id_user_ambito");
  const idUser = q.get("id_user");
  const palabras = sinAcentos(q.get("q")).split(/\\s+/).filter(Boolean);
  const enAmbito = todas.filter((f) => !ambito || String(f.id_user) === ambito);
  const filtradas = enAmbito.filter((f) => (!idUser || String(f.id_user) === idUser)
    && palabras.every((p) => sinAcentos(f.articulo + " " + (f.responsable || "") + " " + f.fecha_prestamo + " " + f.dias_prestado).includes(p)));
  const orden = q.get("orden") || "dias_prestado";
  const asc = q.get("direccion") === "asc";
  const texto = (f, campo) => sinAcentos(f[campo]);
  const porDias = (a, b) => b.dias_prestado - a.dias_prestado || a.id_nm_incident_product - b.id_nm_incident_product;
  let ordenadas;
  if (q.get("agrupar")) {
    const masViejo = (id) => Math.max(...filtradas.filter((f) => f.id_user === id).map((f) => f.dias_prestado));
    ordenadas = [...filtradas].sort((a, b) => masViejo(b.id_user) - masViejo(a.id_user) || a.id_user - b.id_user || porDias(a, b));
  } else if (orden === "dias_prestado") {
    ordenadas = [...filtradas].sort((a, b) => (asc ? -1 : 1) * (b.dias_prestado - a.dias_prestado) || a.id_nm_incident_product - b.id_nm_incident_product);
  } else if (orden === "fecha_prestamo") {
    ordenadas = [...filtradas].sort((a, b) => (asc ? 1 : -1) * a.fecha_prestamo.localeCompare(b.fecha_prestamo) || porDias(a, b));
  } else {
    ordenadas = [...filtradas].sort((a, b) => (asc ? 1 : -1) * texto(a, orden).localeCompare(texto(b, orden)) || porDias(a, b));
  }
  const limit = Number(q.get("limit") || 25);
  const offset = Number(q.get("offset") || 0);
  const masAntiguo = [...filtradas].sort(porDias)[0];
  const reales = new Map();
  for (const f of enAmbito) {
    const r = reales.get(f.id_user) || { id_user: f.id_user, responsable: f.responsable, renglones: 0, mas_antiguo_dias: 0 };
    r.renglones += 1; r.mas_antiguo_dias = Math.max(r.mas_antiguo_dias, f.dias_prestado); reales.set(f.id_user, r);
  }
  return {
    items: ordenadas.slice(offset, offset + limit), total: filtradas.length, limit, offset,
    resumen: {
      renglones: filtradas.length, responsables: new Set(filtradas.map((f) => f.id_user)).size,
      mas_antiguo: masAntiguo ? { dias: masAntiguo.dias_prestado, articulo: masAntiguo.articulo, responsable: masAntiguo.responsable } : null,
    },
    responsables: [...reales.values()].sort((a, b) => String(a.responsable).localeCompare(String(b.responsable))),
  };
}
window.__PETICIONES = [];
window.fetch = async (url) => { window.__PETICIONES.push(String(url)); return new Response(JSON.stringify(servir(url)), { status: 200, headers: { "content-type": "application/json" } }); };
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
const resultados = [];
const paso = (nombre, ok, detalle = "") => resultados.push({ nombre, ok: Boolean(ok), detalle: String(detalle) });
const dentro = (el, caja) => { const r = el.getBoundingClientRect(); return r.width === 0 || (r.left >= caja.left - 1 && r.right <= caja.right + 1); };

async function escenario(nombre, anchoCuadricula, config = {}) {
  const textosDelFixture = !window.__FILAS;
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
  if (textosDelFixture) {
    const visibles = ["Empleado demo", "sample_descripcion", "2025-", "512 días"].map((texto) => {
      const candidatos = [...primera.querySelectorAll("*")].filter((el) => el.textContent.replace(/\\s+/g, " ").includes(texto) && ![...el.children].some((hijo) => hijo.textContent.replace(/\\s+/g, " ").includes(texto)));
      const caja1 = candidatos[0]?.getBoundingClientRect();
      return { texto, ok: !!caja1 && caja1.width > 4 && caja1.height > 4 && caja1.left >= caja.left && caja1.right <= caja.right + 1, rect: caja1 ? [Math.round(caja1.left), Math.round(caja1.right), Math.round(caja1.width), Math.round(caja1.height)].join("/") + " tarjeta " + Math.round(caja.left) + "-" + Math.round(caja.right) + " <" + candidatos[0].tagName + ">" : "sin elemento" };
    });
    paso(nombre + ": articulo, responsable, fecha y dias se ven en el primer renglon", visibles.every((v) => v.ok), visibles.filter((v) => !v.ok).map((v) => v.texto + " " + v.rect).join("; "));
  }
  return { contenedor, tarjeta, filas };
}

// 500 ms: la busqueda espera 300 ms antes de pedir al servidor, y luego llega la respuesta.
const ASENTAR = 500;
const click = async (el) => { el.click(); await esperar(ASENTAR); };
const seleccionar = async (select, valor) => { select.value = valor; select.dispatchEvent(new Event("change", { bubbles: true })); await esperar(ASENTAR); };
const escribir = async (input, valor) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, valor); input.dispatchEvent(new Event("input", { bubbles: true })); await esperar(ASENTAR); };
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
  // El valor de cada opcion es el id_user (no el nombre): la etiqueta dice "Nombre (n)".
  const nombreFiltrado = filtro.options[1].textContent.replace(/ \\(\\d+\\)$/, "");
  await seleccionar(filtro, opciones[0]);
  const solo = filasDe(tarjeta).filter((f) => f.getBoundingClientRect().height > 0);
  paso(nombre + ": filtrar deja solo los renglones de ese responsable, con el orden por dias", solo.length > 0 && solo.every((f) => f.querySelector(".kpi-prestamos-responsable").textContent === nombreFiltrado) && solo.map((f) => +f.querySelector(".kpi-prestamos-chip-texto").textContent.split(" ")[0]).every((d, i, arr) => i === 0 || arr[i - 1] >= d));
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


// El caso real de Adser: mas de 50 renglones y lo nuevo (el vale de agosto de Omar) cae MAS ALLA de la fila 50.
// Antes la tabla pedia las 50 mas antiguas y filtraba/buscaba en el navegador sobre ellas: filtrar por Omar o
// buscar "ESCALERA" no encontraba el vale nuevo, y el conteo por responsable mentia.
function filasDelCasoOmar() {
  const filas = [];
  const agregar = (id_user, responsable, articulo, fecha, dias) => {
    filas.push({ id_nm_incident_product: filas.length + 1, id_user, responsable, articulo, fecha_prestamo: fecha, dias_prestado: dias });
  };
  for (let i = 0; i < 60; i += 1) agregar(1, "OMAR GONZALEZ", "TALADRO DEMO", "2025-10-09", 357);
  for (const art of ["ESCALERA DE TIJERA", "MALETIN DE HERRAMIENTAS", "TANQUE DE CO2"]) agregar(1, "OMAR GONZALEZ", art, "2026-08-11", 51);
  for (let i = 0; i < 40; i += 1) agregar(2, "ANA LOPEZ", "TALADRO DEMO", "2026-01-15", 259);
  for (let i = 0; i < 5; i += 1) { agregar(3, "ESTANCIA EN EL TALLER", "TALADRO DEMO", "2026-03-01", 214); agregar(4, "ESTANCIA EN EL TALLER", "TALADRO DEMO", "2026-03-02", 213); }
  return filas;
}

async function muchosRenglones() {
  const nombre = "mas de 50 renglones";
  window.__FILAS = filasDelCasoOmar();
  const { tarjeta } = await escenario(nombre, 680);
  const resumen = () => textoPlano(tarjeta.querySelector(".kpi-prestamos-resumen"));
  paso(nombre + ": la tarjeta cuenta TODOS los renglones (113), no los que alcanzo a cargar", /^113 renglones/.test(resumen()), resumen());
  const filtro = tarjeta.querySelector(".kpi-prestamos-control select");
  const etiquetas = [...filtro.options].map((o) => o.textContent);
  paso(nombre + ": el desplegable trae el conteo REAL de Omar (63)", etiquetas.some((e) => e === "OMAR GONZALEZ (63)"), etiquetas.join(" | "));
  paso(nombre + ": dos responsables con el mismo nombre son dos opciones, cada una con sus 5", etiquetas.filter((e) => e === "ESTANCIA EN EL TALLER (5)").length === 2);
  const omar = [...filtro.options].find((o) => o.textContent === "OMAR GONZALEZ (63)").value;
  await seleccionar(filtro, omar);
  paso(nombre + ": filtrar por Omar: 63 renglones y 1 responsable", /^63 renglones\\s*1 responsable/.test(resumen()), resumen());
  const verTodos = boton(tarjeta, /Ver todos \\(63\\)/);
  paso(nombre + ": 'Ver todos (63)'", !!verTodos, resumen() + " | " + [...tarjeta.querySelectorAll("button")].map((b) => b.textContent.trim()).join(" / "));
  if (!verTodos) { window.__FILAS = null; return; }
  await click(verTodos);
  const dlg = document.querySelector('[role="dialog"]');
  await esperar(800);
  paso(nombre + ": al abrir 'Ver todos' solo se carga la primera pagina (no todo de golpe)", filasDe(dlg).length === 50, filasDe(dlg).length);
  const lista = dlg.querySelector(".kpi-prestamos-lista");
  const peticionesAntes = window.__PETICIONES.length;
  await esperar(600);
  paso(nombre + ": sin tocar nada no se piden mas paginas", window.__PETICIONES.length === peticionesAntes, window.__PETICIONES.length - peticionesAntes);
  const selectDlg = dlg.querySelector(".kpi-prestamos-control select");
  await seleccionar(selectDlg, omar);
  // 50 (la primera pagina) o 63 si el observador de scroll ya pidio la siguiente: segun el modo de Chrome puede o no
  // dispararse solo. Lo estricto -que abrir la ventana NO carga todo de golpe- se comprueba arriba.
  paso(nombre + ": Omar en la ventana: la primera pagina (50) o ya el resto (63)", [50, 63].includes(filasDe(dlg).length), filasDe(dlg).length);
  // El scroll infinito usa IntersectionObserver, que este Chrome sin cabeza y con tiempo virtual no dispara:
  // se verifico aparte en un Chrome normal (Dashboard real, 63 de 63 al llegar al final). Aqui el resto se pide
  // por el boton de respaldo, que carga lo mismo desde el servidor.
  lista.scrollTop = lista.scrollHeight;
  await esperar(300);
  for (let i = 0; i < 4 && filasDe(dlg).length < 63; i += 1) {
    const mas63 = [...dlg.querySelectorAll("button")].find((b) => /Mostrar más/.test(b.textContent));
    if (!mas63) break;
    await click(mas63);
  }
  const cuerpo = textoPlano(dlg.querySelector(".kpi-prestamos-lista"));
  paso(nombre + ": el resto se pide al servidor: los 63 de Omar", filasDe(dlg).length === 63, filasDe(dlg).length);
  paso(nombre + ": estan los viejos (2025-10-09) Y el vale nuevo (2026-08-11)", cuerpo.includes("2025-10-09") && cuerpo.includes("2026-08-11"));
  paso(nombre + ": estan ESCALERA, MALETIN y TANQUE", ["ESCALERA DE TIJERA", "MALETIN DE HERRAMIENTAS", "TANQUE DE CO2"].every((a) => cuerpo.includes(a)));
  await seleccionar(selectDlg, "");
  const buscador = dlg.querySelector('input[type="search"]');
  await escribir(buscador, "ESCALERA");
  paso(nombre + ": buscar ESCALERA (mas alla de la fila 50) la encuentra", filasDe(dlg).length === 1 && textoPlano(filasDe(dlg)[0]).includes("OMAR GONZALEZ"), filasDe(dlg).length);
  const resumenDlg = textoPlano(dlg.querySelector(".kpi-prestamos-resumen"));
  paso(nombre + ": el resumen de la busqueda: 1 renglon, 1 responsable", /^1 renglón\\s*1 responsable/.test(resumenDlg), resumenDlg);
  paso(nombre + ": los conteos del desplegable no cambian al buscar", [...selectDlg.options].some((o) => o.textContent === "OMAR GONZALEZ (63)"));
  await escribir(buscador, "");
  const mas = [...dlg.querySelectorAll("button")].find((b) => /Mostrar más/.test(b.textContent));
  paso(nombre + ": sin filtros hay un boton 'Mostrar más' de respaldo", !!mas, filasDe(dlg).length + " filas");
  if (!mas) { window.__FILAS = null; return; }
  const antes = filasDe(dlg).length;
  await click(mas);
  paso(nombre + ": 'Mostrar más' trae otra pagina del servidor", filasDe(dlg).length === antes + 50, antes + " -> " + filasDe(dlg).length);
  paso(nombre + ": el pie dice 'Mostrando N de 113'", /Mostrando \\d+ de 113/.test(textoPlano(dlg)));
  const taller = [...selectDlg.options].filter((o) => o.textContent === "ESTANCIA EN EL TALLER (5)");
  await seleccionar(selectDlg, taller[0].value);
  const fechas = new Set(filasDe(dlg).map((f) => textoPlano(f).match(/2026-03-0\\d/)?.[0]));
  paso(nombre + ": un responsable con nombre repetido trae solo SUS renglones", filasDe(dlg).length === 5 && fechas.size === 1, [...fechas].join());
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await esperar(200);
  window.__FILAS = null;
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
  await muchosRenglones();
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

// Opt-in: ver el comentario de arriba. `1`, `true` o `si`, como las demas variables de entorno del proyecto.
const PEDIDA = ["1", "true", "si"].includes(String(process.env.KPI_CHROME_TESTS || "").trim().toLowerCase());
const MOTIVO_DE_SALTO = !CHROME
  ? "no hay Chrome/Chromium (define CHROME_BIN)"
  : !PEDIDA
    ? "opt-in: es intermitente (ver el comentario del archivo); define KPI_CHROME_TESTS=1 para correrla"
    : false;

test("la tabla de material prestado en Chrome, con la respuesta REAL del backend, a tres anchos", { skip: MOTIVO_DE_SALTO }, async () => {
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
