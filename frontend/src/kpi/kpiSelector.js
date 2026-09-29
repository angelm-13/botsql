// Logica pura del selector de KPI (components/kpi-widgets/SelectorDeKpi.jsx):
// agrupar por modulo, filtrar por busqueda y decidir que opciones se pueden
// elegir. Sin React -- ver kpi.test.js.
import { normalizarBusqueda } from "./kpiDatos.js";
import { motivoParaNoCombinar } from "./kpiParametros.js";

export const GRUPO_VARIABLES = "variables";

/** Un KPI "variable suelta": sin desglose (dimension "global", ej. ingresos y
 * egresos totales). No se elige "por modulo" sino para combinarlo con otros en
 * un mismo grafico, asi que vive en su propio grupo. */
export function esVariable(kpi) {
  return kpi?.dimensiones?.[0] === "global";
}

/** El catalogo agrupado por modulo, con "Variables" como un grupo mas al final.
 *
 * `busqueda` (ya escrita por la persona, sin normalizar) filtra por nombre,
 * descripcion y clave, sin distinguir mayusculas ni acentos; un grupo que se
 * queda sin opciones desaparece. Los modulos salen en el orden en que aparecen
 * en el catalogo. */
export function agruparKpis(catalogo, busqueda = "") {
  const filtro = normalizarBusqueda(busqueda);
  const coincide = (kpi) => !filtro
    || normalizarBusqueda(`${kpi.etiqueta || ""} ${kpi.descripcion || ""} ${kpi.clave || ""}`).includes(filtro);

  const porModulo = new Map();
  const variables = [];
  (catalogo || []).filter(coincide).forEach((kpi) => {
    if (esVariable(kpi)) {
      variables.push(kpi);
      return;
    }
    const lista = porModulo.get(kpi.modulo) || [];
    lista.push(kpi);
    porModulo.set(kpi.modulo, lista);
  });

  const grupos = [...porModulo.entries()].map(([modulo, kpis]) => ({ clave: modulo, modulo, esVariables: false, kpis }));
  if (variables.length) grupos.push({ clave: GRUPO_VARIABLES, modulo: null, esVariables: true, kpis: variables });
  return grupos;
}

/** Como se ve una opcion: elegida, elegible o bloqueada (con el motivo).
 *
 * El bloqueo solo existe al combinar varios KPIs (`multiple`): con un solo KPI
 * por grafico, elegir otro simplemente reemplaza al anterior. Una opcion ya
 * elegida nunca se bloquea (siempre se puede quitar). */
export function estadoDeOpcion({ kpi, seleccionados, catalogo, multiple }) {
  const id = String(kpi.id_kpi_definition);
  const elegida = seleccionados.includes(id);
  if (elegida || !multiple) return { elegida, motivo: null };
  const infos = seleccionados
    .map((idElegido) => (catalogo || []).find((otro) => String(otro.id_kpi_definition) === idElegido))
    .filter(Boolean);
  return { elegida, motivo: motivoParaNoCombinar(infos, kpi) };
}
