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

/**
 * La guia del proceso: en que paso va la orden, que sigue y quien lo hace.
 *
 * Es UNA sola fuente para la barra de pasos, el recuadro "Que sigue" y el aviso que
 * sale despues de cada accion. Quien puede hacer que lo dice el servidor
 * (`orden.actions`, calculado para ESTE usuario); aqui solo se traduce a una frase.
 * Cada frase lleva su clave de traduccion (`clave`), el texto en espanol por omision
 * (`texto`) y los numeros que se le insertan (`datos`, con `{nombre}` en el texto).
 */
// Cada paso lleva su color (`tono`, el mismo en la guia, la barra y "Que sigue") y una
// linea de POR QUE existe, para quien no esta acostumbrado a un sistema.
export const PASOS_DE_ORDEN = [
  { clave: "draft", etiqueta: "Armar", tono: "azul",
    porque: "Se anota qué se compra, a quién y cuánto cuesta." },
  { clave: "pending_authorization", etiqueta: "Autorizar", tono: "ambar",
    porque: "Gerencia revisa que el gasto quepa en el presupuesto." },
  { clave: "authorized", etiqueta: "Comprar", tono: "morado",
    porque: "La factura o el ticket es la prueba de lo que se pagó." },
  { clave: "purchased", etiqueta: "Recibir", tono: "agua",
    porque: "Se cuenta lo que llegó contra lo que se pidió." },
  { clave: "received", etiqueta: "Recibida", tono: "verde",
    porque: "El material ya está listo para la obra." },
];

/** Los pasos de Por comprar, antes de que exista una orden. */
export const PASOS_DE_POR_COMPRAR = [
  { clave: "request", etiqueta: "La obra pide", tono: "azul",
    porque: "El supervisor anota en su proyecto lo que le hace falta." },
  { clave: "review", etiqueta: "Revisar", tono: "ambar",
    porque: "Se ve si ya hay en el almacén, para no comprar dos veces." },
  { clave: "order", etiqueta: "Armar la orden", tono: "morado",
    porque: "Se junta lo que se compra a un mismo proveedor." },
  { clave: "follow", etiqueta: "Seguir en Órdenes", tono: "verde",
    porque: "Ahí se autoriza, se compra y se recibe." },
];

const INDICE_DEL_PASO = {
  draft: 0, rejected: 0, pending_authorization: 1, authorized: 2,
  purchased: 3, partially_received: 3, received: 4, closed: 4,
};

/** El paso actual (indice en PASOS_DE_ORDEN) y si la orden se desvio (rechazada o cancelada). */
export function pasoDeOrden(estado) {
  if (estado === "cancelled") return { indice: -1, desvio: "cancelled", terminada: true };
  return {
    indice: INDICE_DEL_PASO[estado] ?? 0,
    desvio: estado === "rejected" ? "rejected" : null,
    terminada: estado === "received" || estado === "closed",
  };
}

const frase = (clave, texto, tono = "info", datos = {}) => ({ clave: `order.next.${clave}`, texto, tono, datos });

/** Inserta los `datos` en un texto con `{nombre}`. */
export function conDatos(texto, datos = {}) {
  return String(texto || "").replace(/\{(\w+)\}/g, (todo, k) => (k in datos ? String(datos[k]) : todo));
}

/** Cuanto ha llegado de toda la orden, en piezas. */
export function avanceDeRecepcion(renglones) {
  let total = 0;
  let recibido = 0;
  for (const r of renglones || []) {
    // La maquinaria rentada no se recibe en el almacen: no cuenta como piezas.
    if (r.line_kind === "rental") continue;
    total += Number(r.quantity) || 0;
    recibido += Math.min(Number(r.quantity_received) || 0, Number(r.quantity) || 0);
  }
  return { total, recibido, faltan: Math.max(0, total - recibido) };
}

/**
 * Que sigue con la orden, dicho a quien la esta viendo. Devuelve la frase principal y,
 * si aplica, una secundaria (`extra`).
 */
