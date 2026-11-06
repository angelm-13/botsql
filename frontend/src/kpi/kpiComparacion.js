// Contra que fechas compara un widget: de donde sale el rango B y como se rotula. Puro y sin React -- ver kpiComparacion.test.js.
import { formatoDeRango, formatoDeRangoCorto } from "./kpiRango.js";

/** El rango contra el que se compara: el que DEVOLVIO el servidor (`rango_b.inicio/fin`, la verdad de lo que se calculo) o, si
 * la respuesta no lo trae, el que el cliente calcula de los `parametros` efectivos (`fecha_inicio_b`/`fecha_fin_b`, que para un
 * rango relativo ya vienen resueltos por `parametrosEfectivos`: periodo anterior o N dias atras). `null` si no se compara. */
export function rangoComparadoDe({ snapshot, parametros } = {}) {
  const delServidor = snapshot?.rango_b;
  if (delServidor?.inicio && delServidor?.fin) return { inicio: delServidor.inicio, fin: delServidor.fin, origen: "servidor" };
  const guardados = parametros || {};
  if (guardados.fecha_inicio_b && guardados.fecha_fin_b) return { inicio: guardados.fecha_inicio_b, fin: guardados.fecha_fin_b, origen: "cliente" };
  return null;
}

/** El año del rango principal (para omitirlo en la leyenda del comparado cuando es el mismo): el del servidor o el de los parametros. */
export function anioDelRangoPrincipal({ snapshot, parametros } = {}) {
  const fin = snapshot?.rango_a?.fin || parametros?.fecha_fin || "";
  const anio = Number(String(fin).slice(0, 4));
  return Number.isInteger(anio) && anio > 0 ? anio : null;
}

/** "6 sep – 5 oct" (corta, para la tarjeta) o "6 sep – 5 oct 2026" (completa, para el editor y la leyenda de una grafica). "" sin rango. */
export function etiquetaDeRangoComparado(rango, { locale = "es-MX", anioDeReferencia = null, completa = false } = {}) {
  if (!rango) return "";
  return completa
    ? formatoDeRango(rango.inicio, rango.fin, { locale })
    : formatoDeRangoCorto(rango.inicio, rango.fin, { locale, anioDeReferencia });
}

/** "vs. {rango}" con la plantilla traducida (`kpi_dashboard.vs_compare_range`). */
export function textoVsRango(plantilla, etiqueta) {
  return String(plantilla || "vs. {rango}").replace("{rango}", etiqueta);
}
