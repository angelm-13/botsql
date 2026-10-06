import { Fragment, useCallback, useRef, useState } from "react";
import PropTypes from "prop-types";
import { AlertTriangle, ExternalLink, Paperclip } from "lucide-react";
import {
  authorizePurchaseOrder, buyPurchaseOrder, cancelPurchaseOrder, downloadPurchaseVoucher,
  receivePurchaseOrder, rejectPurchaseOrder, removePurchaseVoucher, submitPurchaseOrder,
  uploadPurchaseVoucher,
} from "../api";
import {
  COMPROBANTES_DE_COMPRA, METODOS_DE_PAGO, TIPOS_DE_COMPROBANTE, agruparPorProyecto, dinero,
  esXml, estadoDeOrden, excedeLoAutorizado, requiereReferencia,
} from "../utils/ordenDeCompra";
import { useI18n } from "../i18n";
import "../styles/ordenes-de-compra.css";

const EVENTOS = {
  created: "Orden creada",
  updated: "Se editó la orden",
  submitted: "Enviada a autorización",
  resubmitted: "Reenviada tras corregirla",
  auto_authorized: "Autorizada por la política (monto bajo el límite)",
  authorized: "Autorizada",
  rejected: "Rechazada",
  reopened: "Reabierta para corregirla",
  voucher_added: "Comprobante agregado",
  voucher_removed: "Comprobante retirado",
  reauthorization_required: "Volvió a autorización: el comprobante sale más caro de lo autorizado",
  purchased: "Comprada",
  partially_received: "Recibida en parte",
  received: "Recibida completa",
  cancelled: "Cancelada",
};

// Desde aqui ya hay material comprado: la tabla de renglones muestra cuanto ha llegado.
const ESTADOS_CON_RECEPCION = ["purchased", "partially_received", "received"];

// Que comprobantes se aceptan segun el estado: la factura solo despues de autorizar.
const TIPOS_POR_ESTADO = {
  draft: ["quote"],
  pending_authorization: ["quote"],
  rejected: ["quote"],
  authorized: ["invoice", "receipt", "quote", "payment_proof"],
  purchased: ["payment_proof"],
  partially_received: ["payment_proof"],
  received: ["payment_proof"],
};

function fecha(iso) {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-MX");
}

function fechaHora(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("es-MX");
}

