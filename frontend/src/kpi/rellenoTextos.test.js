// Los textos del selector de relleno (Solido | Con texturas) del asistente: existen en es, en, pt y de, sin llaves repetidas.
import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

const IDIOMAS = ["es", "en", "pt", "de"];
const LLAVES = ["fill", "fill_solid", "fill_texture", "fill_help"];
const locale = (idioma) => readFileSync(new URL(`../i18n/locales/${idioma}.json`, import.meta.url), "utf8");

test("los textos del relleno existen en es, en, pt y de, dentro de kpi_dashboard, y no estan vacios", () => {
  for (const idioma of IDIOMAS) {
    const textos = JSON.parse(locale(idioma)).kpi_dashboard;
    for (const llave of LLAVES) {
      assert.equal(typeof textos[llave], "string", `${idioma}.kpi_dashboard.${llave}`);
      assert.ok(textos[llave].trim().length > 0, `${idioma}.kpi_dashboard.${llave} esta vacio`);
    }
  }
});

test("el espanol dice lo que el selector muestra por omision, y el ingles no es una copia", () => {
  const es = JSON.parse(locale("es")).kpi_dashboard;
  assert.deepEqual([es.fill, es.fill_solid, es.fill_texture], ["Relleno", "Sólido", "Con texturas"]);
  const en = JSON.parse(locale("en")).kpi_dashboard;
  for (const llave of LLAVES) assert.notEqual(en[llave], es[llave], llave);
});

test("agregar los textos no duplico ninguna llave del archivo", () => {
  for (const idioma of IDIOMAS) {
    const lineas = locale(idioma).split("\n").filter((linea) => /^\s*"fill(_solid|_texture|_help)?":/.test(linea));
    assert.equal(lineas.length, LLAVES.length, `${idioma}: las llaves de relleno salen ${lineas.length} veces`);
  }
});
