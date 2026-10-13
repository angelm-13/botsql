// Logica pura del selector de KPI (components/kpi-widgets/SelectorDeKpi.jsx):
// agrupar por modulo, filtrar por busqueda y decidir que opciones se pueden
// elegir. Sin React -- ver kpi.test.js.
import { CATEGORICAL, normalizarBusqueda } from "./kpiDatos.js";
import { motivoParaNoCombinar } from "./kpiParametros.js";

export const GRUPO_VARIABLES = "variables";

/** Un KPI "variable suelta": sin desglose (dimension "global", ej. ingresos y
 * egresos totales). No se elige "por modulo" sino para combinarlo con otros en
 * un mismo grafico, asi que vive en su propio grupo. */
export function esVariable(kpi) {
  return kpi?.dimensiones?.[0] === "global";
}

// Orden fijo de los botones de modulo. El catalogo llega en el orden de la base de
// datos (arbitrario), y un selector que reordena sus botones segun la consulta se
// siente roto; los modulos que no esten aqui van despues, por nombre.
export const ORDEN_DE_MODULOS = ["operaciones", "inventario", "facturacion", "laboratorio", "documentos", "restaurante"];
const posicionDeModulo = (clave) => {
  const posicion = ORDEN_DE_MODULOS.indexOf(clave);
  return posicion === -1 ? ORDEN_DE_MODULOS.length : posicion;
};

/** El catalogo agrupado por modulo, con "Variables" como un grupo mas al final.
 *
 * `busqueda` (ya escrita por la persona, sin normalizar) filtra por nombre,
 * descripcion y clave, sin distinguir mayusculas ni acentos; un grupo que se
 * queda sin opciones desaparece. Los modulos salen en un orden fijo
 * (ORDEN_DE_MODULOS), no en el del catalogo. */
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

  const grupos = [...porModulo.entries()]
    .map(([modulo, kpis]) => ({ clave: modulo, modulo, esVariables: false, kpis }))
    .sort((a, b) => posicionDeModulo(a.clave) - posicionDeModulo(b.clave) || a.clave.localeCompare(b.clave));
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

// Un color por modulo para el boton del selector: neutro en reposo, a color al
// elegirlo. Los cinco modulos con KPIs hoy tienen el suyo fijo (mismos tonos vivos
// de la paleta categorica, distintos entre si); un modulo nuevo cae a un tono de
// la paleta segun su nombre, siempre el mismo.
export const COLOR_DE_MODULO = {
  facturacion: CATEGORICAL[0],
  operaciones: CATEGORICAL[1],
  inventario: CATEGORICAL[2],
  laboratorio: CATEGORICAL[6],
  documentos: CATEGORICAL[5],
  restaurante: CATEGORICAL[3],
  [GRUPO_VARIABLES]: CATEGORICAL[4],
};

export function colorDeModulo(clave) {
  if (COLOR_DE_MODULO[clave]) return COLOR_DE_MODULO[clave];
  let suma = 0;
  for (const caracter of String(clave)) suma += caracter.charCodeAt(0);
  return CATEGORICAL[suma % CATEGORICAL.length];
}

/** La clave del grupo al que pertenece un KPI en el selector. */
export function claveDeGrupo(kpi) {
  return esVariable(kpi) ? GRUPO_VARIABLES : kpi.modulo;
}

/** Modulo con el que abre el selector: el del primer KPI ya elegido, o si no hay
 * ninguno, el primero de la lista. */
export function grupoInicial(grupos, catalogo, seleccionados) {
  const primero = (seleccionados || [])
    .map((id) => (catalogo || []).find((kpi) => String(kpi.id_kpi_definition) === id))
    .find(Boolean);
  const clave = primero ? claveDeGrupo(primero) : null;
  return grupos.some((grupo) => grupo.clave === clave) ? clave : grupos[0]?.clave ?? null;
}

/** Lo que muestra cada boton de modulo: cuantos KPIs tiene, cuantos coinciden con
 * la busqueda actual y cuantos de los YA ELEGIDOS caen ahi (la seleccion se
 * conserva al cambiar de modulo, y esto es lo que la deja ver). Solo aparecen los
 * modulos con al menos un KPI en el catalogo: lo que no llega en
 * GET /kpi_definition/ (por plan o por permiso) no tiene boton. */
export function resumenDeModulos(catalogo, busqueda, seleccionados) {
  const coincidencias = new Map(agruparKpis(catalogo, busqueda).map((grupo) => [grupo.clave, grupo.kpis.length]));
  return agruparKpis(catalogo).map((grupo) => ({
    clave: grupo.clave,
    modulo: grupo.modulo,
    esVariables: grupo.esVariables,
    total: grupo.kpis.length,
    coincidencias: coincidencias.get(grupo.clave) ?? 0,
    elegidos: grupo.kpis.filter((kpi) => (seleccionados || []).includes(String(kpi.id_kpi_definition))).length,
  }));
}
