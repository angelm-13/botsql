import test from "node:test";
import assert from "node:assert/strict";
import { contieneColorModerno } from "./colorParaPdf.js";

test("detecta las funciones de color que html2canvas no sabe leer", () => {
  for (const valor of [
    "color(srgb 0.9 0.5 0.1 / 0.14)",
    "color-mix(in srgb, red 14%, white)",
    "oklch(0.7 0.1 200)",
    "lab(50% 40 59)",
    "0px 0px 0px 4px color(srgb 0.16 0.47 0.84 / 0.35)",
  ]) assert.equal(contieneColorModerno(valor), true, valor);
});

test("deja pasar los formatos que html2canvas si entiende", () => {
  for (const valor of ["#173b66", "rgb(23, 59, 102)", "rgba(23, 59, 102, 0.4)", "hsl(210 60% 25%)", "transparent", "none"])
    assert.equal(contieneColorModerno(valor), false, valor);
});
