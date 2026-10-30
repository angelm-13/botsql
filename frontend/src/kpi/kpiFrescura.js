// Cuando se calcularon por ultima vez los datos de un widget, y si ya van atrasados. Puro y sin React -- ver
// kpiFrescura.test.js.
//
// El servidor manda `computed_at` en cada rango de `/kpi_snapshot/query`: la ultima escritura de las filas del
// rango, como fecha y hora SIN zona (la hora de la base al escribirla). Se lee como hora de pared del negocio, igual
// que el resto de las fechas sin zona (`formatearFechaHora`). Es por fila, no por corrida del job: un KPI que solo
// escribe cuando hay un evento puede tener un `computed_at` viejo con el job sano.
import { ZONA_DE_NEGOCIO, formatearFechaHora } from "../utils/fechas.js";

export const UN_DIA_MS = 24 * 60 * 60 * 1000;

// Pasadas estas horas sin un calculo, los datos se consideran atrasados: es la UNICA constante del umbral, la usan
// la linea global del tablero y el chip de cada tarjeta. 36 y no 24 para no avisar por la corrida de una sola noche.
export const UMBRAL_DATOS_ATRASADOS_HORAS = 36;
export const UMBRAL_DATOS_ATRASADOS_MS = UMBRAL_DATOS_ATRASADOS_HORAS * 60 * 60 * 1000;
// "Actualizado ahora" mientras la ultima actualizacion de esta sesion tenga menos de esto.
export const RECIENTE_MS = 10 * 60 * 1000;

const CON_ZONA = /(Z|[+-]\d{2}:?\d{2})$/i;
const COMPONENTES = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/;

// La hora de pared de un instante en la zona del negocio, como milisegundos "UTC" de esos componentes: sirve para
// restar dos horas de pared sin que el navegador las mueva.
export function paredDeInstante(instante, zona = ZONA_DE_NEGOCIO) {
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: zona, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    }).formatToParts(instante).map((parte) => [parte.type, parte.value]),
  );
  return Date.UTC(Number(partes.year), Number(partes.month) - 1, Number(partes.day), Number(partes.hour), Number(partes.minute), Number(partes.second));
}

// `null` si el texto no es una fecha con hora.
export function paredDeTexto(texto, zona = ZONA_DE_NEGOCIO) {
  if (typeof texto !== "string") return null;
  const limpio = texto.trim();
  if (CON_ZONA.test(limpio)) {
    const instante = new Date(limpio.replace(/(\.\d{3})\d+/, "$1"));
    return Number.isNaN(instante.getTime()) ? null : paredDeInstante(instante, zona);
  }
  const partes = COMPONENTES.exec(limpio);
  if (!partes) return null;
  const [, anio, mes, dia, hora, minuto, segundo] = partes;
  return Date.UTC(Number(anio), Number(mes) - 1, Number(dia), Number(hora), Number(minuto), Number(segundo || 0));
}

// El `computed_at` mas reciente de los rangos A de los snapshots de un widget (varios KPIs = varias respuestas).
export function computedAtDeSnapshots(snapshots) {
  const marcas = (Array.isArray(snapshots) ? snapshots : [snapshots])
    .map((snapshot) => snapshot?.rango_a?.computed_at)
    .filter((marca) => typeof marca === "string" && paredDeTexto(marca) !== null);
  if (marcas.length === 0) return null;
  return marcas.reduce((mayor, marca) => (paredDeTexto(marca) > paredDeTexto(mayor) ? marca : mayor));
}

// `null` si no hay `computed_at`; si no, el texto de la fecha. Es informativo y neutro: un KPI que solo escribe cuando
// hay un evento puede tener una fecha vieja con el job sano, asi que el atraso no se juzga aqui sino con el ultimo
// calculo de TODOS los KPIs (`estadoGlobalDeDatos`) y el chip de cada tarjeta (`chipDeTarjeta`).
export function frescuraDeWidget(snapshots) {
  const computedAt = computedAtDeSnapshots(snapshots);
  if (!computedAt) return null;
  const fecha = formatearFechaHora(computedAt);
  return fecha ? { fecha } : null;
}

const ES_DE_ZONA = "UTC";

function ahoraDePared(ahora, zona) {
  return paredDeTexto(ahora, zona) ?? paredDeInstante(new Date(), zona);
}

// El calculo mas reciente entre el que manda el servidor y lo que esta sesion recalculo (`recalculados`: id -> fecha con
// zona). Un indicador sin eventos no escribe filas, asi que recalcularlo no mueve el del servidor.
export function ultimoCalculoEfectivo(ultimoCalculo, recalculados = {}, zona = ZONA_DE_NEGOCIO) {
  const candidatos = [ultimoCalculo, ...Object.values(recalculados || {})].filter((texto) => paredDeTexto(texto, zona) !== null);
  if (candidatos.length === 0) return null;
  return candidatos.reduce((mayor, texto) => (paredDeTexto(texto, zona) > paredDeTexto(mayor, zona) ? texto : mayor));
}

