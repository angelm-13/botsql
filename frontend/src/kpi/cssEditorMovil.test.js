// Las pastillas del paso "Periodo" en movil: cuatro por fila sin partir "Personalizado". Se midio en Chrome a 390 y 360 px (una sola linea,
// sin desborde); aqui solo se cuida que la regla no se pierda.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles/kpi-editor.css", import.meta.url), "utf8");
const movil = css.slice(css.indexOf(".kpi-editor-chips-periodo"));

test("movil: rejilla de 4 columnas con la ultima al ancho de su palabra y sin partir palabras", () => {
  assert.match(movil, /\.kpi-editor-chips-periodo \{[^}]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\) minmax\(max-content, 1\.2fr\)/);
  const chip = /\.kpi-editor-chips-periodo \.kpi-editor-chip \{([^}]*)\}/.exec(movil)?.[1] || "";
  assert.match(chip, /min-height: 44px/);
  assert.match(chip, /overflow-wrap: normal/);
  assert.doesNotMatch(chip, /overflow-wrap: anywhere|word-break: break-all/);
});
