// Rangos de fechas relativos ("ultimos 30 dias", "mes anterior"...) del
// Dashboard de KPIs. Puro y sin React -- ver kpi.test.js.
//
// Un widget guarda `parametros.rango_relativo` ADEMAS de sus fechas
// absolutas: las fechas son la foto del dia en que se guardo (asi cualquier
// cliente que no conozca el campo nuevo sigue viendo lo mismo de siempre) y
// `rango_relativo` es la instruccion de volver a calcularlas cada vez que se
// mira. Un widget sin `rango_relativo` -todos los que ya existian- se
// comporta exactamente como antes: sus fechas absolutas mandan.

/** Los rangos que el editor ofrece como chips (mas "personalizado", que es no
 * usar ninguno y elegir las fechas a mano). Orden = orden de los chips. */
export const RANGOS_RELATIVOS = ["hoy", "7_dias", "30_dias", "90_dias", "este_mes", "mes_anterior", "este_anio"];
export const RANGO_PERSONALIZADO = "personalizado";

/** Texto de cada rango cuando la traduccion (`kpi_dashboard.range_<clave>`) no
 * lo trae: el nombre de un chip del editor y el rotulo del encabezado de una
 * tarjeta. La clave interna (`30_dias`) nunca se le muestra a nadie. */
export const ETIQUETA_RANGO_POR_OMISION = {
  hoy: "Hoy",
  "7_dias": "7 días",
  "30_dias": "30 días",
  "90_dias": "90 días",
  este_mes: "Este mes",
  mes_anterior: "Mes anterior",
  este_anio: "Este año",
  personalizado: "Personalizado",
};
export const RANGO_RELATIVO_POR_OMISION = "30_dias";

const MS_POR_DIA = 86400000;

/** AAAA-MM-DD de una fecha en HORA LOCAL. `toISOString()` da la fecha en UTC:
 * en Mexico, despues de las 18:00 ya es "manana" -- un rango "hasta hoy"
 * saldria corrido un dia. */
export function fechaLocalIso(fecha) {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function desdeIso(iso) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function sumarDias(fecha, dias) {
  const copia = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  copia.setDate(copia.getDate() + dias);
  return copia;
}

/** `{ fecha_inicio, fecha_fin }` de un rango relativo, o null si la clave no
 * es una que este codigo conozca (un valor de una version futura). "N dias"
 * cuenta HOY: los ultimos 7 dias son hoy y los 6 anteriores. */
export function resolverRangoRelativo(clave, hoy = new Date()) {
  const dia = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  let inicio;
  let fin = dia;
  switch (clave) {
    case "hoy": inicio = dia; break;
    case "7_dias": inicio = sumarDias(dia, -6); break;
    case "30_dias": inicio = sumarDias(dia, -29); break;
    case "90_dias": inicio = sumarDias(dia, -89); break;
    case "este_mes": inicio = new Date(dia.getFullYear(), dia.getMonth(), 1); break;
    case "mes_anterior":
      inicio = new Date(dia.getFullYear(), dia.getMonth() - 1, 1);
      fin = new Date(dia.getFullYear(), dia.getMonth(), 0); // dia 0 = ultimo del mes anterior
      break;
    case "este_anio": inicio = new Date(dia.getFullYear(), 0, 1); break;
    default: return null;
  }
  return { fecha_inicio: fechaLocalIso(inicio), fecha_fin: fechaLocalIso(fin) };
}

/** El periodo inmediatamente anterior y de la misma duracion: contra el que se
 * compara un rango relativo (los rangos B guardados a mano se quedarian viejos
 * en cuanto pasara un dia). */
export function periodoAnterior({ fecha_inicio: inicio, fecha_fin: fin }) {
  const dias = Math.round((desdeIso(fin) - desdeIso(inicio)) / MS_POR_DIA) + 1;
  const finAnterior = sumarDias(desdeIso(inicio), -1);
  const inicioAnterior = sumarDias(finAnterior, -(dias - 1));
  return { fecha_inicio_b: fechaLocalIso(inicioAnterior), fecha_fin_b: fechaLocalIso(finAnterior) };
}

/** Un `rango_relativo` valido que de verdad hay que recalcular (no vacio, no
 * "personalizado", no una clave desconocida). */
export function esRangoRelativoVigente(clave) {
  return RANGOS_RELATIVOS.includes(clave);
}

/** Los `parametros` de un widget con sus fechas al dia de `hoy`. Un widget sin
 * `rango_relativo` (todos los de antes) sale IGUAL, tal cual estaba guardado. */
export function parametrosEfectivos(parametros, hoy = new Date()) {
  const guardados = parametros || {};
  if (!esRangoRelativoVigente(guardados.rango_relativo)) return guardados;
  const rango = resolverRangoRelativo(guardados.rango_relativo, hoy);
  const efectivos = { ...guardados, ...rango };
  if (guardados.comparar_anterior) Object.assign(efectivos, periodoAnterior(rango));
  return efectivos;
}