/** "28 oct" (con el anio si no es el actual). `null` si el texto no es fecha. */
export function fechaCorta(texto, ahora, { zona = ZONA_DE_NEGOCIO, locale = "es-MX" } = {}) {
  const pared = paredDeTexto(texto, zona);
  if (pared === null) return null;
  const actual = typeof ahora === "number" ? ahora : ahoraDePared(ahora, zona);
  const mismoAnio = new Date(pared).getUTCFullYear() === new Date(actual).getUTCFullYear();
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", ...(mismoAnio ? {} : { year: "numeric" }), timeZone: ES_DE_ZONA }).format(new Date(pared));
}

/** "hoy 1:00 a.m.", "ayer 8:00 p.m." o "28 oct 1:00 a.m." (con el anio si no es el actual). `null` si el texto no es fecha. */
export function etiquetaDeCuando(texto, ahora, { zona = ZONA_DE_NEGOCIO, locale = "es-MX", palabras = {} } = {}) {
  const pared = paredDeTexto(texto, zona);
  if (pared === null) return null;
  const actual = ahoraDePared(ahora, zona);
  const hora = new Intl.DateTimeFormat(locale, { hour: "numeric", minute: "2-digit", hour12: true, timeZone: ES_DE_ZONA }).format(new Date(pared));
  const diferenciaDeDias = Math.floor(actual / UN_DIA_MS) - Math.floor(pared / UN_DIA_MS);
  if (diferenciaDeDias === 0) return `${palabras.hoy || "hoy"} ${hora}`;
  if (diferenciaDeDias === 1) return `${palabras.ayer || "ayer"} ${hora}`;
  return `${fechaCorta(texto, actual, { zona, locale })} ${hora}`;
}

/** La linea global del tablero. `ultimoCalculo` es el `max(computed_at)` de `GET /kpi_definition/` (todos los
 * indicadores de serie que ve la persona), no el de una tarjeta: con UN solo indicador reciente la linea sigue "al dia"
 * aunque otro, que solo escribe cuando hay eventos, tenga una fecha vieja; eso lo dice el chip de su tarjeta.
 * `null` sin ultimo calculo; si no, `{ tipo: "al_dia" | "atrasado", cuando, dias }` (`dias` solo si esta atrasado). */
export function estadoGlobalDeDatos(ultimoCalculo, ahora, { zona = ZONA_DE_NEGOCIO, locale = "es-MX", palabras = {} } = {}) {
  const ultimo = paredDeTexto(ultimoCalculo, zona);
  if (ultimo === null) return null;
  const edad = ahoraDePared(ahora, zona) - ultimo;
  const cuando = etiquetaDeCuando(ultimoCalculo, ahora, { zona, locale, palabras });
  if (edad <= UMBRAL_DATOS_ATRASADOS_MS) return { tipo: "al_dia", cuando };
  return { tipo: "atrasado", cuando, dias: Math.max(1, Math.floor(edad / UN_DIA_MS)) };
}

/** El chip de una tarjeta, o `null` si no hace falta. `recalculadoEn`: cuando esta sesion dejo al dia TODOS sus
 * indicadores (o `null`). Con eso es `{ tipo: "al_dia", reciente, cuando }`; si no, solo pasadas las 36 h
 * `{ tipo: "ultimo_dato", cuando }` con la fecha corta de su ultimo calculo. */
export function chipDeTarjeta({ computedAt, recalculadoEn, ahora, ahoraNavegador = new Date(), zona = ZONA_DE_NEGOCIO, locale = "es-MX", palabras = {} }) {
  if (recalculadoEn && paredDeTexto(recalculadoEn, zona) !== null) {
    const reciente = paredDeInstante(ahoraNavegador, zona) - paredDeTexto(recalculadoEn, zona) < RECIENTE_MS;
    return { tipo: "al_dia", reciente, cuando: etiquetaDeCuando(recalculadoEn, ahoraNavegador.toISOString(), { zona, locale, palabras }) };
  }
  const ultimo = paredDeTexto(computedAt, zona);
  if (ultimo === null) return null;
  if (ahoraDePared(ahora, zona) - ultimo <= UMBRAL_DATOS_ATRASADOS_MS) return null;
  return { tipo: "ultimo_dato", cuando: fechaCorta(computedAt, ahoraDePared(ahora, zona), { zona, locale }) };
}
