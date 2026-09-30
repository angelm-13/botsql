import { useCallback, useRef } from "react";

// Masonry de tarjetas con CSS grid, sin libreria (kpi-dashboard.css, `.kpi-widget-grid`).
//
// La cuadricula tiene filas de MASONRY_FILA_PX de alto y cada tarjeta ocupa tantas filas como
// mide, asi que conserva su ALTURA NATURAL y las de abajo suben a llenar el hueco. Ese numero de
// filas (`grid-row-end: span N`) no se puede escribir en CSS: depende de lo que mida la tarjeta,
// que cambia cuando cargan sus datos o cuando la ventana cambia el ancho de su columna.
//
// Se escribe directo en el DOM, no en el estado de React, y la primera vez dentro del callback ref
// (antes de que el navegador pinte): asi la tarjeta nace ya en su sitio y un cambio posterior de
// alto se corrige antes del siguiente cuadro, sin parpadeo y sin volver a renderizar nada.
export const MASONRY_FILA_PX = 4;
export const MASONRY_HUECO_PX = 16;

// Las funciones de ajuste de las tarjetas montadas, para poder pedirles que midan otra vez a mano
// (`remedirMasonry`). El ResizeObserver lo hace solo en un navegador normal; esto existe para las
// pruebas, que corren Chrome con reloj virtual (--virtual-time-budget), donde no se entregan
// notificaciones de tamano porque no se pintan cuadros.
const activos = new Set();

/** Vuelve a medir todas las tarjetas ahora. */
export function remedirMasonry() {
  activos.forEach((ajustar) => ajustar());
}

/** Filas que ocupa una tarjeta de `alto` px, contando el hueco de abajo. */
export function filasQueOcupa(alto, fila = MASONRY_FILA_PX, hueco = MASONRY_HUECO_PX) {
  if (!Number.isFinite(alto) || alto <= 0) return 1;
  return Math.max(1, Math.ceil((alto + hueco) / fila));
}

/** Ref callback para el elemento que es HIJO DIRECTO de la cuadricula. `offsetHeight` (y no
 * getBoundingClientRect) a proposito: no cambia con el `transform: scale` de la tarjeta que se
 * esta arrastrando, que si no haria saltar a las demas. */
export default function useMasonryRef() {
  const observador = useRef(null);
  return useCallback((nodo) => {
    if (observador.current) {
      observador.current.disconnect();
      activos.delete(observador.current.ajustar);
      observador.current = null;
    }
    if (!nodo) return;
    const ajustar = () => {
      nodo.style.gridRowEnd = `span ${filasQueOcupa(nodo.offsetHeight)}`;
    };
    ajustar();
    activos.add(ajustar);
    if (typeof ResizeObserver !== "undefined") {
      observador.current = new ResizeObserver(ajustar);
      observador.current.ajustar = ajustar;
      observador.current.observe(nodo);
    } else {
      observador.current = { disconnect() {}, ajustar };
    }
  }, []);
}
