import assert from "node:assert/strict";
import test from "node:test";
import {
  disenoDeBarras, recortarEtiqueta, MAX_CATEGORIAS_HORIZONTAL, MAX_CATEGORIAS_VERTICAL, RECORTE_HORIZONTAL, RECORTE_VERTICAL,
} from "./kpiEtiquetasEje.js";

const nombres = (cuantos, largo = 6) => Array.from({ length: cuantos }, (_, i) => `${"N".repeat(largo)}${i}`);

test("recortarEtiqueta deja intacto lo que cabe y recorta con puntos suspensivos contando el tope", () => {
  assert.equal(recortarEtiqueta("Ana", 18), "Ana");
  assert.equal(recortarEtiqueta("a".repeat(18), 18), "a".repeat(18));
  const recortada = recortarEtiqueta("a".repeat(19), 18);
  assert.equal(recortada, `${"a".repeat(17)}…`);
  assert.equal(Array.from(recortada).length, 18);
});

test("recortarEtiqueta tolera vacios, numeros y caracteres compuestos", () => {
  assert.equal(recortarEtiqueta(null, 18), "");
  assert.equal(recortarEtiqueta(undefined, 18), "");
  assert.equal(recortarEtiqueta(12345, 3), "12…");
  assert.equal(recortarEtiqueta("  Jose  ", 18), "Jose");
  assert.equal(recortarEtiqueta("😀".repeat(20), 18), `${"😀".repeat(17)}…`);
  // sin espacio ni particula colgando antes de los puntos
  assert.equal(recortarEtiqueta("Maria del Carmen Lopez", 11), "Maria…");
  assert.equal(recortarEtiqueta("Maria Elena Carmen Lopez", 13), "Maria Elena…");
});

test("recortarEtiqueta conserva la inicial de desempate y no deja una particula colgando", () => {
  // sin esto las dos «Luis Fernando Torres» quedarian iguales: «Luis Fernando Torr…»
  const vega = recortarEtiqueta("Luis Fernando Torres V.", 18);
  const rios = recortarEtiqueta("Luis Fernando Torres R.", 18);
  assert.equal(vega, "Luis Fernando… V.");
  assert.equal(rios, "Luis Fernando… R.");
  assert.notEqual(vega, rios);
  assert.ok(Array.from(vega).length <= 18);
  assert.equal(recortarEtiqueta("Luis Fernando Torres V.", 28), "Luis Fernando Torres V.");
  assert.equal(recortarEtiqueta("Miguel Hidalgo y Costilla", 18), "Miguel Hidalgo…");
  assert.equal(recortarEtiqueta("Ana Pérez de la Torre Soto", 14), "Ana Pérez…");
  // un punto final que no es inicial de desempate no se trata como tal
  assert.equal(recortarEtiqueta("Compañia Ejemplo Sociedad Ltda.", 18), "Compañia Ejemplo…");
});

test("hasta 12 categorias con una serie: vertical, todas visibles, sin recorte", () => {
  const diseno = disenoDeBarras({ etiquetas: nombres(12) });
  assert.equal(diseno.modo, "vertical");
  assert.equal(diseno.mostradas, 12);
  assert.equal(diseno.recortado, false);
  assert.equal(diseno.todasLasEtiquetas, true);
  assert.equal(diseno.inclinar, true);
});

test("13 categorias con una serie pasan a horizontal; el tope son 20 filas", () => {
  const trece = disenoDeBarras({ etiquetas: nombres(13) });
  assert.equal(trece.modo, "horizontal");
  assert.equal(trece.mostradas, 13);
  assert.equal(trece.recortado, false);
  const muchas = disenoDeBarras({ etiquetas: nombres(35) });
  assert.equal(muchas.modo, "horizontal");
  assert.equal(muchas.mostradas, MAX_CATEGORIAS_HORIZONTAL);
  assert.equal(muchas.total, 35);
  assert.equal(muchas.recortado, true);
  assert.equal(muchas.maxCaracteres, RECORTE_HORIZONTAL);
  // ~500 px con las 20 filas: cabe en una pagina
  assert.ok(muchas.alto >= 480 && muchas.alto <= 540, `alto ${muchas.alto}`);
});

