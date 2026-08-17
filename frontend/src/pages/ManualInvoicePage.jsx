import { useEffect, useState } from "react";
import { FileCheck2, FileText, Plus, Trash2 } from "lucide-react";
import { createManualInvoice, getAllCustomerSupplier, getAllProyect, previewManualInvoice } from "../api";

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
  };
}

function money(value) {
  return Number(value || 0).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

export default function ManualInvoicePage() {
  const currentUser = JSON.parse(localStorage.getItem("user") || "null") || {};
  const [contacts, setContacts] = useState([]);
  const [projects, setProjects] = useState([]);
  const [concepts, setConcepts] = useState([newConcept()]);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    id_proyect: currentUser.id_proyect || "",
    id_customer_supplier: "",
    id_issuer_customer_supplier: "",
    date_emision: today(),
    date_expiration: afterDays(30),
    currency: "MXN",
    forma_pago: "03",
    metodo_pago: "PUE",
    uso_cfdi: "G03",
    iva_rate: "16",
    isr_ret_rate: "0",
    iva_ret_rate: "0",
    condiciones_pago: "",
    notas: "",
  });

  useEffect(() => {
    Promise.all([getAllCustomerSupplier({ per_page: 500 }), getAllProyect({ per_page: 500 })])
      .then(([contactPayload, projectPayload]) => {
        setContacts(asArray(contactPayload));
        setProjects(asArray(projectPayload));
      })
      .catch((requestError) => setError(requestError.message || "No se pudieron cargar los catálogos."));
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
    return { ...form, concepts: concepts.map(({ key, ...concept }) => concept) };
  }

  function readableError(requestError) {
    const response = requestError?.payload || requestError?.response?.data || {};
    if (Array.isArray(response?.meta?.errors)) return response.meta.errors.join(" · ");
    return response.error || response.error_key || requestError.message || "No se pudo completar la solicitud.";
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
      setMessage(`Factura manual #${result.invoice.id_invoice} guardada correctamente.`);
      setConcepts([newConcept()]);
      setPreview(null);
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  }

  const clients = contacts.filter((item) => !item.type || item.type === "client");
  const issuers = contacts.filter((item) => !item.type || item.type === "supplier");

  return (
    <section className="entity-page quotation-page">
      <div className="entity-heading">
        <div><h1>Facturación manual</h1><p className="quotation-subtitle">Captura fiscal sin cotización previa</p></div>
        <FileText size={30} aria-hidden="true" />
      </div>

      <form className="form-card quotation-form" onSubmit={handleCreate}>
        <div className="form-header quotation-section-title"><h2>Datos del comprobante</h2></div>
        <div className="form-grid">
          <label className="field">Proyecto<select required value={form.id_proyect} onChange={(event) => updateForm("id_proyect", event.target.value)}><option value="">Seleccionar</option>{projects.map((item) => <option key={item.id_proyect} value={item.id_proyect}>{item.title || item.proyect_description}</option>)}</select></label>
          <label className="field">Cliente receptor<select required value={form.id_customer_supplier} onChange={(event) => updateForm("id_customer_supplier", event.target.value)}><option value="">Seleccionar</option>{clients.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name} · {item.tax_id || "Sin RFC"}</option>)}</select></label>
          <label className="field">Empresa emisora<select required value={form.id_issuer_customer_supplier} onChange={(event) => updateForm("id_issuer_customer_supplier", event.target.value)}><option value="">Seleccionar</option>{issuers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name} · {item.tax_id || "Sin RFC"}</option>)}</select></label>
          <label className="field">Emisión<input required type="date" value={form.date_emision} onChange={(event) => updateForm("date_emision", event.target.value)} /></label>
          <label className="field">Vencimiento<input required type="date" value={form.date_expiration} onChange={(event) => updateForm("date_expiration", event.target.value)} /></label>
          <label className="field">Moneda<select value={form.currency} onChange={(event) => updateForm("currency", event.target.value)}><option value="MXN">MXN</option><option value="USD">USD</option></select></label>
          <label className="field">Forma de pago<input maxLength="2" value={form.forma_pago} onChange={(event) => updateForm("forma_pago", event.target.value)} /></label>
          <label className="field">Método de pago<select value={form.metodo_pago} onChange={(event) => updateForm("metodo_pago", event.target.value)}><option value="PUE">PUE</option><option value="PPD">PPD</option></select></label>
          <label className="field">Uso CFDI<input maxLength="4" value={form.uso_cfdi} onChange={(event) => updateForm("uso_cfdi", event.target.value)} /></label>
          <label className="field">IVA %<input min="0" max="100" step="0.0001" type="number" value={form.iva_rate} onChange={(event) => updateForm("iva_rate", event.target.value)} /></label>
          <label className="field">Retención ISR %<input min="0" max="100" step="0.0001" type="number" value={form.isr_ret_rate} onChange={(event) => updateForm("isr_ret_rate", event.target.value)} /></label>
          <label className="field">Retención IVA %<input min="0" max="100" step="0.0001" type="number" value={form.iva_ret_rate} onChange={(event) => updateForm("iva_ret_rate", event.target.value)} /></label>
        </div>

        <div className="quotation-items-card">
          <div className="form-header quotation-section-title"><h2>Conceptos</h2><button className="button" type="button" onClick={() => setConcepts((current) => [...current, newConcept()])}><Plus size={16} />Agregar</button></div>
          {concepts.map((concept, index) => (
            <div className="quotation-line-item" key={concept.key}>
              <div className="quotation-line-head"><strong>Concepto {index + 1}</strong><button className="icon-button" title="Eliminar concepto" type="button" disabled={concepts.length === 1} onClick={() => setConcepts((current) => current.filter((item) => item.key !== concept.key))}><Trash2 size={16} /></button></div>
              <div className="form-grid quotation-item-grid">
                <label className="field">Descripción<input required value={concept.description} onChange={(event) => updateConcept(concept.key, "description", event.target.value)} /></label>
                <label className="field">Clave SAT producto<input required value={concept.sat_product_key} onChange={(event) => updateConcept(concept.key, "sat_product_key", event.target.value)} /></label>
                <label className="field">Clave SAT unidad<input required value={concept.sat_unit_key} onChange={(event) => updateConcept(concept.key, "sat_unit_key", event.target.value)} /></label>
                <label className="field">Cantidad<input required min="0.0001" step="0.0001" type="number" value={concept.quantity} onChange={(event) => updateConcept(concept.key, "quantity", event.target.value)} /></label>
                <label className="field">Precio unitario<input required min="0" step="0.01" type="number" value={concept.unit_price} onChange={(event) => updateConcept(concept.key, "unit_price", event.target.value)} /></label>
                <label className="field">Descuento<input min="0" step="0.01" type="number" value={concept.discount} onChange={(event) => updateConcept(concept.key, "discount", event.target.value)} /></label>
                <label className="field">Objeto de impuesto<select value={concept.tax_object} onChange={(event) => updateConcept(concept.key, "tax_object", event.target.value)}><option value="02">02 · Sí objeto</option><option value="01">01 · No objeto</option></select></label>
              </div>
            </div>
          ))}
        </div>

        {error && <div className="alert error">{error}</div>}
        {message && <div className="alert success">{message}</div>}
        {preview && <div className="quotation-totals"><span>Subtotal <strong>{money(preview.subtotal)}</strong></span><span>Descuento <strong>{money(preview.discount)}</strong></span><span>IVA <strong>{money(preview.iva)}</strong></span><span>Ret. ISR <strong>-{money(preview.isr_retention)}</strong></span><span>Ret. IVA <strong>-{money(preview.iva_retention)}</strong></span><span>Total <strong>{money(preview.total)}</strong></span></div>}
        {preview?.errors?.length > 0 && <div className="alert error">{preview.errors.join(" · ")}</div>}
        <div className="form-actions"><button className="button" type="button" disabled={busy} onClick={handlePreview}><FileCheck2 size={16} />Vista previa</button><button className="button primary" type="submit" disabled={busy || !preview?.can_create}>Guardar factura</button></div>
      </form>
    </section>
  );
}