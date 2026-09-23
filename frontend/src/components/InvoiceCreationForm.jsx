import { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { BadgeCheck, CheckCircle2, Download, FileText, Plus, Trash2 } from "lucide-react";
import {
  createManualInvoice, downloadInvoicePdf, downloadInvoiceXml, getAllCustomerSupplier,
  getAllProyect, getInvoiceCatalogs, getStampingConfig, previewManualInvoice, searchSatProductKeys,
} from "../api";
import SatProductKeyField from "./SatProductKeyField";
import { useI18n } from "../i18n";

const DESCRIPTION_SUGGEST_DEBOUNCE_MS = 400;
const DESCRIPTION_SUGGEST_MIN_LENGTH = 4;

/**
 * Mientras se captura la descripcion de un concepto, sugiere la clave del SAT
 * que le corresponde -- sin esto hay que abrir aparte el buscador de la Clave
 * producto SAT y volver a escribir lo mismo. Se apaga sola en cuanto el
 * concepto ya tiene una clave (elegida aqui o desde ese otro buscador).
 */
function ConceptDescriptionField({ value, claveProdServ, onChangeDescription, onPickClave, t }) {
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const requestRef = useRef(0);

  useEffect(() => {
    const text = value.trim();
    if (claveProdServ || text.length < DESCRIPTION_SUGGEST_MIN_LENGTH) {
      setResults([]);
      setNotice("");
      setOpen(false);
      return undefined;
    }
    const ticket = requestRef.current + 1;
    requestRef.current = ticket;
    const timer = window.setTimeout(() => {
      setBusy(true);
      searchSatProductKeys(text, 6)
        .then((payload) => {
          if (requestRef.current !== ticket) return;
          const items = payload?.items || [];
          setResults(items);
          setNotice(payload?.catalog_loaded === false ? t("sat_catalog.not_loaded", "El catálogo del SAT no está cargado. Pide que se importe para poder buscar.") : "");
          setOpen(true);
        })
        .catch(() => {
          if (requestRef.current === ticket) { setResults([]); setOpen(false); }
        })
        .finally(() => {
          if (requestRef.current === ticket) setBusy(false);
        });
    }, DESCRIPTION_SUGGEST_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [value, claveProdServ, t]);

  return (
    <label className="field concept-description concept-description-suggest">
      <span>{t("manual_invoice.description", "Descripción")}</span>
      <input
        required
        value={value}
        onChange={(event) => onChangeDescription(event.target.value)}
        onFocus={() => { if (results.length || notice) setOpen(true); }}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open && !claveProdServ && (
        <div className="sat-key-popover">
          {busy && <p className="sat-key-message">{t("sat_catalog.searching", "Buscando en el catálogo del SAT...")}</p>}
          {!busy && notice && <p className="sat-key-message error">{notice}</p>}
          {!busy && !notice && !results.length && (
            <p className="sat-key-message">{t("sat_catalog.no_results", "Sin resultados. Prueba con otra palabra.")}</p>
          )}
          {!busy && Boolean(results.length) && (
            <ul className="sat-key-results">
              {results.map((item) => (
                <li key={item.clave}>
                  <button type="button" onMouseDown={(event) => { event.preventDefault(); onPickClave(item.clave); setOpen(false); }}>
                    <span className="sat-key-code">{item.clave}</span>
                    <span className="sat-key-description">{item.description}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </label>
  );
}

ConceptDescriptionField.propTypes = {
  value: PropTypes.string.isRequired,
  claveProdServ: PropTypes.string,
  onChangeDescription: PropTypes.func.isRequired,
  onPickClave: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};

const RETENTION_PRESETS = {
  none: { labelKey: "invoice_creation.retention_none", isr: 0, iva: 0 },
  serv_612: { labelKey: "invoice_creation.retention_professional_services", isr: 10, iva: 10.6667 },
  resico_serv: { labelKey: "invoice_creation.retention_resico_services", isr: 1.25, iva: 10.6667 },
  resico_bienes: { labelKey: "invoice_creation.retention_resico_goods", isr: 1.25, iva: 0 },
  autotransporte: { labelKey: "invoice_creation.retention_freight", isr: 0, iva: 4 },
};

function today() { return new Date().toISOString().slice(0, 10); }
function afterDays(days) { const date = new Date(); date.setDate(date.getDate() + days); return date.toISOString().slice(0, 10); }
function asItems(payload) { return Array.isArray(payload) ? payload : payload?.items || payload?.data || []; }
function newConcept() { return { key: crypto.randomUUID(), descripcion: "", cantidad: "1", valor_unitario: "0", descuento: "0", clave_prod_serv: "", clave_unidad: "H87", objeto_imp: "02" }; }
function options(catalog) { return Object.entries(catalog || {}).map(([code, label]) => <option key={code} value={code}>{code} · {label}</option>); }
function money(value, lang) { return Number(value || 0).toLocaleString(lang, { style: "currency", currency: "MXN" }); }

export default function InvoiceCreationForm({ onCreated }) {
  const { lang, t } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null") || {};
  // Solo para saber si el boton dice "timbrar" o "simulado" -- la edicion de
  // la cuenta de Facturama vive en su propia pagina de Configuracion.
  const isAdmin = Boolean(currentUser.is_superuser || currentUser.is_bootstrap_admin || String(currentUser.user_type || "").toLowerCase() === "admin");
  const [stampingProvider, setStampingProvider] = useState("fake");
  const [contacts, setContacts] = useState([]);
  const [projects, setProjects] = useState([]);
  const [catalogs, setCatalogs] = useState({});
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    id_proyect: currentUser.id_proyect || "", id_customer_supplier: "", id_issuer_customer_supplier: "",
    date_emision: today(), date_expiration: afterDays(30), currency: "MXN", type_exchange_rate: "1",
    rfc: "", razon_social_fiscal: "", regimen_fiscal: "", cp_fiscal: "", uso_cfdi: "G03",
    forma_pago: "03", metodo_pago: "PUE", iva_tipo: "16", ret_preset: "none",
    isr_ret_rate: 0, iva_ret_rate: 0, condiciones_pago: "", notas: "", apply_inventory: true, concepts: [newConcept()],
  });

  useEffect(() => {
    let mounted = true;
    Promise.all([
      getAllCustomerSupplier({ page: 1, per_page: 500 }), getAllProyect({ page: 1, per_page: 500 }),
      getInvoiceCatalogs(), isAdmin ? getStampingConfig() : Promise.resolve(null),
    ]).then(([contactPayload, projectPayload, catalogPayload, configPayload]) => {
      if (!mounted) return;
      const nextContacts = asItems(contactPayload);
      const issuers = nextContacts.filter((item) => item.is_principal || item.type === "supplier");
      setContacts(nextContacts); setProjects(asItems(projectPayload)); setCatalogs(catalogPayload || {});
      if (configPayload) setStampingProvider(configPayload.provider || "fake");
      setForm((current) => ({ ...current, id_issuer_customer_supplier: current.id_issuer_customer_supplier || String(issuers[0]?.id_customer_supplier || "") }));
    }).catch((requestError) => setError(requestError.message || "invoice_creation.error_catalogs"))
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [isAdmin]);

  const payload = useMemo(() => ({
    ...form,
    concepts: form.concepts.map((concept) => {
      const payloadConcept = { ...concept };
      delete payloadConcept.key;
      return payloadConcept;
    }),
  }), [form]);

  useEffect(() => {
    if (loading || result || !form.id_proyect || !form.id_customer_supplier || !form.id_issuer_customer_supplier) { setPreview(null); return; }
    const timer = window.setTimeout(() => {
      previewManualInvoice(payload).then((data) => { setPreview(data); setError(""); }).catch((requestError) => { setPreview(null); setError(readableError(requestError)); });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [loading, payload, result, form.id_proyect, form.id_customer_supplier, form.id_issuer_customer_supplier]);

  function readableError(requestError) {
    const response = requestError?.payload || {};
    if (Array.isArray(response?.meta?.errors)) return response.meta.errors.join(" · ");
    return response.error || response.error_key || requestError.message || "invoice_creation.error_request";
  }
  function update(field, value) { setForm((current) => ({ ...current, [field]: value })); setResult(null); }
  function updateConcept(key, field, value) { setForm((current) => ({ ...current, concepts: current.concepts.map((item) => item.key === key ? { ...item, [field]: value } : item) })); }
  function pickClient(id) {
    const client = contacts.find((item) => String(item.id_customer_supplier) === String(id));
    setForm((current) => ({ ...current, id_customer_supplier: id, rfc: client?.tax_id || "", razon_social_fiscal: client?.name || "", regimen_fiscal: client?.fiscal_type || "", cp_fiscal: client?.postal_code || "", uso_cfdi: current.uso_cfdi === "P01" ? "G03" : current.uso_cfdi }));
  }
  function applyRetentionPreset(key) { const preset = RETENTION_PRESETS[key] || RETENTION_PRESETS.none; setForm((current) => ({ ...current, ret_preset: key, isr_ret_rate: preset.isr, iva_ret_rate: preset.iva })); }
  function setPaymentMethod(value) { setForm((current) => ({ ...current, metodo_pago: value, forma_pago: value === "PPD" ? "99" : current.forma_pago === "99" ? "03" : current.forma_pago })); }

  async function handleCreate(event) {
    event.preventDefault();
    if (!preview?.can_create) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await createManualInvoice({ ...payload, stamp_now: true, apply_inventory: Boolean(form.apply_inventory), idempotency_key: crypto.randomUUID() });
      setResult(response); await onCreated?.();
      const status = response.operation?.status;
      setNotice(status === "stamped" ? t("invoice_creation.stamped_success") : status === "rejected" ? t("invoice_creation.stamp_rejected") : t("invoice_creation.simulated_success"));
    } catch (requestError) { setError(readableError(requestError)); }
    finally { setBusy(false); }
  }

  async function download(type) {
    const invoice = result?.invoice;
    if (!invoice) return;
    try {
      const blob = type === "xml" ? await downloadInvoiceXml(invoice.id_invoice) : await downloadInvoicePdf(invoice.id_invoice);
      const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `${type === "xml" ? "CFDI" : "Factura"}-${invoice.id_invoice}.${type}`; link.click(); URL.revokeObjectURL(url);
    } catch (requestError) { setError(readableError(requestError)); }
  }

  const clients = contacts.filter((item) => !item.type || item.type === "client");
  const issuers = contacts.filter((item) => item.is_principal || item.type === "supplier");
  const validUses = Object.fromEntries(Object.entries(catalogs.uso_cfdi || {}).filter(([code]) => !form.regimen_fiscal || (catalogs.uso_regimenes_validos?.[code] || []).includes(form.regimen_fiscal)));

  if (loading) return <div className="empty">{t("invoice_creation.loading_form", "Cargando formulario fiscal...")}</div>;
  return (
    <div className="invoice-creation-workspace">
      <div className="invoice-creation-heading"><div><p className="eyebrow">CFDI 4.0</p><h3>{t("invoice_creation.new_invoice", "Nueva factura")}</h3><p>{t("invoice_creation.subtitle", "Captura, valida y timbra con el PAC configurado.")}</p></div></div>

      {error && <div className="alert error">{t(error, error)}</div>}{notice && <div className="alert success">{t(notice, notice)}</div>}
      {result ? <section className="invoice-result-panel"><CheckCircle2 size={28} /><div><strong>{t(notice, notice)}</strong><p>{result.inventory?.applied_lines ? `${t("invoice_creation.inventory_moved", "Almacén actualizado")}: ${result.inventory.applied_lines} · ` : result.inventory?.error_key ? `${t(result.inventory.error_key, result.inventory.error_key)} · ` : ""}{t("manual_invoice.invoice", "Factura")} #{result.invoice?.id_invoice} · UUID {result.invoice?.folio_fiscal || result.operation?.provider_reference || t("invoice_creation.unassigned", "No asignado")} · {money(result.invoice?.total, lang)}</p></div><div className="form-actions"><button className="button" type="button" onClick={() => download("pdf")}><FileText size={16} />PDF</button>{result.operation?.status === "stamped" && <button className="button" type="button" onClick={() => download("xml")}><Download size={16} />XML</button>}<button className="button primary" type="button" onClick={() => { setResult(null); setPreview(null); setNotice(""); setForm((current) => ({ ...current, concepts: [newConcept()] })); }}>{t("invoice_creation.new_invoice", "Nueva factura")}</button></div></section> :
      <form className="form-card invoice-fiscal-form" onSubmit={handleCreate}>
        <section className="invoice-create-section"><div className="form-header"><strong>{t("invoice_creation.issuer_receiver", "Emisor y receptor")}</strong></div><div className="form-grid">
          <label className="field"><span>{t("manual_invoice.project", "Proyecto")}</span><select required value={form.id_proyect} onChange={(event) => update("id_proyect", event.target.value)}><option value="">{t("manual_invoice.select", "Seleccionar")}</option>{projects.map((item) => <option key={item.id_proyect} value={item.id_proyect}>{item.proyect_description || item.title}</option>)}</select></label>
          <label className="field"><span>{t("manual_invoice.issuer", "Empresa emisora")}</span><select required value={form.id_issuer_customer_supplier} onChange={(event) => update("id_issuer_customer_supplier", event.target.value)}><option value="">{t("manual_invoice.select", "Seleccionar")}</option>{issuers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name} · {item.tax_id || t("manual_invoice.no_tax_id", "Sin RFC")}</option>)}</select></label>
          <label className="field wide-field"><span>{t("manual_invoice.receiver", "Cliente receptor")}</span><select required value={form.id_customer_supplier} onChange={(event) => pickClient(event.target.value)}><option value="">{t("manual_invoice.select", "Seleccionar")}</option>{clients.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name} · {item.tax_id || t("manual_invoice.no_tax_id", "Sin RFC")}</option>)}</select></label>
          <label className="field wide-field"><span>{t("invoice_creation.fiscal_name", "Razón social fiscal")}</span><input required value={form.razon_social_fiscal} onChange={(event) => update("razon_social_fiscal", event.target.value)} /></label>
          <label className="field"><span>RFC</span><input required maxLength="13" value={form.rfc} onChange={(event) => update("rfc", event.target.value.toUpperCase())} /></label>
          <label className="field"><span>{t("invoice_creation.fiscal_regime", "Régimen fiscal")}</span><select required value={form.regimen_fiscal} onChange={(event) => update("regimen_fiscal", event.target.value)}><option value="">{t("manual_invoice.select", "Seleccionar")}</option>{options(catalogs.regimen_fiscal)}</select></label>
          <label className="field"><span>{t("invoice_creation.fiscal_postal_code", "Código postal fiscal")}</span><input required inputMode="numeric" maxLength="5" value={form.cp_fiscal} onChange={(event) => update("cp_fiscal", event.target.value.replace(/\D/g, ""))} /></label>
          <label className="field"><span>{t("manual_invoice.cfdi_use", "Uso CFDI")}</span><select required value={form.uso_cfdi} onChange={(event) => update("uso_cfdi", event.target.value)}>{options(Object.keys(validUses).length ? validUses : catalogs.uso_cfdi)}</select></label>
        </div></section>

        <section className="invoice-create-section"><div className="form-header"><strong>{t("manual_invoice.concepts", "Conceptos")}</strong><button className="button" type="button" onClick={() => setForm((current) => ({ ...current, concepts: [...current.concepts, newConcept()] }))}><Plus size={16} />{t("manual_invoice.add", "Agregar")}</button></div><div className="invoice-concept-list">{form.concepts.map((concept, index) => <div className="invoice-concept-row" key={concept.key}><strong>{index + 1}</strong><ConceptDescriptionField value={concept.descripcion} claveProdServ={concept.clave_prod_serv} onChangeDescription={(text) => updateConcept(concept.key, "descripcion", text)} onPickClave={(clave) => updateConcept(concept.key, "clave_prod_serv", clave)} t={t} /><label className="field"><span>{t("manual_invoice.quantity", "Cantidad")}</span><input required type="number" min="0.0001" step="any" value={concept.cantidad} onChange={(event) => updateConcept(concept.key, "cantidad", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.unit_price", "Precio unitario")}</span><input required type="number" min="0" step="0.01" value={concept.valor_unitario} onChange={(event) => updateConcept(concept.key, "valor_unitario", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.discount", "Descuento")}</span><input type="number" min="0" step="0.01" value={concept.descuento} onChange={(event) => updateConcept(concept.key, "descuento", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.sat_product_key", "Clave producto SAT")}</span><SatProductKeyField required value={concept.clave_prod_serv} onChange={(clave) => updateConcept(concept.key, "clave_prod_serv", clave)} onDescriptionPick={(description) => { if (!concept.descripcion) updateConcept(concept.key, "descripcion", description); }} /></label><label className="field"><span>{t("manual_invoice.sat_unit_key", "Clave unidad")}</span><select value={concept.clave_unidad} onChange={(event) => updateConcept(concept.key, "clave_unidad", event.target.value)}>{options(catalogs.clave_unidad)}</select></label><button className="icon-button" title={t("manual_invoice.delete_concept", "Eliminar concepto")} aria-label={t("manual_invoice.delete_concept", "Eliminar concepto")} type="button" disabled={form.concepts.length === 1} onClick={() => setForm((current) => ({ ...current, concepts: current.concepts.filter((item) => item.key !== concept.key) }))}><Trash2 size={16} /></button></div>)}</div></section>

        <section className="invoice-create-section"><div className="form-header"><strong>{t("invoice_creation.payment_taxes_dates", "Pago, impuestos y fechas")}</strong></div><div className="form-grid">
          <label className="field"><span>{t("manual_invoice.payment_form", "Forma de pago")}</span><select value={form.forma_pago} onChange={(event) => update("forma_pago", event.target.value)}>{options(catalogs.forma_pago)}</select></label><label className="field"><span>{t("manual_invoice.payment_method", "Método de pago")}</span><select value={form.metodo_pago} onChange={(event) => setPaymentMethod(event.target.value)}>{options(catalogs.metodo_pago)}</select></label><label className="field"><span>{t("invoice_creation.vat_treatment", "Tratamiento de IVA")}</span><select value={form.iva_tipo} onChange={(event) => update("iva_tipo", event.target.value)}><option value="16">{t("invoice_creation.vat_16", "IVA 16%")}</option><option value="8">{t("invoice_creation.vat_border_8", "IVA 8% frontera")}</option><option value="0">{t("invoice_creation.vat_zero", "IVA tasa 0%")}</option><option value="exento">{t("invoice_creation.vat_exempt", "Exento")}</option><option value="sin_iva">{t("invoice_creation.vat_not_subject", "No objeto de IVA")}</option></select></label><label className="field"><span>{t("invoice_creation.retentions", "Retenciones")}</span><select value={form.ret_preset} onChange={(event) => applyRetentionPreset(event.target.value)}>{Object.entries(RETENTION_PRESETS).map(([key, preset]) => <option key={key} value={key}>{t(preset.labelKey)}</option>)}</select></label><label className="field"><span>{t("manual_invoice.issue_date", "Emisión")}</span><input type="date" required value={form.date_emision} onChange={(event) => update("date_emision", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.due_date", "Vencimiento")}</span><input type="date" required value={form.date_expiration} onChange={(event) => update("date_expiration", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.currency", "Moneda")}</span><select value={form.currency} onChange={(event) => update("currency", event.target.value)}><option value="MXN">MXN</option><option value="USD">USD</option></select></label>{form.currency !== "MXN" && <label className="field"><span>{t("invoice_creation.exchange_rate", "Tipo de cambio")}</span><input type="number" min="0.0001" step="0.0001" value={form.type_exchange_rate} onChange={(event) => update("type_exchange_rate", event.target.value)} /></label>}<label className="field wide-field"><span>{t("invoice_creation.payment_terms", "Condiciones de pago")}</span><input maxLength="100" value={form.condiciones_pago} onChange={(event) => update("condiciones_pago", event.target.value)} /></label><label className="field wide-field"><span>{t("invoice_creation.notes", "Notas")}</span><input maxLength="300" value={form.notas} onChange={(event) => update("notas", event.target.value)} /></label>
        </div></section>

        <aside className="invoice-live-preview" aria-live="polite"><div><span>{t("manual_invoice.subtotal", "Subtotal")}</span><strong>{money(preview?.subtotal, lang)}</strong></div><div><span>{t("manual_invoice.discount", "Descuento")}</span><strong>-{money(preview?.discount, lang)}</strong></div><div><span>{t("manual_invoice.tax", "IVA")}</span><strong>{money(preview?.iva, lang)}</strong></div>{Number(preview?.isr_retention || 0) > 0 && <div><span>{t("manual_invoice.isr_short", "Ret. ISR")}</span><strong>-{money(preview?.isr_retention, lang)}</strong></div>}{Number(preview?.iva_retention || 0) > 0 && <div><span>{t("manual_invoice.iva_short", "Ret. IVA")}</span><strong>-{money(preview?.iva_retention, lang)}</strong></div>}<div className="invoice-preview-total"><span>{t("manual_invoice.total", "Total")}</span><strong>{money(preview?.total, lang)}</strong></div></aside>
        {preview?.errors?.length > 0 && <div className="alert error">{preview.errors.join(" · ")}</div>}
        <label className="field checkbox-field" title={t("invoice_creation.apply_inventory_help", "Una venta descuenta del almacén y una compra lo surte, segun la direccion de la factura.")}><input type="checkbox" checked={Boolean(form.apply_inventory)} onChange={(event) => update("apply_inventory", event.target.checked)} />{t("invoice_creation.apply_inventory", "Mover el almacén al timbrar")}</label><div className="form-actions"><button className="button primary" type="submit" disabled={busy || !preview?.can_create}><BadgeCheck size={17} />{busy ? t("invoice_creation.stamping", "Timbrando...") : stampingProvider === "fake" ? t("invoice_creation.create_simulated", "Crear CFDI simulado") : t("invoice_creation.stamp_invoice", "Timbrar factura")}</button></div>
      </form>}
    </div>
  );
}

InvoiceCreationForm.propTypes = {
  onCreated: PropTypes.func,
};
