// Logica pura del reordenamiento de tarjetas (components/kpi-widgets/useReordenarTarjetas.js).
// Sin React -- ver kpi.test.js.

/** El orden que resulta de soltar `activo` donde esta `sobre`: `activo` pasa a ocupar el lugar de
 * `sobre` y las demas se recorren. Es la misma semantica de `arrayMove` de dnd-kit, y por eso lo
 * que se ve durante el arrastre es exactamente lo que se guarda al soltar. Sin cambios (mismo
 * arreglo) si alguno no esta o son el mismo. */
export function ordenTrasMover(ids, activo, sobre) {
  const de = ids.indexOf(activo);
  const a = ids.indexOf(sobre);
  if (de === -1 || a === -1 || de === a) return ids;
  const copia = [...ids];
  copia.splice(a, 0, copia.splice(de, 1)[0]);
  return copia;
}

/** Dos ordenes son el mismo. */
export function mismoOrden(a, b) {
  return a.length === b.length && a.every((id, i) => id === b[i]);
}

// Tras cada cambio de orden, el arrastre no acepta otro durante este rato: la tarjeta que acaba de
// correrse todavia esta animandose y, sin este freno, la que queda bajo el puntero cambia en cada
// cuadro y las tarjetas "tiemblan".
export const PAUSA_TRAS_MOVER_MS = 220;
export const DURACION_CORRIMIENTO_MS = 220;
