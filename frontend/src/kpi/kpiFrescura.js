// Cuando se calcularon por ultima vez los datos de un widget, y si ya van atrasados. Puro y sin React -- ver
// kpiFrescura.test.js.
//
// El servidor manda `computed_at` en cada rango de `/kpi_snapshot/query`: la ultima escritura de las filas del
// rango, como fecha y hora SIN zona (la hora de la base al escribirla). Se lee como hora de pared del negocio, igual
// que el resto de las fechas sin zona (`formatearFechaHora`). Es por fila, no por corrida del job: un KPI que solo
// escribe cuando hay un evento puede tener un `computed_at` viejo con el job sano.
import { ZONA_DE_NEGOCIO, formatearFechaHora } from "../utils/fechas.js";

export const UN_DIA_MS = 24 * 60 * 60 * 1000;

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
// calculo de TODOS los KPIs (`avisoDeDatosAtrasados`).
export function frescuraDeWidget(snapshots) {
  const computedAt = computedAtDeSnapshots(snapshots);
  if (!computedAt) return null;
  const fecha = formatearFechaHora(computedAt);
  return fecha ? { fecha } : null;
}

// El aviso global del tablero: `ultimoCalculo` es el `max(computed_at)` de `kpi_snapshot` que manda
// `GET /kpi_definition/` (de los KPIs de serie que ve la persona) y `ahora` el reloj del servidor, ambos con zona.
// Se restan entre si, sin depender del reloj del navegador; sin `ahora` valido se usa el del navegador.
// `null` si no hay ultimo calculo (nada que avisar: cada tarjeta dice "No calculado") o si va al dia; si no, la fecha
// formateada. Justo 24 h no es atraso.
export function avisoDeDatosAtrasados(ultimoCalculo, ahora, zona = ZONA_DE_NEGOCIO) {
  const ultimo = paredDeTexto(ultimoCalculo, zona);
  if (ultimo === null) return null;
  const ahoraPared = paredDeTexto(ahora, zona) ?? paredDeInstante(new Date(), zona);
  if (ahoraPared - ultimo <= UN_DIA_MS) return null;
  const fecha = formatearFechaHora(ultimoCalculo);
  return fecha ? { fecha } : null;
}
