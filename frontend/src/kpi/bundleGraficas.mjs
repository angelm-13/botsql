// Empaqueta graficasAnchoFijo.entry.jsx con esbuild, cambiando el ResponsiveContainer de Recharts por uno de tamano fijo
// (el real mide 0 sin navegador). Mismo enfoque que bundleRender.mjs: sin dependencias nuevas.
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const ENTRADA = fileURLToPath(new URL("./graficasAnchoFijo.entry.jsx", import.meta.url));
const SHIM = fileURLToPath(new URL("./graficasAnchoFijo.shim.jsx", import.meta.url));
const CACHE_DIR = fileURLToPath(new URL("../../node_modules/.cache/kpi-render-test/", import.meta.url));

const recharts = {
  name: "recharts-ancho-fijo",
  setup(construccion) {
    construccion.onResolve({ filter: /^recharts$/ }, (args) => (
      args.importer === SHIM ? { path: "recharts", external: true } : { path: SHIM }
    ));
  },
};

export async function cargarGraficas() {
  globalThis.localStorage ??= { getItem: () => null, setItem() {}, removeItem() {} };
  mkdirSync(CACHE_DIR, { recursive: true });
  const salida = `${CACHE_DIR}graficas.mjs`;
  await build({
    entryPoints: [ENTRADA],
    outfile: salida,
    bundle: true,
    platform: "node",
    format: "esm",
    jsx: "automatic",
    packages: "external",
    plugins: [recharts],
    loader: { ".js": "jsx", ".css": "empty" },
    define: { "import.meta.env": JSON.stringify({ MODE: "test" }) },
    logLevel: "silent",
  });
  return import(`${salida}?${Date.now()}`);
}
