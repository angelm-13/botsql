import test from "node:test";
import assert from "node:assert/strict";
import {
  agruparPorProyecto, avisoTrasAccion, avanceDeRecepcion, conDatos, esXml, excedeLoAutorizado,
  estadoDeOrden, PASOS_DE_ORDEN, PASOS_DE_POR_COMPRAR, pasoDeOrden, queSigue, requiereReferencia,
  totalDeRenglones,
} from "./ordenDeCompra.js";

const sigue = (orden) => queSigue(orden).principal.clave.replace("order.next.", "");

test("cada paso de la guia trae su color y su porque", () => {
  const tonos = ["azul", "ambar", "morado", "agua", "verde"];
  for (const p of [...PASOS_DE_ORDEN, ...PASOS_DE_POR_COMPRAR]) {
    assert.ok(tonos.includes(p.tono), `${p.clave} sin tono conocido`);
    assert.ok(p.porque && p.porque.length > 10, `${p.clave} sin porque`);
  }
});

test("la barra de pasos ubica cada estado y marca los desvios", () => {
  assert.deepEqual(pasoDeOrden("draft"), { indice: 0, desvio: null, terminada: false });
  assert.deepEqual(pasoDeOrden("rejected"), { indice: 0, desvio: "rejected", terminada: false });
  assert.equal(pasoDeOrden("partially_received").indice, 3);
  assert.equal(pasoDeOrden("closed").terminada, true);
  assert.deepEqual(pasoDeOrden("cancelled"), { indice: -1, desvio: "cancelled", terminada: true });
});

test("en borrador dice que falta antes de poder enviarla", () => {
  const actions = { edit: true };
  assert.equal(sigue({ order_status: "draft", actions, lines: [] }), "draft_no_lines");
  const sinCosto = queSigue({ order_status: "draft", actions,
    lines: [{ quantity: 2, unit_cost: null }, { quantity: 1, unit_cost: "" }, { quantity: 1, unit_cost: 5 }] });
  assert.equal(sinCosto.principal.clave, "order.next.draft_missing_costs");
  assert.equal(sinCosto.principal.datos.n, 2);
  assert.equal(sigue({ order_status: "draft", actions, lines: [{ quantity: 1, unit_cost: 5 }] }), "draft_ready");
  // Quien no la arma solo se entera de en que va.
  assert.equal(sigue({ order_status: "draft", actions: {}, lines: [] }), "draft_others");
});

test("por autorizar le habla distinto a quien autoriza, a quien la pidio y a los demas", () => {
  const base = { order_status: "pending_authorization" };
  assert.equal(sigue({ ...base, actions: { authorize: true, reject: true } }), "authorize");
  assert.equal(sigue({ ...base, exceeds_budget: true, actions: { authorize: true, reject: true } }), "authorize_over_budget");
  assert.equal(sigue({ ...base, actions: { authorize: false, reject: true } }), "authorize_own");
  assert.equal(sigue({ ...base, actions: {} }), "waiting_authorization");
});

test("autorizada: primero el comprobante, luego registrar la compra", () => {
  const base = { order_status: "authorized" };
  assert.equal(sigue({ ...base, actions: { attach_voucher: true }, vouchers: [] }), "upload_invoice");
  assert.equal(sigue({ ...base, actions: { attach_voucher: true }, vouchers: [{ kind: "quote" }] }), "upload_invoice");
  assert.equal(sigue({ ...base, actions: { purchase: true }, vouchers: [{ kind: "invoice" }] }), "register_purchase");
  assert.equal(sigue({ ...base, actions: {}, vouchers: [] }), "buy_others");
});

test("comprada: el almacen registra lo que llega, con el avance", () => {
  const lines = [{ quantity: 100, quantity_received: 60 }, { quantity: 10, quantity_received: 0 }];
  assert.equal(sigue({ order_status: "purchased", actions: { receive: true }, lines }), "receive");
  const parcial = queSigue({ order_status: "partially_received", actions: { receive: true }, lines });
  assert.equal(parcial.principal.clave, "order.next.receive_rest");
  assert.equal(conDatos(parcial.principal.texto, parcial.principal.datos),
    "Te toca: llegaron 60 de 110 piezas. Registra el resto cuando llegue.");
  assert.equal(sigue({ order_status: "purchased", actions: {}, lines }), "bought_others");
});

test("recibida con proyectos le recuerda al encargado de la obra que puede iniciar", () => {
  assert.equal(sigue({ order_status: "received", lines: [{ id_proyect: 3 }] }), "received_projects");
  assert.equal(sigue({ order_status: "received", lines: [{ id_proyect: null }] }), "received");
});

