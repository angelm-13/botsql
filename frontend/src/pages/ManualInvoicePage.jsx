import { useEffect, useState } from "react";
import { BadgeCheck, Download, FileCheck2, FileText, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { createManualInvoice, downloadInvoicePdf, downloadInvoiceXml, getAllCustomerSupplier, getAllProyect, getInvoiceCatalogs, preflightInvoiceStamping, previewManualInvoice, stampInvoice } from "../api";
import { stampingOutcome } from "../utils/stampingOutcome";
import SatProductKeyField from "../components/SatProductKeyField";
import { useI18n } from "../i18n";

function asArray(payload) {
  if (Array.isArray(payload?.items)) return payload.items;
  return Array.isArray(payload) ? payload : [];
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function afterDays(days) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
}

function newConcept() {
  return {
    key: crypto.randomUUID(), description: "", quantity: "1", unit_price: "0",
    discount: "0", sat_product_key: "", sat_unit_key: "E48", tax_object: "02",
    iva_exempt: false,
  };
}

// Opciones ordenadas a partir de un catalogo {clave: descripcion} del backend.
function options(catalog) {
  return Object.entries(catalog || {}).sort(([a], [b]) => a.localeCompare(b));
}

// El SAT solo acepta ciertos regimenes del receptor para cada UsoCFDI.
function allowedCfdiUses(catalogs, receiverRegime) {
  const uses = options(catalogs?.uso_cfdi);
  if (!receiverRegime) return uses;
  const matrix = catalogs?.uso_regimenes_validos || {};
  const compatible = uses.filter(([code]) => (matrix[code] || []).includes(receiverRegime));
  return compatible.length ? compatible : uses;
}

function money(value, locale) {
  return Number(value || 0).toLocaleString(locale, { style: "currency", currency: "MXN" });
}

export default function ManualInvoicePage() {
  const { lang, t } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null") || {};
  const [contacts, setContacts] = useState([]);
  const [projects, setProjects] = useState([]);
  const [catalogs, setCatalogs] = useState(null);
  const [preflight, setPreflight] = useState(null);
  const [concepts, setConcepts] = useState([newConcept()]);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [createdInvoice, setCreatedInvoice] = useState(null);
  const [form, setForm] = useState({
    id_proyect: currentUser.id_proyect || "",
    id_customer_supplier: "",
    id_issuer_customer_supplier: "",
    date_emision: today(),
    date_expiration: afterDays(30),
    currency: "MXN",
    type_exchange_rate: "1",
    forma_pago: "03",
    metodo_pago: "PUE",
    uso_cfdi: "G03",
    iva_tipo: "16",
    iva_rate: "16",
    isr_ret_rate: "0",
    iva_ret_rate: "0",
    condiciones_pago: "",
    notas: "",
  });

  useEffect(() => {
    Promise.all([getAllCustomerSupplier({ per_page: 500 }), getAllProyect({ per_page: 500 }), getInvoiceCatalogs()])
      .then(([contactPayload, projectPayload, catalogPayload]) => {
        setContacts(asArray(contactPayload));
        setProjects(asArray(projectPayload));
        setCatalogs(catalogPayload);
      })
      .catch((requestError) => setError(requestError.message || "manual_invoice.error_catalogs"));
  }, []);

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setPreview(null);
  }

  function updateConcept(key, field, value) {
    setConcepts((current) => current.map((item) => item.key === key ? { ...item, [field]: value } : item));
    setPreview(null);
  }

  function payload() {
    return { ...form, concepts: concepts.map((concept) => {
      const payloadConcept = { ...concept };
      delete payloadConcept.key;
      return payloadConcept;
    }) };
  }

  function readableError(requestError) {
    const response = requestError?.payload || requestError?.response?.data || {};
    if (Array.isArray(response?.meta?.errors)) return response.meta.errors.join(" · ");
    return response.error || response.error_key || requestError.message || t("manual_invoice.error_request");
  }

  async function handlePreview() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setPreview(await previewManualInvoice(payload()));
    } catch (requestError) {
      setPreview(null);
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate(event) {
    event.preventDefault();
    if (!preview?.can_create) return;
    setBusy(true);
    setError("");
    try {
      const result = await createManualInvoice(payload());
      setMessage(`${t("manual_invoice.invoice_number")} #${result.invoice.id_invoice} ${t("manual_invoice.saved_success")}`);
      setCreatedInvoice(result.invoice);
      setConcepts([newConcept()]);
      setPreview(null);
      setPreflight(null);
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  }

  function saveBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handlePreflight() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setPreflight(await preflightInvoiceStamping(createdInvoice.id_invoice));
    } catch (requestError) {
      setPreflight(null);
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function handleStamp() {
    setBusy(true);
    setError("");
    try {
      const result = await stampInvoice(createdInvoice.id_invoice);
      const outcome = stampingOutcome(result);
      if (!outcome.ok) {
        setError(outcome.message);
        return;
      }
      setCreatedInvoice((current) => ({ ...current, folio_fiscal: result.operation.provider_reference }));
      setMessage(`${t("manual_invoice.invoice")} #${createdInvoice.id_invoice} ${t("manual_invoice.stamped_success")}`);
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload(type) {
    try {
      const blob = type === "xml" ? await downloadInvoiceXml(createdInvoice.id_invoice) : await downloadInvoicePdf(createdInvoice.id_invoice);
      saveBlob(blob, `${type === "xml" ? "CFDI" : t("manual_invoice.invoice")}-${createdInvoice.id_invoice}.${type}`);
    } catch (requestError) {
      setError(readableError(requestError));
    }
  }

  const clients = contacts.filter((item) => !item.type || item.type === "client");
  // Igual que InvoiceCreationForm.jsx: is_principal es la propia empresa
  // (venta), type "supplier" cubre registrar una compra de un proveedor real.
  const issuers = contacts.filter((item) => item.is_principal || item.type === "supplier");
  const receiver = clients.find((item) => String(item.id_customer_supplier) === String(form.id_customer_supplier));
  // Los codigos vienen del backend, que es la misma fuente que valida el
  // timbrado: asi no se puede capturar una clave que el SAT rechazaria.
  const paymentForms = options(catalogs?.forma_pago);
  const taxObjects = options(catalogs?.objeto_imp);
  const cfdiUses = allowedCfdiUses(catalogs, receiver?.fiscal_type);
  const percentages = (rates) => ["0", ...(rates || []).filter((rate) => Number(rate) > 0).map((rate) => String(Number(rate) * 100))];
  const isrRetentions = percentages(catalogs?.tasas_isr_retencion);
  const ivaRetentions = percentages(catalogs?.tasas_iva_retencion);

  return (
    <section className="entity-page quotation-page">
      <div className="entity-heading">
        <div><h1>{t("manual_invoice.title")}</h1><p className="quotation-subtitle">{t("manual_invoice.subtitle")}</p></div>
        <FileText size={30} aria-hidden="true" />
      </div>

      <form className="form-card quotation-form" onSubmit={handleCreate}>
        <div className="form-header quotation-section-title"><h2>{t("manual_invoice.document_data")}</h2></div>
        <div className="form-grid">
          <label className="field">{t("manual_invoice.project")}<select required value={form.id_proyect} onChange={(event) => updateForm("id_proyect", event.target.value)}><option value="">{t("manual_invoice.select")}</option>{projects.map((item) => <option key={item.id_proyect} value={item.id_proyect}>{item.title || item.proyect_description}</option>)}</select></label>
          <label className="field">{t("manual_invoice.receiver")}<select required value={form.id_customer_supplier} onChange={(event) => updateForm("id_customer_supplier", event.target.value)}><option value="">{t("manual_invoice.select")}</option>{clients.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name} · {item.tax_id || t("manual_invoice.no_tax_id")}</option>)}</select></label>
          <label className="field">{t("manual_invoice.issuer")}<select required value={form.id_issuer_customer_supplier} onChange={(event) => updateForm("id_issuer_customer_supplier", event.target.value)}><option value="">{t("manual_invoice.select")}</option>{issuers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name} · {item.tax_id || t("manual_invoice.no_tax_id")}</option>)}</select></label>
          <label className="field">{t("manual_invoice.issue_date")}<input required type="date" value={form.date_emision} onChange={(event) => updateForm("date_emision", event.target.value)} /></label>
          <label className="field">{t("manual_invoice.due_date")}<input required type="date" value={form.date_expiration} onChange={(event) => updateForm("date_expiration", event.target.value)} /></label>
          <label className="field">{t("manual_invoice.currency")}<select value={form.currency} onChange={(event) => updateForm("currency", event.target.value)}><option value="MXN">MXN</option><option value="USD">USD</option><option value="EUR">EUR</option></select></label>
          {form.currency !== "MXN" && <label className="field">{t("manual_invoice.exchange_rate")}<input required min="0.000001" step="0.000001" type="number" value={form.type_exchange_rate} onChange={(event) => updateForm("type_exchange_rate", event.target.value)} /></label>}
          <label className="field">{t("manual_invoice.payment_form")}<select value={form.forma_pago} onChange={(event) => updateForm("forma_pago", event.target.value)}>{paymentForms.map(([code, label]) => <option key={code} value={code}>{code} · {label}</option>)}</select></label>
          <label className="field">{t("manual_invoice.payment_method")}<select value={form.metodo_pago} onChange={(event) => updateForm("metodo_pago", event.target.value)}>{options(catalogs?.metodo_pago).map(([code, label]) => <option key={code} value={code}>{code} · {label}</option>)}</select></label>
          <label className="field">{t("manual_invoice.cfdi_use")}<select value={form.uso_cfdi} onChange={(event) => updateForm("uso_cfdi", event.target.value)}>{cfdiUses.map(([code, label]) => <option key={code} value={code}>{code} · {label}</option>)}</select></label>
          <label className="field">{t("manual_invoice.iva_type")}<select value={form.iva_tipo} onChange={(event) => updateForm("iva_tipo", event.target.value)}><option value="16">16%</option><option value="8">8% ({t("manual_invoice.border_rate")})</option><option value="0">0% ({t("manual_invoice.zero_rate")})</option><option value="exento">{t("manual_invoice.exempt")}</option><option value="sin_iva">{t("manual_invoice.not_taxable")}</option></select></label>
          <label className="field">{t("manual_invoice.isr_retention")}<select value={form.isr_ret_rate} onChange={(event) => updateForm("isr_ret_rate", event.target.value)}>{isrRetentions.map((rate) => <option key={rate} value={rate}>{rate}%</option>)}</select></label>
          <label className="field">{t("manual_invoice.iva_retention")}<select value={form.iva_ret_rate} onChange={(event) => updateForm("iva_ret_rate", event.target.value)}>{ivaRetentions.map((rate) => <option key={rate} value={rate}>{rate}%</option>)}</select></label>
        </div>

        <div className="quotation-items-card">
          <div className="form-header quotation-section-title"><h2>{t("manual_invoice.concepts")}</h2><button className="button" type="button" onClick={() => setConcepts((current) => [...current, newConcept()])}><Plus size={16} />{t("manual_invoice.add")}</button></div>
          {concepts.map((concept, index) => (
            <div className="quotation-line-item" key={concept.key}>
              <div className="quotation-line-head"><strong>{t("manual_invoice.concept")} {index + 1}</strong><button className="icon-button" title={t("manual_invoice.delete_concept")} type="button" disabled={concepts.length === 1} onClick={() => setConcepts((current) => current.filter((item) => item.key !== concept.key))}><Trash2 size={16} /></button></div>
              <div className="form-grid quotation-item-grid">
                <label className="field">{t("manual_invoice.description")}<input required value={concept.description} onChange={(event) => updateConcept(concept.key, "description", event.target.value)} /></label>
                <label className="field">{t("manual_invoice.sat_product_key")}<SatProductKeyField required value={concept.sat_product_key} onChange={(clave) => updateConcept(concept.key, "sat_product_key", clave)} onDescriptionPick={(description) => { if (!concept.description) updateConcept(concept.key, "description", description); }} /></label>
                <label className="field">{t("manual_invoice.sat_unit_key")}<input required list="sat-unit-keys" maxLength="3" value={concept.sat_unit_key} onChange={(event) => updateConcept(concept.key, "sat_unit_key", event.target.value.toUpperCase())} /></label>
                <label className="field">{t("manual_invoice.quantity")}<input required min="0.0001" step="0.0001" type="number" value={concept.quantity} onChange={(event) => updateConcept(concept.key, "quantity", event.target.value)} /></label>
                <label className="field">{t("manual_invoice.unit_price")}<input required min="0" step="0.01" type="number" value={concept.unit_price} onChange={(event) => updateConcept(concept.key, "unit_price", event.target.value)} /></label>
                <label className="field">{t("manual_invoice.discount")}<input min="0" step="0.01" type="number" value={concept.discount} onChange={(event) => updateConcept(concept.key, "discount", event.target.value)} /></label>
                <label className="field">{t("manual_invoice.tax_object")}<select value={concept.tax_object} onChange={(event) => updateConcept(concept.key, "tax_object", event.target.value)}>{taxObjects.map(([code, label]) => <option key={code} value={code}>{code} · {label}</option>)}</select></label>
              </div>
            </div>
          ))}
        </div>

        {error && <div className="alert error">{t(error, error)}</div>}
        {message && <div className="alert success">{message}</div>}
        {createdInvoice && <div className="form-actions">{!createdInvoice.folio_fiscal && <button className="button" type="button" disabled={busy} onClick={handlePreflight}><ShieldCheck size={16} />{t("manual_invoice.preflight")}</button>}{!createdInvoice.folio_fiscal && <button className="button primary" type="button" disabled={busy} onClick={handleStamp}><BadgeCheck size={16} />{t("manual_invoice.stamp")}</button>}<button className="button" type="button" onClick={() => handleDownload("pdf")}><FileText size={16} />PDF</button>{createdInvoice.folio_fiscal && <button className="button" type="button" onClick={() => handleDownload("xml")}><Download size={16} />XML</button>}</div>}
        {preflight && (
          <div className={`alert ${preflight.can_stamp ? "success" : "error"}`}>
            <strong>{preflight.can_stamp ? t("manual_invoice.preflight_ready") : t("manual_invoice.preflight_blocked")}</strong>
            {` · ${t("manual_invoice.total")} ${money(preflight.totals?.total, lang)}`}
            {preflight.errors?.length > 0 && <ul>{preflight.errors.map((key) => <li key={key}>{t(key, key)}</li>)}</ul>}
            {preflight.warnings?.length > 0 && <ul>{preflight.warnings.map((key) => <li key={key}>{t(key, key)}</li>)}</ul>}
          </div>
        )}
        {preview && <div className="quotation-totals"><span>{t("manual_invoice.subtotal")} <strong>{money(preview.subtotal, lang)}</strong></span><span>{t("manual_invoice.discount")} <strong>{money(preview.discount, lang)}</strong></span><span>{t("manual_invoice.tax")} <strong>{money(preview.iva, lang)}</strong></span><span>{t("manual_invoice.isr_short")} <strong>-{money(preview.isr_retention, lang)}</strong></span><span>{t("manual_invoice.iva_short")} <strong>-{money(preview.iva_retention, lang)}</strong></span><span>{t("manual_invoice.total")} <strong>{money(preview.total, lang)}</strong></span></div>}
        {preview?.errors?.length > 0 && <div className="alert error">{preview.errors.join(" · ")}</div>}
        <div className="form-actions"><button className="button" type="button" disabled={busy} onClick={handlePreview}><FileCheck2 size={16} />{t("manual_invoice.preview")}</button><button className="button primary" type="submit" disabled={busy || !preview?.can_create}>{t("manual_invoice.save_invoice")}</button></div>
        <datalist id="sat-unit-keys">
          {options(catalogs?.clave_unidad).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
        </datalist>
      </form>
    </section>
  );
}