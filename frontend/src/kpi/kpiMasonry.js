// Logica pura del masonry del tablero y de la eleccion del hueco al arrastrar (sin React ni DOM;
// ver kpi.test.js). Lo usa components/kpi-widgets/useReordenarTarjetas.js.
//
// El CSS (`.kpi-widget-grid`, kpi-dashboard.css) acomoda las tarjetas con `grid-auto-flow: row dense`:
// cada una, EN EL ORDEN DEL DOM, cae en el primer hueco donde cabe (la fila mas alta y, en ella, la
// columna mas a la izquierda). `colocarMasonry` repite ese algoritmo, asi que el arrastre puede saber
// DONDE caeria la tarjeta con cada orden posible sin tener que pintarlo: el hueco que se ensena es
// el lugar real, no una aproximacion.

import { columnasDeWidget, filasDeWidget } from "./kpiParametros.js";

/** Alto de una fila de la cuadricula (`--kpi-fila`) y hueco entre tarjetas (`--kpi-hueco`). */
export const FILA_PX = 4;

/** Una tarjeta "grande" ocupa mas de 1x1: 2 columnas o 2 filas (hoy solo las tablas). Su lugar en el
 * tablero esta protegido: arrastrar una tarjeta chica nunca la mueve (ver `elegirOrden`). */
export function esTarjetaGrande(widget) {
  return columnasDeWidget(widget) === 2 || filasDeWidget(widget) === 2;
}

function cabe(ocupado, col, cols, fila, filas) {
  for (let c = col; c < col + cols; c += 1) {
    for (const [ini, fin] of ocupado[c]) {
      if (ini < fila + filas && fin > fila) return false;
    }
  }
  return true;
}

/** Donde pone el navegador cada tarjeta. `tarjetas`: `[{ id, cols, filas }]` en orden de DOM;
 * `cols` se recorta al numero de columnas (con una sola, un ancho doble vuelve a ocupar una).
 * Devuelve `Map(id -> { col, fila })` con col y fila desde 0.
 *
 * Solo hay que probar la fila 0 y las filas donde termina alguna tarjeta: si una tarjeta cabe en la
 * fila r > 0 y no en r - 1, es porque algo que estorbaba en r - 1 termina justo ahi. */
export function colocarMasonry(tarjetas, columnas) {
  const n = Math.max(1, columnas);
  const ocupado = Array.from({ length: n }, () => []);
  const finales = new Set([0]);
  const posiciones = new Map();
  for (const t of tarjetas) {
    const cols = Math.min(Math.max(1, t.cols), n);
    const filas = Math.max(1, t.filas);
    let puesto = null;
    for (const fila of [...finales].sort((a, b) => a - b)) {
      for (let col = 0; col + cols <= n && !puesto; col += 1) {
        if (cabe(ocupado, col, cols, fila, filas)) puesto = { col, fila };
      }
      if (puesto) break;
    }
    posiciones.set(t.id, puesto);
    for (let c = puesto.col; c < puesto.col + cols; c += 1) ocupado[c].push([puesto.fila, puesto.fila + filas]);
    finales.add(puesto.fila + filas);
  }
  return posiciones;
}

/** El rectangulo (px, relativo a la cuadricula) de una tarjeta ya colocada. `geom`:
 * `{ anchoColumna, hueco }`. */
export function rectangulo(pos, t, geom, columnas) {
  const cols = Math.min(Math.max(1, t.cols), Math.max(1, columnas));
  return {
    x: pos.col * (geom.anchoColumna + geom.hueco),
    y: pos.fila * FILA_PX,
    w: cols * geom.anchoColumna + (cols - 1) * geom.hueco,
    h: t.alto,
  };
}

function distanciaAlRect(p, r) {
  const dx = Math.max(r.x - p.x, 0, p.x - (r.x + r.w));
  const dy = Math.max(r.y - p.y, 0, p.y - (r.y + r.h));
  return Math.hypot(dx, dy);
}

function distanciaAlCentro(p, r) {
  return Math.hypot(p.x - (r.x + r.w / 2), p.y - (r.y + r.h / 2));
}

/** El orden que resulta de meter `activo` en la posicion `indice` del orden SIN el (0..n-1). */
export function ordenConInsercion(orden, activo, indice) {
  const base = orden.filter((id) => id !== activo);
  base.splice(Math.min(Math.max(0, indice), base.length), 0, activo);
  return base;
}

/** Dos ordenes son el mismo. */
export function mismoOrden(a, b) {
  return a.length === b.length && a.every((id, i) => id === b[i]);
}

/** Elige el orden al que pasa el tablero mientras se arrastra `activo` con el puntero en `puntero`
 * (px, relativo a la cuadricula).
 *
 * Por cada lugar posible de la lista se simula el masonry y se mira donde quedaria el hueco de
 * `activo`. Reglas:
 *  1. Si el puntero sigue DENTRO del hueco actual, no pasa nada. Es lo que evita el parpadeo: el
 *     hueco solo cambia cuando el puntero sale de el.
 *  2. Si no, gana el hueco que contiene al puntero (el de centro mas cercano) o, si ninguno lo
 *     contiene, el mas cercano; y solo si mejora al actual por mas de `margen` px. Despues del
 *     cambio el puntero queda dentro del hueco nuevo (o mas cerca que antes), asi que nunca se
 *     regresa al anterior: no hay ciclos.
 *  3. Si `activo` es chica, solo valen los lugares donde NINGUNA tarjeta grande cambia de lugar
 *     (`protegidas`: donde esta cada una al empezar el arrastre). La tabla solo se mueve si la
 *     arrastras tu.
 *
 * `tarjetas`: `Map(id -> { cols, filas, alto, grande })`. Devuelve el mismo arreglo `orden` si no
 * hay cambio. */
export function elegirOrden({ orden, activo, tarjetas, columnas, geom, puntero, protegidas, margen = 8 }) {
  const t = tarjetas.get(activo);
  if (!t) return orden;
  const proteger = !t.grande && protegidas;
  const actual = orden.indexOf(activo);
  const candidatos = [];
  for (let i = 0; i < orden.length; i += 1) {
    const candidato = i === actual ? orden : ordenConInsercion(orden, activo, i);
    const posiciones = colocarMasonry(candidato.map((id) => ({ id, ...tarjetas.get(id) })), columnas);
    if (proteger) {
      let intacta = true;
      for (const [id, donde] of protegidas) {
        const ahora = posiciones.get(id);
        if (id !== activo && (!ahora || ahora.col !== donde.col || ahora.fila !== donde.fila)) { intacta = false; break; }
      }
      if (!intacta) continue;
    }
    const rect = rectangulo(posiciones.get(activo), t, geom, columnas);
    candidatos.push({
      i, orden: candidato, rect, dentro: distanciaAlRect(puntero, rect) === 0,
      dist: distanciaAlRect(puntero, rect), centro: distanciaAlCentro(puntero, rect),
    });
  }
  const aqui = candidatos.find((c) => c.i === actual);
  if (!aqui || aqui.dentro) return orden;
  const mejor = candidatos.reduce((a, b) => (
    b.dist < a.dist || (b.dist === a.dist && (b.centro < a.centro || (b.centro === a.centro && Math.abs(b.i - actual) < Math.abs(a.i - actual)))) ? b : a
  ));
  if (mejor.i === actual) return orden;
  if (!mejor.dentro && mejor.dist > aqui.dist - margen) return orden;
  return mejor.orden;
}
