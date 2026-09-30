import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { contarColumnasDelGrid } from "../../kpi/kpiColumnas.js";
import { casillasDeRelleno, filasParaLlenar } from "../../kpi/kpiRelleno.js";

// Cuantos recuadros punteados "Agregar gráfico" van en la cuadricula (la aritmetica esta en
// kpi/kpiRelleno.js). Lee del navegador las columnas que hay AHORA (no reproduce la formula de
// `auto-fill`) y, si el tablero esta vacio, cuanto alto queda a la vista para llenarlo. Se vuelve
// a medir cuando cambia el ancho del grid o el de la ventana; es aritmetica sobre esos numeros,
// asi que no hay ciclo de medicion.
export default function useRellenoDelGrid(cantidad, dobles) {
  // El nodo en ESTADO (callback ref): el grid se desmonta y se vuelve a montar con cada carga del
  // tablero, y un `useRef` no avisa a los efectos cuando su `.current` cambia.
  const [nodo, setNodo] = useState(null);
  const [medida, setMedida] = useState({ columnas: null, filasVisibles: 2 });
  const asignarNodo = useCallback((actual) => setNodo(actual), []);

  const medir = useCallback(() => {
    if (!nodo) return;
    const arriba = nodo.getBoundingClientRect().top + window.scrollY;
    const columnas = contarColumnasDelGrid(nodo);
    const filasVisibles = filasParaLlenar(window.innerHeight - arriba);
    setMedida((previa) => (previa.columnas === columnas && previa.filasVisibles === filasVisibles ? previa : { columnas, filasVisibles }));
  }, [nodo]);

  useLayoutEffect(() => {
    if (!nodo) return undefined;
    medir();
    const observador = typeof ResizeObserver !== "undefined" ? new ResizeObserver(medir) : null;
    observador?.observe(nodo);
    return () => observador?.disconnect();
  }, [nodo, medir]);
  useEffect(() => {
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, [medir]);

  return [casillasDeRelleno({ cantidad, dobles, columnas: medida.columnas, filasVisibles: medida.filasVisibles }), asignarNodo];
}