test("con mas de una serie nunca hay horizontal: vertical y tope de 12", () => {
  for (const series of [2, 3, 6]) {
    const diseno = disenoDeBarras({ etiquetas: nombres(30), cantidadSeries: series });
    assert.equal(diseno.modo, "vertical", `series=${series}`);
    assert.equal(diseno.mostradas, MAX_CATEGORIAS_VERTICAL);
    assert.equal(diseno.recortado, true);
    assert.equal(diseno.maxCaracteres, RECORTE_VERTICAL);
  }
  const sinRecorte = disenoDeBarras({ etiquetas: nombres(5), cantidadSeries: 2 });
  assert.equal(sinRecorte.recortado, false);
});

test("por periodo es un eje de tiempo: ni horizontal ni recorte, y Recharts decide que fechas rotular", () => {
  const diseno = disenoDeBarras({ etiquetas: nombres(40), porPeriodo: true });
  assert.equal(diseno.modo, "vertical");
  assert.equal(diseno.mostradas, 40);
  assert.equal(diseno.recortado, false);
  assert.equal(diseno.todasLasEtiquetas, false);
});

test("el eje y el alto crecen con la etiqueta mas larga, y la leyenda de series suma altura", () => {
  const cortas = disenoDeBarras({ etiquetas: nombres(6, 3) });
  const largas = disenoDeBarras({ etiquetas: nombres(6, 40) });
  assert.ok(largas.altoEjeX > cortas.altoEjeX);
  // el recorte a 18 caracteres acota el eje: 40 o 400 caracteres miden lo mismo
  assert.equal(disenoDeBarras({ etiquetas: nombres(6, 400) }).altoEjeX, largas.altoEjeX);
  const dosSeries = disenoDeBarras({ etiquetas: nombres(6, 3), cantidadSeries: 2 });
  assert.ok(dosSeries.alto > cortas.alto);
  const sieteSeries = disenoDeBarras({ etiquetas: nombres(6, 3), cantidadSeries: 7 });
  assert.ok(sieteSeries.alto > dosSeries.alto);
});

test("las etiquetas solo se inclinan cuando no caben rectas en su banda (se mide el ancho)", () => {
  const cortas = nombres(6, 3); // 4 caracteres: 31 px
  assert.equal(disenoDeBarras({ etiquetas: cortas, anchoGrafica: 340 }).inclinar, false);
  // la misma lista en una grafica muy angosta ya no cabe recta
  assert.equal(disenoDeBarras({ etiquetas: cortas, anchoGrafica: 140 }).inclinar, true);
  // nombres cortos de persona (14 caracteres) en 5 categorias: caben en 700 px, no en 340
  const personas = ["Carlos Mendoza", "Luis Fernando Torres", "Miguel Hidalgo y Costilla", "Ana Perez", "Maria Jose Ramirez"];
  assert.equal(disenoDeBarras({ etiquetas: personas, anchoGrafica: 340 }).inclinar, true);
  assert.equal(disenoDeBarras({ etiquetas: personas, anchoGrafica: 900 }).inclinar, false);
  // una sola categoria nunca se inclina
  assert.equal(disenoDeBarras({ etiquetas: ["Un nombre bastante largo"], anchoGrafica: 100 }).inclinar, false);
  // recto: el eje vuelve a su alto plano y el margen no crece
  const recto = disenoDeBarras({ etiquetas: cortas, anchoGrafica: 900 });
  assert.equal(recto.altoEjeX, 28);
  assert.equal(recto.margenIzquierdo, -16);
});

test("con pocas categorias el texto va recto y la grafica conserva su alto de siempre (220)", () => {
  const diseno = disenoDeBarras({ etiquetas: nombres(3) });
  assert.equal(diseno.inclinar, false);
  assert.equal(diseno.alto, 220);
  assert.equal(diseno.margenIzquierdo, -16);
});

test("la etiqueta inclinada ensancha el margen izquierdo solo lo que el eje de valores no cubre", () => {
  const larga = disenoDeBarras({ etiquetas: nombres(8, 40), anchoEje: 60 });
  assert.ok(larga.margenIzquierdo > -16);
  const ejeAncho = disenoDeBarras({ etiquetas: nombres(8, 40), anchoEje: 200 });
  assert.equal(ejeAncho.margenIzquierdo, -16);
});

test("sin categorias no revienta", () => {
  const diseno = disenoDeBarras({ etiquetas: [] });
  assert.equal(diseno.modo, "vertical");
  assert.equal(diseno.mostradas, 0);
  assert.equal(diseno.recortado, false);
});

test("horizontal: el ancho del eje de nombres se acota", () => {
  const diseno = disenoDeBarras({ etiquetas: nombres(15, 80) });
  assert.equal(diseno.modo, "horizontal");
  assert.ok(diseno.anchoEjeCategorias <= 190);
});
