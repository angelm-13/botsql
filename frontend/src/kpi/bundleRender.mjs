// Empaqueta renderTarjetas.entry.jsx con esbuild (el que ya trae Vite: sin
// dependencias nuevas) y devuelve sus funciones de render en servidor. Lo
// comparten las pruebas de render y de layout.
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const ENTRADA = fileURLToPath(new URL("./renderTarjetas.entry.jsx", import.meta.url));
// Dentro de node_modules para que los paquetes externos se resuelvan igual.
export const CACHE_DIR = fileURLToPath(new URL("../../node_modules/.cache/kpi-render-test/", import.meta.url));

export async function cargarRender() {
  // El modulo se ejecuta en Node: lo unico del navegador que se toca al importar
  // es localStorage/window, y solo dentro de funciones que estas pruebas no llaman.
  globalThis.localStorage ??= { getItem: () => null, setItem() {}, removeItem() {} };
  mkdirSync(CACHE_DIR, { recursive: true });
  const salida = `${CACHE_DIR}entrada.mjs`;
  await build({
    entryPoints: [ENTRADA],
    outfile: salida,
    bundle: true,
    platform: "node",
    format: "esm",
    jsx: "automatic",
    packages: "external",
    loader: { ".js": "jsx", ".css": "empty" },
    define: { "import.meta.env": JSON.stringify({ VITE_API_BASE_URL: "/api", MODE: "test", DEV: false, BASE_URL: "/" }) },
    logLevel: "silent",
  });
  return import(`${salida}?${Date.now()}`);
}