test("una orden de renta no se recibe en el almacen: llega a obra y se devuelve", () => {
  const renta = (stage, actions = {}) => ({
    line_kind: "rental", quantity: 1, quantity_received: 0,
    rental: { stage, actions, rental_end: "2026-11-20" },
  });
  assert.equal(sigue({ order_status: "purchased", actions: {}, lines: [renta("waiting_arrival", { arrive: true })] }), "rental_arrive");
  assert.equal(sigue({ order_status: "purchased", actions: {}, lines: [renta("waiting_arrival")] }), "rental_waiting");
  const enObra = queSigue({ order_status: "received", actions: {}, lines: [renta("on_site")] });
  assert.equal(conDatos(enObra.principal.texto, enObra.principal.datos).includes("2026-11-20"), true);
  assert.equal(sigue({ order_status: "received", actions: {}, lines: [renta("overdue")] }), "rental_overdue");
  assert.equal(sigue({ order_status: "closed", actions: {}, lines: [renta("returned")] }), "rental_closed");
  // Con material por recibir, primero lo del almacen.
  assert.equal(sigue({ order_status: "purchased", actions: { receive: true },
    lines: [renta("waiting_arrival"), { quantity: 5, quantity_received: 0 }] }), "receive");
});

test("el avance de recepcion no cuenta de mas lo recibido de mas", () => {
  assert.deepEqual(avanceDeRecepcion([{ quantity: 5, quantity_received: 9 }, { quantity: 5, quantity_received: 1 }]),
    { total: 10, recibido: 6, faltan: 4 });
});

test("el aviso tras enviar distingue la autorizacion automatica por politica", () => {
  assert.equal(avisoTrasAccion("enviar", { order_status: "authorized" }).clave, "order.done.auto_authorized");
  assert.equal(avisoTrasAccion("enviar", { order_status: "pending_authorization" }).clave, "order.done.submitted");
  assert.equal(avisoTrasAccion("guardar", { order_status: "draft" }).clave, "order.done.saved");
  assert.equal(avisoTrasAccion("guardar", { order_status: "pending_authorization" }).clave, "order.done.submitted");
  const parcial = avisoTrasAccion("recibir", { order_status: "partially_received",
    lines: [{ quantity: 10, quantity_received: 4 }] });
  assert.equal(conDatos(parcial.texto, parcial.datos), "Recepción registrada: faltan 6 piezas por llegar.");
  assert.equal(avisoTrasAccion("comprar", { order_status: "pending_authorization" }).clave, "order.done.reauthorization");
  assert.equal(avisoTrasAccion("otra", {}), null);
});

test("suma cantidad por costo sin errores de coma flotante", () => {
  assert.equal(totalDeRenglones([
    { quantity: 3, unit_cost: "0.1" }, { quantity: 3, unit_cost: "0.2" },
  ]), 0.9);
  assert.equal(totalDeRenglones([
    { quantity: 10, unit_cost: 400 }, { quantity: 40, unit_cost: 150 },
  ]), 10000);
});

test("un total con un costo que falta no es un total", () => {
  assert.equal(totalDeRenglones([
    { quantity: 10, unit_cost: 400 }, { quantity: 40, unit_cost: "" },
  ]), null);
  assert.equal(totalDeRenglones([{ quantity: 1, unit_cost: null }]), null);
});

test("avisa cuando lo comprado se pasa de lo autorizado mas la tolerancia", () => {
  assert.equal(excedeLoAutorizado(10000, 10900, 10), false);
  assert.equal(excedeLoAutorizado(10000, 11000, 10), false);
  assert.equal(excedeLoAutorizado(10000, 11000.01, 10), true);
  assert.equal(excedeLoAutorizado(10000, 8000, 10), false);
  assert.equal(excedeLoAutorizado(null, 8000, 10), false);
});

test("transferencia, cheque y tarjeta piden su referencia; efectivo no", () => {
  assert.deepEqual(
    ["transfer", "check", "card", "cash", "credit", "other"].filter(requiereReferencia),
    ["transfer", "check", "card"]);
});

test("reconoce el XML por su extension", () => {
  assert.equal(esXml("factura.XML"), true);
  assert.equal(esXml("factura.pdf"), false);
  assert.equal(esXml(""), false);
});

test("un estado que no conoce no rompe la pantalla", () => {
  assert.equal(estadoDeOrden("pending_authorization").etiqueta, "Por autorizar");
  assert.equal(estadoDeOrden("inventado").etiqueta, "inventado");
});

test("agrupa los renglones por proyecto y deja los sueltos al final", () => {
  const grupos = agruparPorProyecto([
    { id_proyect: null, description: "guantes" },
    { id_proyect: 20, description: "cemento", project: { folio: "PRJ-20" } },
    { id_proyect: 10, description: "soldadura", project: { folio: "PRJ-10" } },
    { id_proyect: 20, description: "arena", project: { folio: "PRJ-20" } },
  ]);
  assert.deepEqual(grupos.map((g) => g.renglones.map((r) => r.description)),
    [["soldadura"], ["cemento", "arena"], ["guantes"]]);
});
