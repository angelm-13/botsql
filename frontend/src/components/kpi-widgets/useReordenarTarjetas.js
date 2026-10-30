import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { DURACION_CORRIMIENTO_MS } from "../../kpi/kpiReorden.js";
import {
  colocarMasonry, elegirOrden, esTarjetaGrande, mismoOrden,
} from "../../kpi/kpiMasonry.js";
import { contarColumnasDelGrid } from "../../kpi/kpiColumnas.js";

// Reordenar las tarjetas del masonry arrastrando.
//
// * dnd-kit solo pone el gesto (sensor del puntero y la copia que sigue al cursor). QUE orden toma el
//   tablero no lo decide la tarjeta "sobre la que esta el puntero": lo decide `elegirOrden`
//   (kpi/kpiMasonry.js), que simula el masonry para cada lugar posible de la lista y se queda con el
//   hueco que corresponde al puntero. Asi el hueco que se ve es el lugar REAL donde caera la tarjeta,
//   y no cambia mientras el puntero siga dentro de el.
// * El orden VISTO durante el arrastre (`ordenVista`) es la lista con la tarjeta arrastrada ya en ese
//   lugar. Las tarjetas se pintan en ESE orden y el navegador las acomoda; la arrastrada se queda en
//   el DOM, escondida, como hueco (mismo tamano: es la propia tarjeta).
// * Arrastrar una tarjeta chica nunca mueve una grande (la tabla): solo valen los lugares donde las
//   grandes quedan donde estaban al empezar.
// * Al soltar se guarda ESE MISMO orden: el resultado coincide con lo que mostraba el hueco.
// * Las demas tarjetas se recorren con animacion (FLIP con la Web Animations API), salvo con
//   prefers-reduced-motion, donde cambian de lugar de golpe.

/** dnd-kit pide una deteccion de colisiones; aqui no se usa (ver arriba), asi que no calcula nada. */
export const sinColision = () => [];

const numeroDe = (texto) => { const n = parseFloat(texto); return Number.isFinite(n) ? n : 0; };
const spanDe = (texto) => { const m = /span\s+(\d+)/.exec(texto || ""); return m ? Number(m[1]) : 1; };

/** Lo que hace falta del DOM para simular el masonry: columnas, su ancho y, por tarjeta, cuantas
 * columnas y filas ocupa (los valores ya calculados por el CSS) y su alto real. */
function medirCuadricula(grid, widgets) {
  const estilo = getComputedStyle(grid);
  const columnas = contarColumnasDelGrid(grid);
  const pistas = estilo.gridTemplateColumns.trim().split(/\s+/);
  const geom = { anchoColumna: numeroDe(pistas[0]), hueco: numeroDe(estilo.columnGap) };
  const porId = new Map(widgets.map((w) => [String(w.id_kpi_dashboard_widget), w]));
  const tarjetas = new Map();
  for (const hijo of grid.children) {
    const id = hijo.dataset.widgetId;
    if (!id) continue;
    const e = getComputedStyle(hijo);
    tarjetas.set(id, {
      // `grid-column: span 2` es `grid-column-start: span 2` (el final queda en `auto`).
      cols: Math.min(spanDe(e.gridColumnStart), columnas),
      filas: spanDe(e.gridRowEnd),
      alto: hijo.offsetHeight,
      grande: esTarjetaGrande(porId.get(id)),
    });
  }
  return { columnas, geom, tarjetas };
}

