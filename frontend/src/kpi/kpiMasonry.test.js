// El masonry simulado y la eleccion del hueco al arrastrar (kpiMasonry.js). Los numeros del tablero
// "Operacion Adser" son los medidos en Chrome real a 1920 px (4 columnas de 382 px, hueco de 16):
// una tabla de 2 columnas x 676 px y 4 tarjetas chicas.
import assert from "node:assert/strict";
import test from "node:test";
import {
  colocarMasonry, elegirOrden, esTarjetaGrande, mismoOrden, ordenConInsercion, rectangulo,
} from "./kpiMasonry.js";

const COLUMNAS = 4;
const GEOM = { anchoColumna: 382, hueco: 16 };
const filasDe = (alto) => Math.ceil((alto + 16) / 4);
const tarjeta = (cols, alto, grande = false) => ({ cols, filas: filasDe(alto), alto, grande });
const TARJETAS = new Map([
  ["T", tarjeta(2, 676, true)],
  ["a", tarjeta(1, 193)],
  ["b", tarjeta(1, 350)],
  ["c", tarjeta(1, 350)],
  ["d", tarjeta(1, 200)],
]);
const lista = (orden, tarjetas = TARJETAS) => orden.map((id) => ({ id, ...tarjetas.get(id) }));
const donde = (orden, columnas = COLUMNAS) => colocarMasonry(lista(orden), columnas);
const PROTEGIDAS = (orden) => new Map([["T", donde(orden).get("T")]]);

test("masonry simulado: reproduce lo que midio Chrome con la tabla primero", () => {
  const p = donde(["T", "a", "b", "c", "d"]);
  // x medidas: 0, 795, 1193 -> columnas 0, 2, 3; y medidas: 0, 0, 0, 212, 368 -> filas 0, 0, 0, 53, 92.
  assert.deepEqual(p.get("T"), { col: 0, fila: 0 });
  assert.deepEqual(p.get("a"), { col: 2, fila: 0 });
  assert.deepEqual(p.get("b"), { col: 3, fila: 0 });
  assert.deepEqual(p.get("c"), { col: 2, fila: 53 });
  assert.deepEqual(p.get("d"), { col: 3, fila: 92 });
});

test("masonry simulado: una chica antes de la tabla la manda al centro (la causa del brinco)", () => {
  // Con `a` antes, ocupa la columna 0 y la tabla, de 2 columnas, ya no cabe en 0-1: cae en 1-2.
  assert.deepEqual(donde(["a", "T", "b", "c", "d"]).get("T"), { col: 1, fila: 0 });
  // Con dos antes, en 2-3.
  assert.deepEqual(donde(["a", "b", "T", "c", "d"]).get("T"), { col: 2, fila: 0 });
});

test("masonry simulado: dense rellena los huecos y un ancho doble con una sola columna ocupa una", () => {
  // La tabla de 2 columnas no cabe junto a las dos primeras: queda debajo y `c` sube al hueco de la derecha.
  const p = colocarMasonry([
    { id: "a", cols: 1, filas: 50 }, { id: "b", cols: 1, filas: 50 }, { id: "c", cols: 1, filas: 50 },
    { id: "T", cols: 2, filas: 100 }, { id: "d", cols: 1, filas: 10 },
  ], 3);
  assert.deepEqual(p.get("T"), { col: 0, fila: 50 });
  assert.deepEqual(p.get("d"), { col: 2, fila: 50 });
  assert.deepEqual(colocarMasonry([{ id: "T", cols: 2, filas: 10 }, { id: "a", cols: 1, filas: 10 }], 1).get("a"), { col: 0, fila: 10 });
});

test("rectangulo: el lugar en px de una tarjeta ya colocada", () => {
  const p = donde(["T", "a", "b", "c", "d"]);
  assert.deepEqual(rectangulo(p.get("T"), TARJETAS.get("T"), GEOM, COLUMNAS), { x: 0, y: 0, w: 780, h: 676 });
  assert.deepEqual(rectangulo(p.get("c"), TARJETAS.get("c"), GEOM, COLUMNAS), { x: 796, y: 212, w: 382, h: 350 });
});

test("ordenConInsercion y mismoOrden", () => {
  assert.deepEqual(ordenConInsercion(["a", "b", "c", "d"], "d", 1), ["a", "d", "b", "c"]);
  assert.deepEqual(ordenConInsercion(["a", "b", "c", "d"], "a", 3), ["b", "c", "d", "a"]);
  assert.ok(mismoOrden(["a", "b"], ["a", "b"]));
  assert.ok(!mismoOrden(["a", "b"], ["b", "a"]));
  assert.ok(!mismoOrden(["a"], ["a", "b"]));
});

test("esTarjetaGrande: 2 columnas o 2 filas", () => {
  assert.ok(esTarjetaGrande({ tipo_grafica: "tabla", parametros: { columnas: 2, filas: 2 } }));
  assert.ok(esTarjetaGrande({ tipo_grafica: "tabla", parametros: { filas: 2 } }));
  assert.ok(!esTarjetaGrande({ tipo_grafica: "tabla", parametros: {} }));
  assert.ok(!esTarjetaGrande({ tipo_grafica: "barras", parametros: { columnas: 2 } }));
});

