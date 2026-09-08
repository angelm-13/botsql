import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowLeftRight, Ban, Check, Plus, RefreshCw, Trash2, Wallet, X } from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/invoice-fiscal.css";
import {
  createInvoiceCreditNote,
  getInvoiceCancellation,
  getInvoiceCatalogs,
  getInvoiceCreditNotes,
  getInvoiceRelations,
  getInvoiceStatement,
  getPaymentComplement,
  refreshInvoiceCancellation,
  registerInvoicePayment,
  requestInvoiceCancellation
} from "../api";

// El panel abre sobre una factura ya timbrada. Los tres actos que reune
// -cancelar, abonar y acreditar- solo existen para un CFDI con folio fiscal,
// asi que el propio panel lo comprueba y lo dice en lugar de dejar que el
// backend responda con un error que el usuario no puede interpretar.
const TABS = [
  { key: "cancellation", icon: Ban },
  { key: "payments", icon: Wallet },
  { key: "credit_notes", icon: ArrowLeftRight }
];

// Motivo que obliga a declarar el comprobante que sustituye al cancelado.
const MOTIVE_REQUIRING_SUBSTITUTION = "01";
// Relacion que devuelve mercancia al almacen; la otra es un simple descuento.
const RELATION_RETURNS_GOODS = "03";

const hoy = () => new Date().toISOString().slice(0, 10);

