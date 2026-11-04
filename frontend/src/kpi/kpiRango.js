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

/** Con qué se puede comparar un rango relativo, además del periodo anterior: el
 * mismo rango pero corrido N días atrás (`comparar_desfase_dias`). "Hoy contra
 * hace 30 días" es un dia contra otro dia, no contra "ayer". */
export const DESFASES_DE_COMPARACION = [7, 30, 90, 365];

/** El mismo rango, corrido `dias` hacia atras. */
export function rangoDesfasado({ fecha_inicio: inicio, fecha_fin: fin }, dias) {
  return {
    fecha_inicio_b: fechaLocalIso(sumarDias(desdeIso(inicio), -dias)),
    fecha_fin_b: fechaLocalIso(sumarDias(desdeIso(fin), -dias)),
  };
}

/** Los `parametros` de un widget con sus fechas al dia de `hoy`. Un widget sin
 * `rango_relativo` (todos los de antes) sale IGUAL, tal cual estaba guardado. */
export function parametrosEfectivos(parametros, hoy = new Date()) {
  const guardados = parametros || {};
  if (!esRangoRelativoVigente(guardados.rango_relativo)) return guardados;
  const rango = resolverRangoRelativo(guardados.rango_relativo, hoy);
  const efectivos = { ...guardados, ...rango };
  const desfase = Number(guardados.comparar_desfase_dias);
  if (Number.isInteger(desfase) && desfase > 0) Object.assign(efectivos, rangoDesfasado(rango, desfase));
  else if (guardados.comparar_anterior) Object.assign(efectivos, periodoAnterior(rango));
  return efectivos;
}

// --- como se ve el rango en una tarjeta ---------------------------------------------------------------------------------
// Nunca en ISO ni con flechas: "Ultimos 30 dias" si el widget es relativo, y si no "1 – 30 oct 2026". Las fechas exactas
// van en el tooltip. Son fechas de calendario (AAAA-MM-DD), asi que se formatean en UTC para que la zona no las mueva.

/** Texto de cada rango relativo EN UNA TARJETA (distinto del nombre corto del chip del editor). */
export const ETIQUETA_DE_RANGO_EN_TARJETA = {
  hoy: "Hoy",
  "7_dias": "Últimos 7 días",
  "30_dias": "Últimos 30 días",
  "90_dias": "Últimos 90 días",
  este_mes: "Este mes",
  mes_anterior: "Mes anterior",
  este_anio: "Este año",
};

function partesDeFecha(iso) {
  const encontrada = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!encontrada) return null;
  return { anio: Number(encontrada[1]), mes: Number(encontrada[2]) - 1, dia: Number(encontrada[3]) };
}

function nombreDeMes(mes, anio, estilo, locale) {
  return new Intl.DateTimeFormat(locale, { month: estilo, timeZone: "UTC" }).format(new Date(Date.UTC(anio, mes, 1)));
}

/** "30 oct 2026", "1 – 30 oct 2026", "28 sep – 30 oct 2026" o "28 dic 2025 – 3 ene 2026". "" si una fecha no es valida. */
export function formatoDeRango(inicio, fin, { locale = "es-MX" } = {}) {
  const a = partesDeFecha(inicio);
  const b = partesDeFecha(fin);
  if (!a || !b) return "";
  const mesA = nombreDeMes(a.mes, a.anio, "short", locale);
  const mesB = nombreDeMes(b.mes, b.anio, "short", locale);
  if (a.anio === b.anio && a.mes === b.mes) {
    return a.dia === b.dia ? `${a.dia} ${mesA} ${a.anio}` : `${a.dia} – ${b.dia} ${mesA} ${a.anio}`;
  }
  if (a.anio === b.anio) return `${a.dia} ${mesA} – ${b.dia} ${mesB} ${a.anio}`;
  return `${a.dia} ${mesA} ${a.anio} – ${b.dia} ${mesB} ${b.anio}`;
}

/** Como `formatoDeRango`, pero SIN el año cuando todo el rango cae en `anioDeReferencia` ("6 sep – 5 oct"): para leyendas chicas, donde el
 * año ya lo dice el rango principal. Si algun extremo es de otro año, lleva el año completo. Sin `anioDeReferencia` es `formatoDeRango`. */
export function formatoDeRangoCorto(inicio, fin, { locale = "es-MX", anioDeReferencia = null } = {}) {
  const a = partesDeFecha(inicio);
  const b = partesDeFecha(fin);
  if (!a || !b) return "";
  if (!anioDeReferencia || a.anio !== anioDeReferencia || b.anio !== anioDeReferencia) return formatoDeRango(inicio, fin, { locale });
  const mesA = nombreDeMes(a.mes, a.anio, "short", locale);
  const mesB = nombreDeMes(b.mes, b.anio, "short", locale);
  if (a.mes === b.mes) return a.dia === b.dia ? `${a.dia} ${mesA}` : `${a.dia} – ${b.dia} ${mesA}`;
  return `${a.dia} ${mesA} – ${b.dia} ${mesB}`;
}

/** "1 de octubre de 2026 al 30 de octubre de 2026": para el tooltip. */
export function formatoDeRangoLargo(inicio, fin, { locale = "es-MX", al = "al" } = {}) {
  const a = partesDeFecha(inicio);
  const b = partesDeFecha(fin);
  if (!a || !b) return "";
  const dar = (fecha) => new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(fecha.anio, fecha.mes, fecha.dia)));
  return `${dar(a)} ${al} ${dar(b)}`;
}

/** Lo que dice el pie de una tarjeta sobre su rango: `{ texto, detalle }`. `etiquetaRelativa` es el nombre traducido del
 * rango relativo del widget (o `null` si sus fechas son fijas); `detalle` trae las fechas exactas y, si compara, contra que. */
export function textoDeRango({ inicio, fin, inicioB, finB, etiquetaRelativa = null, locale = "es-MX", palabras = {} }) {
  const corto = formatoDeRango(inicio, fin, { locale });
  const detalleA = formatoDeRangoLargo(inicio, fin, { locale, al: palabras.al });
  const detalleB = inicioB && finB ? formatoDeRangoLargo(inicioB, finB, { locale, al: palabras.al }) : "";
  return {
    texto: etiquetaRelativa || corto,
    detalle: detalleB ? `${detalleA} (${palabras.vs || "vs."} ${detalleB})` : detalleA,
  };
}
