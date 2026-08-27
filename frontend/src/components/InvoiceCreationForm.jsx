import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { BadgeCheck, CheckCircle2, Download, FileText, Plus, PlugZap, Save, Settings, Trash2 } from "lucide-react";
import {
  createManualInvoice, downloadInvoicePdf, downloadInvoiceXml, getAllCustomerSupplier,
  getAllProyect, getInvoiceCatalogs, getStampingConfig, previewManualInvoice,
  saveStampingConfig, testStampingConfig,
} from "../api";
import SatProductKeyField from "./SatProductKeyField";
import { useI18n } from "../i18n";

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
  const isAdmin = Boolean(currentUser.is_superuser || currentUser.is_bootstrap_admin || String(currentUser.user_type || "").toLowerCase() === "admin");
  const [contacts, setContacts] = useState([]);
  const [projects, setProjects] = useState([]);
  const [catalogs, setCatalogs] = useState({});
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pacOpen, setPacOpen] = useState(false);
  const [pacTesting, setPacTesting] = useState(false);
  const [pacSaving, setPacSaving] = useState(false);
  const [pacResult, setPacResult] = useState(null);
  const [pacConfig, setPacConfig] = useState({ provider: "fake", facturama_username: "", facturama_password: "", facturama_base_url: "", expedition_place: "", name_id: "1", has_password: false });
  const [form, setForm] = useState({
    id_proyect: currentUser.id_proyect || "", id_customer_supplier: "", id_issuer_customer_supplier: "",
    date_emision: today(), date_expiration: afterDays(30), currency: "MXN", type_exchange_rate: "1",
    rfc: "", razon_social_fiscal: "", regimen_fiscal: "", cp_fiscal: "", uso_cfdi: "G03",
    forma_pago: "03", metodo_pago: "PUE", iva_tipo: "16", ret_preset: "none",
    isr_ret_rate: 0, iva_ret_rate: 0, condiciones_pago: "", notas: "", concepts: [newConcept()],
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
      if (configPayload) setPacConfig((current) => ({ ...current, ...configPayload, facturama_password: "" }));
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
      const response = await createManualInvoice({ ...payload, stamp_now: true, idempotency_key: crypto.randomUUID() });
      setResult(response); await onCreated?.();
      const status = response.operation?.status;
      setNotice(status === "stamped" ? t("invoice_creation.stamped_success") : status === "rejected" ? t("invoice_creation.stamp_rejected") : t("invoice_creation.simulated_success"));
    } catch (requestError) { setError(readableError(requestError)); }
    finally { setBusy(false); }
  }

  async function handlePacTest() {
    setPacTesting(true); setPacResult(null);
    try { setPacResult(await testStampingConfig(pacConfig)); } catch (requestError) { setPacResult({ ok: false, message: readableError(requestError) }); }
    finally { setPacTesting(false); }
  }
  async function handlePacSave() {
    setPacSaving(true); setError("");
    try { const saved = await saveStampingConfig(pacConfig); setPacConfig((current) => ({ ...current, ...saved, facturama_password: "" })); setPacResult({ ok: true, message: t("invoice_creation.config_saved") }); }
    catch (requestError) { setError(readableError(requestError)); }
    finally { setPacSaving(false); }
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
      <div className="invoice-creation-heading"><div><p className="eyebrow">CFDI 4.0</p><h3>{t("invoice_creation.new_invoice", "Nueva factura")}</h3><p>{t("invoice_creation.subtitle", "Captura, valida y timbra con el PAC configurado.")}</p></div>{isAdmin && <button className="button ghost" type="button" onClick={() => setPacOpen((open) => !open)}><Settings size={16} />{t("invoice_creation.configure_facturama", "Configurar Facturama")}</button>}</div>

      {isAdmin && pacOpen && <section className="invoice-pac-panel">
        <div className="form-header"><PlugZap size={18} /><strong>{t("invoice_creation.stamping_connection", "Conexión de timbrado")}</strong></div>
        <div className="form-grid">
          <label className="field"><span>{t("invoice_creation.provider", "Proveedor")}</span><select value={pacConfig.provider} onChange={(event) => setPacConfig((current) => ({ ...current, provider: event.target.value }))}><option value="fake">{t("invoice_creation.provider_fake", "Simulado, sin validez fiscal")}</option><option value="facturama_sandbox">{t("invoice_creation.provider_sandbox", "Facturama · Pruebas")}</option><option value="facturama">{t("invoice_creation.provider_production", "Facturama · Producción")}</option></select></label>
          {pacConfig.provider !== "fake" && <><label className="field"><span>{t("invoice_creation.facturama_user", "Usuario Facturama")}</span><input value={pacConfig.facturama_username} onChange={(event) => setPacConfig((current) => ({ ...current, facturama_username: event.target.value }))} /></label><label className="field"><span>{t("invoice_creation.password", "Contraseña")} {pacConfig.has_password && <small>{t("invoice_creation.saved", "guardada")}</small>}</span><input type="password" autoComplete="new-password" placeholder={pacConfig.has_password ? t("invoice_creation.keep_saved_password", "Conservar contraseña guardada") : ""} value={pacConfig.facturama_password} onChange={(event) => setPacConfig((current) => ({ ...current, facturama_password: event.target.value }))} /></label><label className="field"><span>{t("invoice_creation.expedition_place", "Lugar de expedición")}</span><input inputMode="numeric" maxLength="5" value={pacConfig.expedition_place} onChange={(event) => setPacConfig((current) => ({ ...current, expedition_place: event.target.value.replace(/\D/g, "") }))} /></label><label className="field"><span>{t("invoice_creation.name_id", "Name ID / perfil")}</span><input value={pacConfig.name_id} onChange={(event) => setPacConfig((current) => ({ ...current, name_id: event.target.value }))} /></label></>}
        </div>
        {pacResult && <div className={`alert ${pacResult.ok ? "success" : "error"}`}>{pacResult.message}</div>}
        <div className="form-actions"><button className="button" type="button" disabled={pacTesting} onClick={handlePacTest}><PlugZap size={16} />{pacTesting ? t("invoice_creation.testing") : t("invoice_creation.test_connection")}</button><button className="button primary" type="button" disabled={pacSaving} onClick={handlePacSave}><Save size={16} />{pacSaving ? t("invoice_creation.saving") : t("invoice_creation.save_config")}</button></div>
      </section>}

      {error && <div className="alert error">{t(error, error)}</div>}{notice && <div className="alert success">{t(notice, notice)}</div>}
      {result ? <section className="invoice-result-panel"><CheckCircle2 size={28} /><div><strong>{t(notice, notice)}</strong><p>{t("manual_invoice.invoice", "Factura")} #{result.invoice?.id_invoice} · UUID {result.invoice?.folio_fiscal || result.operation?.provider_reference || t("invoice_creation.unassigned", "No asignado")} · {money(result.invoice?.total, lang)}</p></div><div className="form-actions"><button className="button" type="button" onClick={() => download("pdf")}><FileText size={16} />PDF</button>{result.operation?.status === "stamped" && <button className="button" type="button" onClick={() => download("xml")}><Download size={16} />XML</button>}<button className="button primary" type="button" onClick={() => { setResult(null); setPreview(null); setNotice(""); setForm((current) => ({ ...current, concepts: [newConcept()] })); }}>{t("invoice_creation.new_invoice", "Nueva factura")}</button></div></section> :
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

        <section className="invoice-create-section"><div className="form-header"><strong>{t("manual_invoice.concepts", "Conceptos")}</strong><button className="button" type="button" onClick={() => setForm((current) => ({ ...current, concepts: [...current.concepts, newConcept()] }))}><Plus size={16} />{t("manual_invoice.add", "Agregar")}</button></div><div className="invoice-concept-list">{form.concepts.map((concept, index) => <div className="invoice-concept-row" key={concept.key}><strong>{index + 1}</strong><label className="field concept-description"><span>{t("manual_invoice.description", "Descripción")}</span><input required value={concept.descripcion} onChange={(event) => updateConcept(concept.key, "descripcion", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.quantity", "Cantidad")}</span><input required type="number" min="0.0001" step="any" value={concept.cantidad} onChange={(event) => updateConcept(concept.key, "cantidad", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.unit_price", "Precio unitario")}</span><input required type="number" min="0" step="0.01" value={concept.valor_unitario} onChange={(event) => updateConcept(concept.key, "valor_unitario", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.discount", "Descuento")}</span><input type="number" min="0" step="0.01" value={concept.descuento} onChange={(event) => updateConcept(concept.key, "descuento", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.sat_product_key", "Clave producto SAT")}</span><SatProductKeyField required value={concept.clave_prod_serv} onChange={(clave) => updateConcept(concept.key, "clave_prod_serv", clave)} onDescriptionPick={(description) => { if (!concept.descripcion) updateConcept(concept.key, "descripcion", description); }} /></label><label className="field"><span>{t("manual_invoice.sat_unit_key", "Clave unidad")}</span><select value={concept.clave_unidad} onChange={(event) => updateConcept(concept.key, "clave_unidad", event.target.value)}>{options(catalogs.clave_unidad)}</select></label><button className="icon-button" title={t("manual_invoice.delete_concept", "Eliminar concepto")} aria-label={t("manual_invoice.delete_concept", "Eliminar concepto")} type="button" disabled={form.concepts.length === 1} onClick={() => setForm((current) => ({ ...current, concepts: current.concepts.filter((item) => item.key !== concept.key) }))}><Trash2 size={16} /></button></div>)}</div></section>

        <section className="invoice-create-section"><div className="form-header"><strong>{t("invoice_creation.payment_taxes_dates", "Pago, impuestos y fechas")}</strong></div><div className="form-grid">
          <label className="field"><span>{t("manual_invoice.payment_form", "Forma de pago")}</span><select value={form.forma_pago} onChange={(event) => update("forma_pago", event.target.value)}>{options(catalogs.forma_pago)}</select></label><label className="field"><span>{t("manual_invoice.payment_method", "Método de pago")}</span><select value={form.metodo_pago} onChange={(event) => setPaymentMethod(event.target.value)}>{options(catalogs.metodo_pago)}</select></label><label className="field"><span>{t("invoice_creation.vat_treatment", "Tratamiento de IVA")}</span><select value={form.iva_tipo} onChange={(event) => update("iva_tipo", event.target.value)}><option value="16">{t("invoice_creation.vat_16", "IVA 16%")}</option><option value="8">{t("invoice_creation.vat_border_8", "IVA 8% frontera")}</option><option value="0">{t("invoice_creation.vat_zero", "IVA tasa 0%")}</option><option value="exento">{t("invoice_creation.vat_exempt", "Exento")}</option><option value="sin_iva">{t("invoice_creation.vat_not_subject", "No objeto de IVA")}</option></select></label><label className="field"><span>{t("invoice_creation.retentions", "Retenciones")}</span><select value={form.ret_preset} onChange={(event) => applyRetentionPreset(event.target.value)}>{Object.entries(RETENTION_PRESETS).map(([key, preset]) => <option key={key} value={key}>{t(preset.labelKey)}</option>)}</select></label><label className="field"><span>{t("manual_invoice.issue_date", "Emisión")}</span><input type="date" required value={form.date_emision} onChange={(event) => update("date_emision", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.due_date", "Vencimiento")}</span><input type="date" required value={form.date_expiration} onChange={(event) => update("date_expiration", event.target.value)} /></label><label className="field"><span>{t("manual_invoice.currency", "Moneda")}</span><select value={form.currency} onChange={(event) => update("currency", event.target.value)}><option value="MXN">MXN</option><option value="USD">USD</option></select></label>{form.currency !== "MXN" && <label className="field"><span>{t("invoice_creation.exchange_rate", "Tipo de cambio")}</span><input type="number" min="0.0001" step="0.0001" value={form.type_exchange_rate} onChange={(event) => update("type_exchange_rate", event.target.value)} /></label>}<label className="field wide-field"><span>{t("invoice_creation.payment_terms", "Condiciones de pago")}</span><input maxLength="100" value={form.condiciones_pago} onChange={(event) => update("condiciones_pago", event.target.value)} /></label><label className="field wide-field"><span>{t("invoice_creation.notes", "Notas")}</span><input maxLength="300" value={form.notas} onChange={(event) => update("notas", event.target.value)} /></label>
        </div></section>

        <aside className="invoice-live-preview" aria-live="polite"><div><span>{t("manual_invoice.subtotal", "Subtotal")}</span><strong>{money(preview?.subtotal, lang)}</strong></div><div><span>{t("manual_invoice.discount", "Descuento")}</span><strong>-{money(preview?.discount, lang)}</strong></div><div><span>{t("manual_invoice.tax", "IVA")}</span><strong>{money(preview?.iva, lang)}</strong></div>{Number(preview?.isr_retention || 0) > 0 && <div><span>{t("manual_invoice.isr_short", "Ret. ISR")}</span><strong>-{money(preview?.isr_retention, lang)}</strong></div>}{Number(preview?.iva_retention || 0) > 0 && <div><span>{t("manual_invoice.iva_short", "Ret. IVA")}</span><strong>-{money(preview?.iva_retention, lang)}</strong></div>}<div className="invoice-preview-total"><span>{t("manual_invoice.total", "Total")}</span><strong>{money(preview?.total, lang)}</strong></div></aside>
        {preview?.errors?.length > 0 && <div className="alert error">{preview.errors.join(" · ")}</div>}
        <div className="form-actions"><button className="button primary" type="submit" disabled={busy || !preview?.can_create}><BadgeCheck size={17} />{busy ? t("invoice_creation.stamping", "Timbrando...") : pacConfig.provider === "fake" ? t("invoice_creation.create_simulated", "Crear CFDI simulado") : t("invoice_creation.stamp_invoice", "Timbrar factura")}</button></div>
      </form>}
    </div>
  );
}

InvoiceCreationForm.propTypes = {
  onCreated: PropTypes.func,
};
