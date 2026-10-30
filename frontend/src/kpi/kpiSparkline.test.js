import test from "node:test";
import assert from "node:assert/strict";
import { TRAZO_SPARKLINE, puntosDeSparkline } from "./kpiSparkline.js";

const ANCHO = 96;
const ALTO = 28;
const MARGEN = TRAZO_SPARKLINE / 2 + 1;

test("ningun punto toca el borde: la mitad del trazo cabe dentro del svg", () => {
  const puntos = puntosDeSparkline([1, 9, 3, 7, 2], ANCHO, ALTO);
  for (const { x, y } of puntos) {
    assert.ok(x >= MARGEN && x <= ANCHO - MARGEN, `x ${x}`);
    assert.ok(y >= MARGEN && y <= ALTO - MARGEN, `y ${y}`);
  }
});

test("el primero y el ultimo punto quedan justo en el margen (no se pierde ancho)", () => {
  const puntos = puntosDeSparkline([1, 2, 3], ANCHO, ALTO);
  assert.equal(puntos[0].x, MARGEN);
  assert.equal(puntos[puntos.length - 1].x, ANCHO - MARGEN);
});

test("el valor mas alto va arriba y el mas bajo abajo", () => {
  const [bajo, alto] = puntosDeSparkline([1, 9], ANCHO, ALTO);
  assert.equal(alto.y, MARGEN);
  assert.equal(bajo.y, ALTO - MARGEN);
});

test("una serie plana va a media altura y menos de dos valores no dibujan nada", () => {
  assert.deepEqual(puntosDeSparkline([5, 5, 5], ANCHO, ALTO).map((p) => p.y), [ALTO / 2, ALTO / 2, ALTO / 2]);
  assert.deepEqual(puntosDeSparkline([5], ANCHO, ALTO), []);
  assert.deepEqual(puntosDeSparkline(null, ANCHO, ALTO), []);
});