export function queSigue(orden) {
  const a = orden?.actions || {};
  const estado = orden?.order_status;
  const renglones = orden?.lines || [];
  const comprobantes = orden?.vouchers || [];
  const factura = comprobantes.some((v) => COMPROBANTES_DE_COMPRA.includes(v.kind));
  const avance = avanceDeRecepcion(renglones);
  const conProyectos = renglones.some((r) => r.id_proyect);

  if (estado === "cancelled") {
    return { principal: frase("cancelled", "Esta orden se canceló y ya no sigue. Si todavía hace falta el material, arma una orden nueva desde Por comprar.", "neutro") };
  }
  if (estado === "draft" || estado === "rejected") {
    if (!a.edit) {
      return { principal: estado === "rejected"
        ? frase("rejected_others", "Se rechazó; quien la armó la está corrigiendo.", "neutro")
        : frase("draft_others", "Todavía se está armando; no se ha enviado a autorización.", "neutro") };
    }
    const sinCosto = renglones.filter((r) => r.unit_cost === null || r.unit_cost === undefined || r.unit_cost === "").length;
    let principal;
    if (renglones.length === 0) {
      principal = frase("draft_no_lines", "Agrega lo que vas a comprar (desde Por comprar o un renglón propio) para poder enviarla.", "alerta");
    } else if (sinCosto > 0) {
      principal = frase("draft_missing_costs", "Faltan costos en {n} renglón(es). Corrígela y captura el costo para poder enviarla.", "alerta", { n: sinCosto });
    } else if (estado === "rejected") {
      principal = frase("rejected_mine", "Se rechazó (el motivo está abajo). Corrígela y vuelve a enviarla, o cancélala si ya no aplica.", "alerta");
    } else {
      principal = frase("draft_ready", "Revisa proveedor, cantidades y costos, y envíala a autorización.");
    }
    return { principal, extra: comprobantes.length === 0
      ? frase("draft_quote", "Si tienes la cotización del proveedor, súbela: ayuda a quien autoriza.", "neutro") : null };
  }
  if (estado === "pending_authorization") {
    if (a.authorize) {
      return { principal: orden.exceeds_budget
        ? frase("authorize_over_budget", "Rebasa el presupuesto de un proyecto: si la autorizas, escribe el motivo. Si no, recházala.", "alerta")
        : frase("authorize", "Te toca: revisa monto, proveedor y renglones; autorízala o recházala.", "accion") };
    }
    if (a.reject) {
      return { principal: frase("authorize_own", "Tú la pediste, así que la autoriza otra persona. Si ya no aplica, puedes rechazarla.", "neutro") };
    }
    return { principal: frase("waiting_authorization", "Espera la autorización. Cuando se decida, te llega un aviso.", "neutro") };
  }
  if (estado === "authorized") {
    if (factura) {
      return { principal: a.purchase
        ? frase("register_purchase", "Te toca: ya tiene comprobante. Registra la compra con la fecha y la forma de pago.", "accion")
        : frase("purchase_others", "Ya tiene comprobante; falta registrar la compra.", "neutro") };
    }
    return { principal: a.attach_voucher
      ? frase("upload_invoice", "Autorizada: ya puedes comprar. Sube la factura (de preferencia el XML) o el ticket para registrar la compra.", "accion")
      : frase("buy_others", "Autorizada; falta comprarla y subir su factura o ticket.", "neutro") };
  }
  // Maquinaria rentada: no pasa por el almacen. Llega a la obra y se devuelve.
  const rentas = renglones.filter((r) => r.line_kind === "rental" && r.rental);
  const rentaPorLlegar = rentas.find((r) => r.rental.stage === "waiting_arrival");
  const rentaEnObra = rentas.find((r) => ["on_site", "overdue"].includes(r.rental.stage));
  const soloRentas = rentas.length > 0 && rentas.length === renglones.length;
  if (rentas.length > 0 && ["purchased", "partially_received", "received"].includes(estado)
      && (soloRentas || !a.receive)) {
    if (rentaPorLlegar) {
      return { principal: rentaPorLlegar.rental.actions?.arrive
        ? frase("rental_arrive", "Te toca: cuando la maquinaria llegue a la obra, marca \"Llegó a obra\". Desde ahí corre la renta.", "accion")
        : frase("rental_waiting", "Contratada. Quien lleva la obra marca \"Llegó a obra\" cuando llegue.", "neutro") };
    }
    if (rentaEnObra) {
      const r = rentaEnObra.rental;
      return { principal: r.stage === "overdue"
        ? frase("rental_overdue", "La renta ya venció: devuélvela al proveedor o pide una prórroga.", "alerta")
        : frase("rental_on_site", "En obra hasta el {fin}. Al terminar, marca \"Devuelta al proveedor\"; si se necesita más tiempo, pide prórroga.", "neutro", { fin: r.rental_end }) };
    }
  }
  if (estado === "closed" && rentas.length > 0) {
    return { principal: frase("rental_closed", "Todo llegó y la maquinaria rentada ya se devolvió. La orden está cerrada.", "ok") };
  }
  if (estado === "purchased" || estado === "partially_received") {
    const parcial = estado === "partially_received";
    const principal = a.receive
      ? (parcial
        ? frase("receive_rest", "Te toca: llegaron {recibido} de {total} piezas. Registra el resto cuando llegue.", "accion", avance)
        : frase("receive", "Te toca: cuando llegue el material, registra cuánto llegó de cada renglón.", "accion"))
      : (parcial
        ? frase("partial_others", "Llegaron {recibido} de {total} piezas; el resto se registra cuando llegue.", "neutro", avance)
        : frase("bought_others", "Comprada. Falta registrar la recepción cuando llegue el material.", "neutro"));
    const pago = comprobantes.some((v) => v.kind === "payment_proof");
    return { principal, extra: a.attach_voucher && !pago
      ? frase("payment_proof", "Si pagaste por separado, sube el comprobante de pago.", "neutro") : null };
  }
  if (estado === "received" || estado === "closed") {
    return { principal: conProyectos
      ? frase("received_projects", "Llegó todo. El encargado de cada obra ya puede marcar \"Material recibido, iniciar\" en su proyecto.", "ok")
      : frase("received", "Llegó todo. La orden está completa.", "ok") };
  }
  return { principal: frase("unknown", "Revisa el estado de la orden.", "neutro") };
}