// Mueve el puntero a (x, y) las veces que haga falta hasta que el orden deje de cambiar. Devuelve el
// orden final y cuantas vueltas dio: si el algoritmo oscilara, nunca se estabilizaria.
function asentar(orden, activo, p, { protegidas, tarjetas = TARJETAS, columnas = COLUMNAS } = {}) {
  let actual = orden;
  for (let vuelta = 0; vuelta < 12; vuelta += 1) {
    const siguiente = elegirOrden({ orden: actual, activo, tarjetas, columnas, geom: GEOM, puntero: p, protegidas });
    if (siguiente === actual) return { orden: actual, vueltas: vuelta };
    actual = siguiente;
  }
  return { orden: actual, vueltas: Infinity };
}

test("arrastrar una chica NUNCA mueve la tabla, en ningun punto de la cuadricula", () => {
  const inicial = ["T", "a", "b", "c", "d"];
  const protegidas = PROTEGIDAS(inicial);
  for (const activo of ["a", "b", "c", "d"]) {
    for (let x = -50; x <= 1650; x += 50) {
      for (let y = -50; y <= 1000; y += 50) {
        const { orden, vueltas } = asentar(inicial, activo, { x, y }, { protegidas });
        assert.ok(vueltas <= 2, `${activo} en (${x},${y}): ${vueltas} vueltas`);
        assert.deepEqual(donde(orden).get("T"), { col: 0, fila: 0 }, `${activo} en (${x},${y}) -> ${orden}`);
      }
    }
  }
});

test("arrastrar una chica despacio por encima de la tabla no oscila ni cambia de lugar la tabla", () => {
  // El caso real: el puntero cruza la tabla de derecha a izquierda, en pasos de 10 px.
  const inicial = ["T", "a", "b", "c", "d"];
  const protegidas = PROTEGIDAS(inicial);
  let orden = inicial;
  const vistos = [];
  for (let x = 1100; x >= 50; x -= 10) {
    orden = elegirOrden({ orden, activo: "c", tarjetas: TARJETAS, columnas: COLUMNAS, geom: GEOM, puntero: { x, y: 200 }, protegidas });
    if (!vistos.length || vistos[vistos.length - 1] !== orden.join("")) vistos.push(orden.join(""));
    assert.deepEqual(donde(orden).get("T"), { col: 0, fila: 0 });
  }
  // Cada orden aparece una sola vez en el recorrido: nunca se vuelve a uno anterior.
  assert.equal(new Set(vistos).size, vistos.length, vistos.join(" > "));
  assert.ok(vistos.length <= 3, vistos.join(" > "));
});

test("arrastrar la tabla: el hueco donde cae es el que contiene al puntero y no cambia mientras siga dentro", () => {
  const inicial = ["T", "a", "b", "c", "d"];
  for (let x = 0; x <= 1500; x += 25) {
    for (let y = 0; y <= 900; y += 25) {
      const { orden, vueltas } = asentar(inicial, "T", { x, y });
      assert.ok(vueltas <= 2, `T en (${x},${y}): ${vueltas} vueltas`);
      const r = rectangulo(donde(orden).get("T"), TARJETAS.get("T"), GEOM, COLUMNAS);
      const dentro = x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
      // Si alguna posicion de la lista deja el hueco bajo el puntero, el elegido lo deja.
      const alguna = inicial.some((_, i) => {
        const o = ordenConInsercion(inicial, "T", i);
        const q = rectangulo(donde(o).get("T"), TARJETAS.get("T"), GEOM, COLUMNAS);
        return x >= q.x && x <= q.x + q.w && y >= q.y && y <= q.y + q.h;
      });
      if (alguna) assert.ok(dentro, `T en (${x},${y}) -> ${orden}`);
    }
  }
});

test("arrastrar la tabla despacio no brinca: cada orden aparece una sola vez en el recorrido", () => {
  let orden = ["T", "a", "b", "c", "d"];
  const vistos = [];
  for (let x = 100; x <= 1450; x += 10) {
    orden = elegirOrden({ orden, activo: "T", tarjetas: TARJETAS, columnas: COLUMNAS, geom: GEOM, puntero: { x, y: 300 } });
    if (!vistos.length || vistos[vistos.length - 1] !== orden.join("")) vistos.push(orden.join(""));
  }
  assert.equal(new Set(vistos).size, vistos.length, vistos.join(" > "));
});

test("con una sola columna el arrastre es vertical y una tabla ancha ocupa una", () => {
  const tarjetas = new Map([["T", tarjeta(2, 300, true)], ["a", tarjeta(1, 200)], ["b", tarjeta(1, 200)]]);
  const inicial = ["T", "a", "b"];
  const protegidas = new Map([["T", colocarMasonry(lista(inicial, tarjetas), 1).get("T")]]);
  // `b` arriba del todo (y = 0) dejaria la tabla mas abajo: no vale; queda debajo de la tabla.
  const { orden } = asentar(inicial, "b", { x: 100, y: 5 }, { protegidas, tarjetas, columnas: 1 });
  assert.deepEqual(orden.indexOf("T"), 0);
  // Arrastrando la tabla, si.
  const arrastrada = asentar(inicial, "T", { x: 100, y: 450 }, { tarjetas, columnas: 1 }).orden;
  assert.notDeepEqual(arrastrada, inicial);
});