function money(value) {
  const numero = Number(value);
  if (!Number.isFinite(numero)) return "—";
  return numero.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

const conceptoVacio = () => ({
  description: "",
  quantity: "1",
  unit_price: "",
  sat_product_key: "",
  sat_unit_key: "H87",
  id_product: ""
});

export default function InvoiceFiscalPanel({ invoice, onClose, onChanged }) {
  const { t } = useI18n();
  const [tab, setTab] = useState("cancellation");
  const [catalogs, setCatalogs] = useState(null);
  const [busy, setBusy] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [errorMeta, setErrorMeta] = useState(null);
  const [noticeKey, setNoticeKey] = useState("");

  const [cancellation, setCancellation] = useState(null);
  const [motive, setMotive] = useState("02");
  const [substitution, setSubstitution] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  const [statement, setStatement] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentForm, setPaymentForm] = useState("03");
  const [paymentDate, setPaymentDate] = useState(hoy());
  const [complement, setComplement] = useState(null);

  const [creditSummary, setCreditSummary] = useState(null);
  const [relations, setRelations] = useState(null);
  const [relationType, setRelationType] = useState("01");
  const [concepts, setConcepts] = useState([conceptoVacio()]);

  const invoiceId = invoice?.id_invoice;
  const isStamped = Boolean(invoice?.folio_fiscal);

  function report(error) {
    setErrorKey(error?.message || "errors.request_failed");
    setErrorMeta(error?.payload?.meta || null);
  }

  const load = useCallback(async () => {
    if (!invoiceId || !isStamped) return;
    setBusy(true);
    setErrorKey("");
    try {
      const [cancelData, statementData, creditData, relationData] = await Promise.all([
        getInvoiceCancellation(invoiceId),
        getInvoiceStatement(invoiceId),
        getInvoiceCreditNotes(invoiceId),
        getInvoiceRelations(invoiceId)
      ]);
      setCancellation(cancelData);
      setStatement(statementData);
      setCreditSummary(creditData);
      setRelations(relationData);
      // El importe se propone completo, que es el caso mas comun; el usuario lo
      // reduce si el abono fue parcial.
      setPaymentAmount(statementData?.outstanding || "");
    } catch (error) {
      report(error);
    } finally {
      setBusy(false);
    }
  }, [invoiceId, isStamped]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let vivo = true;
    getInvoiceCatalogs()
      .then((data) => {
        if (vivo) setCatalogs(data);
      })
      .catch(() => {
        // Sin catalogos los campos siguen capturables a mano; no vale bloquear
        // la pantalla entera por un select.
      });
    return () => {
      vivo = false;
    };
  }, []);

  const formasPago = useMemo(() => {
    const catalogo = catalogs?.forma_pago || {};
    // "99 por definir" existe para una factura por pagar, no para un abono que
    // ya ocurrio: el backend lo rechaza, asi que no se ofrece.
    return Object.entries(catalogo).filter(([clave]) => clave !== "99");
  }, [catalogs]);

  const relacionesNota = useMemo(
    () => catalogs?.tipo_relacion_nota_credito || ["01", "03"],
    [catalogs]
  );

  async function actuar(accion, avisoKey) {
    setBusy(true);
    setErrorKey("");
    setNoticeKey("");
    try {
      await accion();
      setNoticeKey(avisoKey);
      await load();
      if (onChanged) onChanged();
    } catch (error) {
      report(error);
    } finally {
      setBusy(false);
    }
  }

  // --- cancelacion --------------------------------------------------------

  function enviarCancelacion(evento) {
    evento.preventDefault();
    const etiqueta = cancellation?.motives?.[motive] || motive;
    const aviso = [
      t("fiscal.cancel_confirm", "Se pedirá al SAT la cancelación de este CFDI."),
      "",
      `${t("fiscal.motive", "Motivo")}: ${motive} — ${etiqueta}`,
      cancellation?.inventory_movements_to_reverse
        ? t(
            "fiscal.cancel_reverses_inventory",
            "Al confirmarlo el SAT, el almacén recibirá de vuelta lo facturado."
          )
        : "",
      "",
      t("common.continue", "¿Continuar?")
    ]
      .filter(Boolean)
      .join("\n");
    if (!window.confirm(aviso)) return;

    actuar(
      () =>
        requestInvoiceCancellation(invoiceId, {
          motive,
          ...(motive === MOTIVE_REQUIRING_SUBSTITUTION
            ? { substitution_uuid: substitution.trim() }
            : {}),
          ...(cancelReason.trim() ? { reason: cancelReason.trim() } : {})
        }),
      "fiscal.cancel_requested"
    );
  }

  function renderCancelacion() {
    if (!cancellation) return null;
    const vigente = cancellation.current_request;
    const historial = cancellation.history || [];

    return (
      <div className="fiscal-section">
        <dl className="fiscal-facts">
          <div>
            <dt>{t("fiscal.fiscal_folio", "Folio fiscal")}</dt>
            <dd className="mono">{cancellation.folio_fiscal || "—"}</dd>
          </div>
          <div>
            <dt>{t("fiscal.invoice_status", "Estatus")}</dt>
            <dd>{cancellation.invoice_status || "—"}</dd>
          </div>
          <div>
            <dt>{t("fiscal.inventory_to_reverse", "Movimientos a revertir")}</dt>
            <dd>{cancellation.inventory_movements_to_reverse ?? 0}</dd>
          </div>
        </dl>

        {vigente && (
          <div className="fiscal-standing">
            <p>
              <strong>{t("fiscal.pending_request", "Solicitud en curso")}</strong> ·{" "}
              {vigente.status} · {vigente.motive}
            </p>
            <p className="muted">
              {t(
                "fiscal.cancel_waiting_sat",
                "El receptor tiene 72 horas para aceptar o rechazar. Consulta al SAT para actualizar el estado."
              )}
            </p>
            <button
              type="button"
              className="button"
              disabled={busy}
              onClick={() =>
                actuar(
                  () => refreshInvoiceCancellation(vigente.id_invoice_cancellation),
                  "fiscal.cancel_refreshed"
                )
              }
            >
              <RefreshCw size={15} />
              {t("fiscal.ask_sat", "Consultar al SAT")}
            </button>
          </div>
        )}

        {cancellation.can_request ? (
          <form className="fiscal-form" onSubmit={enviarCancelacion}>
            <div className="field">
              <label htmlFor="fiscal-motive">{t("fiscal.motive", "Motivo")}</label>
              <select
                id="fiscal-motive"
                value={motive}
                onChange={(event) => setMotive(event.target.value)}
              >
                {Object.entries(cancellation.motives || {}).map(([clave, etiqueta]) => (
                  <option key={clave} value={clave}>
                    {clave} — {etiqueta}
                  </option>
                ))}
              </select>
            </div>

            {motive === MOTIVE_REQUIRING_SUBSTITUTION && (
              <div className="field">
                <label htmlFor="fiscal-substitution">
                  {t("fiscal.substitution_uuid", "Folio fiscal que lo sustituye")}
                </label>
                <input
                  id="fiscal-substitution"
                  value={substitution}
                  onChange={(event) => setSubstitution(event.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                  required
                />
                <p className="field-hint muted">
                  {t(
                    "fiscal.substitution_hint",
                    "El motivo 01 sustituye un comprobante por otro, así que hace falta el folio del que lo reemplaza."
                  )}
                </p>
              </div>
            )}

            <div className="field">
              <label htmlFor="fiscal-reason">
                {t("fiscal.internal_reason", "Nota interna")}
              </label>
              <input
                id="fiscal-reason"
                value={cancelReason}
                onChange={(event) => setCancelReason(event.target.value)}
                maxLength={300}
              />
            </div>

            <div className="form-actions">
              <button className="button danger" type="submit" disabled={busy}>
                <Ban size={15} />
                {t("fiscal.request_cancellation", "Solicitar cancelación")}
              </button>
            </div>
          </form>
        ) : (
          <p className="muted">
            {vigente
              ? t("fiscal.cancel_already_requested", "Ya hay una solicitud en curso.")
              : t(
                  "fiscal.cancel_not_available",
                  "Esta factura no se puede cancelar: no está timbrada o ya se canceló."
                )}
          </p>
        )}

        {historial.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("fiscal.motive", "Motivo")}</th>
                  <th>{t("fiscal.status", "Estado")}</th>
                  <th>{t("fiscal.requested_at", "Solicitada")}</th>
                  <th>{t("fiscal.resolved_at", "Resuelta")}</th>
                </tr>
              </thead>
              <tbody>
                {historial.map((fila) => (
                  <tr key={fila.id_invoice_cancellation}>
                    <td>{fila.motive}</td>
                    <td>{fila.status}</td>
                    <td className="mono">{(fila.requested_at || "").slice(0, 19)}</td>
                    <td className="mono">{(fila.resolved_at || "—").slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // --- abonos y complemento ------------------------------------------------

  function enviarAbono(evento) {
    evento.preventDefault();
    actuar(
      () =>
        registerInvoicePayment(invoiceId, {
          amount: paymentAmount,
          payment_form: paymentForm,
          paid_at: paymentDate
        }),
      "fiscal.payment_registered"
    );
  }

  async function verComplemento(idPayment) {
    setBusy(true);
    setErrorKey("");
    try {
      setComplement(await getPaymentComplement(idPayment));
    } catch (error) {
      report(error);
    } finally {
      setBusy(false);
    }
  }

  function renderPagos() {
    if (!statement) return null;
    const abonos = statement.payments || [];

    return (
      <div className="fiscal-section">
        <dl className="fiscal-facts">
          <div>
            <dt>{t("fiscal.total", "Total")}</dt>
            <dd className="mono">{money(statement.total)}</dd>
          </div>
          <div>
            <dt>{t("fiscal.paid", "Pagado")}</dt>
            <dd className="mono">{money(statement.paid)}</dd>
          </div>
          <div>
            <dt>{t("fiscal.outstanding", "Insoluto")}</dt>
            <dd className="mono">{money(statement.outstanding)}</dd>
          </div>
        </dl>

        {!statement.requires_payment_complement && (
          <p className="fiscal-hint">
            <AlertTriangle size={15} />
            {t(
              "fiscal.complement_only_for_ppd",
              "El complemento de pago corresponde al método PPD (parcialidades o diferido). Esta factura es PUE, así que se considera pagada al emitirse."
            )}
          </p>
        )}

        {statement.is_settled ? (
          <p className="muted">{t("fiscal.already_settled", "La factura está saldada.")}</p>
        ) : (
          <form className="fiscal-form" onSubmit={enviarAbono}>
            <div className="form-grid-2">
              <div className="field">
                <label htmlFor="fiscal-amount">{t("fiscal.amount", "Importe")}</label>
                <input
                  id="fiscal-amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={paymentAmount}
                  onChange={(event) => setPaymentAmount(event.target.value)}
                  required
                />
                <p className="field-hint muted">
                  {t("fiscal.instalment_number", "Parcialidad")} {statement.next_instalment}
                </p>
              </div>
              <div className="field">
                <label htmlFor="fiscal-form">{t("fiscal.payment_form", "Forma de pago")}</label>
                <select
                  id="fiscal-form"
                  value={paymentForm}
                  onChange={(event) => setPaymentForm(event.target.value)}
                >
                  {formasPago.map(([clave, etiqueta]) => (
                    <option key={clave} value={clave}>
                      {clave} — {etiqueta}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="fiscal-date">{t("fiscal.paid_at", "Fecha del pago")}</label>
                <input
                  id="fiscal-date"
                  type="date"
                  value={paymentDate}
                  onChange={(event) => setPaymentDate(event.target.value)}
                  required
                />
              </div>
            </div>
            <div className="form-actions">
              <button className="button primary" type="submit" disabled={busy}>
                <Plus size={15} />
                {t("fiscal.register_payment", "Registrar abono")}
              </button>
            </div>
          </form>
        )}

        {abonos.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>{t("fiscal.paid_at", "Fecha")}</th>
                  <th>{t("fiscal.amount", "Importe")}</th>
                  <th>{t("fiscal.previous_balance", "Saldo anterior")}</th>
                  <th>{t("fiscal.outstanding", "Insoluto")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {abonos.map((abono) => (
                  <tr key={abono.id_invoice_payment}>
                    <td>{abono.instalment}</td>
                    <td className="mono">{(abono.paid_at || "").slice(0, 10)}</td>
                    <td className="mono">{money(abono.amount)}</td>
                    <td className="mono">{money(abono.previous_balance)}</td>
                    <td className="mono">{money(abono.outstanding_balance)}</td>
                    <td className="row-actions">
                      <button
                        type="button"
                        onClick={() => verComplemento(abono.id_invoice_payment)}
                        title={t("fiscal.view_complement", "Ver complemento de pago")}
                      >
                        {t("fiscal.complement", "Complemento")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {complement && (
          <div className="fiscal-standing">
            <div className="fiscal-standing-head">
              <strong>
                {t("fiscal.complement_of_instalment", "Complemento de la parcialidad")}{" "}
                {complement.related_document?.instalment}
              </strong>
              <button type="button" className="button ghost" onClick={() => setComplement(null)}>
                <X size={14} />
              </button>
            </div>
            <p className="muted">
              {t(
                "fiscal.complement_explainer",
                "El comprobante va en ceros: el importe vive en el complemento, no en el cuerpo del CFDI."
              )}
            </p>
            <dl className="fiscal-facts">
              <div>
                <dt>{t("fiscal.cfdi_type", "Tipo")}</dt>
                <dd className="mono">{complement.cfdi_type}</dd>
              </div>
              <div>
                <dt>{t("fiscal.cfdi_use", "Uso CFDI")}</dt>
                <dd className="mono">{complement.cfdi_use}</dd>
              </div>
              <div>
                <dt>{t("fiscal.total", "Total")}</dt>
                <dd className="mono">{complement.total}</dd>
              </div>
              <div>
                <dt>{t("fiscal.related_uuid", "Documento relacionado")}</dt>
                <dd className="mono">{complement.related_document?.uuid}</dd>
              </div>
              <div>
                <dt>{t("fiscal.payment_method", "Método")}</dt>
                <dd className="mono">{complement.related_document?.payment_method}</dd>
              </div>
              <div>
                <dt>{t("fiscal.amount_paid", "Importe pagado")}</dt>
                <dd className="mono">{money(complement.related_document?.amount_paid)}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    );
  }

  // --- notas de credito ----------------------------------------------------

  function actualizarConcepto(indice, campo, valor) {
    setConcepts((previos) =>
      previos.map((concepto, i) => (i === indice ? { ...concepto, [campo]: valor } : concepto))
    );
  }

  const totalNota = useMemo(
    () =>
      concepts.reduce((suma, concepto) => {
        const cantidad = Number(concepto.quantity) || 0;
        const precio = Number(concepto.unit_price) || 0;
        return suma + cantidad * precio;
      }, 0),
    [concepts]
  );

  function enviarNota(evento) {
    evento.preventDefault();
    const devuelve = relationType === RELATION_RETURNS_GOODS;
    const aviso = [
      devuelve
        ? t(
            "fiscal.credit_note_returns_goods",
            "Devolución de mercancía: lo acreditado volverá al almacén del que salió."
          )
        : t(
            "fiscal.credit_note_discount_only",
            "Descuento o bonificación: el cliente se queda con la mercancía, así que el almacén NO se toca."
          ),
      "",
      t("common.continue", "¿Continuar?")
    ].join("\n");
    if (!window.confirm(aviso)) return;

    actuar(
      () =>
        createInvoiceCreditNote(invoiceId, {
          relation_type: relationType,
          concepts: concepts.map((concepto) => ({
            description: concepto.description,
            quantity: concepto.quantity,
            unit_price: concepto.unit_price,
            sat_product_key: concepto.sat_product_key,
            sat_unit_key: concepto.sat_unit_key,
            ...(concepto.id_product ? { id_product: Number(concepto.id_product) } : {})
          }))
        }),
      "fiscal.credit_note_created"
    );
    setConcepts([conceptoVacio()]);
  }

  function renderNotas() {
    if (!creditSummary) return null;
    const notas = creditSummary.credit_notes || [];
    const acreditable = Number(creditSummary.creditable) || 0;
    const excede = totalNota > acreditable + 0.005;

    return (
      <div className="fiscal-section">
        <dl className="fiscal-facts">
          <div>
            <dt>{t("fiscal.total", "Total de la factura")}</dt>
            <dd className="mono">{money(creditSummary.total)}</dd>
          </div>
          <div>
            <dt>{t("fiscal.credited", "Ya acreditado")}</dt>
            <dd className="mono">{money(creditSummary.credited)}</dd>
          </div>
          <div>
            <dt>{t("fiscal.creditable", "Acreditable")}</dt>
            <dd className="mono">{money(creditSummary.creditable)}</dd>
          </div>
        </dl>

        {creditSummary.can_credit ? (
          <form className="fiscal-form" onSubmit={enviarNota}>
            <div className="field">
              <label htmlFor="fiscal-relation">
                {t("fiscal.relation_type", "Tipo de relación")}
              </label>
              <select
                id="fiscal-relation"
                value={relationType}
                onChange={(event) => setRelationType(event.target.value)}
              >
                {relacionesNota.map((clave) => (
                  <option key={clave} value={clave}>
                    {clave} — {catalogs?.tipo_relacion?.[clave] || clave}
                  </option>
                ))}
              </select>
              <p className="field-hint muted">
                {relationType === RELATION_RETURNS_GOODS
                  ? t(
                      "fiscal.relation_03_hint",
                      "Devolución de mercancía: vuelve al almacén del que salió."
                    )
                  : t(
                      "fiscal.relation_01_hint",
                      "Descuento o bonificación: el almacén no se toca."
                    )}
              </p>
            </div>

            {concepts.map((concepto, indice) => (
              <div className="fiscal-concept" key={indice}>
                <div className="form-grid-2">
                  <div className="field">
                    <label htmlFor={`nc-desc-${indice}`}>
                      {t("fiscal.description", "Descripción")}
                    </label>
                    <input
                      id={`nc-desc-${indice}`}
                      value={concepto.description}
                      onChange={(event) =>
                        actualizarConcepto(indice, "description", event.target.value)
                      }
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`nc-qty-${indice}`}>
                      {t("fiscal.quantity", "Cantidad")}
                    </label>
                    <input
                      id={`nc-qty-${indice}`}
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={concepto.quantity}
                      onChange={(event) =>
                        actualizarConcepto(indice, "quantity", event.target.value)
                      }
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`nc-price-${indice}`}>
                      {t("fiscal.unit_price", "Precio unitario")}
                    </label>
                    <input
                      id={`nc-price-${indice}`}
                      type="number"
                      step="0.01"
                      min="0"
                      value={concepto.unit_price}
                      onChange={(event) =>
                        actualizarConcepto(indice, "unit_price", event.target.value)
                      }
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`nc-sat-${indice}`}>
                      {t("fiscal.sat_product_key", "Clave del producto (SAT)")}
                    </label>
                    <input
                      id={`nc-sat-${indice}`}
                      value={concepto.sat_product_key}
                      onChange={(event) =>
                        actualizarConcepto(indice, "sat_product_key", event.target.value)
                      }
                      list="fiscal-sat-products"
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`nc-unit-${indice}`}>
                      {t("fiscal.sat_unit_key", "Clave de unidad (SAT)")}
                    </label>
                    <input
                      id={`nc-unit-${indice}`}
                      value={concepto.sat_unit_key}
                      onChange={(event) =>
                        actualizarConcepto(indice, "sat_unit_key", event.target.value)
                      }
                      list="fiscal-sat-units"
                      required
                    />
                  </div>
                  {relationType === RELATION_RETURNS_GOODS && (
                    <div className="field">
                      <label htmlFor={`nc-product-${indice}`}>
                        {t("fiscal.product_id", "Producto del almacén")}
                      </label>
                      <input
                        id={`nc-product-${indice}`}
                        type="number"
                        value={concepto.id_product}
                        onChange={(event) =>
                          actualizarConcepto(indice, "id_product", event.target.value)
                        }
                      />
                      <p className="field-hint muted">
                        {t(
                          "fiscal.product_id_hint",
                          "Sin producto la partida no regresa al almacén, solo acredita el importe."
                        )}
                      </p>
                    </div>
                  )}
                </div>
                {concepts.length > 1 && (
                  <button
                    type="button"
                    className="button ghost"
                    onClick={() => setConcepts((previos) => previos.filter((_, i) => i !== indice))}
                  >
                    <Trash2 size={14} />
                    {t("common.remove", "Quitar")}
                  </button>
                )}
              </div>
            ))}

            <datalist id="fiscal-sat-products">
              {Object.entries(catalogs?.clave_prod_serv || {}).map(([clave, etiqueta]) => (
                <option key={clave} value={clave}>
                  {etiqueta}
                </option>
              ))}
            </datalist>
            <datalist id="fiscal-sat-units">
              {Object.entries(catalogs?.clave_unidad || {}).map(([clave, etiqueta]) => (
                <option key={clave} value={clave}>
                  {etiqueta}
                </option>
              ))}
            </datalist>

            <div className="fiscal-total-row">
              <span>{t("fiscal.credit_note_subtotal", "Suma de partidas")}</span>
              <strong className="mono">{money(totalNota)}</strong>
            </div>
            {excede && (
              <p className="error">
                {t(
                  "fiscal.credit_note_exceeds",
                  "La nota supera lo que queda por acreditar de esta factura."
                )}
              </p>
            )}

            <div className="form-actions">
              <button
                type="button"
                className="button ghost"
                onClick={() => setConcepts((previos) => [...previos, conceptoVacio()])}
              >
                <Plus size={15} />
                {t("fiscal.add_concept", "Agregar partida")}
              </button>
              <button className="button primary" type="submit" disabled={busy || excede}>
                <Check size={15} />
                {t("fiscal.create_credit_note", "Emitir nota de crédito")}
              </button>
            </div>
            <p className="field-hint muted">
              {t(
                "fiscal.credit_note_needs_stamping",
                "La nota se emite sin timbrar. Se timbra después desde el listado de facturas, como cualquier CFDI."
              )}
            </p>
          </form>
        ) : (
          <p className="muted">
            {t(
              "fiscal.credit_note_not_available",
              "No se puede acreditar: la factura no está timbrada, está cancelada, o ya se acreditó por completo."
            )}
          </p>
        )}

        {notas.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("fiscal.credit_note", "Nota")}</th>
                  <th>{t("fiscal.fiscal_folio", "Folio fiscal")}</th>
                  <th>{t("fiscal.total", "Total")}</th>
                  <th>{t("fiscal.status", "Estado")}</th>
                </tr>
              </thead>
              <tbody>
                {notas.map((nota) => (
                  <tr key={nota.id_invoice}>
                    <td className="mono">#{nota.id_invoice}</td>
                    <td className="mono">{nota.folio_fiscal || "—"}</td>
                    <td className="mono">{money(nota.total)}</td>
                    <td>{nota.invoice_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {relations?.related_documents?.length > 0 && (
          <p className="muted">
            {t("fiscal.declared_relations", "Relaciones declaradas ante el SAT")}:{" "}
            {relations.related_documents
              .map((relacion) => `${relacion.relation_type} → ${relacion.uuid}`)
              .join(" · ")}
          </p>
        )}
      </div>
    );
  }

  // --- armado -------------------------------------------------------------

  if (!invoice) return null;

  return (
    <div className="fiscal-panel-backdrop" role="dialog" aria-modal="true" aria-label={t("fiscal.panel_title", "Actos fiscales")}>
      <div className="fiscal-panel">
        <header className="fiscal-panel-head">
          <div>
            <p className="eyebrow">{t("fiscal.panel_title", "Actos fiscales")}</p>
            <h2>
              {invoice.folio ? `#${invoice.folio}` : `#${invoice.id_invoice}`}{" "}
              <span className="mono muted">{invoice.folio_fiscal || ""}</span>
            </h2>
          </div>
          <button type="button" className="button ghost" onClick={onClose} aria-label={t("common.close", "Cerrar")}>
            <X size={18} />
          </button>
        </header>

        {!isStamped ? (
          <p className="fiscal-hint">
            <AlertTriangle size={15} />
            {t(
              "fiscal.requires_stamped_invoice",
              "Cancelar, cobrar con complemento y acreditar solo aplican a una factura timbrada. Timbra la factura primero."
            )}
          </p>
        ) : (
          <>
            <nav className="fiscal-tabs">
              {TABS.map(({ key, icon: Icono }) => (
                <button
                  key={key}
                  type="button"
                  className={tab === key ? "button active" : "button"}
                  onClick={() => setTab(key)}
                >
                  <Icono size={15} />
                  {t(`fiscal.tab_${key}`, key)}
                </button>
              ))}
            </nav>

            {errorKey && (
              <p className="error">
                {t(errorKey, errorKey)}
                {errorMeta ? ` (${JSON.stringify(errorMeta)})` : ""}
              </p>
            )}
            {noticeKey && <p className="notice">{t(noticeKey, noticeKey)}</p>}

            {busy && <p className="muted">{t("common.loading", "Cargando…")}</p>}

            {tab === "cancellation" && renderCancelacion()}
            {tab === "payments" && renderPagos()}
            {tab === "credit_notes" && renderNotas()}
          </>
        )}
      </div>
    </div>
  );
}