/**
 * El aviso corto que sale despues de una accion: que paso y que sigue. `accion` es la
 * que se hizo; `orden` es la orden YA cambiada que devolvio el servidor.
 */
export function avisoTrasAccion(accion, orden) {
  const estado = orden?.order_status;
  const avance = avanceDeRecepcion(orden?.lines);
  const aviso = (clave, texto, datos = {}) => ({ clave: `order.done.${clave}`, texto, datos });
  switch (accion) {
    case "guardar":
      if (estado === "draft") return aviso("saved", "Borrador guardado. Envíalo a autorización cuando esté completo.");
      return avisoTrasAccion("enviar", orden);
    case "enviar":
      return estado === "authorized"
        ? aviso("auto_authorized", "Se autorizó sola por la política (monto bajo el límite). Ya puedes comprarla.")
        : aviso("submitted", "Enviada a autorización. Quien autoriza recibe el aviso.");
    case "autorizar":
      return aviso("authorized", "Autorizada. Ya se puede comprar.");
    case "rechazar":
      return aviso("rejected", "Rechazada. El motivo queda en la orden para corregirla.");
    case "cancelar":
      return aviso("cancelled", "Orden cancelada.");
    case "subir":
      return estado === "authorized" && (orden?.vouchers || []).some((v) => COMPROBANTES_DE_COMPRA.includes(v.kind))
        ? aviso("voucher_then_buy", "Comprobante guardado. Ahora registra la compra.")
        : aviso("voucher", "Comprobante guardado.");
    case "quitar":
      return aviso("voucher_removed", "Comprobante retirado.");
    case "comprar":
      return estado === "pending_authorization"
        ? aviso("reauthorization", "El comprobante sale más caro de lo autorizado: la orden volvió a autorización con el monto real.")
        : aviso("bought", "Compra registrada. Falta registrar la recepción cuando llegue el material.");
    case "recibir":
      return estado === "received" || estado === "closed"
        ? aviso("received", "Recepción completa: la orden quedó recibida.")
        : aviso("received_part", "Recepción registrada: faltan {faltan} piezas por llegar.", avance);
    default:
      return null;
  }
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
