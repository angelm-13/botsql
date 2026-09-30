import assert from "node:assert/strict";
import test from "node:test";
import { casillasDeRelleno, filasParaLlenar, RELLENO_CASILLAS_MINIMAS } from "./kpiRelleno.js";

test("tablero vacio: filas completas de recuadros, segun lo que alcance a verse", () => {
  assert.equal(casillasDeRelleno({ cantidad: 0, columnas: 4, filasVisibles: 3 }), 12);
  assert.equal(casillasDeRelleno({ cantidad: 0, columnas: 2, filasVisibles: 3 }), 6);
  assert.equal(casillasDeRelleno({ cantidad: 0, columnas: 1, filasVisibles: 3 }), 3);
  // Acotado: nunca una sola fila, nunca mas de cuatro.
  assert.equal(casillasDeRelleno({ cantidad: 0, columnas: 4, filasVisibles: 1 }), 8);
  assert.equal(casillasDeRelleno({ cantidad: 0, columnas: 4, filasVisibles: 9 }), 16);
});

test("con tarjetas: completa la ultima fila y no baja del minimo de casillas", () => {
  // 4 columnas: 1 tarjeta -> 8 casillas (7 recuadros); 5 -> 8 (3); 6 -> 8 (2); 8 -> 8 (0); 9 -> 12 (3).
  for (const [cantidad, esperado] of [[1, 7], [5, 3], [6, 2], [8, 0], [9, 3]]) {
    assert.equal(casillasDeRelleno({ cantidad, columnas: 4 }), esperado, `${cantidad} tarjetas`);
  }
  // 3 columnas: el total siempre es multiplo de 3 y de al menos 6.
  for (let n = 1; n <= 14; n += 1) {
    const total = n + casillasDeRelleno({ cantidad: n, columnas: 3 });
    assert.equal(total % 3, 0);
    assert.ok(total >= RELLENO_CASILLAS_MINIMAS);
    assert.ok(total - n < 3 || n < RELLENO_CASILLAS_MINIMAS, `${n}: sobran recuadros`);
  }
});

test("una tarjeta de ancho doble pesa 2 mientras haya al menos dos columnas", () => {
  assert.equal(casillasDeRelleno({ cantidad: 5, dobles: 1, columnas: 4 }), 2); // peso 6 -> 8
  assert.equal(casillasDeRelleno({ cantidad: 1, dobles: 1, columnas: 4 }), 6); // peso 2 -> 8
  // Con una columna, ocupa una.
  assert.equal(casillasDeRelleno({ cantidad: 5, dobles: 1, columnas: 1 }), 1); // peso 5 -> 6
});

test("sin medir todavia las columnas, completa hasta el minimo", () => {
  assert.equal(casillasDeRelleno({ cantidad: 2, columnas: null }), RELLENO_CASILLAS_MINIMAS - 2);
  assert.equal(casillasDeRelleno({ cantidad: 9, columnas: null }), 0);
});

test("filasParaLlenar: cuantas filas de 240 px caben, entre 2 y 4", () => {
  assert.equal(filasParaLlenar(100), 2);
  assert.equal(filasParaLlenar(520), 3); // (520 + 16) / 256 = 2.09 -> 3
  assert.equal(filasParaLlenar(2000), 4);
  assert.equal(filasParaLlenar(NaN), 2);
});
