import test from "node:test";
import assert from "node:assert/strict";
import { descripcionSospechosa, UNIDADES } from "./descripcionDeNecesidad.js";

const REALES = [
  "soldadura 6013", "tornillo 1/4 x 2", "Pintura esmalte blanca", "cable THW calibre 12",
  "electrodo E7018", "cemento gris", "lija 120", "varilla 3/8", "malla electrosoldada 6x6",
  "construcción", "tuerca M8x1.25", "brocha 4 pulgadas", "thinner", "disco de corte 4 1/2",
  "guantes de carnaza", "clavo 2 1/2", "cinta teflón", "pegamento PVC", "manguera 1/2 pulgada",
  "extensión eléctrica 15 m", "grasa multiusos", "WD-40", "tubo cuadrado 2x2",
  "perfil estructural IPR", "anclas expansivas 3/8", "cable THHN calibre 10",
];
const ABSURDOS = [
  "12o3pifsfjg", "asdfgh", "qwerty", "aaaaa", "xxxxx", "jjjjjjj", "123456",
  "....", "bcdfghjk", "pifsfjg", "ab", "  ",
];

test("no rechaza ningun pedido real", () => {
  assert.deepEqual(REALES.filter((t) => descripcionSospechosa(t)), []);
});

test("atrapa lo evidente", () => {
  assert.deepEqual(ABSURDOS.filter((t) => !descripcionSospechosa(t)), []);
});

test("dice por que", () => {
  assert.equal(descripcionSospechosa("ab"), "too_short");
  assert.equal(descripcionSospechosa("6013"), "no_letters");
  assert.equal(descripcionSospechosa("aaaaa"), "repeated");
  assert.equal(descripcionSospechosa("pifsfjg"), "few_vowels");
});

test("la lista de unidades no repite ni deja una vacia", () => {
  assert.equal(new Set(UNIDADES).size, UNIDADES.length);
  assert.ok(UNIDADES.every((u) => u.trim() !== ""));
});
