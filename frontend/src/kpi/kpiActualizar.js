// "Actualizar datos": que indicadores de un tablero se recalculan, con que rango, y como se resume el resultado.
// Puro y sin React -- ver kpiActualizar.test.js.
//
// El backend recalcula UN indicador por llamada (POST /kpi_dashboard/<id>/recalcular); el contador "n de N" es real
// porque el cliente llama en secuencia. El rango de cada indicador es el que sus widgets muestran HOY (un widget con
// `rango_relativo` se resuelve al dia de hoy, `parametrosEfectivos`), no el que quedo guardado.

import { parametrosEfectivos } from "./kpiRango.js";

// Mismo tope que el backend (`kpi_rango_dias_max`, 365 por omision).
export const RANGO_DIAS_MAX = 365;
// Cuanto espera el boton despues de un exito: el backend ya responde "ya al dia" por debajo de 60 s.
export const ESPERA_TRAS_EXITO_MS = 60 * 1000;

const MS_POR_DIA = 86400000;

function dias(inicio, fin) {
  return Math.round((new Date(`${fin}T00:00:00`) - new Date(`${inicio}T00:00:00`)) / MS_POR_DIA);
}

/** Un item por indicador de serie visible: `{ id_kpi_definition, fecha_inicio, fecha_fin }`.
 * Si un indicador esta en varios widgets (o tiene periodo de comparacion), se pide la union de sus rangos; si esa union
 * pasa del tope, se queda solo con el rango principal. Se omiten tablas en vivo, KPIs sin permiso (no estan en el
 * catalogo) y widgets sin rango. */
export function itemsAActualizar(widgets, kpiCatalog, hoy = new Date()) {
  const porKpi = new Map();
  for (const widget of widgets || []) {
    if (widget.tipo_grafica === "tabla") continue;
    const parametros = parametrosEfectivos(widget.parametros, hoy);
    if (!parametros.fecha_inicio || !parametros.fecha_fin) continue;
    const rangos = [[parametros.fecha_inicio, parametros.fecha_fin]];
    if (parametros.fecha_inicio_b && parametros.fecha_fin_b) rangos.push([parametros.fecha_inicio_b, parametros.fecha_fin_b]);
    const ids = Array.isArray(widget.ids_kpi_definition) ? widget.ids_kpi_definition : [];
    for (const id of ids) {
      const kpi = (kpiCatalog || []).find((item) => item.id_kpi_definition === id);
      if (!kpi || kpi.modo === "vivo") continue;
      const actual = porKpi.get(id) || { principal: null, todos: [] };
      if (!actual.principal) actual.principal = rangos[0];
      actual.todos.push(...rangos);
      porKpi.set(id, actual);
    }
  }
  return [...porKpi.entries()].map(([id, { principal, todos }]) => {
    const inicio = todos.reduce((menor, [i]) => (i < menor ? i : menor), todos[0][0]);
    const fin = todos.reduce((mayor, [, f]) => (f > mayor ? f : mayor), todos[0][1]);
    const [fecha_inicio, fecha_fin] = dias(inicio, fin) > RANGO_DIAS_MAX ? principal : [inicio, fin];
    return { id_kpi_definition: id, fecha_inicio, fecha_fin };
  });
}

/** Suma lo que respondieron las llamadas: `{ actualizados, yaAlDia, omitidos }` (conteos de indicadores). */
export function sumarRespuestas(respuestas) {
  return (respuestas || []).reduce((suma, respuesta) => ({
    actualizados: suma.actualizados + (respuesta?.actualizados?.length || 0),
    yaAlDia: suma.yaAlDia + (respuesta?.ya_al_dia?.length || 0),
    omitidos: suma.omitidos + (respuesta?.omitidos?.length || 0),
  }), { actualizados: 0, yaAlDia: 0, omitidos: 0 });
}

/** Como termina una corrida: "nada" (sin indicadores que calcular), "en_curso" (otro recalculo corriendo), "error",
 * "listo" (se recalculo algo; `al_dia` = indicadores que quedaron al dia) o "ya_al_dia" (nada hubo que recalcular). */
export function resultadoFinal({ total, respuestas, fallo }) {
  if (total === 0) return { tipo: "nada" };
  const suma = sumarRespuestas(respuestas);
  if (fallo === "kpis.recalculation_in_progress") return { tipo: "en_curso", ...suma };
  if (fallo) return { tipo: "error", ...suma };
  if (suma.actualizados > 0) return { tipo: "listo", ...suma, alDia: suma.actualizados + suma.yaAlDia };
  if (suma.yaAlDia > 0) return { tipo: "ya_al_dia", ...suma };
  return { tipo: "nada", ...suma };
}

/** Ids de indicador que quedaron al dia en esta corrida (recalculados o ya al dia), para recordarlos en la sesion. */
export function idsAlDia(respuestas) {
  return (respuestas || []).flatMap((respuesta) => [...(respuesta?.actualizados || []), ...(respuesta?.ya_al_dia || [])]);
}
