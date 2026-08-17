import { useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllInvoiceMaterialService, createInvoiceMaterialService, updateInvoiceMaterialService, deleteInvoiceMaterialService, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllInvoice, getAllMaterial, getAllService, getAllUser, getAllStatus, getAllCustomerSupplier, getAllProduct, getAllUnit } from "../api";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";

const emptyForm = { id_invoice: "", id_material: "", id_service: "", invoice_material_service_description: "", max_requirement_date: "", is_directly_related_to_product_service_creation: false, id_authorized: "", id_status: "", id_buyer: "", id_customer_supplier: "", gross_price: "", quantity: "", id_product: "", line_type: "", tax_applicable: false, line_tax: "", line_total: "", id_unit: "", authorization_status: "", authorization_note: "", authorization_date: "" };
const validationRules = allValidationRules["invoice_material_service"] || {};
const ENTITY_KEY = "invoice_material_service";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_invoice_material_service', 'id_invoice', 'id_material', 'id_service', 'invoice_material_service_description', 'max_requirement_date', 'is_directly_related_to_product_service_creation', 'id_authorized', 'id_status', 'id_buyer'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function InvoiceMaterialServicePage() {
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
  const showRowActions = canRead && (canUpdate || canDelete);
  const [invoiceOptions, setInvoiceOptions] = useState([]);
  const [materialOptions, setMaterialOptions] = useState([]);
  const [serviceOptions, setServiceOptions] = useState([]);
  const [userOptions, setUserOptions] = useState([]);
  const [statusOptions, setStatusOptions] = useState([]);
  const [customerSupplierOptions, setCustomerSupplierOptions] = useState([]);
  const [productOptions, setProductOptions] = useState([]);
  const [unitOptions, setUnitOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllInvoiceMaterialService({ page, per_page: perPage });
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
      if (canSeeField("id_invoice")) {
        try {
          const invoiceData = await getAllInvoice({ page: 1, per_page: 100 });
          setInvoiceOptions(Array.isArray(invoiceData) ? invoiceData : (invoiceData.items || []));
        } catch (_) {
          setInvoiceOptions([]);
        }
      }
      if (canSeeField("id_material")) {
        try {
          const materialData = await getAllMaterial({ page: 1, per_page: 100 });
          setMaterialOptions(Array.isArray(materialData) ? materialData : (materialData.items || []));
        } catch (_) {
          setMaterialOptions([]);
        }
      }
      if (canSeeField("id_service")) {
        try {
          const serviceData = await getAllService({ page: 1, per_page: 100 });
          setServiceOptions(Array.isArray(serviceData) ? serviceData : (serviceData.items || []));
        } catch (_) {
          setServiceOptions([]);
        }
      }
      if (canSeeField("id_authorized") || canSeeField("id_buyer")) {
        try {
          const userData = await getAllUser({ page: 1, per_page: 100 });
          setUserOptions(Array.isArray(userData) ? userData : (userData.items || []));
        } catch (_) {
          setUserOptions([]);
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
      if (canSeeField("id_customer_supplier")) {
        try {
          const customerSupplierData = await getAllCustomerSupplier({ page: 1, per_page: 100 });
          setCustomerSupplierOptions(Array.isArray(customerSupplierData) ? customerSupplierData : (customerSupplierData.items || []));
        } catch (_) {
          setCustomerSupplierOptions([]);
        }
      }
      if (canSeeField("id_product")) {
        try {
          const productData = await getAllProduct({ page: 1, per_page: 100 });
          setProductOptions(Array.isArray(productData) ? productData : (productData.items || []));
        } catch (_) {
          setProductOptions([]);
        }
      }
      if (canSeeField("id_unit")) {
        try {
          const unitData = await getAllUnit({ page: 1, per_page: 100 });
          setUnitOptions(Array.isArray(unitData) ? unitData : (unitData.items || []));
        } catch (_) {
          setUnitOptions([]);
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
    const fieldLabel = t(`fields.invoice_material_service.${fieldName}`, fieldName);
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
    const validation = validateForm("invoice_material_service", submitPayload, validationRules);
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
      if (editingId) await updateInvoiceMaterialService(editingId, submitPayload);
      else await createInvoiceMaterialService(submitPayload);
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
    setEditingId(item.id_invoice_material_service);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteInvoiceMaterialService(item.id_invoice_material_service); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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

  function formatEntityCatalogLabel(entityName, fallback = "") {
    if (!entityName) return "";
    return t(`menu.${entityName}`, fallback || entityName);
  }

  function formatControlTypeLabel(value) {
    const numeric = Number(value);
    const labels = [];
    if ((numeric & 1) === 1) labels.push(t("common.create", "Crear"));
    if ((numeric & 2) === 2) labels.push(t("common.read", "Leer"));
    if ((numeric & 4) === 4) labels.push(t("common.update", "Actualizar"));
    if ((numeric & 8) === 8) labels.push(t("common.delete", "Eliminar"));
    if (!labels.length) return String(value ?? "");
    const description = numeric === 15 ? t("common.crud_full", "CRUD completo") : labels.join(" + ");
    return `${numeric} - ${description}`;
  }

  // issue_12_phase3b_invoice_project_link_summary
  function invoiceProjectLabel(invoice) {
    if (ENTITY_KEY !== "invoice") return "";
    const rawProjectId = invoice?.id_proyect;
    if (rawProjectId === null || rawProjectId === undefined || String(rawProjectId).trim() === "") return "Sin proyecto";
    const project = proyectOptions.find((item) => String(item.id_proyect ?? item.id ?? "") === String(rawProjectId));
    return project ? getOptionLabel(project, "proyect") : `Proyecto #${rawProjectId}`;
  }

  function invoiceLinkStatus(invoice) {
    const rawProjectId = invoice?.id_proyect;
    return rawProjectId === null || rawProjectId === undefined || String(rawProjectId).trim() === "" ? "Sin vincular" : "Vinculada";
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

  function renderInvoiceProjectSummary() {
    if (ENTITY_KEY !== "invoice" || !canRead || !filtered.length) return null;
    const linked = invoiceLinkedCount();
    const unlinked = filtered.length - linked;
    return (
      <div className="table-card invoice-project-card">
        <div className="invoice-project-header">
          <div>
            <strong>Facturas / Proyecto</strong>
            <p className="muted">Identifica facturas cargadas desde XML y corrige su proyecto desde el formulario existente.</p>
          </div>
          <div className="invoice-project-metrics">
            <span><strong>{filtered.length}</strong>Total</span>
            <span><strong>{linked}</strong>Vinculadas</span>
            <span><strong>{unlinked}</strong>Sin proyecto</span>
          </div>
        </div>
        <div className="table-wrap">
          <table className="invoice-project-table">
            <thead>
              <tr>
                <th>Factura / UUID</th>
                <th>Emisor</th>
                <th>Receptor</th>
                <th>Total</th>
                <th>Proyecto</th>
                <th>Vinculación</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={`invoice-link-${item.id_invoice}`}>
                  <td><strong>{invoiceDisplayFolio(item)}</strong><p className="cell-value">{item.folio_fiscal || item.cfdi_code || "—"}</p></td>
                  <td><span>{item.nombre_emisor || "—"}</span></td>
                  <td><span>{item.nombre_receptor || item.id_customer_supplier || "—"}</span></td>
                  <td><strong>{invoiceMoney(item.total)}</strong></td>
                  <td><span>{invoiceProjectLabel(item)}</span></td>
                  <td><span className={item.id_proyect ? "invoice-link-badge linked" : "invoice-link-badge unlinked"}>{invoiceLinkStatus(item)}</span></td>
                  <td>{canUpdate ? <button type="button" className="button small" onClick={() => startEdit(item)}>Editar relación</button> : <span className="muted">Sin permiso</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderError() {
    if (!errorKey) return "";
    const fieldLabel = errorMeta?.field ? t(`fields.invoice_material_service.${errorMeta.field}`, errorMeta.field) : "";
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
    const key = String(item.id_status ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <div className="page-heading">
        <div><p className="eyebrow">{t("common.module")}</p><h2>{t("menu.invoice_material_service")}</h2></div>
        <button className="button ghost" onClick={loadData} disabled={!canRead}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </div>

      {canSubmitForm && <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-header"><Plus size={18} /><strong>{editingId ? t("common.edit") : t("common.new")}</strong></div>
        <div className="form-grid">
          {canSeeField("id_invoice") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_invoice")}</span>
            <select name="id_invoice" value={formData.id_invoice ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_invoice"])} {...inputPropsForField("id_invoice", validationRules["id_invoice"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {invoiceOptions.map((item) => (
                <option key={item.id_invoice ?? item.id ?? JSON.stringify(item)} value={item.id_invoice ?? item.id ?? ""}>
                  {getOptionLabel(item, "invoice")}
                </option>
              ))}
            </select>
            {fieldErrors["id_invoice"] && <span className="field-error">{formatFieldError("id_invoice")}</span>}
          </label>
          )}
          {canSeeField("id_material") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_material")}</span>
            <select name="id_material" value={formData.id_material ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_material"])} {...inputPropsForField("id_material", validationRules["id_material"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {materialOptions.map((item) => (
                <option key={item.id_material ?? item.id ?? JSON.stringify(item)} value={item.id_material ?? item.id ?? ""}>
                  {getOptionLabel(item, "material")}
                </option>
              ))}
            </select>
            {fieldErrors["id_material"] && <span className="field-error">{formatFieldError("id_material")}</span>}
          </label>
          )}
          {canSeeField("id_service") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_service")}</span>
            <select name="id_service" value={formData.id_service ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_service"])} {...inputPropsForField("id_service", validationRules["id_service"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {serviceOptions.map((item) => (
                <option key={item.id_service ?? item.id ?? JSON.stringify(item)} value={item.id_service ?? item.id ?? ""}>
                  {getOptionLabel(item, "service")}
                </option>
              ))}
            </select>
            {fieldErrors["id_service"] && <span className="field-error">{formatFieldError("id_service")}</span>}
          </label>
          )}
          {canSeeField("invoice_material_service_description") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.invoice_material_service_description")}</span>
            <input name="invoice_material_service_description" type="text" maxLength={200} value={formData.invoice_material_service_description ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.invoice_material_service_description")} aria-invalid={Boolean(fieldErrors["invoice_material_service_description"])} {...inputPropsForField("invoice_material_service_description", validationRules["invoice_material_service_description"], "text")} />
            {fieldErrors["invoice_material_service_description"] && <span className="field-error">{formatFieldError("invoice_material_service_description")}</span>}
          </label>
          )}
          {canSeeField("max_requirement_date") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.max_requirement_date")}</span>
            <input name="max_requirement_date" type="datetime-local" value={formData.max_requirement_date ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.max_requirement_date")} aria-invalid={Boolean(fieldErrors["max_requirement_date"])} {...inputPropsForField("max_requirement_date", validationRules["max_requirement_date"], "datetime-local")} />
            {fieldErrors["max_requirement_date"] && <span className="field-error">{formatFieldError("max_requirement_date")}</span>}
          </label>
          )}
          {canSeeField("is_directly_related_to_product_service_creation") && (
          <label className="field checkbox-field">
            <span>{t("fields.invoice_material_service.is_directly_related_to_product_service_creation")}</span>
            <input name="is_directly_related_to_product_service_creation" type="checkbox" checked={Boolean(formData.is_directly_related_to_product_service_creation)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["is_directly_related_to_product_service_creation"])} {...inputPropsForField("is_directly_related_to_product_service_creation", validationRules["is_directly_related_to_product_service_creation"], "checkbox")} />
            {fieldErrors["is_directly_related_to_product_service_creation"] && <span className="field-error">{formatFieldError("is_directly_related_to_product_service_creation")}</span>}
          </label>
          )}
          {canSeeField("id_authorized") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_authorized")}</span>
            <select name="id_authorized" value={formData.id_authorized ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_authorized"])} {...inputPropsForField("id_authorized", validationRules["id_authorized"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {userOptions.map((item) => (
                <option key={item.id_user ?? item.id ?? JSON.stringify(item)} value={item.id_user ?? item.id ?? ""}>
                  {getOptionLabel(item, "user")}
                </option>
              ))}
            </select>
            {fieldErrors["id_authorized"] && <span className="field-error">{formatFieldError("id_authorized")}</span>}
          </label>
          )}
          {canSeeField("id_status") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_status")}</span>
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
          {canSeeField("id_buyer") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_buyer")}</span>
            <select name="id_buyer" value={formData.id_buyer ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_buyer"])} {...inputPropsForField("id_buyer", validationRules["id_buyer"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {userOptions.map((item) => (
                <option key={item.id_user ?? item.id ?? JSON.stringify(item)} value={item.id_user ?? item.id ?? ""}>
                  {getOptionLabel(item, "user")}
                </option>
              ))}
            </select>
            {fieldErrors["id_buyer"] && <span className="field-error">{formatFieldError("id_buyer")}</span>}
          </label>
          )}
          {canSeeField("id_customer_supplier") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_customer_supplier")}</span>
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
          {canSeeField("gross_price") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.gross_price")}</span>
            <input name="gross_price" type="number" value={formData.gross_price ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.gross_price")} aria-invalid={Boolean(fieldErrors["gross_price"])} {...inputPropsForField("gross_price", validationRules["gross_price"], "number")} />
            {fieldErrors["gross_price"] && <span className="field-error">{formatFieldError("gross_price")}</span>}
          </label>
          )}
          {canSeeField("quantity") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.quantity")}</span>
            <input name="quantity" type="number" value={formData.quantity ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.quantity")} aria-invalid={Boolean(fieldErrors["quantity"])} {...inputPropsForField("quantity", validationRules["quantity"], "number")} />
            {fieldErrors["quantity"] && <span className="field-error">{formatFieldError("quantity")}</span>}
          </label>
          )}
          {canSeeField("id_product") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_product")}</span>
            <select name="id_product" value={formData.id_product ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_product"])} {...inputPropsForField("id_product", validationRules["id_product"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {productOptions.map((item) => (
                <option key={item.id_product ?? item.id ?? JSON.stringify(item)} value={item.id_product ?? item.id ?? ""}>
                  {getOptionLabel(item, "product")}
                </option>
              ))}
            </select>
            {fieldErrors["id_product"] && <span className="field-error">{formatFieldError("id_product")}</span>}
          </label>
          )}
          {canSeeField("line_type") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.line_type")}</span>
            <select name="line_type" value={formData.line_type ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["line_type"])} {...inputPropsForField("line_type", validationRules["line_type"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="product" value="product">product</option>
              <option key="service" value="service">service</option>
              <option key="custom" value="custom">custom</option>
            </select>
            {fieldErrors["line_type"] && <span className="field-error">{formatFieldError("line_type")}</span>}
          </label>
          )}
          {canSeeField("tax_applicable") && (
          <label className="field checkbox-field">
            <span>{t("fields.invoice_material_service.tax_applicable")}</span>
            <input name="tax_applicable" type="checkbox" checked={Boolean(formData.tax_applicable)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["tax_applicable"])} {...inputPropsForField("tax_applicable", validationRules["tax_applicable"], "checkbox")} />
            {fieldErrors["tax_applicable"] && <span className="field-error">{formatFieldError("tax_applicable")}</span>}
          </label>
          )}
          {canSeeField("line_tax") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.line_tax")}</span>
            <input name="line_tax" type="number" value={formData.line_tax ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.line_tax")} aria-invalid={Boolean(fieldErrors["line_tax"])} {...inputPropsForField("line_tax", validationRules["line_tax"], "number")} />
            {fieldErrors["line_tax"] && <span className="field-error">{formatFieldError("line_tax")}</span>}
          </label>
          )}
          {canSeeField("line_total") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.line_total")}</span>
            <input name="line_total" type="number" value={formData.line_total ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.line_total")} aria-invalid={Boolean(fieldErrors["line_total"])} {...inputPropsForField("line_total", validationRules["line_total"], "number")} />
            {fieldErrors["line_total"] && <span className="field-error">{formatFieldError("line_total")}</span>}
          </label>
          )}
          {canSeeField("id_unit") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.id_unit")}</span>
            <select name="id_unit" value={formData.id_unit ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_unit"])} {...inputPropsForField("id_unit", validationRules["id_unit"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {unitOptions.map((item) => (
                <option key={item.id_unit ?? item.id ?? JSON.stringify(item)} value={item.id_unit ?? item.id ?? ""}>
                  {getOptionLabel(item, "unit")}
                </option>
              ))}
            </select>
            {fieldErrors["id_unit"] && <span className="field-error">{formatFieldError("id_unit")}</span>}
          </label>
          )}
          {canSeeField("authorization_status") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.authorization_status")}</span>
            <select name="authorization_status" value={formData.authorization_status ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["authorization_status"])} {...inputPropsForField("authorization_status", validationRules["authorization_status"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="pending" value="pending">pending</option>
              <option key="authorized" value="authorized">authorized</option>
              <option key="rejected" value="rejected">rejected</option>
            </select>
            {fieldErrors["authorization_status"] && <span className="field-error">{formatFieldError("authorization_status")}</span>}
          </label>
          )}
          {canSeeField("authorization_note") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.authorization_note")}</span>
            <input name="authorization_note" type="text" maxLength={500} value={formData.authorization_note ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.authorization_note")} aria-invalid={Boolean(fieldErrors["authorization_note"])} {...inputPropsForField("authorization_note", validationRules["authorization_note"], "text")} />
            {fieldErrors["authorization_note"] && <span className="field-error">{formatFieldError("authorization_note")}</span>}
          </label>
          )}
          {canSeeField("authorization_date") && (
          <label className="field">
            <span>{t("fields.invoice_material_service.authorization_date")}</span>
            <input name="authorization_date" type="datetime-local" value={formData.authorization_date ?? ""} onChange={handleChange} placeholder={t("fields.invoice_material_service.authorization_date")} aria-invalid={Boolean(fieldErrors["authorization_date"])} {...inputPropsForField("authorization_date", validationRules["authorization_date"], "datetime-local")} />
            {fieldErrors["authorization_date"] && <span className="field-error">{formatFieldError("authorization_date")}</span>}
          </label>
          )}
        </div>
        <div className="form-actions">
          <button className="button primary" type="submit">{t("common.save")}</button>
          <button className="button" type="button" onClick={() => { setFormData(emptyForm); setEditingId(null); setFieldErrors({}); }}>{t("common.cancel")}</button>
        </div>
      </form>}

      {canRead && <div className="toolbar">
        <div className="search-box"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("common.search")} /></div>
        <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1); }}>
          <option value="10">10 {t("common.per_page")}</option><option value="25">25 {t("common.per_page")}</option><option value="50">50 {t("common.per_page")}</option>
        </select>
        <button className={view === "table" ? "button active" : "button"} onClick={() => setView("table")}>{t("common.table")}</button>
        <button className={view === "kanban" ? "button active" : "button"} onClick={() => setView("kanban")}>{t("common.kanban")}</button>
      </div>}

      {errorKey && <div className="alert error">{renderError()}</div>}
      {loading && <div className="alert">{t("common.loading")}</div>}
      {permissionReady && !canRead && !canCreate && <div className="empty"><strong>{t("security.permission.read_denied", "Sin permiso de lectura")}</strong><p>{t("common.module_hidden_hint", "Este módulo no tiene acciones seleccionadas; quedará oculto y sus campos no se mostrarán.")}</p></div>}
      {canRead && !loading && filtered.length === 0 && <div className="empty"><strong>{t("common.empty_title")}</strong><p>{t("common.empty_body")}</p></div>}

      {view === "table" && renderInvoiceProjectSummary()}

      {canRead && view === "table" && filtered.length > 0 && <div className="table-card"><table><thead><tr>{showRowActions && <th>{t("common.actions")}</th>}
              {canSeeField("id_invoice_material_service") && <th>{t("fields.invoice_material_service.id_invoice_material_service")}</th>}
              {canSeeField("id_invoice") && <th>{t("fields.invoice_material_service.id_invoice")}</th>}
              {canSeeField("id_material") && <th>{t("fields.invoice_material_service.id_material")}</th>}
              {canSeeField("id_service") && <th>{t("fields.invoice_material_service.id_service")}</th>}
              {canSeeField("invoice_material_service_description") && <th>{t("fields.invoice_material_service.invoice_material_service_description")}</th>}
              {canSeeField("max_requirement_date") && <th>{t("fields.invoice_material_service.max_requirement_date")}</th>}
              {canSeeField("is_directly_related_to_product_service_creation") && <th>{t("fields.invoice_material_service.is_directly_related_to_product_service_creation")}</th>}
              {canSeeField("id_authorized") && <th>{t("fields.invoice_material_service.id_authorized")}</th>}
              {canSeeField("id_status") && <th>{t("fields.invoice_material_service.id_status")}</th>}
              {canSeeField("id_buyer") && <th>{t("fields.invoice_material_service.id_buyer")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_invoice_material_service}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_invoice_material_service") && <td><pre className="cell-value">{formatTableValue(item.id_invoice_material_service)}</pre></td>}
              {canSeeField("id_invoice") && <td><pre className="cell-value">{formatTableValue(item.id_invoice)}</pre></td>}
              {canSeeField("id_material") && <td><pre className="cell-value">{formatTableValue(item.id_material)}</pre></td>}
              {canSeeField("id_service") && <td><pre className="cell-value">{formatTableValue(item.id_service)}</pre></td>}
              {canSeeField("invoice_material_service_description") && <td><pre className="cell-value">{formatTableValue(item.invoice_material_service_description)}</pre></td>}
              {canSeeField("max_requirement_date") && <td><pre className="cell-value">{formatTableValue(item.max_requirement_date)}</pre></td>}
              {canSeeField("is_directly_related_to_product_service_creation") && <td><pre className="cell-value">{formatTableValue(item.is_directly_related_to_product_service_creation)}</pre></td>}
              {canSeeField("id_authorized") && <td><pre className="cell-value">{formatTableValue(item.id_authorized)}</pre></td>}
              {canSeeField("id_status") && <td><pre className="cell-value">{formatTableValue(item.id_status)}</pre></td>}
              {canSeeField("id_buyer") && <td><pre className="cell-value">{formatTableValue(item.id_buyer)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_invoice_material_service}><strong>{String(item.invoice_material_service_description ?? item.id_invoice_material_service)}</strong><small>#{item.id_invoice_material_service}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

      <div className="pagination"><button className="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t("common.previous")}</button><span>{t("common.page")} {page}</span><button className="button" onClick={() => setPage(page + 1)}>{t("common.next")}</button></div>
    </section>
  );
}
