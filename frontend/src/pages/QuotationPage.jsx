import { useEffect, useMemo, useState } from "react";
import { createInvoice, createInvoiceMaterialService, deleteInvoiceMaterialService, downloadInvoicePdf, getAllCustomerSupplier, getAllInvoice, getAllInvoiceMaterialService, getAllMaterial, getAllProduct, getAllProyect, getAllService, getAllUnit, transitionQuotation, updateInvoice } from "../api";
import { useI18n } from "../i18n";
import QuotationWorkflowBoard, { normalizeQuotationStatus, quotationStatusLabel, QUOTATION_STATUS_CODES } from "../components/QuotationWorkflowBoard.jsx";

function asArray(payload) {
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload)) return payload;
  return [];
}

function todayInput() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysInput(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

function formatDate(value) {
  if (!value) return "—";
  const raw = String(value);
  const normalized = raw.includes("T") ? raw.slice(0, 10) : raw;
  const parts = normalized.split("-");
  if (parts.length === 3) {
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }
  return raw;
}

function newLineItem() {
  return {
    local_id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    line_type: "custom",
    id_product: "",
    id_service: "",
    id_unit: "",
    description: "",
    quantity: "1",
    gross_price: "0",
  };
}

export default function QuotationPage() {
  const { t } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const [quotations, setQuotations] = useState([]);
  const [quotationItems, setQuotationItems] = useState([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");
  const [editingInvoiceId, setEditingInvoiceId] = useState("");
  const [activeView, setActiveView] = useState("board");
  const [transitioningId, setTransitioningId] = useState("");
  const [customers, setCustomers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [products, setProducts] = useState([]);
  const [services, setServices] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [items, setItems] = useState([newLineItem()]);
  const [form, setForm] = useState({
    folio: "",
    date_emision: todayInput(),
    date_expiration: addDaysInput(15),
    id_issuer_customer_supplier: "",
    id_customer_supplier: "",
    id_proyect: "",
    currency: "MXN",
    apply_tax: true,
    tax_rate: "16",
    tax_certification_supplier: "",
    commercial_terms: "",
    note: "",
  });

  const customerById = useMemo(() => Object.fromEntries(customers.map((item) => [Number(item.id_customer_supplier), item])), [customers]);
  const projectById = useMemo(() => Object.fromEntries(projects.map((item) => [Number(item.id_proyect), item])), [projects]);
  const productById = useMemo(() => Object.fromEntries(products.map((item) => [Number(item.id_product), item])), [products]);
  const serviceById = useMemo(() => Object.fromEntries(services.map((item) => [Number(item.id_service), item])), [services]);
  const materialById = useMemo(() => Object.fromEntries(materials.map((item) => [Number(item.id_material), item])), [materials]);
  const unitById = useMemo(() => Object.fromEntries(units.map((item) => [Number(item.id_unit), item])), [units]);
  const selectedQuotation = useMemo(() => quotations.find((item) => Number(item.id_invoice) === Number(selectedInvoiceId)) || null, [quotations, selectedInvoiceId]);
  const selectedQuotationItems = useMemo(() => quotationItems.filter((item) => Number(item.id_invoice) === Number(selectedInvoiceId)), [quotationItems, selectedInvoiceId]);
  const quotationItemCounts = useMemo(() => quotationItems.reduce((counts, item) => {
    counts[item.id_invoice] = (counts[item.id_invoice] || 0) + 1;
    return counts;
  }, {}), [quotationItems]);

  function itemSubtotal(item) {
    return Number(item.quantity || 0) * Number(item.gross_price || 0);
  }

  const taxRate = Number(form.tax_rate || 0);
  const subtotal = items.reduce((sum, item) => sum + itemSubtotal(item), 0);
  const tax = form.apply_tax ? subtotal * (taxRate / 100) : 0;
  const total = subtotal + tax;

  function resolveError(err) {
    const payload = err?.payload || err?.response?.data || {};
    const raw = payload?.error_key || err?.error_key || err?.message || "";
    const field = payload?.meta?.field || err?.meta?.field || "";
    if (raw === "validations.invoice.date_expiration.after_emision" || (field === "date_expiration" && raw.includes("after_emision"))) {
      return t("quotation.validation_expiration_after_emision", "La fecha de vencimiento debe ser igual o posterior a la fecha de emisión.");
    }
    if (field === "tax_certification_supplier" && raw === "errors.invalid_field") {
      return t("quotation.validation_tax_certification_supplier_numeric", "El proveedor de certificación fiscal debe seleccionarse desde la lista.");
    }
    if (raw === "validations.invoice_material_service.authorization_status.required" || (field === "authorization_status" && raw.includes("authorization_status"))) {
      return t("quotation.validation_authorization_status_required", "No se pudo guardar porque la partida no tiene estado de autorización inicial.");
    }
    if (raw === "validations.invoice.tax_certification_supplier.required" || raw.includes("tax_certification_supplier")) {
      return t("quotation.validation_tax_certification_supplier_required", "Selecciona el proveedor de certificación fiscal.");
    }
    if (raw === "errors.database_constraint") {
      const detail = String(payload?.meta?.detail || err?.meta?.detail || "");
      if (detail.includes("fk_invoice_material_service_id_buyer")) {
        return t("quotation.validation_id_buyer_fk", "No se pudo guardar la partida porque el comprador debe ser un usuario válido del sistema.");
      }
      return t("quotation.validation_database_constraint", "No se pudo guardar por una relación inválida en la base de datos. Revisa los campos relacionados.");
    }
    if (raw === "errors.invalid_field") {
      return t("quotation.validation_invalid_field", "Revisa los datos capturados; hay un campo con formato inválido.");
    }
    if (raw.includes("REQUIRED_FIELD")) {
      return t("quotation.validation_required_field", "Falta capturar un campo obligatorio.");
    }
    return raw || t("errors.request_failed", "No se pudo completar la solicitud");
  }

  function hydrateLineDescription(line) {
    if (line.line_type === "product") {
      const product = productById[Number(line.id_product)];
      return line.description || product?.descripcion || product?.product_code || "";
    }
    if (line.line_type === "service") {
      const service = serviceById[Number(line.id_service)];
      return line.description || service?.service_description || "";
    }
    return line.description || "";
  }

  function detailLineDescription(line) {
    if (line.line_type === "product") {
      const product = productById[Number(line.id_product)];
      return line.invoice_material_service_description || product?.descripcion || product?.product_code || "—";
    }
    if (line.line_type === "service") {
      const service = serviceById[Number(line.id_service)];
      return line.invoice_material_service_description || service?.service_description || "—";
    }
    return line.invoice_material_service_description || "—";
  }

  function detailLineReference(line) {
    if (line.line_type === "product") {
      const product = productById[Number(line.id_product)];
      return product?.product_code || line.id_product || "—";
    }
    if (line.line_type === "service") {
      const service = serviceById[Number(line.id_service)];
      return service?.service_description || line.id_service || "—";
    }
    return t("quotation.line_type_custom", "Concepto personalizado");
  }

  function unitLabelFromUnit(unit) {
    return valueOrDash(unit?.symbol || unit?.unit_code || unit?.unit_name);
  }

  function defaultServiceUnitId() {
    const unit = units.find((item) => String(item.unit_category || "").toLowerCase() === "servicio" || String(item.unit_code || "").toUpperCase() === "HRA");
    return unit?.id_unit ? String(unit.id_unit) : "";
  }

  function productDefaultUnitId(product) {
    const material = materialById[Number(product?.id_material)];
    return material?.id_unit ? String(material.id_unit) : "";
  }

  function detailLineUnit(line) {
    return unitLabelFromUnit(unitById[Number(line.id_unit)]);
  }

  function valueOrDash(value) {
    const text = String(value ?? "").trim();
    return text || "—";
  }

  function joinClean(parts) {
    return parts.map((part) => String(part ?? "").trim()).filter(Boolean).join(", ");
  }

  function quotationFolio(invoice) {
    const raw = String(invoice?.folio || "").trim();
    if (raw) return raw;
    const id = String(invoice?.id_invoice || "").padStart(6, "0");
    return id ? "COT-" + id : "—";
  }

  function customerName(customer, fallback) {
    return valueOrDash(customer?.name || fallback);
  }

  function customerAddress(customer) {
    if (!customer) return "—";
    const street = joinClean([customer.street, customer.number_ext ? "No. " + customer.number_ext : "", customer.number_int ? "Int. " + customer.number_int : ""]);
    const city = joinClean([customer.neighborhood, customer.city, customer.geographic_state]);
    const postalCode = String(customer.postal_code || "").trim();
    return valueOrDash(joinClean([street, city, postalCode ? "CP " + postalCode : ""]));
  }

  function customerContactLine(customer) {
    if (!customer) return "—";
    return valueOrDash(joinClean([customer.contact_name, customer.phone]));
  }

  function lineToFormItem(line) {
    const lineType = line.line_type || (line.id_product ? "product" : line.id_service ? "service" : "custom");
    return {
      local_id: "existing-" + (line.id_invoice_material_service || Date.now()) + "-" + Math.random().toString(16).slice(2),
      line_type: lineType,
      id_product: line.id_product ? String(line.id_product) : "",
      id_service: line.id_service ? String(line.id_service) : "",
      id_unit: line.id_unit ? String(line.id_unit) : "",
      description: line.invoice_material_service_description || "",
      quantity: String(line.quantity ?? "1"),
      gross_price: String(line.gross_price ?? "0"),
    };
  }

  function startEditQuotation(invoice) {
    if (!invoice) return;
    const invoiceId = Number(invoice.id_invoice);
    const currentItems = quotationItems.filter((item) => Number(item.id_invoice) === invoiceId);
    setEditingInvoiceId(String(invoice.id_invoice));
    setActiveView("manage");
    setSelectedInvoiceId(String(invoice.id_invoice));
    setMessage("");
    setError("");
    setForm((prev) => ({
      ...prev,
      folio: invoice.folio || quotationFolio(invoice),
      date_emision: String(invoice.date_emision || "").slice(0, 10) || todayInput(),
      date_expiration: String(invoice.date_expiration || "").slice(0, 10) || addDaysInput(15),
      id_issuer_customer_supplier: invoice.id_issuer_customer_supplier ? String(invoice.id_issuer_customer_supplier) : "",
      id_customer_supplier: invoice.id_customer_supplier ? String(invoice.id_customer_supplier) : "",
      id_proyect: invoice.id_proyect ? String(invoice.id_proyect) : "",
      currency: invoice.currency || "MXN",
      apply_tax: invoice.apply_tax === undefined || invoice.apply_tax === null ? true : Boolean(invoice.apply_tax),
      tax_rate: String(invoice.tax_rate ?? "16"),
      tax_certification_supplier: invoice.tax_certification_supplier ? String(invoice.tax_certification_supplier) : "",
      commercial_terms: invoice.commercial_terms || "",
      note: invoice.note || "",
    }));
    setItems(currentItems.length ? currentItems.map(lineToFormItem) : [newLineItem()]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEditQuotation() {
    setEditingInvoiceId("");
    setMessage("");
    setError("");
    setItems([newLineItem()]);
    setForm((prev) => ({
      ...prev,
      folio: "",
      date_emision: todayInput(),
      date_expiration: addDaysInput(15),
      commercial_terms: "",
      note: "",
      apply_tax: true,
      tax_rate: "16",
    }));
  }

  function startNewQuotation() {
    cancelEditQuotation();
    setSelectedInvoiceId("");
    setActiveView("manage");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function viewQuotation(invoice) {
    setSelectedInvoiceId(String(invoice.id_invoice));
    setActiveView("manage");
    window.setTimeout(() => document.querySelector(".quotation-detail-card")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  }

  async function moveQuotation(invoice, status) {
    setTransitioningId(String(invoice.id_invoice));
    setMessage("");
    setError("");
    try {
      const updated = await transitionQuotation(invoice.id_invoice, status);
      setQuotations((current) => current.map((item) => Number(item.id_invoice) === Number(invoice.id_invoice) ? { ...item, invoice_status: updated.invoice_status } : item));
      setMessage(`Cotización ${quotationFolio(invoice)} movida a ${quotationStatusLabel(status, t)}.`);
    } catch (requestError) {
      setError(resolveError(requestError));
    } finally {
      setTransitioningId("");
    }
  }

  function loadData() {
    setLoading(true);
    setError("");
    Promise.all([
      getAllInvoice({ per_page: 500 }),
      getAllInvoiceMaterialService({ per_page: 500 }),
      getAllCustomerSupplier({ per_page: 500 }),
      getAllProyect({ per_page: 500 }),
      getAllProduct({ per_page: 500 }),
      getAllService({ per_page: 500 }),
      getAllMaterial({ per_page: 500 }),
      getAllUnit({ per_page: 500 }),
    ])
      .then(([invoicePayload, itemPayload, customerPayload, projectPayload, productPayload, servicePayload, materialPayload, unitPayload]) => {
        const rows = asArray(invoicePayload)
          .filter((item) => QUOTATION_STATUS_CODES.includes(normalizeQuotationStatus(item.invoice_status)))
          .sort((a, b) => Number(b.id_invoice || 0) - Number(a.id_invoice || 0));
        const customerRows = asArray(customerPayload);
        const projectRows = asArray(projectPayload);
        const productRows = asArray(productPayload);
        const serviceRows = asArray(servicePayload);
        const materialRows = asArray(materialPayload);
        const unitRows = asArray(unitPayload);
        setQuotations(rows);
        setQuotationItems(asArray(itemPayload));
        setCustomers(customerRows);
        setProjects(projectRows);
        setProducts(productRows);
        setServices(serviceRows);
        setMaterials(materialRows);
        setUnits(unitRows);
        setForm((prev) => ({
          ...prev,
          id_issuer_customer_supplier: prev.id_issuer_customer_supplier || String(customerRows[0]?.id_customer_supplier || ""),
          id_customer_supplier: prev.id_customer_supplier || String(customerRows[0]?.id_customer_supplier || ""),
          tax_certification_supplier: prev.tax_certification_supplier || String(customerRows[0]?.id_customer_supplier || ""),
        }));
      })
      .catch((err) => setError(resolveError(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  function updateForm(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function updateItem(localId, name, value) {
    setItems((prev) => prev.map((item) => {
      if (item.local_id !== localId) return item;
      const next = { ...item, [name]: value };
      if (name === "line_type") {
        next.id_product = "";
        next.id_service = "";
        next.id_unit = "";
        next.description = "";
      }
      if (name === "id_product") {
        const product = productById[Number(value)];
        next.description = product?.descripcion || product?.product_code || "";
        next.id_unit = productDefaultUnitId(product) || next.id_unit || "";
        next.gross_price = String(product?.gross_price ?? next.gross_price ?? "0");
      }
      if (name === "id_service") {
        const service = serviceById[Number(value)];
        next.description = service?.service_description || "";
        next.id_unit = next.id_unit || defaultServiceUnitId();
        next.gross_price = String(service?.average_time_cost ?? service?.gross_price ?? next.gross_price ?? "0");
      }
      return next;
    }));
  }

  function addItem() {
    setItems((prev) => [...prev, newLineItem()]);
  }

  function removeItem(localId) {
    setItems((prev) => prev.length > 1 ? prev.filter((item) => item.local_id !== localId) : prev);
  }

  function validateItems() {
    if (!items.length) return t("quotation.add_at_least_one_item", "Agrega al menos una partida.");
    for (const item of items) {
      const description = hydrateLineDescription(item).trim();
      const quantity = Number(item.quantity || 0);
      const price = Number(item.gross_price || 0);
      if (item.line_type === "product" && !item.id_product) return t("quotation.select_product_required", "Selecciona producto.");
      if (item.line_type === "service" && !item.id_service) return t("quotation.select_service_required", "Selecciona servicio.");
      if (!description) return t("quotation.description_required", "Captura concepto.");
      if (!(quantity > 0)) return t("quotation.quantity_required", "La cantidad debe ser mayor a 0.");
      if (!(price >= 0)) return t("quotation.price_required", "El precio unitario debe ser mayor o igual a 0.");
    }
    return "";
  }

  function itemPayload(invoiceId, item) {
    const lineSubtotal = itemSubtotal(item);
    const lineTax = form.apply_tax ? lineSubtotal * (taxRate / 100) : 0;
    const description = hydrateLineDescription(item);
    const userId = Number(currentUser?.id_user || 1);
    const customerId = Number(form.id_customer_supplier);
    return {
      id_invoice: Number(invoiceId),
      id_product: item.line_type === "product" ? Number(item.id_product) : null,
      id_service: item.line_type === "service" ? Number(item.id_service) : null,
      id_unit: item.id_unit ? Number(item.id_unit) : null,
      id_material: null,
      invoice_material_service_description: description,
      quantity: Number(item.quantity || 0),
      gross_price: Number(item.gross_price || 0),
      line_type: item.line_type,
      authorization_status: "pending",
      authorization_note: "",
      tax_applicable: Boolean(form.apply_tax),
      line_tax: lineTax,
      line_total: lineSubtotal,
      id_customer_supplier: customerId,
      id_buyer: userId,
      id_authorized: userId,
      id_status: 1,
      is_directly_related_to_product_service_creation: item.line_type !== "custom",
      created_by: userId,
    };
  }

  function submitQuotation(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    if (!form.id_issuer_customer_supplier || !form.id_customer_supplier) {
      setError(t("quotation.select_required", "Selecciona empresa emisora y cliente receptor."));
      return;
    }
    if (form.date_emision && form.date_expiration && form.date_expiration < form.date_emision) {
      setError(t("quotation.validation_expiration_after_emision", "La fecha de vencimiento debe ser igual o posterior a la fecha de emisión."));
      return;
    }
    if (!String(form.tax_certification_supplier || "").trim()) {
      setError(t("quotation.validation_tax_certification_supplier_required", "Selecciona el proveedor de certificación fiscal."));
      return;
    }
    const validationError = validateItems();
    if (validationError) {
      setError(validationError);
      return;
    }
    const userId = Number(currentUser?.id_user || 1);
    const payload = {
      folio: form.folio || null,
      date_emision: form.date_emision || null,
      date_expiration: form.date_expiration || null,
      subtotal,
      tax,
      total,
      invoice_status: editingInvoiceId ? (quotations.find((quotation) => Number(quotation.id_invoice) === Number(editingInvoiceId))?.invoice_status || "draft") : "draft",
      note: form.note || "",
      currency: form.currency || "MXN",
      tax_certification_supplier: Number(form.tax_certification_supplier),
      id_customer_supplier: Number(form.id_customer_supplier),
      id_issuer_customer_supplier: Number(form.id_issuer_customer_supplier),
      id_proyect: form.id_proyect ? Number(form.id_proyect) : null,
      apply_tax: Boolean(form.apply_tax),
      tax_rate: taxRate,
      commercial_terms: form.commercial_terms || "",
      created_by: userId,
      id_status: 1,
    };
    setSaving(true);
    const isEditing = Boolean(editingInvoiceId);
    const saveItemsForInvoice = (invoiceId) => Promise.all(items.map((item) => createInvoiceMaterialService(itemPayload(invoiceId, item)))).then(() => invoiceId);
    const request = isEditing
      ? updateInvoice(Number(editingInvoiceId), payload)
          .then(() => Promise.all(quotationItems
            .filter((line) => Number(line.id_invoice) === Number(editingInvoiceId) && line.id_invoice_material_service)
            .map((line) => deleteInvoiceMaterialService(line.id_invoice_material_service))))
          .then(() => saveItemsForInvoice(Number(editingInvoiceId)))
      : createInvoice(payload)
          .then((created) => {
            const invoiceId = created?.id_invoice || created?.item?.id_invoice || created?.data?.id_invoice;
            if (!invoiceId) throw new Error(t("quotation.created_without_id", "La cotización se creó sin identificador."));
            return saveItemsForInvoice(invoiceId);
          });

    request
      .then((invoiceId) => {
        setMessage(isEditing ? t("quotation.updated_success", "Cotización actualizada correctamente.") : t("quotation.created_success", "Cotización creada correctamente."));
        setForm((prev) => ({ ...prev, folio: "", commercial_terms: "", note: "" }));
        setItems([newLineItem()]);
        setEditingInvoiceId("");
        setSelectedInvoiceId(String(invoiceId));
        loadData();
      })
      .catch((err) => setError(resolveError(err)))
      .finally(() => setSaving(false));
  }

  function countItems(invoiceId) {
    return quotationItems.filter((item) => Number(item.id_invoice) === Number(invoiceId)).length;
  }

  async function printQuotationPdf() {
    if (!selectedQuotation?.id_invoice) return;
    setError("");
    try {
      const blob = await downloadInvoicePdf(selectedQuotation.id_invoice, "quotation");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Cotizacion-${selectedQuotation.id_invoice}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(resolveError(requestError));
    }
  }

  return (
    <section className="entity-page quotation-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">CRM</p>
          <h2>{t("quotation.title", "Cotizaciones")}</h2>
          <p className="quotation-subtitle">{t("quotation.subtitle", "Cotizaciones comerciales generadas sobre factura con estatus Cotización.")}</p>
        </div>
        <button type="button" className="button" onClick={loadData} disabled={loading}>{loading ? t("common.loading", "Cargando...") : t("common.refresh", "Actualizar")}</button>
      </div>

      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="quotation-view-controls" role="tablist" aria-label={t("quotation.views", "Vistas de cotizaciones")}>
        <button type="button" role="tab" aria-selected={activeView === "board"} className={activeView === "board" ? "active" : ""} onClick={() => setActiveView("board")}>{t("quotation.board", "Tablero")}</button>
        <button type="button" role="tab" aria-selected={activeView === "manage"} className={activeView === "manage" ? "active" : ""} onClick={() => setActiveView("manage")}>{t("quotation.manage", "Gestionar")}</button>
        <button type="button" className="button primary" onClick={startNewQuotation}>{t("quotation.new_title", "Nueva cotización")}</button>
      </div>

      {activeView === "board" ? (
        <QuotationWorkflowBoard quotations={quotations} customers={customers} projects={projects} itemCounts={quotationItemCounts} loading={loading} transitioningId={transitioningId} onTransition={moveQuotation} onView={viewQuotation} onEdit={startEditQuotation} onCreate={startNewQuotation} />
      ) : <>
      <form className="form-card quotation-form" onSubmit={submitQuotation}>
        <div className="form-header quotation-section-title">
          <strong>{editingInvoiceId ? t("quotation.edit_title", "Editar cotización") : t("quotation.new_title", "Nueva cotización")}</strong>
          <span className="muted">{editingInvoiceId ? t("quotation.editing_hint", "Editando cotización existente. Al guardar se reemplazarán sus partidas por las capturadas.") : t("quotation.dynamic_items_hint", "Encabezado y partidas dinámicas.")}</span>
        </div>

        <div className="form-grid">
          <label className="field">{t("quotation.folio", "Folio")}<input value={form.folio} onChange={(event) => updateForm("folio", event.target.value)} placeholder="COT-000001" /></label>
          <label className="field">{t("quotation.issuer_company", "Empresa emisora")}<select value={form.id_issuer_customer_supplier} onChange={(event) => updateForm("id_issuer_customer_supplier", event.target.value)} required><option value="">{t("quotation.select_company", "Seleccionar empresa")}</option>{customers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name || `#${item.id_customer_supplier}`}</option>)}</select></label>
          <label className="field">{t("quotation.receiver_customer", "Cliente receptor")}<select value={form.id_customer_supplier} onChange={(event) => updateForm("id_customer_supplier", event.target.value)} required><option value="">{t("quotation.select_customer", "Seleccionar cliente")}</option>{customers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name || `#${item.id_customer_supplier}`}</option>)}</select></label>
          <label className="field">{t("quotation.related_project", "Proyecto relacionado")}<select value={form.id_proyect} onChange={(event) => updateForm("id_proyect", event.target.value)}><option value="">{t("quotation.no_project", "Sin proyecto")}</option>{projects.map((item) => <option key={item.id_proyect} value={item.id_proyect}>{item.title || item.proyect_description || `#${item.id_proyect}`}</option>)}</select></label>
          <label className="field">{t("quotation.issue_date", "Fecha emisión")}<input type="date" value={form.date_emision} onChange={(event) => updateForm("date_emision", event.target.value)} /></label>
          <label className="field">{t("quotation.expiration_date", "Fecha vencimiento")}<input type="date" min={form.date_emision || undefined} value={form.date_expiration} onChange={(event) => updateForm("date_expiration", event.target.value)} /></label>
          <label className="field">{t("quotation.currency", "Moneda")}<input value={form.currency} onChange={(event) => updateForm("currency", event.target.value)} /></label>
          <label className="field">{t("quotation.tax_certification_supplier_select", "Proveedor certificación fiscal")}<select value={form.tax_certification_supplier} onChange={(event) => updateForm("tax_certification_supplier", event.target.value)} required><option value="">{t("quotation.select_tax_certification_supplier", "Seleccionar proveedor fiscal")}</option>{customers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name || `#${item.id_customer_supplier}`}</option>)}</select></label>
          <label className="field checkbox-field"><input type="checkbox" checked={form.apply_tax} onChange={(event) => updateForm("apply_tax", event.target.checked)} />{t("quotation.apply_tax", "Aplicar IVA")}</label>
          <label className="field">{t("quotation.tax_rate", "Tasa IVA %")}<input type="number" min="0" max="100" step="0.01" value={form.tax_rate} onChange={(event) => updateForm("tax_rate", event.target.value)} /></label>
          <label className="field wide-field">{t("quotation.commercial_terms", "Condiciones comerciales")}<input value={form.commercial_terms} onChange={(event) => updateForm("commercial_terms", event.target.value)} placeholder={t("quotation.commercial_terms_placeholder", "Vigencia, forma de pago, tiempos de entrega...")} /></label>
          <label className="field wide-field">{t("quotation.note", "Nota")}<input value={form.note} onChange={(event) => updateForm("note", event.target.value)} placeholder={t("quotation.note_placeholder", "Observaciones internas o comerciales")} /></label>
        </div>

        <div className="quotation-items-card">
          <div className="form-header quotation-section-title">
            <strong>{t("quotation.items_title", "Partidas de cotización")}</strong>
            <button type="button" className="button" onClick={addItem}>{t("quotation.add_item", "Agregar partida")}</button>
          </div>
          {items.map((item, index) => {
            const lineSubtotal = itemSubtotal(item);
            const lineTax = form.apply_tax ? lineSubtotal * (taxRate / 100) : 0;
            return (
              <div className="quotation-line-item" key={item.local_id}>
                <div className="quotation-line-head">
                  <strong>{t("quotation.item", "Partida")} #{index + 1}</strong>
                  <button type="button" className="button danger" onClick={() => removeItem(item.local_id)} disabled={items.length === 1}>{t("quotation.remove_item", "Quitar")}</button>
                </div>
                <div className="form-grid quotation-item-grid">
                  <label className="field">{t("quotation.line_type", "Tipo de partida")}<select value={item.line_type} onChange={(event) => updateItem(item.local_id, "line_type", event.target.value)}><option value="product">{t("quotation.line_type_product", "Producto existente")}</option><option value="service">{t("quotation.line_type_service", "Servicio existente")}</option><option value="custom">{t("quotation.line_type_custom", "Concepto personalizado")}</option></select></label>
                  {item.line_type === "product" && <label className="field">{t("quotation.product", "Producto")}<select value={item.id_product} onChange={(event) => updateItem(item.local_id, "id_product", event.target.value)}><option value="">{t("quotation.select_product", "Seleccionar producto")}</option>{products.map((product) => <option key={product.id_product} value={product.id_product}>{product.product_code || product.descripcion || `#${product.id_product}`}</option>)}</select></label>}
                  {item.line_type === "service" && <label className="field">{t("quotation.service", "Servicio")}<select value={item.id_service} onChange={(event) => updateItem(item.local_id, "id_service", event.target.value)}><option value="">{t("quotation.select_service", "Seleccionar servicio")}</option>{services.map((service) => <option key={service.id_service} value={service.id_service}>{service.service_description || `#${service.id_service}`}</option>)}</select></label>}
                  <label className="field wide-field">{t("quotation.concept", "Concepto")}<input value={item.description} onChange={(event) => updateItem(item.local_id, "description", event.target.value)} placeholder={t("quotation.concept_placeholder", "Descripción de la partida")} /></label>
                  <label className="field">{t("quotation.quantity", "Cantidad")}<input type="number" min="0.01" step="0.01" value={item.quantity} onChange={(event) => updateItem(item.local_id, "quantity", event.target.value)} /></label>
                  <label className="field">{t("quotation.unit_measure", "Unidad")}<select value={item.id_unit} onChange={(event) => updateItem(item.local_id, "id_unit", event.target.value)}><option value="">{t("quotation.no_unit", "Sin unidad")}</option>{units.map((unit) => <option key={unit.id_unit} value={unit.id_unit}>{unitLabelFromUnit(unit)}</option>)}</select></label>
                  <label className="field">{t("quotation.unit_price", "Precio unitario")}<input type="number" min="0" step="0.01" value={item.gross_price} onChange={(event) => updateItem(item.local_id, "gross_price", event.target.value)} /></label>
                </div>
                <div className="quotation-line-totals">
                  <span>{t("quotation.subtotal", "Subtotal")}: <strong>{money(lineSubtotal)}</strong></span>
                  <span>{t("quotation.tax", "IVA")}: <strong>{money(lineTax)}</strong></span>
                  <span>{t("quotation.total", "Total")}: <strong>{money(lineSubtotal + lineTax)}</strong></span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="quotation-totals">
          <span>{t("quotation.subtotal", "Subtotal")} <strong>{money(subtotal)}</strong></span>
          <span>{t("quotation.tax", "IVA")} <strong>{money(tax)}</strong></span>
          <span>{t("quotation.total", "Total")} <strong>{money(total)}</strong></span>
        </div>
        <div className="form-actions"><button type="submit" className="button primary" disabled={saving}>{saving ? t("quotation.saving", "Guardando...") : (editingInvoiceId ? t("quotation.update_button", "Actualizar cotización") : t("quotation.save_button", "Guardar cotización"))}</button>{editingInvoiceId && <button type="button" className="button" onClick={cancelEditQuotation} disabled={saving}>{t("quotation.cancel_edit", "Cancelar edición")}</button>}</div>
      </form>

      <div className="table-card quotation-list-card">
        <div className="form-header quotation-section-title">
          <strong>{t("quotation.list_title", "Listado de cotizaciones")}</strong>
          <span className="muted">{quotations.length} {t("quotation.records", "registro(s)")}</span>
        </div>
        <div className="table-wrap"><table><thead><tr><th>{t("quotation.id", "ID")}</th><th>{t("quotation.customer", "Cliente")}</th><th>{t("quotation.project", "Proyecto")}</th><th>{t("quotation.date", "Fecha")}</th><th>{t("quotation.status", "Estatus")}</th><th>{t("quotation.items", "Partidas")}</th><th>{t("quotation.subtotal", "Subtotal")}</th><th>{t("quotation.tax", "IVA")}</th><th>{t("quotation.total", "Total")}</th><th>{t("quotation.detail", "Detalle")}</th></tr></thead><tbody>{quotations.map((item) => (<tr key={item.id_invoice}><td>{quotationFolio(item)}</td><td>{customerById[Number(item.id_customer_supplier)]?.name || item.id_customer_supplier || "—"}</td><td>{projectById[Number(item.id_proyect)]?.title || item.id_proyect || "—"}</td><td>{formatDate(item.date_emision)}</td><td><span className={`quotation-status-badge status-${normalizeQuotationStatus(item.invoice_status)}`}>{quotationStatusLabel(item.invoice_status, t)}</span></td><td>{countItems(item.id_invoice)}</td><td>{money(item.subtotal)}</td><td>{money(item.tax)}</td><td>{money(item.total)}</td><td><button type="button" className="button small" onClick={() => setSelectedInvoiceId(String(item.id_invoice))}>{t("quotation.view_detail", "Ver detalle")}</button></td></tr>))}{!quotations.length && <tr><td colSpan="10" className="muted">{t("quotation.empty", "Sin cotizaciones registradas.")}</td></tr>}</tbody></table></div>
      </div>

      {selectedQuotation && (
        <div className="table-card quotation-detail-card">
          <div className="form-header quotation-section-title">
            <div>
              <strong>{t("quotation.detail_title", "Detalle de cotización")} {quotationFolio(selectedQuotation)}</strong>
              <p className="muted">{t("quotation.pdf_ready_hint", "Vista preparada como base para el PDF descargable.")}</p>
            </div>
            <div className="quotation-detail-actions"><button type="button" className="button" onClick={() => startEditQuotation(selectedQuotation)}>{t("quotation.edit_button", "Editar cotización")}</button><button type="button" className="button primary" onClick={printQuotationPdf}>{t("quotation.pdf_button", "Generar PDF")}</button><button type="button" className="button" onClick={() => setSelectedInvoiceId("")}>{t("quotation.close_detail", "Cerrar detalle")}</button></div>
          </div>
          <div className="quotation-meta-strip">
            <div><span>{t("quotation.folio", "Folio")}</span><strong>{quotationFolio(selectedQuotation)}</strong></div>
            <div><span>{t("quotation.status", "Estatus")}</span><strong>{quotationStatusLabel(selectedQuotation.invoice_status, t)}</strong></div>
          </div>

          <div className="quotation-party-grid">
            <div className="quotation-party-card">
              <h4>{t("quotation.issuer_data", "Datos de empresa emisora")}</h4>
              <p className="quotation-party-name">{customerName(customerById[Number(selectedQuotation.id_issuer_customer_supplier)], selectedQuotation.id_issuer_customer_supplier)}</p>
              <p><span>{t("quotation.tax_id", "RFC")}</span><strong>{valueOrDash(customerById[Number(selectedQuotation.id_issuer_customer_supplier)]?.tax_id)}</strong></p>
              <p><span>{t("quotation.fiscal_type", "Tipo fiscal")}</span><strong>{valueOrDash(customerById[Number(selectedQuotation.id_issuer_customer_supplier)]?.fiscal_type)}</strong></p>
              <p><span>{t("quotation.address", "Dirección")}</span><strong>{customerAddress(customerById[Number(selectedQuotation.id_issuer_customer_supplier)])}</strong></p>
              <p><span>{t("quotation.contact", "Contacto")}</span><strong>{customerContactLine(customerById[Number(selectedQuotation.id_issuer_customer_supplier)])}</strong></p>
              <p><span>{t("quotation.website", "Sitio web")}</span><strong>{valueOrDash(customerById[Number(selectedQuotation.id_issuer_customer_supplier)]?.web_site)}</strong></p>
            </div>
            <div className="quotation-party-card">
              <h4>{t("quotation.receiver_data", "Datos de cliente receptor")}</h4>
              <p className="quotation-party-name">{customerName(customerById[Number(selectedQuotation.id_customer_supplier)], selectedQuotation.id_customer_supplier)}</p>
              <p><span>{t("quotation.tax_id", "RFC")}</span><strong>{valueOrDash(customerById[Number(selectedQuotation.id_customer_supplier)]?.tax_id)}</strong></p>
              <p><span>{t("quotation.fiscal_type", "Tipo fiscal")}</span><strong>{valueOrDash(customerById[Number(selectedQuotation.id_customer_supplier)]?.fiscal_type)}</strong></p>
              <p><span>{t("quotation.address", "Dirección")}</span><strong>{customerAddress(customerById[Number(selectedQuotation.id_customer_supplier)])}</strong></p>
              <p><span>{t("quotation.contact", "Contacto")}</span><strong>{customerContactLine(customerById[Number(selectedQuotation.id_customer_supplier)])}</strong></p>
              <p><span>{t("quotation.website", "Sitio web")}</span><strong>{valueOrDash(customerById[Number(selectedQuotation.id_customer_supplier)]?.web_site)}</strong></p>
            </div>
          </div>

          <div className="quotation-detail-grid">
            <div><span>{t("quotation.tax_certification_supplier_select", "Proveedor certificación fiscal")}</span><strong>{customerById[Number(selectedQuotation.tax_certification_supplier)]?.name || selectedQuotation.tax_certification_supplier || "—"}</strong></div>
            <div><span>{t("quotation.related_project", "Proyecto relacionado")}</span><strong>{projectById[Number(selectedQuotation.id_proyect)]?.title || selectedQuotation.id_proyect || t("quotation.no_project", "Sin proyecto")}</strong></div>
            <div><span>{t("quotation.issue_date", "Fecha emisión")}</span><strong>{formatDate(selectedQuotation.date_emision)}</strong></div>
            <div><span>{t("quotation.expiration_date", "Fecha vencimiento")}</span><strong>{formatDate(selectedQuotation.date_expiration)}</strong></div>
            <div><span>{t("quotation.currency", "Moneda")}</span><strong>{selectedQuotation.currency || "MXN"}</strong></div>
            <div><span>{t("quotation.commercial_terms", "Condiciones comerciales")}</span><strong>{selectedQuotation.commercial_terms || "—"}</strong></div>
          </div>
          <div className="table-wrap"><table><thead><tr><th>#</th><th>{t("quotation.line_type", "Tipo de partida")}</th><th>{t("quotation.reference", "Referencia")}</th><th>{t("quotation.concept", "Concepto")}</th><th>{t("quotation.quantity", "Cantidad")}</th><th>{t("quotation.unit_measure", "Unidad")}</th><th>{t("quotation.unit_price", "Precio unitario")}</th><th>{t("quotation.subtotal", "Subtotal")}</th><th>{t("quotation.tax", "IVA")}</th><th>{t("quotation.total", "Total")}</th></tr></thead><tbody>{selectedQuotationItems.map((line, index) => (<tr key={line.id_invoice_material_service}><td>{index + 1}</td><td>{t(`quotation.line_type_${line.line_type}`, line.line_type || "—")}</td><td>{detailLineReference(line)}</td><td>{detailLineDescription(line)}</td><td>{line.quantity || "—"}</td><td>{detailLineUnit(line)}</td><td>{money(line.gross_price)}</td><td>{money(line.line_total)}</td><td>{money(line.line_tax)}</td><td>{money(Number(line.line_total || 0) + Number(line.line_tax || 0))}</td></tr>))}{!selectedQuotationItems.length && <tr><td colSpan="10" className="muted">{t("quotation.no_items", "Sin partidas registradas.")}</td></tr>}</tbody></table></div>
          <div className="quotation-totals quotation-detail-totals">
            <span>{t("quotation.subtotal", "Subtotal")} <strong>{money(selectedQuotation.subtotal)}</strong></span>
            <span>{t("quotation.tax", "IVA")} <strong>{money(selectedQuotation.tax)}</strong></span>
            <span>{t("quotation.total", "Total")} <strong>{money(selectedQuotation.total)}</strong></span>
          </div>
          {selectedQuotation.note && <p className="quotation-detail-note"><strong>{t("quotation.note", "Nota")}:</strong> {selectedQuotation.note}</p>}
        </div>
      )}
      </>}
    </section>
  );
}
