// Fechas con zona horaria definida: la del negocio (UTC-6, America/Mexico_City).
//
// La convencion completa esta en backend/app/utils/tiempo.py:
//  - Las fechas de auditoria (creacion, actualizacion) llegan en UTC con "Z".
//    Aqui se convierten a la zona del negocio para mostrarlas.
//  - Las fechas de negocio (incident_date, cierres) llegan sin zona y YA son la
//    hora de pared del cliente: se muestran tal cual, sin pasar por la zona del
//    navegador. `new Date("2026-10-14T14:33:12")` las tomaba por hora local del
//    equipo, asi que quien abriera el sistema desde otra zona las veia movidas.
//
// Una sola zona, y no la del navegador: dos personas del mismo cliente ven la
// misma hora para el mismo registro.

export const ZONA_DE_NEGOCIO = import.meta.env?.VITE_APP_TIMEZONE || "America/Mexico_City";

const CON_ZONA = /(Z|[+-]\d{2}:?\d{2})$/i;
const FECHA_HORA = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/;

const SOLO_FECHA = { dateStyle: "medium" };
const FECHA_Y_HORA = { dateStyle: "medium", timeStyle: "short" };

// Devuelve "" si el texto no es una fecha, para que quien llama caiga a su
// propio formato en lugar de mostrar "Invalid Date".
export function formatearFechaHora(valor, locale = "es-MX") {
  if (typeof valor !== "string") return "";
  const texto = valor.trim();
  const partes = FECHA_HORA.exec(texto);
  if (!partes) return "";

  if (CON_ZONA.test(texto)) {
    // Los microsegundos de Python (.049979) no los acepta todo navegador.
    const instante = new Date(texto.replace(/(\.\d{3})\d+/, "$1"));
    if (Number.isNaN(instante.getTime())) return "";
    return new Intl.DateTimeFormat(locale, { ...FECHA_Y_HORA, timeZone: ZONA_DE_NEGOCIO }).format(instante);
  }

  const [, anio, mes, dia, hora, minuto, segundo] = partes;
  const horaDePared = Date.UTC(
    Number(anio), Number(mes) - 1, Number(dia),
    Number(hora || 0), Number(minuto || 0), Number(segundo || 0),
  );
  const fecha = new Date(horaDePared);
  if (Number.isNaN(fecha.getTime())) return "";
  // Medianoche sin zona es una fecha sin hora (las columnas de tipo fecha viajan asi).
  const sinHora = hora === undefined || (Number(hora) === 0 && Number(minuto) === 0 && !Number(segundo || 0));
  // timeZone "UTC" porque la fecha se armo con los componentes tal cual: es la
  // forma de imprimir esa hora de pared sin que el navegador la mueva.
  return new Intl.DateTimeFormat(locale, { ...(sinHora ? SOLO_FECHA : FECHA_Y_HORA), timeZone: "UTC" }).format(fecha);
}