export default function useReordenarTarjetas({ widgets, guardarOrden, gridNodeRef, reducirMovimiento }) {
  const ids = useMemo(() => widgets.map((w) => String(w.id_kpi_dashboard_widget)), [widgets]);
  const [activoId, setActivoId] = useState(null);
  const [ordenVista, setOrdenVista] = useState(null);
  const [instantanea, setInstantanea] = useState(null);
  // Lo medido al empezar el arrastre y el ultimo lugar del puntero (px de pantalla).
  const medida = useRef(null);
  const puntero = useRef(null);

  const widgetsVista = useMemo(() => {
    if (!ordenVista) return widgets;
    const porId = new Map(widgets.map((w) => [String(w.id_kpi_dashboard_widget), w]));
    return ordenVista.map((id) => porId.get(id)).filter(Boolean);
  }, [widgets, ordenVista]);

  const limpiar = useCallback(() => {
    medida.current = null;
    puntero.current = null;
    setActivoId(null);
    setOrdenVista(null);
    setInstantanea(null);
  }, []);

  const alEmpezar = useCallback(({ active, activatorEvent }) => {
    const id = String(active.id);
    const tarjeta = document.querySelector(`[data-widget-id="${id}"] .kpi-widget-card`);
    setInstantanea(tarjeta ? { html: tarjeta.outerHTML, ancho: tarjeta.getBoundingClientRect().width } : null);
    const grid = gridNodeRef.current;
    if (grid) {
      const m = medirCuadricula(grid, widgets);
      // Donde esta cada tarjeta grande ahora: es lo que una tarjeta chica no puede mover.
      const posiciones = colocarMasonry(ids.map((i) => ({ id: i, ...m.tarjetas.get(i) })), m.columnas);
      const protegidas = new Map();
      for (const i of ids) if (m.tarjetas.get(i)?.grande) protegidas.set(i, posiciones.get(i));
      medida.current = { ...m, protegidas };
    }
    if (activatorEvent && "clientX" in activatorEvent) puntero.current = { x: activatorEvent.clientX, y: activatorEvent.clientY };
    setActivoId(id);
    setOrdenVista(ids);
  }, [ids, widgets, gridNodeRef]);

  // El puntero se sigue con eventos propios (no con `over` de dnd-kit): su rectangulo de la tarjeta
  // "sobre la que esta" se queda con la posicion que tenia al medirse y, con tarjetas de distinto
  // tamano, el orden que sale de ahi se desajusta del que se ve.
  const decidir = useCallback(() => {
    const m = medida.current;
    const p = puntero.current;
    const grid = gridNodeRef.current;
    if (!m || !p || !grid || !activoId) return;
    const caja = grid.getBoundingClientRect();
    const enCuadricula = { x: p.x - caja.left, y: p.y - caja.top };
    setOrdenVista((actual) => {
      if (!actual) return actual;
      return elegirOrden({
        orden: actual, activo: activoId, tarjetas: m.tarjetas, columnas: m.columnas,
        geom: m.geom, puntero: enCuadricula, protegidas: m.protegidas,
      });
    });
  }, [activoId, gridNodeRef]);

  useEffect(() => {
    if (!activoId) return undefined;
    const alPuntero = (evento) => { puntero.current = { x: evento.clientX, y: evento.clientY }; decidir(); };
    // Si la pagina se desplaza (autoscroll) sin mover el puntero, el lugar del puntero en la
    // cuadricula cambia igual.
    window.addEventListener("pointermove", alPuntero);
    window.addEventListener("scroll", decidir, true);
    return () => {
      window.removeEventListener("pointermove", alPuntero);
      window.removeEventListener("scroll", decidir, true);
    };
  }, [activoId, decidir]);

  const alSoltar = useCallback(() => {
    const final = ordenVista;
    limpiar();
    if (final && !mismoOrden(final, ids)) guardarOrden(final);
  }, [ordenVista, ids, limpiar, guardarOrden]);

  // --- FLIP: las tarjetas que cambian de lugar se deslizan desde donde estaban ----------------
  // `posiciones` guarda donde quedo cada tarjeta en el layout anterior. Si alguna seguia animandose,
  // su lugar VISIBLE era ese mas el desplazamiento que llevaba: se arranca desde ahi, no desde el
  // layout, o la tarjeta daria un salto al interrumpirse.
  const posiciones = useRef(new Map());
  const claveOrden = widgetsVista.map((w) => w.id_kpi_dashboard_widget).join(",");
  useLayoutEffect(() => {
    const grid = gridNodeRef.current;
    if (!grid) return;
    const nuevas = new Map();
    for (const hijo of grid.children) {
      if (hijo.dataset.widgetId) nuevas.set(hijo.dataset.widgetId, { x: hijo.offsetLeft, y: hijo.offsetTop, nodo: hijo });
    }
    if (!reducirMovimiento && posiciones.current.size && typeof Element.prototype.animate === "function") {
      for (const [id, ahora] of nuevas) {
        const antes = posiciones.current.get(id);
        if (!antes) continue;
        let enCurso = { x: 0, y: 0 };
        const animaciones = ahora.nodo.getAnimations ? ahora.nodo.getAnimations() : [];
        if (animaciones.length) {
          const m = new DOMMatrixReadOnly(getComputedStyle(ahora.nodo).transform);
          enCurso = { x: m.m41, y: m.m42 };
          animaciones.forEach((a) => a.cancel());
        }
        const dx = antes.x + enCurso.x - ahora.x;
        const dy = antes.y + enCurso.y - ahora.y;
        if (!dx && !dy) continue;
        ahora.nodo.animate(
          [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }],
          { duration: DURACION_CORRIMIENTO_MS, easing: "cubic-bezier(.2,.8,.2,1)" },
        );
      }
    }
    posiciones.current = nuevas;
  }, [claveOrden, reducirMovimiento, gridNodeRef]);

  return {
    widgetsVista,
    activoId,
    instantanea,
    idsVista: widgetsVista.map((w) => w.id_kpi_dashboard_widget),
    handlers: { onDragStart: alEmpezar, onDragEnd: alSoltar, onDragCancel: limpiar },
  };
}