function hoyISO() {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

function quien(nombre, id) {
  return nombre || (id ? `#${id}` : "");
}

/**
 * Una orden de compra completa: lo cotizado, lo autorizado y lo comprado; los renglones
 * por proyecto; los comprobantes; y la bitacora de quien hizo que.
 *
 * Los botones salen de `orden.actions`, que el servidor calcula para ESTE usuario: es
 * ayuda para no ofrecer lo que no puede hacer, no la seguridad -cada accion se vuelve a
 * comprobar al ejecutarla-.
 */
export default function OrdenDeCompraDetalle({ orden, politica, onCambio, onEditar }) {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  // Una accion que pide un motivo: cual y que se lleva escrito.
  const [motivo, setMotivo] = useState({ accion: "", nota: "", id: null });
  const [comprobante, setComprobante] = useState({
    kind: "", file: null, folio: "", amount: "", issue_date: hoyISO(),
  });
  const [compra, setCompra] = useState({
    purchase_date: hoyISO(), payment_method: "transfer", payment_reference: "", paid_externally: false,
  });
  // Lo que llego en ESTA recepcion, por renglon (id -> texto), y una nota opcional.
  const [recepcion, setRecepcion] = useState({ cantidades: {}, nota: "" });

  const decirError = useCallback((e, porOmision) => setError(
    e?.payload?.error_key
      ? traducir.current(e.payload.error_key, porOmision)
      : traducir.current("errors.request_failed", porOmision)), []);

  const acciones = orden.actions || {};
  const estado = estadoDeOrden(orden.order_status);
  const moneda = orden.currency || "MXN";
  const tiposPermitidos = (TIPOS_POR_ESTADO[orden.order_status] || [])
    .filter((k) => k !== "invoice" && k !== "receipt"
      || !(orden.vouchers || []).some((v) => COMPROBANTES_DE_COMPRA.includes(v.kind)));
  const tipoElegido = comprobante.kind && tiposPermitidos.includes(comprobante.kind)
    ? comprobante.kind : (tiposPermitidos[0] || "");
  const conXml = esXml(comprobante.file?.name) && COMPROBANTES_DE_COMPRA.includes(tipoElegido);
  const pideDatos = COMPROBANTES_DE_COMPRA.includes(tipoElegido) && !conXml;
  const factura = (orden.vouchers || []).find((v) => COMPROBANTES_DE_COMPRA.includes(v.kind));
  const pasaDeLoAutorizado = factura && orden.authorized_total
    && excedeLoAutorizado(orden.authorized_total, factura.amount, politica?.overrun_percent);
  const volvioPorExceso = orden.order_status === "pending_authorization"
    && (orden.events || []).some((e) => e.event_type === "reauthorization_required");

  async function ejecutar(accion, mensajeError, despues) {
    setOcupado(true);
    setError("");
    setAviso("");
    try {
      const respuesta = await accion();
      onCambio(respuesta);
      if (despues) despues(respuesta);
    } catch (e) {
      decirError(e, mensajeError);
    } finally {
      setOcupado(false);
    }
  }

  const enviar = () => ejecutar(() => submitPurchaseOrder(orden.id_purchase_order),
    "No se pudo enviar la orden.");
  const autorizar = () => ejecutar(
    () => authorizePurchaseOrder(orden.id_purchase_order, motivo.nota.trim() || null),
    "No se pudo autorizar la orden.", () => setMotivo({ accion: "", nota: "", id: null }));
  const rechazar = () => ejecutar(
    () => rejectPurchaseOrder(orden.id_purchase_order, motivo.nota.trim()),
    "No se pudo rechazar la orden.", () => setMotivo({ accion: "", nota: "", id: null }));
  const cancelar = () => ejecutar(
    () => cancelPurchaseOrder(orden.id_purchase_order, motivo.nota.trim()),
    "No se pudo cancelar la orden.", () => setMotivo({ accion: "", nota: "", id: null }));
  const quitar = () => ejecutar(
    () => removePurchaseVoucher(motivo.id, motivo.nota.trim()),
    "No se pudo quitar el comprobante.", () => setMotivo({ accion: "", nota: "", id: null }));

  const subir = () => ejecutar(
    () => uploadPurchaseVoucher(orden.id_purchase_order, comprobante.file, {
      kind: tipoElegido,
      ...(pideDatos ? {
        folio: comprobante.folio, amount: comprobante.amount, issue_date: comprobante.issue_date,
      } : {}),
    }),
    "No se pudo subir el comprobante.",
    () => setComprobante({ kind: "", file: null, folio: "", amount: "", issue_date: hoyISO() }));

  const comprar = () => ejecutar(
    () => buyPurchaseOrder(orden.id_purchase_order, {
      ...compra, paid_externally: compra.paid_externally ? "true" : "",
    }),
    "No se pudo registrar la compra.",
    (r) => {
      if (r?.reauthorization_required) {
        setAviso(traducir.current(
          "order.reauthorization",
          "El comprobante sale más caro de lo autorizado: la orden volvió a autorización con el monto real."));
      }
    });

  // Cada recepcion SUMA a lo ya recibido: se manda solo lo que llego ahora.
  const llegado = (orden.lines || [])
    .map((l) => ({ id_purchase_order_line: l.id_purchase_order_line,
                   quantity: Number(recepcion.cantidades[l.id_purchase_order_line] || 0) }))
    .filter((l) => Number.isInteger(l.quantity) && l.quantity > 0);
  const pendiente = (l) => Math.max(0, Number(l.quantity) - Number(l.quantity_received || 0));
  const recepcionValida = llegado.length > 0 && (orden.lines || []).every((l) => {
    const n = Number(recepcion.cantidades[l.id_purchase_order_line] || 0);
    return Number.isInteger(n) && n >= 0 && n <= pendiente(l);
  });
  const recibir = () => ejecutar(
    () => receivePurchaseOrder(orden.id_purchase_order, {
      lines: llegado, note: recepcion.nota.trim() || null,
    }),
    "No se pudo registrar la recepción.",
    () => setRecepcion({ cantidades: {}, nota: "" }));
  const recibirTodo = () => setRecepcion({
    ...recepcion,
    cantidades: Object.fromEntries((orden.lines || [])
      .filter((l) => pendiente(l) > 0)
      .map((l) => [l.id_purchase_order_line, String(pendiente(l))])),
  });

  // El archivo se pide con el token, asi que no puede ser un enlace directo.
  async function verArchivo(v) {
    setError("");
    try {
      const blob = await downloadPurchaseVoucher(v.id_purchase_voucher);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      decirError(e, "No se pudo abrir el comprobante.");
    }
  }

  const grupos = agruparPorProyecto(orden.lines);
  const conRecepcion = ESTADOS_CON_RECEPCION.includes(orden.order_status);
  const notaOk = motivo.nota.trim().length >= 5;

  return (
    <div className="oc-detalle">
      <header className="oc-detalle-cabecera">
        <div>
          <h3>{orden.folio}</h3>
          <p className="muted">
            {orden.supplier?.name}
            {orden.supplier?.tax_id ? ` · ${orden.supplier.tax_id}` : ""}
          </p>
          {orden.description && <p>{orden.description}</p>}
        </div>
        <span className={`oc-estado oc-estado-${estado.clase}`}>{estado.etiqueta}</span>
      </header>

      {error && <div className="alert error">{error}</div>}
      {aviso && <div className="alert warning">{aviso}</div>}
      {volvioPorExceso && (
        <div className="alert warning oc-exceso">
          <AlertTriangle size={16} />
          {t("order.exceeded_banner", "Esta orden volvió a autorización porque el comprobante sale más caro de lo autorizado. Se autoriza el monto real o se rechaza.")}
        </div>
      )}
      {orden.order_status === "rejected" && orden.authorization_note && (
        <div className="alert warning">
          <strong>{t("order.rejected_because", "Se rechazó:")}</strong> {orden.authorization_note}
        </div>
      )}

      <dl className="oc-cifras">
        <div>
          <dt>{t("order.quoted", "Cotizado")}</dt>
          <dd>{dinero(orden.quoted_total, moneda)}</dd>
        </div>
        <div>
          <dt>{t("order.authorized", "Autorizado")}</dt>
          <dd>{dinero(orden.authorized_total, moneda)}</dd>
          {orden.order_status === "authorized" && !orden.authorized_by && (
            <small className="muted">{t("order.by_policy", "por la política")}</small>
          )}
          {orden.authorized_by && (
            <small className="muted">{quien(orden.authorized_by_name, orden.authorized_by)}</small>
          )}
        </div>
        <div>
          <dt>{t("order.bought", "Comprado")}</dt>
          <dd className={pasaDeLoAutorizado ? "oc-excede" : undefined}>
            {dinero(orden.total_amount ?? factura?.amount, moneda)}
          </dd>
          {orden.purchased_by && (
            <small className="muted">{quien(orden.purchased_by_name, orden.purchased_by)}</small>
          )}
        </div>
      </dl>
      <p className="oc-meta muted">
        {t("order.created_by", "Creada por")} {quien(orden.created_by_name, orden.created_by)} · {fecha(orden.creation_date)}
        {orden.expected_date && ` · ${t("order.expected_for", "se espera el")} ${fecha(orden.expected_date)}`}
        {orden.purchase_folio && ` · ${t("order.folio_of_purchase", "folio de compra")} ${orden.purchase_folio}`}
      </p>

      <h4>{t("order.lines", "Renglones")}</h4>
      {grupos.length === 0 ? (
        <p className="muted">{t("order.no_lines_short", "Sin renglones.")}</p>
      ) : (
        <div className="table-card">
          <table className="oc-tabla-renglones">
            <thead>
              <tr>
                <th>{t("order.col_what", "Qué")}</th>
                <th>{t("order.col_qty", "Cantidad")}</th>
                {conRecepcion && <th>{t("order.col_received", "Recibido")}</th>}
                <th>{t("order.col_unit_cost", "Costo unitario")}</th>
                <th>{t("order.col_subtotal", "Subtotal")}</th>
              </tr>
            </thead>
            <tbody>
              {grupos.map((g) => (
                <Fragment key={g.proyecto?.id_proyect || "sin-proyecto"}>
                  <tr className="oc-grupo">
                    <td colSpan={conRecepcion ? 5 : 4}>
                      {g.proyecto
                        ? `#${g.proyecto.folio || g.proyecto.id_proyect}${g.proyecto.title ? ` — ${g.proyecto.title}` : ""}`
                        : t("order.no_project", "Sin proyecto (para el almacén)")}
                    </td>
                  </tr>
                  {g.renglones.map((l) => (
                    <tr key={l.id_purchase_order_line}>
                      <td>
                        {l.description}
                        {l.unit && <span className="muted"> · {l.unit}</span>}
                        {!l.from_need && (
                          <span className="oc-etiqueta oc-etiqueta-propio">
                            {t("order.own_line", "agregado por Compras")}
                          </span>
                        )}
                      </td>
                      <td className="mono">{l.quantity}</td>
                      {conRecepcion && (
                        <td className={`mono${pendiente(l) === 0 ? " oc-completo" : ""}`}>
                          {l.quantity_received || 0} / {l.quantity}
                        </td>
                      )}
                      <td className="mono">{dinero(l.unit_cost, moneda)}</td>
                      <td className="mono">{dinero(l.line_total, moneda)}</td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h4>{t("order.vouchers", "Comprobantes")}</h4>
      {(orden.vouchers || []).length === 0 ? (
        <p className="muted">{t("order.no_vouchers", "Todavía no hay comprobantes. Para comprar hace falta la factura o el ticket.")}</p>
      ) : (
        <ul className="oc-comprobantes">
          {orden.vouchers.map((v) => (
            <li key={v.id_purchase_voucher}>
              <span>
                <strong>{TIPOS_DE_COMPROBANTE.find((x) => x.clave === v.kind)?.etiqueta || v.kind}</strong>
                {v.folio && <span> · {v.folio}</span>}
                {v.amount !== null && v.amount !== undefined && <span> · {dinero(v.amount, moneda)}</span>}
                {v.issue_date && <span className="muted"> · {fecha(v.issue_date)}</span>}
                {v.cfdi_uuid && <small className="muted oc-uuid"> CFDI {v.cfdi_uuid}</small>}
                <small className="muted"> · {t("order.uploaded_by", "subió")} {quien(v.created_by_name, v.created_by)}</small>
              </span>
              <span className="oc-comprobante-acciones">
                <button type="button" className="button button-quiet" onClick={() => verArchivo(v)}>
                  <ExternalLink size={14} /> {t("order.open", "Ver")}
                </button>
                {(acciones.removable_vouchers || []).includes(v.id_purchase_voucher) && (
                  <button type="button" className="button button-quiet"
                          onClick={() => setMotivo({ accion: "quitar", nota: "", id: v.id_purchase_voucher })}>
                    {t("order.remove_voucher", "Quitar")}
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {motivo.accion === "quitar" && (
        <div className="oc-motivo">
          <label>
            <span>{t("order.why_remove", "¿Por qué se quita? (queda en la bitácora)")}</span>
            <input type="text" maxLength={300} autoFocus value={motivo.nota}
                   onChange={(e) => setMotivo({ ...motivo, nota: e.target.value })} />
          </label>
          <button type="button" className="button primary" disabled={ocupado || !notaOk} onClick={quitar}>
            {t("order.remove_voucher", "Quitar")}
          </button>
          <button type="button" className="button" onClick={() => setMotivo({ accion: "", nota: "", id: null })}>
            {t("common.cancel", "Cancelar")}
          </button>
        </div>
      )}

      {acciones.attach_voucher && tiposPermitidos.length > 0 && (
        <div className="oc-subir">
          <label>
            <span>{t("order.voucher_kind", "Tipo")}</span>
            <select value={tipoElegido} onChange={(e) => setComprobante({ ...comprobante, kind: e.target.value })}>
              {tiposPermitidos.map((k) => (
                <option key={k} value={k}>{TIPOS_DE_COMPROBANTE.find((x) => x.clave === k)?.etiqueta}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t("order.file", "Archivo (PDF, foto o XML)")}</span>
            <input type="file" accept=".pdf,.jpg,.jpeg,.png,.xml"
                   onChange={(e) => setComprobante({ ...comprobante, file: e.target.files?.[0] || null })} />
          </label>
          {pideDatos && (
            <>
              <label>
                <span>{t("order.voucher_folio", "Folio")}</span>
                <input type="text" maxLength={60} value={comprobante.folio}
                       onChange={(e) => setComprobante({ ...comprobante, folio: e.target.value })} />
              </label>
              <label>
                <span>{t("order.voucher_amount", "Monto")}</span>
                <input type="number" min="0" step="0.01" className="oc-numero oc-numero-ancho"
                       value={comprobante.amount}
                       onChange={(e) => setComprobante({ ...comprobante, amount: e.target.value })} />
              </label>
              <label>
                <span>{t("order.voucher_date", "Fecha del comprobante")}</span>
                <input type="date" value={comprobante.issue_date}
                       onChange={(e) => setComprobante({ ...comprobante, issue_date: e.target.value })} />
              </label>
            </>
          )}
          {conXml && (
            <p className="muted oc-ayuda-xml">
              {t("order.xml_hint", "El folio, el monto, la fecha y el UUID se leen del XML; no se capturan.")}
            </p>
          )}
          <button type="button" className="button" onClick={subir}
                  disabled={ocupado || !comprobante.file
                    || (pideDatos && (!comprobante.folio.trim() || !comprobante.amount || !comprobante.issue_date))}>
            <Paperclip size={14} /> {t("order.upload", "Subir comprobante")}
          </button>
        </div>
      )}

      {acciones.purchase && (
        <div className="oc-compra">
          <h4>{t("order.register_purchase", "Registrar la compra")}</h4>
          <p className="muted">
            {t("order.purchase_help", "El folio y el monto salen del comprobante. Aquí se dice cuándo y cómo se pagó.")}
          </p>
          <div className="oc-form-grid">
            <label>
              <span>{t("order.purchase_date", "Fecha de compra")}</span>
              <input type="date" value={compra.purchase_date}
                     onChange={(e) => setCompra({ ...compra, purchase_date: e.target.value })} />
            </label>
            <label>
              <span>{t("order.payment_method", "Forma de pago")}</span>
              <select value={compra.payment_method}
                      onChange={(e) => setCompra({ ...compra, payment_method: e.target.value })}>
                {METODOS_DE_PAGO.map((m) => <option key={m.clave} value={m.clave}>{m.etiqueta}</option>)}
              </select>
            </label>
            <label>
              <span>
                {t("order.payment_reference", "Referencia (clave de rastreo, no. de cheque o aprobación)")}
              </span>
              <input type="text" maxLength={80} value={compra.payment_reference}
                     onChange={(e) => setCompra({ ...compra, payment_reference: e.target.value })} />
            </label>
            <label className="oc-casilla">
              <input type="checkbox" checked={compra.paid_externally}
                     onChange={(e) => setCompra({ ...compra, paid_externally: e.target.checked })} />
              <span>{t("order.paid_externally", "Se pagó fuera del sistema")}</span>
            </label>
          </div>
          <button type="button" className="button primary" onClick={comprar}
                  disabled={ocupado || !compra.purchase_date
                    || (requiereReferencia(compra.payment_method) && !compra.payment_reference.trim())}>
            {t("order.mark_bought", "Marcar como comprada")}
          </button>
        </div>
      )}
      {acciones.receive && (
        <div className="oc-compra">
          <h4>{t("order.register_reception", "Registrar la recepción")}</h4>
          <p className="muted">
            {t("order.reception_help", "Anota cuánto llegó de cada renglón. Puedes recibir por partes: lo que falte queda pendiente.")}
          </p>
          <ul className="oc-recepcion">
            {(orden.lines || []).filter((l) => pendiente(l) > 0).map((l) => (
              <li key={l.id_purchase_order_line}>
                <span>
                  {l.description}
                  {l.unit && <span className="muted"> · {l.unit}</span>}
                  <small className="muted"> · {t("order.pending", "faltan")} {pendiente(l)}</small>
                </span>
                <input type="number" min="0" max={pendiente(l)} step="1" className="oc-numero"
                       aria-label={`${t("order.received_now", "Llegó ahora")}: ${l.description}`}
                       value={recepcion.cantidades[l.id_purchase_order_line] ?? ""}
                       onChange={(e) => setRecepcion({
                         ...recepcion,
                         cantidades: { ...recepcion.cantidades, [l.id_purchase_order_line]: e.target.value },
                       })} />
              </li>
            ))}
          </ul>
          <label>
            <span>{t("order.reception_note", "Nota (opcional): faltantes, daños, quién entregó")}</span>
            <input type="text" maxLength={300} value={recepcion.nota}
                   onChange={(e) => setRecepcion({ ...recepcion, nota: e.target.value })} />
          </label>
          <div className="oc-acciones">
            <button type="button" className="button" onClick={recibirTodo} disabled={ocupado}>
              {t("order.receive_all", "Llegó todo lo pendiente")}
            </button>
            <button type="button" className="button primary" onClick={recibir}
                    disabled={ocupado || !recepcionValida}>
              {t("order.receive", "Registrar recepción")}
            </button>
          </div>
        </div>
      )}
      {orden.order_status === "authorized" && !acciones.purchase && !factura && (
        <p className="muted oc-ayuda">
          {t("order.upload_first", "Sube la factura o el ticket para poder registrar la compra.")}
        </p>
      )}

      <div className="oc-acciones">
        {acciones.edit && (
          <button type="button" className="button" onClick={onEditar} disabled={ocupado}>
            {t("order.edit", "Corregir")}
          </button>
        )}
        {acciones.submit && (
          <button type="button" className="button primary" onClick={enviar} disabled={ocupado}>
            {t("order.send", "Enviar a autorización")}
          </button>
        )}
        {acciones.authorize && motivo.accion !== "autorizar" && (
          <button type="button" className="button primary" disabled={ocupado}
                  onClick={() => setMotivo({ accion: "autorizar", nota: "", id: null })}>
            {t("order.authorize", "Autorizar")}
          </button>
        )}
        {acciones.reject && motivo.accion !== "rechazar" && (
          <button type="button" className="button" disabled={ocupado}
                  onClick={() => setMotivo({ accion: "rechazar", nota: "", id: null })}>
            {t("order.reject", "Rechazar")}
          </button>
        )}
        {acciones.cancel && motivo.accion !== "cancelar" && (
          <button type="button" className="button button-quiet" disabled={ocupado}
                  onClick={() => setMotivo({ accion: "cancelar", nota: "", id: null })}>
            {t("order.cancel", "Cancelar orden")}
          </button>
        )}
      </div>
      {acciones.authorize === false && orden.order_status === "pending_authorization" && acciones.reject === false && (
        <p className="muted oc-ayuda">{t("order.waiting_authorization", "Espera a que la autorice quien tiene ese permiso.")}</p>
      )}
      {acciones.authorize === false && acciones.reject && (
        <p className="muted oc-ayuda">
          {t("order.cannot_authorize_own", "No puedes autorizar una orden que tú mismo pediste; puedes rechazarla.")}
        </p>
      )}

      {["autorizar", "rechazar", "cancelar"].includes(motivo.accion) && (
        <div className="oc-motivo">
          <label>
            <span>
              {motivo.accion === "autorizar"
                ? t("order.authorize_note", "Nota (opcional)")
                : t("order.why", "¿Por qué? (queda en la bitácora, mínimo 5 letras)")}
            </span>
            <input type="text" maxLength={300} autoFocus value={motivo.nota}
                   onChange={(e) => setMotivo({ ...motivo, nota: e.target.value })} />
          </label>
          <button type="button" className="button primary"
                  disabled={ocupado || (motivo.accion !== "autorizar" && !notaOk)}
                  onClick={{ autorizar, rechazar, cancelar }[motivo.accion]}>
            {t("common.confirm", "Confirmar")}
          </button>
          <button type="button" className="button" onClick={() => setMotivo({ accion: "", nota: "", id: null })}>
            {t("common.cancel", "Cancelar")}
          </button>
        </div>
      )}

      <h4>{t("order.history", "Bitácora")}</h4>
      <ol className="oc-bitacora">
        {(orden.events || []).map((e) => (
          <li key={e.id_purchase_event}>
            <strong>{EVENTOS[e.event_type] || e.event_type}</strong>
            <span className="muted">
              {" "}· {quien(e.created_by_name, e.created_by)} · {fechaHora(e.creation_date)}
            </span>
            {e.note && <p className="oc-bitacora-nota">{e.note}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

OrdenDeCompraDetalle.propTypes = {
  // La orden completa tal como la arma el backend (`purchase_order_service`).
  orden: PropTypes.object.isRequired,
  politica: PropTypes.shape({ overrun_percent: PropTypes.number }),
  onCambio: PropTypes.func.isRequired,
  onEditar: PropTypes.func.isRequired,
};

OrdenDeCompraDetalle.defaultProps = { politica: null };
