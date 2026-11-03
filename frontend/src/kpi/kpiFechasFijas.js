// Widgets guardados con fechas absolutas ("fechas fijas") y como pasarlos a un rango relativo. Puro y sin React --
// ver kpiFechasFijas.test.js.
//
// Un widget sin `rango_relativo` (todos los de antes de que existiera) se queda con la `fecha_fin` del dia en que se
// creo: no se mueve con el tiempo. La conversion la pide la persona, widget por widget; nada se cambia en masa.
import {
  RANGOS_RELATIVOS, esRangoRelativoVigente, periodoAnterior, resolverRangoRelativo,
} from "./kpiRango.js";

const MS_POR_DIA = 24 * 60 * 60 * 1000;

function desdeIso(texto) {
  const [anio, mes, dia] = String(texto).split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

// Dias del tramo, contando los dos extremos; null si las fechas no son validas o van al reves.
export function diasDelTramo(fechaInicio, fechaFin) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(fechaInicio)) || !/^\d{4}-\d{2}-\d{2}$/.test(String(fechaFin))) return null;
  const dias = Math.round((desdeIso(fechaFin) - desdeIso(fechaInicio)) / MS_POR_DIA) + 1;
  return dias >= 1 ? dias : null;
}

const RANGO_POR_DIAS = { 1: "hoy", 7: "7_dias", 30: "30_dias", 90: "90_dias" };

// El rango relativo que equivale al tramo guardado, solo si coincide EXACTO con la duracion de uno ("hoy", 7, 30 o 90
// dias). Un tramo de 60 dias, un mes suelto o cualquier otro no equivale a ninguno: devuelve null y la persona elige.
export function rangoRelativoPorDuracion(fechaInicio, fechaFin) {
  const dias = diasDelTramo(fechaInicio, fechaFin);
  return dias === null ? null : (RANGO_POR_DIAS[dias] || null);
}

// Si el widget se ve con fechas fijas: tiene un rango guardado sin `rango_relativo` vigente. Una tabla en vivo no
// tiene periodo (no es "fija") y un widget sin fechas ya dice que le falta el rango.
export function esDeFechasFijas(widget, kpiInfos = []) {
  if (!widget || widget.tipo_grafica === "tabla") return false;
  if ((kpiInfos || []).some((info) => info?.modo === "vivo")) return false;
  const parametros = widget.parametros || {};
  if (!parametros.fecha_inicio || !parametros.fecha_fin) return false;
  return !esRangoRelativoVigente(parametros.rango_relativo);
}

// Los `parametros` del widget convertido a `clave`: todo lo demas se conserva. Las fechas guardadas pasan a ser la
// foto de hoy (como las deja el editor). Un rango de comparacion FIJO pasaria a quedar desfasado del rango nuevo, asi
// que se vuelve "contra el periodo anterior"; uno que ya era relativo (desfase o periodo anterior) no se toca.
export function parametrosConRangoRelativo(parametros, clave, hoy = new Date()) {
  if (!RANGOS_RELATIVOS.includes(clave)) throw new Error(`rango relativo desconocido: ${clave}`);
  const guardados = parametros || {};
  const resultado = { ...guardados, rango_relativo: clave, ...resolverRangoRelativo(clave, hoy) };
  const teniaComparacionFija = Boolean(guardados.fecha_inicio_b && guardados.fecha_fin_b)
    && !guardados.comparar_anterior && !(Number(guardados.comparar_desfase_dias) > 0);
  if (teniaComparacionFija) {
    resultado.comparar_anterior = true;
    Object.assign(resultado, periodoAnterior(resolverRangoRelativo(clave, hoy)));
  }
  return resultado;
}

// Para el texto de confirmacion: ¿la conversion cambia un rango de comparacion fijo?
export function cambiaLaComparacion(parametros) {
  const guardados = parametros || {};
  return Boolean(guardados.fecha_inicio_b && guardados.fecha_fin_b)
    && !guardados.comparar_anterior && !(Number(guardados.comparar_desfase_dias) > 0);
}
