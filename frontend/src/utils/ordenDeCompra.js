/**
 * Lo que la pantalla de ordenes de compra necesita saber sin preguntarle al servidor:
 * como se llama cada estado, cuanto suma una orden y si un monto ya se paso.
 *
 * Es ayuda para pintar y para avisar al instante; la regla que cuenta -la que de
 * verdad impide comprar mal- vive en el backend (`purchase_order_service.py`).
 */

export const ESTADOS = {
  draft: { clase: "borrador", etiqueta: "Borrador" },
  pending_authorization: { clase: "por-autorizar", etiqueta: "Por autorizar" },
  authorized: { clase: "autorizada", etiqueta: "Autorizada" },
  rejected: { clase: "rechazada", etiqueta: "Rechazada" },
  purchased: { clase: "comprada", etiqueta: "Comprada" },
  partially_received: { clase: "recibida", etiqueta: "Recibida en parte" },
  received: { clase: "recibida", etiqueta: "Recibida" },
  closed: { clase: "cerrada", etiqueta: "Cerrada" },
  cancelled: { clase: "cancelada", etiqueta: "Cancelada" },
};

export const TIPOS_DE_COMPROBANTE = [
  { clave: "invoice", etiqueta: "Factura" },
  { clave: "receipt", etiqueta: "Ticket o nota" },
  { clave: "quote", etiqueta: "Cotización" },
  { clave: "payment_proof", etiqueta: "Comprobante de pago" },
];

// Solo estos dos justifican el dinero: uno por orden, y de ellos salen el folio y el monto.
export const COMPROBANTES_DE_COMPRA = ["invoice", "receipt"];

export const METODOS_DE_PAGO = [
  { clave: "transfer", etiqueta: "Transferencia" },
  { clave: "cash", etiqueta: "Efectivo" },
  { clave: "card", etiqueta: "Tarjeta" },
  { clave: "check", etiqueta: "Cheque" },
  { clave: "credit", etiqueta: "Crédito del proveedor" },
  { clave: "other", etiqueta: "Otro" },
];

// Lo que deja una clave que se puede contrastar con el estado de cuenta.
const CON_REFERENCIA = ["transfer", "check", "card"];

export const requiereReferencia = (metodo) => CON_REFERENCIA.includes(metodo);

export const esXml = (nombreDeArchivo) => /\.xml$/i.test(String(nombreDeArchivo || "").trim());

export function estadoDeOrden(estado) {
  return ESTADOS[estado] || { clase: "borrador", etiqueta: String(estado || "") };
}

export function dinero(valor, moneda = "MXN") {
  if (valor === null || valor === undefined || valor === "") return "—";
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: moneda }).format(numero);
}

/**
 * Cantidad por costo, de todos los renglones. Vacio si a alguno le falta el costo:
 * un total con huecos parece un total y no lo es.
 */
export function totalDeRenglones(renglones) {
  let centavos = 0;
  for (const r of renglones || []) {
    const costo = Number(r.unit_cost);
    const cantidad = Number(r.quantity);
    if (r.unit_cost === "" || r.unit_cost === null || r.unit_cost === undefined
        || !Number.isFinite(costo) || !Number.isFinite(cantidad)) {
      return null;
    }
    centavos += Math.round(cantidad * costo * 100);
  }
  return centavos / 100;
}

/** Si lo comprado ya se paso de lo autorizado mas la tolerancia, en porcentaje. */
export function excedeLoAutorizado(autorizado, real, porcentaje) {
  const base = Number(autorizado);
  const monto = Number(real);
  if (!Number.isFinite(base) || !Number.isFinite(monto) || base <= 0) return false;
  const tope = Math.round(base * (1 + Number(porcentaje || 0) / 100) * 100) / 100;
  return monto > tope;
}

/** Los renglones de una orden agrupados por proyecto; sin proyecto, al final y juntos. */
export function agruparPorProyecto(renglones) {
  const grupos = new Map();
  for (const r of renglones || []) {
    const llave = r.id_proyect ? String(r.id_proyect) : "";
    if (!grupos.has(llave)) grupos.set(llave, { proyecto: r.project || null, renglones: [] });
    grupos.get(llave).renglones.push(r);
  }
  return [...grupos.entries()]
    .sort(([a], [b]) => (a === "" ? 1 : b === "" ? -1 : Number(a) - Number(b)))
    .map(([, grupo]) => grupo);
}
