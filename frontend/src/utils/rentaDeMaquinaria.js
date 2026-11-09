// Renta de maquinaria: lo que la pantalla necesita saber de una renta.
//
// La regla vive en el servidor (`purchase_order_service.py`): aqui solo se repite el
// calculo de periodos para mostrar el costo mientras Compras escribe la tarifa (el
// servidor lo vuelve a calcular y es el que cuenta) y se traduce la etapa a texto.

export const UNIDADES_DE_TARIFA = ["day", "week", "month"];
const DIAS_POR_UNIDAD = { day: 1, week: 7, month: 30 };
// Igual que RENTAL_DUE_SOON_DAYS en el servidor.
export const DIAS_DE_AVISO = 2;

function aFecha(texto) {
  if (!texto) return null;
  const [a, m, d] = String(texto).slice(0, 10).split("-").map(Number);
  if (!a || !m || !d) return null;
  return Date.UTC(a, m - 1, d);
}

/** Dias del periodo, contando el de inicio y el de fin (del 1 al 3 son 3). */
export function diasDelPeriodo(inicio, fin) {
  const a = aFecha(inicio);
  const b = aFecha(fin);
  if (a === null || b === null || b < a) return null;
  return Math.round((b - a) / 86400000) + 1;
}

/** Cuantos dias, semanas o meses se cobran. Semana y mes redondean hacia arriba. */
export function periodosDeRenta(inicio, fin, unidad = "day") {
  const dias = diasDelPeriodo(inicio, fin);
  const largo = DIAS_POR_UNIDAD[unidad];
  if (dias === null || !largo) return null;
  return Math.max(1, Math.ceil(dias / largo));
}

/** Costo de UNA unidad por todo el periodo (tarifa x periodos), o null si falta algo. */
export function costoDeRenta(tarifa, inicio, fin, unidad = "day") {
  const periodos = periodosDeRenta(inicio, fin, unidad);
  const numero = Number(tarifa);
  if (periodos === null || tarifa === "" || tarifa === null || tarifa === undefined
      || !Number.isFinite(numero) || numero <= 0) return null;
  return Math.round(numero * periodos * 10000) / 10000;
}

/** Clave de texto y clase de color de la etapa de una renta. */
export function etapaDeRenta(renta) {
  if (!renta) return null;
  const etapa = renta.stage;
  if (etapa === "on_site" && renta.days_left !== null && renta.days_left !== undefined
      && renta.days_left <= DIAS_DE_AVISO) {
    return { clave: "rental.stage.due_soon", clase: "por-vencer" };
  }
  const clases = {
    ordering: "pedida", waiting_arrival: "en-camino", on_site: "en-obra",
    overdue: "vencida", returned: "devuelta", cancelled: "cancelada",
  };
  return { clave: `rental.stage.${etapa}`, clase: clases[etapa] || "pedida" };
}
