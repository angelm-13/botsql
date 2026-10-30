// Cuantas columnas tiene la cuadricula del tablero AHORA, leidas de su `grid-template-columns` ya
// resuelto (el navegador lo entrega como una lista de anchos en px, una por pista). No se reproduce
// la formula de `auto-fill`/`minmax`: se lee lo que el navegador decidio.
export function contarColumnasDelGrid(nodo) {
  const pistas = getComputedStyle(nodo).gridTemplateColumns;
  if (!pistas || pistas === "none") return 1;
  return Math.max(1, pistas.trim().split(/\s+/).length);
}
