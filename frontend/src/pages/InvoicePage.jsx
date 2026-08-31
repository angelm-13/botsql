import React, { Fragment, useEffect, useMemo, useState } from "react";
import { BadgeCheck, ChevronDown, ChevronRight, Download, FileText, Plus, RefreshCw, Scale, Search, Trash2, Pencil, Warehouse } from "lucide-react";
import { useI18n } from "../i18n";
import { applyInvoiceInventory, deleteInvoice, downloadInvoicePdf, downloadInvoiceXml, getAllCustomerSupplier, getAllEntityPermission, getAllField, getAllInvoice, getAllNmFieldPermission, getAllProyect, getAllStatus, getInvoiceInventoryPreview, getInvoiceLines, resetUserMfa, stampInvoice, createInvoice, updateInvoice } from "../api";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import InvoiceUploadWidget from "../components/InvoiceUploadWidget.jsx";
import InvoiceCreationForm from "../components/InvoiceCreationForm.jsx";
import InvoiceFiscalPanel from "../components/InvoiceFiscalPanel.jsx";

const emptyForm = { date_emision: "", date_expiration: "", subtotal: "", tax: "", total: "", invoice_status: "", payment_method: "", note: "", id_customer_supplier: "", fiscal_reference: "", serie_csd: "", internationalization: "", currency: "", type_exchange_rate: "", tax_certification_supplier: "", fiscal_certify_serie: "", certification_date: "", cfdi_code: "", sat_code: "", sat_certification_code: "", id_status: "", nombre_emisor: "", lugar_expedicion: "", tipo_de_comprobante: "", rfc_receptor: "", nombre_receptor: "", regimen_fiscal_receptor: "", domicilio_fiscal_receptor: "", id_proveedor_de_sello: "", folio_fiscal: "", exportacion: "", folio: "", no_certificado_sat: "", sello_sat: "", sello_certificacion_sat: "", no_certificado: "", descuento: "", metodo_pago: "", condiciones_pago: "", id_issuer_customer_supplier: "", id_proyect: "", apply_tax: false, tax_rate: "", commercial_terms: "" };
const validationRules = allValidationRules["invoice"] || {};
const ENTITY_KEY = "invoice";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_invoice', 'date_emision', 'date_expiration', 'subtotal', 'tax', 'total', 'invoice_status', 'payment_method', 'note', 'id_customer_supplier'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function InvoicePage() {
  const { lang, t } = useI18n();
  const [items, setItems] = useState([]);
  const [formData, setFormData] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [editingId, setEditingId] = useState(null);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("table");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [errorMeta, setErrorMeta] = useState(null);
  const [noticeKey, setNoticeKey] = useState("");

  const currentUser = useMemo(() => readCurrentUser(), []);
  const isSuperUser = Boolean(currentUser?.is_superuser || currentUser?.is_bootstrap_admin || currentUser?.username === "admin1");
  const currentRoleId = currentUser?.id_permission;
  const [modulePermission, setModulePermission] = useState(null);
  const [visibleFieldNames, setVisibleFieldNames] = useState(new Set());
  const [permissionReady, setPermissionReady] = useState(false);
  const canRead = canUseAction(ACTION_READ);
  const canCreate = canUseAction(ACTION_CREATE);
  const canUpdate = canUseAction(ACTION_UPDATE);
  const canDelete = canUseAction(ACTION_DELETE);
  const canSubmitForm = editingId ? canUpdate : canCreate;
  const showRowActions = canRead;
  const [customerSupplierOptions, setCustomerSupplierOptions] = useState([]);
  const [statusOptions, setStatusOptions] = useState([]);
  const [proyectOptions, setProyectOptions] = useState([]);
  const [expandedInvoiceId, setExpandedInvoiceId] = useState(null);
  const [invoiceLines, setInvoiceLines] = useState({});
  const [invoiceLinesLoading, setInvoiceLinesLoading] = useState(null);
  const [invoiceLinesError, setInvoiceLinesError] = useState({});
  // Factura abierta en el panel de actos fiscales (cancelar, cobrar, acreditar).
  const [fiscalInvoice, setFiscalInvoice] = useState(null);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllInvoice({ page, per_page: perPage });
      setItems(Array.isArray(data) ? data : (data.items || data.data || []));
    } catch (error) {
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(error.payload?.meta || null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, [page, perPage, permissionReady, canRead]);
  useEffect(() => {
    async function loadFormOptions() {
      if (!permissionReady || (!canSubmitForm && !canRead)) return;
      if (canSeeField("id_customer_supplier") || canSeeField("id_issuer_customer_supplier")) {
        try {
          const customerSupplierData = await getAllCustomerSupplier({ page: 1, per_page: 100 });
          setCustomerSupplierOptions(Array.isArray(customerSupplierData) ? customerSupplierData : (customerSupplierData.items || []));
        } catch (_) {
          setCustomerSupplierOptions([]);
        }
      }
      if (canSeeField("id_status")) {
        try {
          const statusData = await getAllStatus({ page: 1, per_page: 100 });
          setStatusOptions(Array.isArray(statusData) ? statusData : (statusData.items || []));
        } catch (_) {
          setStatusOptions([]);
        }
      }
      if (canSeeField("id_proyect")) {
        try {
          const proyectData = await getAllProyect({ page: 1, per_page: 100 });
          setProyectOptions(Array.isArray(proyectData) ? proyectData : (proyectData.items || []));
        } catch (_) {
          setProyectOptions([]);
        }
      }
    }
    loadFormOptions();
  }, [permissionReady, canSubmitForm, canRead, visibleFieldNames]);

  useEffect(() => {
    async function loadRolePermissions() {
      if (isSuperUser) {
        setModulePermission({ control_type: 15 });
        setVisibleFieldNames(new Set(ALL_FIELD_NAMES));
        setPermissionReady(true);
        return;
      }
      if (!currentRoleId) {
        setModulePermission(null);
        setVisibleFieldNames(new Set());
        setPermissionReady(true);
        return;
      }
      try {
        const [entityPermissionData, fieldPermissionData, fieldData] = await Promise.all([
          getAllEntityPermission({ per_page: 5000 }),
          getAllNmFieldPermission({ per_page: 5000 }),
          getAllField({ per_page: 5000 })
        ]);
        const entityPermissions = normalizeList(entityPermissionData);
        const fieldPermissions = normalizeList(fieldPermissionData);
        const fieldsMeta = normalizeList(fieldData);
        const moduleRow = entityPermissions.find((row) =>
          String(row.id_permission ?? "") === String(currentRoleId) &&
          String(row.entity_name ?? "") === ENTITY_KEY
        );
        setModulePermission(moduleRow || null);
        const fieldNameById = new Map();
        fieldsMeta.forEach((field) => {
          if (String(field.table_name || "") === ENTITY_KEY && field.id_field) {
            fieldNameById.set(String(field.id_field), String(field.field_name || ""));
          }
        });
        const allowed = new Set();
        fieldPermissions.forEach((row) => {
          if (String(row.id_permission ?? "") !== String(currentRoleId)) return;
          if (!hasBit(row.control_type, FIELD_VISIBLE_BIT)) return;
          const fieldName = fieldNameById.get(String(row.id_field));
          if (fieldName) allowed.add(fieldName);
        });
        setVisibleFieldNames(allowed);
      } catch (error) {
        setModulePermission(null);
        setVisibleFieldNames(new Set());
      } finally {
        setPermissionReady(true);
      }
    }
    loadRolePermissions();
  }, [currentRoleId, isSuperUser]);

  function canUseAction(bit) {
    if (isSuperUser) return true;
    return hasBit(modulePermission?.control_type, bit);
  }

  function canSeeField(fieldName) {
    if (isSuperUser) return true;
    if (!permissionReady) return false;
    return visibleFieldNames.has(fieldName);
  }


  function handleChange(event) {
    const { name, type, checked, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
    setFieldErrors((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }

  function isBlankValue(value) {
    return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
  }

  function buildSubmitPayload() {
    const payload = { ...formData };
    if (ENTITY_KEY === "user" && editingId && isBlankValue(payload.password)) {
      delete payload.password;
    }
    return payload;
  }

  function formatFieldError(fieldName) {
    const messageKey = fieldErrors[fieldName];
    if (!messageKey) return "";
    const fieldLabel = t(`fields.invoice.${fieldName}`, fieldName);
    if (messageKey === "validations.user.password.strong" || String(messageKey).endsWith(".password.strong")) {
      return t("errors.password_strong", "La contraseña debe tener mínimo 8 caracteres e incluir mayúscula, minúscula, número y símbolo.");
    }
    if (messageKey === "validations.user.password.required") {
      return t("errors.password_required", "La contraseña es obligatoria al crear un usuario.");
    }
    if (messageKey === "validations.user.username.required") {
      return t("errors.username_required", "El nombre de usuario es obligatorio.");
    }
    if (String(messageKey).endsWith(".required")) return `${t("errors.required_field", "Campo obligatorio")}: ${fieldLabel}`;
    return t(messageKey, messageKey);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorKey("");
    setErrorMeta(null);
    setNoticeKey("");
    const submitPayload = buildSubmitPayload();
    const validation = validateForm("invoice", submitPayload, validationRules);
    const nextFieldErrors = { ...validation.errors };
    if (ENTITY_KEY === "user" && !editingId) {
      if (isBlankValue(submitPayload.username)) nextFieldErrors.username = "validations.user.username.required";
      if (isBlankValue(submitPayload.password)) nextFieldErrors.password = "validations.user.password.required";
    }
    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      setErrorKey("errors.validation_failed");
      return;
    }
    setFieldErrors({});
    try {
      if (editingId && !canUpdate) return;
      if (!editingId && !canCreate) return;
      if (editingId) await updateInvoice(editingId, submitPayload);
      else await createInvoice(submitPayload);
      setFormData(emptyForm); setEditingId(null); await loadData();
    } catch (error) {
      const meta = error.payload?.meta || null;
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(meta);
      if (meta?.field) setFieldErrors((prev) => ({ ...prev, [meta.field]: error.message || "errors.invalid_field" }));
    }
  }

  function startEdit(item) {
    if (!canUpdate) return;
    setEditingId(item.id_invoice);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteInvoice(item.id_invoice); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
  }

  function saveBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleStamp(item) {
    setErrorKey("");
    setNoticeKey("");
    try {
      await stampInvoice(item.id_invoice);
      setNoticeKey("Factura timbrada correctamente.");
      await loadData();
    } catch (error) {
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(error.payload?.meta || null);
    }
  }

  async function handleDocument(item, type) {
    setErrorKey("");
    try {
      const blob = type === "xml" ? await downloadInvoiceXml(item.id_invoice) : await downloadInvoicePdf(item.id_invoice);
      saveBlob(blob, `${type === "xml" ? "CFDI" : "Factura"}-${item.id_invoice}.${type}`);
    } catch (error) {
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(error.payload?.meta || null);
    }
  }



  async function resetMfaForItem(item) {
    if (ENTITY_KEY !== "user") return;
    const targetId = item.id_user ?? item.id;
    if (!targetId) return;
    if (!window.confirm(t("common.mfa_reset_confirm", "¿Restablecer MFA de este usuario?"))) return;
    setErrorKey("");
    setErrorMeta(null);
    setNoticeKey("");
    try {
      await resetUserMfa(targetId);
      setNoticeKey("common.mfa_reset_success");
      await loadData();
    } catch (error) {
      setErrorKey(error.message || "common.mfa_reset_error");
      setErrorMeta(error.payload?.meta || null);
    }
  }

  function formatTableValue(value) {
    if (value === null || value === undefined) return "";
    const locale = lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
    if (typeof value === "boolean") {
      const labels = {
        es: { yes: "Sí", no: "No" },
        en: { yes: "Yes", no: "No" },
        pt: { yes: "Sim", no: "Não" },
        de: { yes: "Ja", no: "Nein" },
        ja: { yes: "はい", no: "いいえ" },
      };
      const selected = labels[lang] || labels.es;
      return value ? selected.yes : selected.no;
    }
    if (typeof value === "number") return new Intl.NumberFormat(locale).format(value);
    if (typeof value === "string" && /^[0-9]{4}-[0-9]{2}-[0-9]{2}T/.test(value)) {
      const date = new Date(value);
      if (!Number.isNaN(date.getTime())) {
        const hasTime = !/T00:00(?::00)?/.test(value);
        return new Intl.DateTimeFormat(locale, hasTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(date);
      }
    }
    if (Array.isArray(value)) return value.map((item) => formatTableValue(item)).filter(Boolean).join(", ");
    if (typeof value === "object") {
      try {
        return Object.entries(value)
          .filter(([, val]) => val !== null && val !== undefined && val !== "")
          .slice(0, 6)
          .map(([key, val]) => `${key}: ${typeof val === "object" ? JSON.stringify(val) : String(val)}`)
          .join(", ");
      } catch (_) {
        return String(value);
      }
    }
    return String(value);
  }

  function getOptionLabel(item, entityName = "") {
    if (!item) return "";
    const normalized = String(entityName || "").toLowerCase();
    const specificFields = {
      user: ["full_name", "username", "email", "first_name", "last_name_father"],
      permission: ["permission_description"],
      department: ["department_description"],
      subdepartment: ["subdepartment_description"],
      level: ["level_description"],
      bank: ["bank_name"],
      brand: ["brand_description", "brand_name"],
      unit: ["unit_name", "unit_code", "unit_description", "symbol"],
      material: ["material_description", "material_code"],
      product: ["product_code", "descripcion", "note"],
      product_family: ["product_family_description", "type"],
      location: ["location_description"],
      location_type: ["location_type_description"],
      status: ["status_description", "category"],
      incident_type: ["incident_type_description"],
      payroll_concept: ["payroll_concept_description", "payroll_code"],
      proyect: ["proyect_description", "title"],
      project: ["project_description", "title"],
      service: ["service_description"],
      customer_supplier: ["name", "business_name", "commercial_name", "contact_name", "title"],
      field: ["field_name", "table_name"],
      template: ["template_description"],
      survey_question: ["question", "title"],
      survey_multiple_answer: ["survey_answer_description"],
      task: ["task_description", "task_code", "title"],
    };
    const candidates = [
      ...(specificFields[normalized] || []),
      `${normalized}_description`,
      `${normalized}_name`,
      `${normalized}_code`,
      "description",
      "name",
      "title",
      "code",
      "email",
      "username",
      "full_name",
      "business_name",
      "commercial_name",
      "contact_name",
    ];
    for (const key of candidates) {
      const value = item[key];
      if (value !== null && value !== undefined && String(value).trim() !== "") return String(value);
    }
    const idKey = normalized ? `id_${normalized}` : "";
    const idValue = idKey ? item[idKey] : undefined;
    return String(idValue ?? item.id ?? "");
  }

  // issue_12_phase3b_invoice_project_link_summary
  function invoiceProjectLabel(invoice) {
    if (ENTITY_KEY !== "invoice") return "";
    const rawProjectId = invoice?.id_proyect;
    if (rawProjectId === null || rawProjectId === undefined || String(rawProjectId).trim() === "") return t("invoice_ui.no_project", "Sin proyecto");
    const project = proyectOptions.find((item) => String(item.id_proyect ?? item.id ?? "") === String(rawProjectId));
    return project ? getOptionLabel(project, "proyect") : `${t("invoice_ui.project", "Proyecto")} #${rawProjectId}`;
  }

  function invoiceLinkStatus(invoice) {
    const rawProjectId = invoice?.id_proyect;
    return rawProjectId === null || rawProjectId === undefined || String(rawProjectId).trim() === "" ? t("invoice_ui.unlinked", "Sin vincular") : t("invoice_ui.linked", "Vinculada");
  }

  function invoiceDisplayFolio(invoice) {
    return String(invoice?.folio || invoice?.folio_fiscal || invoice?.cfdi_code || invoice?.id_invoice || "—");
  }

  function invoiceMoney(value) {
    const locale = lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
    const n = Number(value || 0);
    return n.toLocaleString(locale, { style: "currency", currency: "MXN" });
  }

  function invoiceLinkedCount() {
    return filtered.filter((item) => item.id_proyect !== null && item.id_proyect !== undefined && String(item.id_proyect).trim() !== "").length;
  }

  async function handleInventory(item) {
    // Se muestra primero que haria en el almacen y se pide confirmacion: el
    // movimiento afecta existencias reales.
    setErrorKey(""); setNoticeKey("");
    try {
      const preview = await getInvoiceInventoryPreview(item.id_invoice);
      if (!preview.can_apply) {
        if (preview.fully_applied) { setNoticeKey("invoice_ui.inventory_already_applied"); return; }
        const razon = preview.blocked_lines
          ? t("invoice_ui.inventory_blocked", "Alguna partida no alcanza en el almacén.")
          : preview.invoice_direction === "sin_clasificar"
            ? t("errors.invoice_inventory_direction_unknown", "No se sabe si la factura es de venta o de compra.")
            : t("invoice_ui.inventory_nothing_to_apply", "No hay partidas de almacén que aplicar.");
        setErrorKey(razon);
        return;
      }
      const efecto = preview.effect === "incrementa"
        ? t("invoice_ui.inventory_will_increase", "sumará al almacén")
        : t("invoice_ui.inventory_will_decrease", "descontará del almacén");
      const detalle = preview.lines
        .filter((line) => line.applicable)
        .map((line) => `  · ${line.description}: ${line.units}`)
        .join("\n");
      const confirmado = window.confirm(
        [
          `${t("invoice_ui.inventory_confirm", "Esta factura")} ${efecto}:`,
          "",
          detalle,
          "",
          t("common.continue", "¿Continuar?"),
        ].join("\n")
      );
      if (!confirmado) return;
      const resultado = await applyInvoiceInventory(item.id_invoice, {});
      setNoticeKey(resultado.applied_lines
        ? "invoice_ui.inventory_applied"
        : "invoice_ui.inventory_already_applied");
      await loadData();
    } catch (requestError) {
      const payload = requestError?.payload || {};
      setErrorKey(payload.error_key || payload.error || requestError?.message || "errors.request_failed");
      setErrorMeta(payload.meta || null);
    }
  }

  async function toggleInvoiceLines(invoiceId) {
    if (expandedInvoiceId === invoiceId) {
      setExpandedInvoiceId(null);
      return;
    }
    setExpandedInvoiceId(invoiceId);
    if (invoiceLines[invoiceId]) return;
    setInvoiceLinesLoading(invoiceId);
    setInvoiceLinesError((current) => ({ ...current, [invoiceId]: "" }));
    try {
      const response = await getInvoiceLines(invoiceId);
      setInvoiceLines((current) => ({ ...current, [invoiceId]: response.items || [] }));
    } catch (error) {
      setInvoiceLinesError((current) => ({ ...current, [invoiceId]: error.message || "invoice_ui.error_loading_lines" }));
    } finally {
      setInvoiceLinesLoading(null);
    }
  }

  function renderInvoiceProjectSummary() {
    if (ENTITY_KEY !== "invoice" || !canRead || !filtered.length) return null;
    const linked = invoiceLinkedCount();
    const unlinked = filtered.length - linked;
    return (
      <div className="table-card invoice-project-card">
        <div className="invoice-project-header">
          <div>
            <strong>{t("invoice_ui.project_summary", "Facturas / Proyecto")}</strong>
            <p className="muted">{t("invoice_ui.project_summary_help", "Identifica facturas cargadas desde XML y corrige su proyecto desde el formulario existente.")}</p>
          </div>
          <div className="invoice-project-metrics">
            <span><strong>{filtered.length}</strong>{t("invoice_ui.total", "Total")}</span>
            <span><strong>{linked}</strong>{t("invoice_ui.linked_plural", "Vinculadas")}</span>
            <span><strong>{unlinked}</strong>{t("invoice_ui.no_project", "Sin proyecto")}</span>
          </div>
        </div>
        <div className="table-wrap">
          <table className="invoice-project-table">
            <thead>
              <tr>
                <th>{t("invoice_ui.invoice_uuid", "Factura / UUID")}</th>
                <th>{t("invoice_ui.issuer", "Emisor")}</th>
                <th>{t("invoice_ui.receiver", "Receptor")}</th>
                <th>{t("invoice_ui.total", "Total")}</th>
                <th>{t("invoice_ui.project", "Proyecto")}</th>
                <th>{t("invoice_ui.link", "Vinculación")}</th>
                <th>{t("invoice_ui.action", "Acción")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <Fragment key={`invoice-link-${item.id_invoice}`}>
                <tr>
                  <td className="invoice-identity-cell"><button type="button" className="invoice-lines-toggle" onClick={() => toggleInvoiceLines(item.id_invoice)} aria-expanded={expandedInvoiceId === item.id_invoice} title={t("invoice_ui.view_lines")}>{expandedInvoiceId === item.id_invoice ? <ChevronDown size={17} /> : <ChevronRight size={17} />}</button><span><strong>{invoiceDisplayFolio(item)}</strong><p className="cell-value">{item.folio_fiscal || item.cfdi_code || "—"}</p></span></td>
                  <td><span>{item.nombre_emisor || "—"}</span></td>
                  <td><span>{item.nombre_receptor || item.id_customer_supplier || "—"}</span></td>
                  <td><strong>{invoiceMoney(item.total)}</strong></td>
                  <td><span>{invoiceProjectLabel(item)}</span></td>
                  <td><span className={item.id_proyect ? "invoice-link-badge linked" : "invoice-link-badge unlinked"}>{invoiceLinkStatus(item)}</span></td>
                  <td className="row-actions">{canUpdate && <button type="button" onClick={() => startEdit(item)} title={t("invoice_ui.edit_relation")}><Pencil size={15} /></button>}{canUpdate && !item.folio_fiscal && <button type="button" onClick={() => handleStamp(item)} title={t("invoice_ui.stamp_invoice")}><BadgeCheck size={15} /></button>}{canUpdate && <button type="button" onClick={() => handleInventory(item)} title={t("invoice_ui.apply_inventory", "Aplicar al almacén")}><Warehouse size={15} /></button>}{canUpdate && item.folio_fiscal && <button type="button" onClick={() => setFiscalInvoice(item)} title={t("fiscal.open_panel", "Cancelar, cobrar o acreditar")}><Scale size={15} /></button>}<button type="button" onClick={() => handleDocument(item, "pdf")} title={t("invoice_ui.download_pdf")}><FileText size={15} /></button>{item.folio_fiscal && <button type="button" onClick={() => handleDocument(item, "xml")} title={t("invoice_ui.download_xml")}><Download size={15} /></button>}</td>
                </tr>
                {expandedInvoiceId === item.id_invoice && <tr className="invoice-lines-row"><td colSpan="7">
                  {invoiceLinesLoading === item.id_invoice ? <p className="muted">{t("invoice_ui.loading_lines")}</p> : invoiceLinesError[item.id_invoice] ? <p className="field-error">{t(invoiceLinesError[item.id_invoice], invoiceLinesError[item.id_invoice])}</p> : (invoiceLines[item.id_invoice] || []).length === 0 ? <p className="muted">{t("invoice_ui.no_lines")}</p> : <div className="invoice-lines-panel"><table><thead><tr><th>{t("invoice_ui.sat_key")}</th><th>{t("invoice_ui.description")}</th><th>{t("invoice_ui.quantity")}</th><th>{t("invoice_ui.unit")}</th><th>{t("invoice_ui.unit_price")}</th><th>{t("invoice_ui.discount")}</th><th>{t("invoice_ui.tax")}</th><th>{t("invoice_ui.total")}</th></tr></thead><tbody>{invoiceLines[item.id_invoice].map((line) => <tr key={line.id_invoice_material_service}><td>{line.sat_product_key || "—"}</td><td>{line.invoice_material_service_description}</td><td>{formatTableValue(line.quantity)}</td><td>{line.sat_unit_key || "—"}</td><td>{invoiceMoney(line.gross_price)}</td><td>{invoiceMoney(line.discount)}</td><td>{invoiceMoney(line.line_tax)}</td><td><strong>{invoiceMoney(line.line_total)}</strong></td></tr>)}</tbody></table></div>}
                </td></tr>}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderError() {
    if (!errorKey) return "";
    const fieldLabel = errorMeta?.field ? t(`fields.invoice.${errorMeta.field}`, errorMeta.field) : "";
    if (errorKey === "errors.field_too_long" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel} (${errorMeta.actual_length}/${errorMeta.max_length})`;
    }
    if (errorKey === "errors.invalid_field" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel}`;
    }
    return t(errorKey, errorKey);
  }

  const filtered = useMemo(() => {
    const needle = query.toLowerCase();
    if (!needle) return items;
    return items.filter((item) => Object.values(item || {}).some((value) => String(value ?? "").toLowerCase().includes(needle)));
  }, [items, query]);

  const groups = useMemo(() => filtered.reduce((acc, item) => {
    const key = String(item.invoice_status ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <div className="page-heading">
        <div><p className="eyebrow">{t("common.module")}</p><h2>{t("menu.invoice")}</h2></div>
        <button className="button ghost" onClick={loadData} disabled={!canRead}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </div>

      {canSubmitForm && (editingId ? <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-header"><Plus size={18} /><strong>{editingId ? t("common.edit") : t("common.new")}</strong></div>
        <div className="form-grid">
          {canSeeField("date_emision") && (
          <label className="field">
            <span>{t("fields.invoice.date_emision")}</span>
            <input name="date_emision" type="datetime-local" value={formData.date_emision ?? ""} onChange={handleChange} placeholder={t("fields.invoice.date_emision")} aria-invalid={Boolean(fieldErrors["date_emision"])} {...inputPropsForField("date_emision", validationRules["date_emision"], "datetime-local")} />
            {fieldErrors["date_emision"] && <span className="field-error">{formatFieldError("date_emision")}</span>}
          </label>
          )}
          {canSeeField("date_expiration") && (
          <label className="field">
            <span>{t("fields.invoice.date_expiration")}</span>
            <input name="date_expiration" type="datetime-local" value={formData.date_expiration ?? ""} onChange={handleChange} placeholder={t("fields.invoice.date_expiration")} aria-invalid={Boolean(fieldErrors["date_expiration"])} {...inputPropsForField("date_expiration", validationRules["date_expiration"], "datetime-local")} />
            {fieldErrors["date_expiration"] && <span className="field-error">{formatFieldError("date_expiration")}</span>}
          </label>
          )}
          {canSeeField("subtotal") && (
          <label className="field">
            <span>{t("fields.invoice.subtotal")}</span>
            <input name="subtotal" type="number" value={formData.subtotal ?? ""} onChange={handleChange} placeholder={t("fields.invoice.subtotal")} aria-invalid={Boolean(fieldErrors["subtotal"])} {...inputPropsForField("subtotal", validationRules["subtotal"], "number")} />
            {fieldErrors["subtotal"] && <span className="field-error">{formatFieldError("subtotal")}</span>}
          </label>
          )}
          {canSeeField("tax") && (
          <label className="field">
            <span>{t("fields.invoice.tax")}</span>
            <input name="tax" type="number" value={formData.tax ?? ""} onChange={handleChange} placeholder={t("fields.invoice.tax")} aria-invalid={Boolean(fieldErrors["tax"])} {...inputPropsForField("tax", validationRules["tax"], "number")} />
            {fieldErrors["tax"] && <span className="field-error">{formatFieldError("tax")}</span>}
          </label>
          )}
          {canSeeField("total") && (
          <label className="field">
            <span>{t("fields.invoice.total")}</span>
            <input name="total" type="number" value={formData.total ?? ""} onChange={handleChange} placeholder={t("fields.invoice.total")} aria-invalid={Boolean(fieldErrors["total"])} {...inputPropsForField("total", validationRules["total"], "number")} />
            {fieldErrors["total"] && <span className="field-error">{formatFieldError("total")}</span>}
          </label>
          )}
          {canSeeField("invoice_status") && (
          <label className="field">
            <span>{t("fields.invoice.invoice_status")}</span>
            <input name="invoice_status" type="text" maxLength={20} value={formData.invoice_status ?? ""} onChange={handleChange} placeholder={t("fields.invoice.invoice_status")} aria-invalid={Boolean(fieldErrors["invoice_status"])} {...inputPropsForField("invoice_status", validationRules["invoice_status"], "text")} />
            {fieldErrors["invoice_status"] && <span className="field-error">{formatFieldError("invoice_status")}</span>}
          </label>
          )}
          {canSeeField("payment_method") && (
          <label className="field">
            <span>{t("fields.invoice.payment_method")}</span>
            <input name="payment_method" type="text" maxLength={50} value={formData.payment_method ?? ""} onChange={handleChange} placeholder={t("fields.invoice.payment_method")} aria-invalid={Boolean(fieldErrors["payment_method"])} {...inputPropsForField("payment_method", validationRules["payment_method"], "text")} />
            {fieldErrors["payment_method"] && <span className="field-error">{formatFieldError("payment_method")}</span>}
          </label>
          )}
          {canSeeField("note") && (
          <label className="field">
            <span>{t("fields.invoice.note")}</span>
            <input name="note" type="text" maxLength={300} value={formData.note ?? ""} onChange={handleChange} placeholder={t("fields.invoice.note")} aria-invalid={Boolean(fieldErrors["note"])} {...inputPropsForField("note", validationRules["note"], "text")} />
            {fieldErrors["note"] && <span className="field-error">{formatFieldError("note")}</span>}
          </label>
          )}
          {canSeeField("id_customer_supplier") && (
          <label className="field">
            <span>{t("fields.invoice.id_customer_supplier")}</span>
            <select name="id_customer_supplier" value={formData.id_customer_supplier ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_customer_supplier"])} {...inputPropsForField("id_customer_supplier", validationRules["id_customer_supplier"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {customerSupplierOptions.map((item) => (
                <option key={item.id_customer_supplier ?? item.id ?? JSON.stringify(item)} value={item.id_customer_supplier ?? item.id ?? ""}>
                  {getOptionLabel(item, "customer_supplier")}
                </option>
              ))}
            </select>
            {fieldErrors["id_customer_supplier"] && <span className="field-error">{formatFieldError("id_customer_supplier")}</span>}
          </label>
          )}
          {canSeeField("fiscal_reference") && (
          <label className="field">
            <span>{t("fields.invoice.fiscal_reference")}</span>
            <input name="fiscal_reference" type="text" maxLength={50} value={formData.fiscal_reference ?? ""} onChange={handleChange} placeholder={t("fields.invoice.fiscal_reference")} aria-invalid={Boolean(fieldErrors["fiscal_reference"])} {...inputPropsForField("fiscal_reference", validationRules["fiscal_reference"], "text")} />
            {fieldErrors["fiscal_reference"] && <span className="field-error">{formatFieldError("fiscal_reference")}</span>}
          </label>
          )}
          {canSeeField("serie_csd") && (
          <label className="field">
            <span>{t("fields.invoice.serie_csd")}</span>
            <input name="serie_csd" type="text" maxLength={150} value={formData.serie_csd ?? ""} onChange={handleChange} placeholder={t("fields.invoice.serie_csd")} aria-invalid={Boolean(fieldErrors["serie_csd"])} {...inputPropsForField("serie_csd", validationRules["serie_csd"], "text")} />
            {fieldErrors["serie_csd"] && <span className="field-error">{formatFieldError("serie_csd")}</span>}
          </label>
          )}
          {canSeeField("internationalization") && (
          <label className="field">
            <span>{t("fields.invoice.internationalization")}</span>
            <select name="internationalization" value={formData.internationalization ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["internationalization"])} {...inputPropsForField("internationalization", validationRules["internationalization"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="exported" value="exported">exported</option>
              <option key="imported" value="imported">imported</option>
              <option key="local" value="local">local</option>
            </select>
            {fieldErrors["internationalization"] && <span className="field-error">{formatFieldError("internationalization")}</span>}
          </label>
          )}
          {canSeeField("currency") && (
          <label className="field">
            <span>{t("fields.invoice.currency")}</span>
            <input name="currency" type="text" maxLength={30} value={formData.currency ?? ""} onChange={handleChange} placeholder={t("fields.invoice.currency")} aria-invalid={Boolean(fieldErrors["currency"])} {...inputPropsForField("currency", validationRules["currency"], "text")} />
            {fieldErrors["currency"] && <span className="field-error">{formatFieldError("currency")}</span>}
          </label>
          )}
          {canSeeField("type_exchange_rate") && (
          <label className="field">
            <span>{t("fields.invoice.type_exchange_rate")}</span>
            <input name="type_exchange_rate" type="number" value={formData.type_exchange_rate ?? ""} onChange={handleChange} placeholder={t("fields.invoice.type_exchange_rate")} aria-invalid={Boolean(fieldErrors["type_exchange_rate"])} {...inputPropsForField("type_exchange_rate", validationRules["type_exchange_rate"], "number")} />
            {fieldErrors["type_exchange_rate"] && <span className="field-error">{formatFieldError("type_exchange_rate")}</span>}
          </label>
          )}
          {canSeeField("tax_certification_supplier") && (
          <label className="field">
            <span>{t("fields.invoice.tax_certification_supplier")}</span>
            <input name="tax_certification_supplier" type="number" value={formData.tax_certification_supplier ?? ""} onChange={handleChange} placeholder={t("fields.invoice.tax_certification_supplier")} aria-invalid={Boolean(fieldErrors["tax_certification_supplier"])} {...inputPropsForField("tax_certification_supplier", validationRules["tax_certification_supplier"], "number")} />
            {fieldErrors["tax_certification_supplier"] && <span className="field-error">{formatFieldError("tax_certification_supplier")}</span>}
          </label>
          )}
          {canSeeField("fiscal_certify_serie") && (
          <label className="field">
            <span>{t("fields.invoice.fiscal_certify_serie")}</span>
            <input name="fiscal_certify_serie" type="text" maxLength={150} value={formData.fiscal_certify_serie ?? ""} onChange={handleChange} placeholder={t("fields.invoice.fiscal_certify_serie")} aria-invalid={Boolean(fieldErrors["fiscal_certify_serie"])} {...inputPropsForField("fiscal_certify_serie", validationRules["fiscal_certify_serie"], "text")} />
            {fieldErrors["fiscal_certify_serie"] && <span className="field-error">{formatFieldError("fiscal_certify_serie")}</span>}
          </label>
          )}
          {canSeeField("certification_date") && (
          <label className="field">
            <span>{t("fields.invoice.certification_date")}</span>
            <input name="certification_date" type="datetime-local" value={formData.certification_date ?? ""} onChange={handleChange} placeholder={t("fields.invoice.certification_date")} aria-invalid={Boolean(fieldErrors["certification_date"])} {...inputPropsForField("certification_date", validationRules["certification_date"], "datetime-local")} />
            {fieldErrors["certification_date"] && <span className="field-error">{formatFieldError("certification_date")}</span>}
          </label>
          )}
          {canSeeField("cfdi_code") && (
          <label className="field">
            <span>{t("fields.invoice.cfdi_code")}</span>
            <input name="cfdi_code" type="text" maxLength={500} value={formData.cfdi_code ?? ""} onChange={handleChange} placeholder={t("fields.invoice.cfdi_code")} aria-invalid={Boolean(fieldErrors["cfdi_code"])} {...inputPropsForField("cfdi_code", validationRules["cfdi_code"], "text")} />
            {fieldErrors["cfdi_code"] && <span className="field-error">{formatFieldError("cfdi_code")}</span>}
          </label>
          )}
          {canSeeField("sat_code") && (
          <label className="field">
            <span>{t("fields.invoice.sat_code")}</span>
            <input name="sat_code" type="text" maxLength={500} value={formData.sat_code ?? ""} onChange={handleChange} placeholder={t("fields.invoice.sat_code")} aria-invalid={Boolean(fieldErrors["sat_code"])} {...inputPropsForField("sat_code", validationRules["sat_code"], "text")} />
            {fieldErrors["sat_code"] && <span className="field-error">{formatFieldError("sat_code")}</span>}
          </label>
          )}
          {canSeeField("sat_certification_code") && (
          <label className="field">
            <span>{t("fields.invoice.sat_certification_code")}</span>
            <input name="sat_certification_code" type="text" maxLength={500} value={formData.sat_certification_code ?? ""} onChange={handleChange} placeholder={t("fields.invoice.sat_certification_code")} aria-invalid={Boolean(fieldErrors["sat_certification_code"])} {...inputPropsForField("sat_certification_code", validationRules["sat_certification_code"], "text")} />
            {fieldErrors["sat_certification_code"] && <span className="field-error">{formatFieldError("sat_certification_code")}</span>}
          </label>
          )}
          {canSeeField("id_status") && (
          <label className="field">
            <span>{t("fields.invoice.id_status")}</span>
            <select name="id_status" value={formData.id_status ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_status"])} {...inputPropsForField("id_status", validationRules["id_status"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {statusOptions.map((item) => (
                <option key={item.id_status ?? item.id ?? JSON.stringify(item)} value={item.id_status ?? item.id ?? ""}>
                  {getOptionLabel(item, "status")}
                </option>
              ))}
            </select>
            {fieldErrors["id_status"] && <span className="field-error">{formatFieldError("id_status")}</span>}
          </label>
          )}
          {canSeeField("nombre_emisor") && (
          <label className="field">
            <span>{t("fields.invoice.nombre_emisor")}</span>
            <input name="nombre_emisor" type="text" maxLength={150} value={formData.nombre_emisor ?? ""} onChange={handleChange} placeholder={t("fields.invoice.nombre_emisor")} aria-invalid={Boolean(fieldErrors["nombre_emisor"])} {...inputPropsForField("nombre_emisor", validationRules["nombre_emisor"], "text")} />
            {fieldErrors["nombre_emisor"] && <span className="field-error">{formatFieldError("nombre_emisor")}</span>}
          </label>
          )}
          {canSeeField("lugar_expedicion") && (
          <label className="field">
            <span>{t("fields.invoice.lugar_expedicion")}</span>
            <input name="lugar_expedicion" type="text" maxLength={120} value={formData.lugar_expedicion ?? ""} onChange={handleChange} placeholder={t("fields.invoice.lugar_expedicion")} aria-invalid={Boolean(fieldErrors["lugar_expedicion"])} {...inputPropsForField("lugar_expedicion", validationRules["lugar_expedicion"], "text")} />
            {fieldErrors["lugar_expedicion"] && <span className="field-error">{formatFieldError("lugar_expedicion")}</span>}
          </label>
          )}
          {canSeeField("tipo_de_comprobante") && (
          <label className="field">
            <span>{t("fields.invoice.tipo_de_comprobante")}</span>
            <input name="tipo_de_comprobante" type="text" maxLength={50} value={formData.tipo_de_comprobante ?? ""} onChange={handleChange} placeholder={t("fields.invoice.tipo_de_comprobante")} aria-invalid={Boolean(fieldErrors["tipo_de_comprobante"])} {...inputPropsForField("tipo_de_comprobante", validationRules["tipo_de_comprobante"], "text")} />
            {fieldErrors["tipo_de_comprobante"] && <span className="field-error">{formatFieldError("tipo_de_comprobante")}</span>}
          </label>
          )}
          {canSeeField("rfc_receptor") && (
          <label className="field">
            <span>{t("fields.invoice.rfc_receptor")}</span>
            <input name="rfc_receptor" type="text" maxLength={20} value={formData.rfc_receptor ?? ""} onChange={handleChange} placeholder={t("fields.invoice.rfc_receptor")} aria-invalid={Boolean(fieldErrors["rfc_receptor"])} {...inputPropsForField("rfc_receptor", validationRules["rfc_receptor"], "text")} />
            {fieldErrors["rfc_receptor"] && <span className="field-error">{formatFieldError("rfc_receptor")}</span>}
          </label>
          )}
          {canSeeField("nombre_receptor") && (
          <label className="field">
            <span>{t("fields.invoice.nombre_receptor")}</span>
            <input name="nombre_receptor" type="text" maxLength={150} value={formData.nombre_receptor ?? ""} onChange={handleChange} placeholder={t("fields.invoice.nombre_receptor")} aria-invalid={Boolean(fieldErrors["nombre_receptor"])} {...inputPropsForField("nombre_receptor", validationRules["nombre_receptor"], "text")} />
            {fieldErrors["nombre_receptor"] && <span className="field-error">{formatFieldError("nombre_receptor")}</span>}
          </label>
          )}
          {canSeeField("regimen_fiscal_receptor") && (
          <label className="field">
            <span>{t("fields.invoice.regimen_fiscal_receptor")}</span>
            <input name="regimen_fiscal_receptor" type="text" maxLength={100} value={formData.regimen_fiscal_receptor ?? ""} onChange={handleChange} placeholder={t("fields.invoice.regimen_fiscal_receptor")} aria-invalid={Boolean(fieldErrors["regimen_fiscal_receptor"])} {...inputPropsForField("regimen_fiscal_receptor", validationRules["regimen_fiscal_receptor"], "text")} />
            {fieldErrors["regimen_fiscal_receptor"] && <span className="field-error">{formatFieldError("regimen_fiscal_receptor")}</span>}
          </label>
          )}
          {canSeeField("domicilio_fiscal_receptor") && (
          <label className="field">
            <span>{t("fields.invoice.domicilio_fiscal_receptor")}</span>
            <input name="domicilio_fiscal_receptor" type="text" maxLength={250} value={formData.domicilio_fiscal_receptor ?? ""} onChange={handleChange} placeholder={t("fields.invoice.domicilio_fiscal_receptor")} aria-invalid={Boolean(fieldErrors["domicilio_fiscal_receptor"])} {...inputPropsForField("domicilio_fiscal_receptor", validationRules["domicilio_fiscal_receptor"], "text")} />
            {fieldErrors["domicilio_fiscal_receptor"] && <span className="field-error">{formatFieldError("domicilio_fiscal_receptor")}</span>}
          </label>
          )}
          {canSeeField("id_proveedor_de_sello") && (
          <label className="field">
            <span>{t("fields.invoice.id_proveedor_de_sello")}</span>
            <input name="id_proveedor_de_sello" type="number" value={formData.id_proveedor_de_sello ?? ""} onChange={handleChange} placeholder={t("fields.invoice.id_proveedor_de_sello")} aria-invalid={Boolean(fieldErrors["id_proveedor_de_sello"])} {...inputPropsForField("id_proveedor_de_sello", validationRules["id_proveedor_de_sello"], "number")} />
            {fieldErrors["id_proveedor_de_sello"] && <span className="field-error">{formatFieldError("id_proveedor_de_sello")}</span>}
          </label>
          )}
          {canSeeField("folio_fiscal") && (
          <label className="field">
            <span>{t("fields.invoice.folio_fiscal")}</span>
            <input name="folio_fiscal" type="text" maxLength={50} value={formData.folio_fiscal ?? ""} onChange={handleChange} placeholder={t("fields.invoice.folio_fiscal")} aria-invalid={Boolean(fieldErrors["folio_fiscal"])} {...inputPropsForField("folio_fiscal", validationRules["folio_fiscal"], "text")} />
            {fieldErrors["folio_fiscal"] && <span className="field-error">{formatFieldError("folio_fiscal")}</span>}
          </label>
          )}
          {canSeeField("exportacion") && (
          <label className="field">
            <span>{t("fields.invoice.exportacion")}</span>
            <input name="exportacion" type="text" maxLength={50} value={formData.exportacion ?? ""} onChange={handleChange} placeholder={t("fields.invoice.exportacion")} aria-invalid={Boolean(fieldErrors["exportacion"])} {...inputPropsForField("exportacion", validationRules["exportacion"], "text")} />
            {fieldErrors["exportacion"] && <span className="field-error">{formatFieldError("exportacion")}</span>}
          </label>
          )}
          {canSeeField("folio") && (
          <label className="field">
            <span>{t("fields.invoice.folio")}</span>
            <input name="folio" type="text" maxLength={30} value={formData.folio ?? ""} onChange={handleChange} placeholder={t("fields.invoice.folio")} aria-invalid={Boolean(fieldErrors["folio"])} {...inputPropsForField("folio", validationRules["folio"], "text")} />
            {fieldErrors["folio"] && <span className="field-error">{formatFieldError("folio")}</span>}
          </label>
          )}
          {canSeeField("no_certificado_sat") && (
          <label className="field">
            <span>{t("fields.invoice.no_certificado_sat")}</span>
            <input name="no_certificado_sat" type="text" maxLength={50} value={formData.no_certificado_sat ?? ""} onChange={handleChange} placeholder={t("fields.invoice.no_certificado_sat")} aria-invalid={Boolean(fieldErrors["no_certificado_sat"])} {...inputPropsForField("no_certificado_sat", validationRules["no_certificado_sat"], "text")} />
            {fieldErrors["no_certificado_sat"] && <span className="field-error">{formatFieldError("no_certificado_sat")}</span>}
          </label>
          )}
          {canSeeField("sello_sat") && (
          <label className="field">
            <span>{t("fields.invoice.sello_sat")}</span>
            <input name="sello_sat" type="text" maxLength={500} value={formData.sello_sat ?? ""} onChange={handleChange} placeholder={t("fields.invoice.sello_sat")} aria-invalid={Boolean(fieldErrors["sello_sat"])} {...inputPropsForField("sello_sat", validationRules["sello_sat"], "text")} />
            {fieldErrors["sello_sat"] && <span className="field-error">{formatFieldError("sello_sat")}</span>}
          </label>
          )}
          {canSeeField("sello_certificacion_sat") && (
          <label className="field">
            <span>{t("fields.invoice.sello_certificacion_sat")}</span>
            <input name="sello_certificacion_sat" type="text" maxLength={500} value={formData.sello_certificacion_sat ?? ""} onChange={handleChange} placeholder={t("fields.invoice.sello_certificacion_sat")} aria-invalid={Boolean(fieldErrors["sello_certificacion_sat"])} {...inputPropsForField("sello_certificacion_sat", validationRules["sello_certificacion_sat"], "text")} />
            {fieldErrors["sello_certificacion_sat"] && <span className="field-error">{formatFieldError("sello_certificacion_sat")}</span>}
          </label>
          )}
          {canSeeField("no_certificado") && (
          <label className="field">
            <span>{t("fields.invoice.no_certificado")}</span>
            <input name="no_certificado" type="text" maxLength={50} value={formData.no_certificado ?? ""} onChange={handleChange} placeholder={t("fields.invoice.no_certificado")} aria-invalid={Boolean(fieldErrors["no_certificado"])} {...inputPropsForField("no_certificado", validationRules["no_certificado"], "text")} />
            {fieldErrors["no_certificado"] && <span className="field-error">{formatFieldError("no_certificado")}</span>}
          </label>
          )}
          {canSeeField("descuento") && (
          <label className="field">
            <span>{t("fields.invoice.descuento")}</span>
            <input name="descuento" type="number" value={formData.descuento ?? ""} onChange={handleChange} placeholder={t("fields.invoice.descuento")} aria-invalid={Boolean(fieldErrors["descuento"])} {...inputPropsForField("descuento", validationRules["descuento"], "number")} />
            {fieldErrors["descuento"] && <span className="field-error">{formatFieldError("descuento")}</span>}
          </label>
          )}
          {canSeeField("metodo_pago") && (
          <label className="field">
            <span>{t("fields.invoice.metodo_pago")}</span>
            <input name="metodo_pago" type="text" maxLength={50} value={formData.metodo_pago ?? ""} onChange={handleChange} placeholder={t("fields.invoice.metodo_pago")} aria-invalid={Boolean(fieldErrors["metodo_pago"])} {...inputPropsForField("metodo_pago", validationRules["metodo_pago"], "text")} />
            {fieldErrors["metodo_pago"] && <span className="field-error">{formatFieldError("metodo_pago")}</span>}
          </label>
          )}
          {canSeeField("condiciones_pago") && (
          <label className="field">
            <span>{t("fields.invoice.condiciones_pago")}</span>
            <input name="condiciones_pago" type="text" maxLength={100} value={formData.condiciones_pago ?? ""} onChange={handleChange} placeholder={t("fields.invoice.condiciones_pago")} aria-invalid={Boolean(fieldErrors["condiciones_pago"])} {...inputPropsForField("condiciones_pago", validationRules["condiciones_pago"], "text")} />
            {fieldErrors["condiciones_pago"] && <span className="field-error">{formatFieldError("condiciones_pago")}</span>}
          </label>
          )}
          {canSeeField("id_issuer_customer_supplier") && (
          <label className="field">
            <span>{t("fields.invoice.id_issuer_customer_supplier")}</span>
            <select name="id_issuer_customer_supplier" value={formData.id_issuer_customer_supplier ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_issuer_customer_supplier"])} {...inputPropsForField("id_issuer_customer_supplier", validationRules["id_issuer_customer_supplier"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {customerSupplierOptions.map((item) => (
                <option key={item.id_customer_supplier ?? item.id ?? JSON.stringify(item)} value={item.id_customer_supplier ?? item.id ?? ""}>
                  {getOptionLabel(item, "customer_supplier")}
                </option>
              ))}
            </select>
            {fieldErrors["id_issuer_customer_supplier"] && <span className="field-error">{formatFieldError("id_issuer_customer_supplier")}</span>}
          </label>
          )}
          {canSeeField("id_proyect") && (
          <label className="field">
            <span>{t("fields.invoice.id_proyect")}</span>
            <select name="id_proyect" value={formData.id_proyect ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_proyect"])} {...inputPropsForField("id_proyect", validationRules["id_proyect"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {proyectOptions.map((item) => (
                <option key={item.id_proyect ?? item.id ?? JSON.stringify(item)} value={item.id_proyect ?? item.id ?? ""}>
                  {getOptionLabel(item, "proyect")}
                </option>
              ))}
            </select>
            {fieldErrors["id_proyect"] && <span className="field-error">{formatFieldError("id_proyect")}</span>}
          </label>
          )}
          {canSeeField("apply_tax") && (
          <label className="field checkbox-field">
            <span>{t("fields.invoice.apply_tax")}</span>
            <input name="apply_tax" type="checkbox" checked={Boolean(formData.apply_tax)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["apply_tax"])} {...inputPropsForField("apply_tax", validationRules["apply_tax"], "checkbox")} />
            {fieldErrors["apply_tax"] && <span className="field-error">{formatFieldError("apply_tax")}</span>}
          </label>
          )}
          {canSeeField("tax_rate") && (
          <label className="field">
            <span>{t("fields.invoice.tax_rate")}</span>
            <input name="tax_rate" type="number" value={formData.tax_rate ?? ""} onChange={handleChange} placeholder={t("fields.invoice.tax_rate")} aria-invalid={Boolean(fieldErrors["tax_rate"])} {...inputPropsForField("tax_rate", validationRules["tax_rate"], "number")} />
            {fieldErrors["tax_rate"] && <span className="field-error">{formatFieldError("tax_rate")}</span>}
          </label>
          )}
          {canSeeField("commercial_terms") && (
          <label className="field">
            <span>{t("fields.invoice.commercial_terms")}</span>
            <input name="commercial_terms" type="text" maxLength={500} value={formData.commercial_terms ?? ""} onChange={handleChange} placeholder={t("fields.invoice.commercial_terms")} aria-invalid={Boolean(fieldErrors["commercial_terms"])} {...inputPropsForField("commercial_terms", validationRules["commercial_terms"], "text")} />
            {fieldErrors["commercial_terms"] && <span className="field-error">{formatFieldError("commercial_terms")}</span>}
          </label>
          )}
        </div>
        <div className="form-actions">
          <button className="button primary" type="submit">{t("common.save")}</button>
          <button className="button" type="button" onClick={() => { setFormData(emptyForm); setEditingId(null); setFieldErrors({}); }}>{t("common.cancel")}</button>
        </div>
      </form> : <InvoiceCreationForm onCreated={loadData} />)}

      {canRead && <div className="toolbar">
        <div className="search-box"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("common.search")} /></div>
        <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1); }}>
          <option value="10">10 {t("common.per_page")}</option><option value="25">25 {t("common.per_page")}</option><option value="50">50 {t("common.per_page")}</option>
        </select>
        <button className={view === "table" ? "button active" : "button"} onClick={() => setView("table")}>{t("common.table")}</button>
        <button className={view === "kanban" ? "button active" : "button"} onClick={() => setView("kanban")}>{t("common.kanban")}</button>
      </div>}

      {errorKey && <div className="alert error">{renderError()}</div>}
      {noticeKey && <div className="alert success">{t(noticeKey, noticeKey)}</div>}
      {loading && <div className="alert">{t("common.loading")}</div>}
      {permissionReady && !canRead && !canCreate && <div className="empty"><strong>{t("security.permission.read_denied", "Sin permiso de lectura")}</strong><p>{t("common.module_hidden_hint", "Este módulo no tiene acciones seleccionadas; quedará oculto y sus campos no se mostrarán.")}</p></div>}
      {canRead && !loading && filtered.length === 0 && <div className="empty"><strong>{t("common.empty_title")}</strong><p>{t("common.empty_body")}</p></div>}

      {view === "table" && renderInvoiceProjectSummary()}

      {canRead && view === "table" && filtered.length > 0 && <div className="table-card"><table><thead><tr>{showRowActions && <th>{t("common.actions")}</th>}
              {canSeeField("id_invoice") && <th>{t("fields.invoice.id_invoice")}</th>}
              {canSeeField("date_emision") && <th>{t("fields.invoice.date_emision")}</th>}
              {canSeeField("date_expiration") && <th>{t("fields.invoice.date_expiration")}</th>}
              {canSeeField("subtotal") && <th>{t("fields.invoice.subtotal")}</th>}
              {canSeeField("tax") && <th>{t("fields.invoice.tax")}</th>}
              {canSeeField("total") && <th>{t("fields.invoice.total")}</th>}
              {canSeeField("invoice_status") && <th>{t("fields.invoice.invoice_status")}</th>}
              {canSeeField("payment_method") && <th>{t("fields.invoice.payment_method")}</th>}
              {canSeeField("note") && <th>{t("fields.invoice.note")}</th>}
              {canSeeField("id_customer_supplier") && <th>{t("fields.invoice.id_customer_supplier")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_invoice}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canUpdate && !item.folio_fiscal && <button type="button" onClick={() => handleStamp(item)} title={t("invoice_ui.stamp_invoice")}><BadgeCheck size={15} /></button>}{canUpdate && <button type="button" onClick={() => handleInventory(item)} title={t("invoice_ui.apply_inventory", "Aplicar al almacén")}><Warehouse size={15} /></button>}{canUpdate && item.folio_fiscal && <button type="button" onClick={() => setFiscalInvoice(item)} title={t("fiscal.open_panel", "Cancelar, cobrar o acreditar")}><Scale size={15} /></button>}<button type="button" onClick={() => handleDocument(item, "pdf")} title={t("invoice_ui.download_pdf")}><FileText size={15} /></button>{item.folio_fiscal && <button type="button" onClick={() => handleDocument(item, "xml")} title={t("invoice_ui.download_xml")}><Download size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}</td>}
              {canSeeField("id_invoice") && <td><pre className="cell-value">{formatTableValue(item.id_invoice)}</pre></td>}
              {canSeeField("date_emision") && <td><pre className="cell-value">{formatTableValue(item.date_emision)}</pre></td>}
              {canSeeField("date_expiration") && <td><pre className="cell-value">{formatTableValue(item.date_expiration)}</pre></td>}
              {canSeeField("subtotal") && <td><pre className="cell-value">{formatTableValue(item.subtotal)}</pre></td>}
              {canSeeField("tax") && <td><pre className="cell-value">{formatTableValue(item.tax)}</pre></td>}
              {canSeeField("total") && <td><pre className="cell-value">{formatTableValue(item.total)}</pre></td>}
              {canSeeField("invoice_status") && <td><pre className="cell-value">{formatTableValue(item.invoice_status)}</pre></td>}
              {canSeeField("payment_method") && <td><pre className="cell-value">{formatTableValue(item.payment_method)}</pre></td>}
              {canSeeField("note") && <td><pre className="cell-value">{formatTableValue(item.note)}</pre></td>}
              {canSeeField("id_customer_supplier") && <td><pre className="cell-value">{formatTableValue(item.id_customer_supplier)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_invoice}><strong>{String(item.cfdi_code ?? item.id_invoice)}</strong><small>#{item.id_invoice}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

      {canCreate && <InvoiceUploadWidget />}

      <div className="pagination"><button className="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t("common.previous")}</button><span>{t("common.page")} {page}</span><button className="button" onClick={() => setPage(page + 1)}>{t("common.next")}</button></div>

      {fiscalInvoice && (
        <InvoiceFiscalPanel
          invoice={fiscalInvoice}
          onClose={() => setFiscalInvoice(null)}
          onChanged={loadData}
        />
      )}
    </section>
  );
}
