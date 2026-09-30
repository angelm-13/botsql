import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { closestCenter, pointerWithin } from "@dnd-kit/core";
import {
  DURACION_CORRIMIENTO_MS, PAUSA_TRAS_MOVER_MS, mismoOrden, ordenTrasMover,
} from "../../kpi/kpiReorden.js";

// Reordenar las tarjetas del masonry arrastrando.
//
// * El orden VISTO durante el arrastre (`ordenVista`) es el orden de la lista con la tarjeta
//   arrastrada ya movida a donde caeria. Las tarjetas se pintan en ESE orden, asi que el masonry
//   real (las alturas naturales, el primer hueco donde cabe cada una) las acomoda: nada se calcula
//   sobre una reja uniforme.
// * La tarjeta arrastrada se queda en el DOM, en su lugar de destino, como HUECO (mismo tamano que
//   la tarjeta: es la propia tarjeta, escondida). Lo que sigue al puntero es una copia estatica de
//   su HTML en un DragOverlay (no vuelve a pedir datos ni a montar graficas).
// * Al soltar se guarda ESE MISMO orden: el resultado coincide con lo que mostraba el hueco.
// * Las demas tarjetas se recorren con animacion (FLIP con la Web Animations API), salvo con
//   prefers-reduced-motion, donde cambian de lugar de golpe.

/** Colision: la tarjeta que esta bajo el puntero; si el puntero esta en un hueco entre tarjetas, la
 * de centro mas cercano. */
export function colisionPorPuntero(args) {
  const dentro = pointerWithin(args);
  return dentro.length ? dentro : closestCenter(args);
}

export default function useReordenarTarjetas({ widgets, guardarOrden, gridNodeRef, reducirMovimiento }) {
  const ids = useMemo(() => widgets.map((w) => String(w.id_kpi_dashboard_widget)), [widgets]);
  const [activoId, setActivoId] = useState(null);
  const [ordenVista, setOrdenVista] = useState(null);
  const [instantanea, setInstantanea] = useState(null);
  const pausaHasta = useRef(0);

  const widgetsVista = useMemo(() => {
    if (!ordenVista) return widgets;
    const porId = new Map(widgets.map((w) => [String(w.id_kpi_dashboard_widget), w]));
    return ordenVista.map((id) => porId.get(id)).filter(Boolean);
  }, [widgets, ordenVista]);

  const limpiar = useCallback(() => {
    setActivoId(null);
    setOrdenVista(null);
    setInstantanea(null);
  }, []);

  const alEmpezar = useCallback(({ active }) => {
    const id = String(active.id);
    const tarjeta = document.querySelector(`[data-widget-id="${id}"] .kpi-widget-card`);
    setInstantanea(tarjeta ? { html: tarjeta.outerHTML, ancho: tarjeta.getBoundingClientRect().width } : null);
    setActivoId(id);
    setOrdenVista(ids);
    pausaHasta.current = 0;
  }, [ids]);

  // `onDragMove` (y no `onDragOver`): se dispara con cada movimiento, asi que una decision que se
  // pospuso por la pausa se retoma en el siguiente movimiento en vez de perderse.
  const alMover = useCallback(({ active, over }) => {
    if (!over || String(over.id) === String(active.id)) return;
    if (performance.now() < pausaHasta.current) return;
    setOrdenVista((actual) => {
      if (!actual) return actual;
      const siguiente = ordenTrasMover(actual, String(active.id), String(over.id));
      if (siguiente !== actual) pausaHasta.current = performance.now() + PAUSA_TRAS_MOVER_MS;
      return siguiente;
    });
  }, []);

  const alSoltar = useCallback(() => {
    const final = ordenVista;
    limpiar();
    if (final && !mismoOrden(final, ids)) guardarOrden(final);
  }, [ordenVista, ids, limpiar, guardarOrden]);

  // --- FLIP: las tarjetas que cambian de lugar se deslizan desde donde estaban ----------------
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
        const dx = antes.x - ahora.x;
        const dy = antes.y - ahora.y;
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
    handlers: { onDragStart: alEmpezar, onDragMove: alMover, onDragEnd: alSoltar, onDragCancel: limpiar },
  };
}
