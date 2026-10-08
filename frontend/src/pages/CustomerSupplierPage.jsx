import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllCustomerSupplier, createCustomerSupplier, updateCustomerSupplier, deleteCustomerSupplier, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getInvoiceCatalogs } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import CustomerContactsPanel from "../components/CustomerContactsPanel.jsx";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";

/* eslint-disable react/prop-types */

const baseEmptyForm = { postal_code: "", name: "", contact_name: "", phone: "", email: "", web_site: "", street: "", number_ext: "", number_int: "", neighborhood: "", city: "", geographic_state: "", fiscal_type: "", tax_id: "", type: "", sla_level: "standard", credit_limit: "0", is_principal: false, id_user: "", path_logo: "", serie_csd: "" };
const validationRules = allValidationRules["customer_supplier"] || {};
const ENTITY_KEY = "customer_supplier";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_customer_supplier', 'postal_code', 'name', 'title', 'contact_name', 'phone', 'email', 'web_site', 'street', 'number_ext', 'number_int', 'neighborhood', 'city', 'geographic_state', 'fiscal_type', 'last_fiscal_certification_date', 'tax_id', 'type', 'sla_level', 'credit_limit', 'logistics_notes', 'is_principal', 'id_user', 'path_logo', 'serie_csd'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function CustomerSupplierPage({ clientsOnly = false, mode = "all", entityType = "" }) {
  const { lang, t } = useI18n();
  const forcedType = entityType || (mode === "suppliersOnly" ? "supplier" : clientsOnly || mode === "clientsOnly" ? "client" : "");
  const entityLabel = forcedType === "client" ? "Clientes" : forcedType === "supplier" ? "Proveedores" : t("menu.customer_supplier");
  const currentUser = useMemo(() => readCurrentUser(), []);
  // Vendedor precargado con quien esta dando de alta al cliente: es el unico
  // otro campo obligatorio ademas de Nombre (NOT NULL sin default en la
  // base), y casi siempre es la misma persona que abre el formulario. Sigue
  // siendo editable -- un vendedor puede dar de alta un cliente a nombre de
  // otro -- pero ya no hay que elegirlo a mano cada vez.
  const emptyForm = useMemo(() => ({ ...baseEmptyForm, type: forcedType, id_user: currentUser?.id_user ?? "" }), [forcedType, currentUser]);
  const [items, setItems] = useState([]);
  const [formData, setFormData] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [editingId, setEditingId] = useState(null);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("table");
  const [page, setPage] = useState(1);
  const [paginacion, setPaginacion] = useState({ total: 0, pages: 1, perPage: 0 });
  const [perPage, setPerPage] = useState(10);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [errorMeta, setErrorMeta] = useState(null);
  const [noticeKey, setNoticeKey] = useState("");

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
  const [fiscalRegimeCatalog, setFiscalRegimeCatalog] = useState({ regimen_fiscal: {}, persona_fisica: [], persona_moral: [] });
  const proyectOptions = [];

  // Un RFC de 12 caracteres es persona moral, de 13 persona fisica -- mismo
  // criterio que `_regimes_for_rfc` en el backend. Sin RFC capturado aun, se
  // muestran todos para no bloquear la captura.
  const allowedFiscalRegimes = useMemo(() => {
    const rfcLength = String(formData.tax_id || "").trim().length;
    const allowed = rfcLength === 12 ? fiscalRegimeCatalog.persona_moral
      : rfcLength === 13 ? fiscalRegimeCatalog.persona_fisica
      : Object.keys(fiscalRegimeCatalog.regimen_fiscal);
    return allowed.filter((code) => fiscalRegimeCatalog.regimen_fiscal[code]);
  }, [formData.tax_id, fiscalRegimeCatalog]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllCustomerSupplier({ page, per_page: perPage, q: query || undefined, ...(forcedType ? { type: forcedType } : {}) });
      setItems(Array.isArray(data) ? data : (data.items || data.data || []));
      // La respuesta ya traia el total y el numero de paginas; antes se
      // tiraban aqui, y por eso "Siguiente" no sabia cuando parar.
      setPaginacion({
        total: Array.isArray(data) ? 0 : (data.total ?? 0),
        pages: Array.isArray(data) ? 1 : (data.pages ?? 1),
        perPage: Array.isArray(data) ? 0 : (data.per_page ?? perPage),
      });
    } catch (error) {
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(error.payload?.meta || null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const temporizador = setTimeout(() => { loadData(); }, 300);
    return () => clearTimeout(temporizador);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, perPage, permissionReady, canRead, query]);
  useEffect(() => { setPage(1); }, [query]);
  useEffect(() => {
    async function loadFormOptions() {
      if (!permissionReady || (!canSubmitForm && !canRead)) return;
      if (canSeeField("fiscal_type")) {
        try {
          const catalogs = await getInvoiceCatalogs();
          setFiscalRegimeCatalog({
            regimen_fiscal: catalogs?.regimen_fiscal || {},
            persona_fisica: catalogs?.regimen_fiscal_persona_fisica || [],
            persona_moral: catalogs?.regimen_fiscal_persona_moral || [],
          });
        } catch (_) {
          setFiscalRegimeCatalog({ regimen_fiscal: {}, persona_fisica: [], persona_moral: [] });
        }
      }
    }
    loadFormOptions();
  }, [permissionReady, canSubmitForm, canRead, visibleFieldNames]);

  useEffect(() => {
    async function loadRolePermissions() {
      if (isSuperUser) {
        setModulePermission({ scope_create: 4, scope_read: 4, scope_update: 4, scope_delete: 4 });
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
          fetchAllPages(getAllEntityPermission),
          fetchAllPages(getAllNmFieldPermission),
          fetchAllPages(getAllField)
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
    return Number(modulePermission?.[SCOPE_FIELD_BY_BIT[bit]] || 0) !== 0;
  }

  function canSeeField(fieldName) {
    if (isSuperUser) return true;
    if (!permissionReady) return false;
    return CAMPOS_DE_AUDITORIA.has(fieldName) || visibleFieldNames.has(fieldName);
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
    if (forcedType) payload.type = forcedType;
    if (ENTITY_KEY === "user" && editingId && isBlankValue(payload.password)) {
      delete payload.password;
    }
    return payload;
  }

  function formatFieldError(fieldName) {
    const messageKey = fieldErrors[fieldName];
    if (!messageKey) return "";
    const fieldLabel = t(`fields.customer_supplier.${fieldName}`, fieldName);
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
    const validation = validateForm("customer_supplier", submitPayload, validationRules);
    const nextFieldErrors = { ...validation.errors };
    if (ENTITY_KEY === "user" && !editingId) {
      if (isBlankValue(submitPayload.username)) nextFieldErrors.username = "validations.user.username.required";
      if (isBlankValue(submitPayload.password)) nextFieldErrors.password = "validations.user.password.required";
    }
    if (submitPayload.is_principal && isBlankValue(submitPayload.tax_id)) {
      nextFieldErrors.tax_id = "validations.customer_supplier.principal_tax_id.required";
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
      // El vendedor ya no se captura a mano: en el alta lo asigna el servidor (quien
      // captura) y en la edicion se deja el que ya tenia. Se valida con el, pero no viaja.
      const { id_user: _vendedor, ...cuerpo } = submitPayload;
      if (editingId) await updateCustomerSupplier(editingId, cuerpo);
      else await createCustomerSupplier(cuerpo);
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
    setEditingId(item.id_customer_supplier);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteCustomerSupplier(item.id_customer_supplier); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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

  function renderError() {
    if (!errorKey) return "";
    const fieldLabel = errorMeta?.field ? t(`fields.customer_supplier.${errorMeta.field}`, errorMeta.field) : "";
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
    const key = String(item.geographic_state ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang, t]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={forcedType === "client" ? "CRM" : forcedType ? "Logística" : t("common.module")}
        titulo={entityLabel}
        subtitulo={forcedType === "client" ? t("page.customer_client.subtitle", "Aquí se registran las empresas a las que les vendes o das servicio: su razón social, RFC y dirección. Da de alta primero la empresa; después, en Contactos (más abajo), agrega a las personas con quienes tratas en ella.") : undefined}
      >
        <button className="button ghost" onClick={loadData} disabled={!canRead}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>

      {noticeKey && <div className="alert success">{t(noticeKey, noticeKey)}</div>}
      {canSubmitForm && (
      <FormularioPlegable
        titulo={editingId ? t("common.edit") : t("common.new")}
        abrirSi={editingId}
        onSubmit={handleSubmit}
      >
        <div className="form-grid">
          {canSeeField("postal_code") && (
          <label className="field">
            <span>{t("fields.customer_supplier.postal_code")}</span>
            <input name="postal_code" type="text" maxLength={10} value={formData.postal_code ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.postal_code")} aria-invalid={Boolean(fieldErrors["postal_code"])} {...inputPropsForField("postal_code", validationRules["postal_code"], "text")} />
            {fieldErrors["postal_code"] && <span className="field-error">{formatFieldError("postal_code")}</span>}
          </label>
          )}
          {canSeeField("name") && (
          <label className="field">
            <span>{t("fields.customer_supplier.name")}</span>
            <input name="name" type="text" maxLength={150} value={formData.name ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.name")} aria-invalid={Boolean(fieldErrors["name"])} {...inputPropsForField("name", validationRules["name"], "text")} />
            {fieldErrors["name"] && <span className="field-error">{formatFieldError("name")}</span>}
          </label>
          )}
          {canSeeField("contact_name") && (
          <label className="field">
            <span>{t("fields.customer_supplier.contact_name")}</span>
            <input name="contact_name" type="text" maxLength={150} value={formData.contact_name ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.contact_name")} aria-invalid={Boolean(fieldErrors["contact_name"])} {...inputPropsForField("contact_name", validationRules["contact_name"], "text")} />
            {fieldErrors["contact_name"] && <span className="field-error">{formatFieldError("contact_name")}</span>}
          </label>
          )}
          {canSeeField("phone") && (
          <label className="field">
            <span>{t("fields.customer_supplier.phone")}</span>
            <input name="phone" type="text" maxLength={30} value={formData.phone ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.phone")} aria-invalid={Boolean(fieldErrors["phone"])} {...inputPropsForField("phone", validationRules["phone"], "text")} />
            {fieldErrors["phone"] && <span className="field-error">{formatFieldError("phone")}</span>}
          </label>
          )}
          {canSeeField("email") && (
          <label className="field">
            <span>{t("fields.customer_supplier.email")}</span>
            <input name="email" type="email" maxLength={100} value={formData.email ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.email")} aria-invalid={Boolean(fieldErrors["email"])} {...inputPropsForField("email", validationRules["email"], "email")} />
            {fieldErrors["email"] && <span className="field-error">{formatFieldError("email")}</span>}
          </label>
          )}
          {canSeeField("web_site") && (
          <label className="field">
            <span>{t("fields.customer_supplier.web_site")}</span>
            <input name="web_site" type="text" maxLength={50} value={formData.web_site ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.web_site")} aria-invalid={Boolean(fieldErrors["web_site"])} {...inputPropsForField("web_site", validationRules["web_site"], "text")} />
            {fieldErrors["web_site"] && <span className="field-error">{formatFieldError("web_site")}</span>}
          </label>
          )}
          {canSeeField("street") && (
          <label className="field">
            <span>{t("fields.customer_supplier.street")}</span>
            <input name="street" type="text" maxLength={100} value={formData.street ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.street")} aria-invalid={Boolean(fieldErrors["street"])} {...inputPropsForField("street", validationRules["street"], "text")} />
            {fieldErrors["street"] && <span className="field-error">{formatFieldError("street")}</span>}
          </label>
          )}
          {canSeeField("number_ext") && (
          <label className="field">
            <span>{t("fields.customer_supplier.number_ext")}</span>
            <input name="number_ext" type="text" maxLength={5} value={formData.number_ext ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.number_ext")} aria-invalid={Boolean(fieldErrors["number_ext"])} {...inputPropsForField("number_ext", validationRules["number_ext"], "text")} />
            {fieldErrors["number_ext"] && <span className="field-error">{formatFieldError("number_ext")}</span>}
          </label>
          )}
          {canSeeField("number_int") && (
          <label className="field">
            <span>{t("fields.customer_supplier.number_int")}</span>
            <input name="number_int" type="text" maxLength={5} value={formData.number_int ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.number_int")} aria-invalid={Boolean(fieldErrors["number_int"])} {...inputPropsForField("number_int", validationRules["number_int"], "text")} />
            {fieldErrors["number_int"] && <span className="field-error">{formatFieldError("number_int")}</span>}
          </label>
          )}
          {canSeeField("neighborhood") && (
          <label className="field">
            <span>{t("fields.customer_supplier.neighborhood")}</span>
            <input name="neighborhood" type="text" maxLength={50} value={formData.neighborhood ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.neighborhood")} aria-invalid={Boolean(fieldErrors["neighborhood"])} {...inputPropsForField("neighborhood", validationRules["neighborhood"], "text")} />
            {fieldErrors["neighborhood"] && <span className="field-error">{formatFieldError("neighborhood")}</span>}
          </label>
          )}
          {canSeeField("city") && (
          <label className="field">
            <span>{t("fields.customer_supplier.city")}</span>
            <input name="city" type="text" maxLength={50} value={formData.city ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.city")} aria-invalid={Boolean(fieldErrors["city"])} {...inputPropsForField("city", validationRules["city"], "text")} />
            {fieldErrors["city"] && <span className="field-error">{formatFieldError("city")}</span>}
          </label>
          )}
          {canSeeField("geographic_state") && (
          <label className="field">
            <span>{t("fields.customer_supplier.geographic_state")}</span>
            <input name="geographic_state" type="text" maxLength={20} value={formData.geographic_state ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.geographic_state")} aria-invalid={Boolean(fieldErrors["geographic_state"])} {...inputPropsForField("geographic_state", validationRules["geographic_state"], "text")} />
            {fieldErrors["geographic_state"] && <span className="field-error">{formatFieldError("geographic_state")}</span>}
          </label>
          )}
          {canSeeField("fiscal_type") && (
          <label className="field">
            <span>{t("fields.customer_supplier.fiscal_type")}</span>
            <select name="fiscal_type" value={formData.fiscal_type ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["fiscal_type"])} {...inputPropsForField("fiscal_type", validationRules["fiscal_type"], "text")}>
              <option value="">{t("common.select", "— Selecciona —")}</option>
              {allowedFiscalRegimes.map((code) => (
                <option key={code} value={code}>{code} · {fiscalRegimeCatalog.regimen_fiscal[code]}</option>
              ))}
            </select>
            {fieldErrors["fiscal_type"] && <span className="field-error">{formatFieldError("fiscal_type")}</span>}
          </label>
          )}
          {canSeeField("tax_id") && (
          <label className="field">
            <span>{t("fields.customer_supplier.tax_id")}</span>
            <input name="tax_id" type="text" maxLength={50} value={formData.tax_id ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.tax_id")} aria-invalid={Boolean(fieldErrors["tax_id"])} {...inputPropsForField("tax_id", validationRules["tax_id"], "text")} />
            {fieldErrors["tax_id"] && <span className="field-error">{formatFieldError("tax_id")}</span>}
          </label>
          )}
          {canSeeField("type") && !forcedType && (
          <label className="field">
            <span>{t("fields.customer_supplier.type")}</span>
            <select name="type" value={formData.type ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["type"])} {...inputPropsForField("type", validationRules["type"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="client" value="client">client</option>
              <option key="supplier" value="supplier">supplier</option>
            </select>
            {fieldErrors["type"] && <span className="field-error">{formatFieldError("type")}</span>}
          </label>
          )}
          {/* sla_level y credit_limit: escondidos a proposito (2026-09-29).
              Son NOT NULL con DEFAULT en la base ('standard' / 0), pero
              ningun modulo de negocio real los lee -- ni facturacion/POS
              (que tiene su propio credit_limit en `pos`) ni logistica (que
              tiene su propio sla_level en `logistics_contract`). Se dejan en
              `baseEmptyForm` con su valor por omision para que el alta siga
              funcionando sin pedirselos a nadie; si algun dia un modulo real
              los necesita, aqui es donde se vuelven a mostrar. */}
          {canSeeField("is_principal") && (
          <label className="checkbox-inline principal-company-field">
            <input name="is_principal" type="checkbox" checked={Boolean(formData.is_principal)} onChange={handleChange} />
            <span>{t("fields.customer_supplier.is_principal", "Empresa principal")}</span>
            <small>{t("common.principal_company_hint", "Su RFC se usará para clasificar automáticamente facturas XML como compras o ventas.")}</small>
          </label>
          )}
          {canSeeField("serie_csd") && formData.is_principal && (
          <label className="field">
            <span>{t("fields.customer_supplier.serie_csd", "Serie del CFDI (opcional)")}</span>
            <input name="serie_csd" type="text" maxLength={25} value={formData.serie_csd ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.serie_csd", "Serie del CFDI (opcional)")} aria-invalid={Boolean(fieldErrors["serie_csd"])} />
            <small>{t("common.serie_csd_hint", "Se usa como serie por defecto al emitir facturas de esta empresa; una factura puede capturar otra distinta.")}</small>
            {fieldErrors["serie_csd"] && <span className="field-error">{formatFieldError("serie_csd")}</span>}
          </label>
          )}
          {canSeeField("path_logo") && (
          <label className="field">
            <span>{t("fields.customer_supplier.path_logo")}</span>
            <input name="path_logo" type="text" maxLength={150} value={formData.path_logo ?? ""} onChange={handleChange} placeholder={t("fields.customer_supplier.path_logo")} aria-invalid={Boolean(fieldErrors["path_logo"])} {...inputPropsForField("path_logo", validationRules["path_logo"], "text")} />
            {fieldErrors["path_logo"] && <span className="field-error">{formatFieldError("path_logo")}</span>}
          </label>
          )}
        </div>
        <div className="form-actions">
          <button className="button primary" type="submit">{t("common.save")}</button>
          <button className="button" type="button" onClick={() => { setFormData(emptyForm); setEditingId(null); setFieldErrors({}); }}>{t("common.cancel")}</button>
        </div>
      </FormularioPlegable>
      )}

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


      {canRead && view === "table" && filtered.length > 0 && <div className="table-card"><table><thead><tr>{showRowActions && <th>{t("common.actions")}</th>}
              {canSeeField("id_customer_supplier") && <th>{t("fields.customer_supplier.id_customer_supplier")}</th>}
              {canSeeField("postal_code") && <th>{t("fields.customer_supplier.postal_code")}</th>}
              {canSeeField("name") && <th>{t("fields.customer_supplier.name")}</th>}
              {canSeeField("title") && <th>{t("fields.customer_supplier.title")}</th>}
              {canSeeField("contact_name") && <th>{t("fields.customer_supplier.contact_name")}</th>}
              {canSeeField("phone") && <th>{t("fields.customer_supplier.phone")}</th>}
              {canSeeField("email") && <th>{t("fields.customer_supplier.email")}</th>}
              {canSeeField("web_site") && <th>{t("fields.customer_supplier.web_site")}</th>}
              {canSeeField("street") && <th>{t("fields.customer_supplier.street")}</th>}
              {canSeeField("number_ext") && <th>{t("fields.customer_supplier.number_ext")}</th>}
              {canSeeField("sla_level") && <th>Nivel SLA</th>}
              {canSeeField("credit_limit") && <th>Límite de crédito</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_customer_supplier}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_customer_supplier") && <td><pre className="cell-value">{formatTableValue(item.id_customer_supplier)}</pre></td>}
              {canSeeField("postal_code") && <td><pre className="cell-value">{formatTableValue(item.postal_code)}</pre></td>}
              {canSeeField("name") && <td><pre className="cell-value">{formatTableValue(item.name)}{item.is_principal ? ` · ${t("fields.customer_supplier.is_principal", "Empresa principal")}` : ""}</pre></td>}
              {canSeeField("title") && <td><pre className="cell-value">{formatTableValue(item.title)}</pre></td>}
              {canSeeField("contact_name") && <td><pre className="cell-value">{formatTableValue(item.contact_name)}</pre></td>}
              {canSeeField("phone") && <td><pre className="cell-value">{formatTableValue(item.phone)}</pre></td>}
              {canSeeField("email") && <td><pre className="cell-value">{formatTableValue(item.email)}</pre></td>}
              {canSeeField("web_site") && <td><pre className="cell-value">{formatTableValue(item.web_site)}</pre></td>}
              {canSeeField("street") && <td><pre className="cell-value">{formatTableValue(item.street)}</pre></td>}
              {canSeeField("number_ext") && <td><pre className="cell-value">{formatTableValue(item.number_ext)}</pre></td>}
              {canSeeField("sla_level") && <td><pre className="cell-value">{formatTableValue(item.sla_level)}</pre></td>}
              {canSeeField("credit_limit") && <td><pre className="cell-value">{formatTableValue(item.credit_limit)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_customer_supplier}><strong>{String(item.name ?? item.id_customer_supplier)}</strong>{item.is_principal && <span className="principal-company-badge">{t("fields.customer_supplier.is_principal", "Empresa principal")}</span>}<small>#{item.id_customer_supplier}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

      <Pagination
        page={page}
        pages={paginacion.pages}
        total={paginacion.total}
        perPage={paginacion.perPage}
        loading={loading}
        onChange={setPage}
      />

      {/* Contactos por empresa -- solo tiene sentido para clientes, no
          proveedores. Se gestionan aqui porque cuelgan de la empresa, igual
          que `logistics_contact` cuelga de la suya en Logistica. */}
      {forcedType === "client" && <CustomerContactsPanel />}
    </section>
  );
}
