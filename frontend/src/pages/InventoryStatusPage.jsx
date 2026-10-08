import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllInventoryStatus, createInventoryStatus, updateInventoryStatus, deleteInventoryStatus, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllDepartment, getAllSubdepartment, getAllLevel } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";

const emptyForm = { inventory_status_code: "", inventory_status_description: "", color: "", entity_scope: "", flow_scope: "", id_department: "", id_subdepartment: "", id_minimum_level: "", is_active: false, is_terminal: false, visible_to_other_departments: false, sort_order: "" };
const validationRules = allValidationRules["inventory_status"] || {};
const ENTITY_KEY = "inventory_status";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_inventory_status', 'inventory_status_code', 'inventory_status_description', 'color', 'entity_scope', 'flow_scope', 'id_department', 'id_subdepartment', 'id_minimum_level', 'is_active'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function InventoryStatusPage() {
  const { lang, t } = useI18n();
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
  const [departmentOptions, setDepartmentOptions] = useState([]);
  const [subdepartmentOptions, setSubdepartmentOptions] = useState([]);
  const [levelOptions, setLevelOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllInventoryStatus({ page, per_page: perPage, q: query || undefined });
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

  // Se espera a que deje de teclear: una peticion por tecla convierte una
  // busqueda de seis letras en seis consultas.
  useEffect(() => {
    const temporizador = setTimeout(() => { loadData(); }, 300);
    return () => clearTimeout(temporizador);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, perPage, permissionReady, canRead, query]);
  // Buscar algo nuevo vuelve a la primera pagina: sin esto, quien esta en la 7
  // y escribe otra cosa pide la pagina 7 de un resultado distinto.
  useEffect(() => { setPage(1); }, [query]);
  useEffect(() => {
    async function loadFormOptions() {
      if (!permissionReady || (!canSubmitForm && !canRead)) return;
      if (canSeeField("id_department")) {
        try {
          const departmentData = await getAllDepartment({ page: 1, per_page: 100 });
          setDepartmentOptions(Array.isArray(departmentData) ? departmentData : (departmentData.items || []));
        } catch (_) {
          setDepartmentOptions([]);
        }
      }
      if (canSeeField("id_subdepartment")) {
        try {
          const subdepartmentData = await getAllSubdepartment({ page: 1, per_page: 100 });
          setSubdepartmentOptions(Array.isArray(subdepartmentData) ? subdepartmentData : (subdepartmentData.items || []));
        } catch (_) {
          setSubdepartmentOptions([]);
        }
      }
      if (canSeeField("id_minimum_level")) {
        try {
          const levelData = await getAllLevel({ page: 1, per_page: 100 });
          setLevelOptions(Array.isArray(levelData) ? levelData : (levelData.items || []));
        } catch (_) {
          setLevelOptions([]);
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
    if (ENTITY_KEY === "user" && editingId && isBlankValue(payload.password)) {
      delete payload.password;
    }
    return payload;
  }

  function formatFieldError(fieldName) {
    const messageKey = fieldErrors[fieldName];
    if (!messageKey) return "";
    const fieldLabel = t(`fields.inventory_status.${fieldName}`, fieldName);
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
    const submitPayload = buildSubmitPayload();
    const validation = validateForm("inventory_status", submitPayload, validationRules);
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
      if (editingId) await updateInventoryStatus(editingId, submitPayload);
      else await createInventoryStatus(submitPayload);
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
    setEditingId(item.id_inventory_status);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteInventoryStatus(item.id_inventory_status); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
  }



  async function resetMfaForItem(item) {
    if (ENTITY_KEY !== "user") return;
    const targetId = item.id_user ?? item.id;
    if (!targetId) return;
    if (!window.confirm(t("common.mfa_reset_confirm", "¿Restablecer MFA de este usuario?"))) return;
    setErrorKey("");
    setErrorMeta(null);
    try {
      await resetUserMfa(targetId);
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
    const fieldLabel = errorMeta?.field ? t(`fields.inventory_status.${errorMeta.field}`, errorMeta.field) : "";
    if (errorKey === "errors.field_too_long" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel} (${errorMeta.actual_length}/${errorMeta.max_length})`;
    }
    if (errorKey === "errors.invalid_field" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel}`;
    }
    return t(errorKey, errorKey);
  }

  // El buscador pregunta al SERVIDOR, asi que lo que llega ya viene filtrado.
  //
  // Antes se filtraba aqui, sobre `items`, que es solo la pagina cargada: con
  // 2 221 productos en 56 paginas, teclear un nombre estando en la primera no
  // encontraba el que vive en la 34, y el contador seguia diciendo 2 221. El
  // servidor busca por todas las columnas de texto y, si lo escrito es un
  // numero, tambien por los identificadores -- asi "8580" encuentra el
  // producto 8580 aunque no se sepa como se llama.
  const filtered = items;

  const groups = useMemo(() => filtered.reduce((acc, item) => {
    const key = String(item.id_inventory_status ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.inventory_status")}
        subtitulo={t("page.inventory_status.subtitle", "")}
      >
        <button className="button ghost" onClick={loadData} disabled={!canRead}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>

      {canSubmitForm && (
      <FormularioPlegable
        titulo={editingId ? t("common.edit") : t("common.new")}
        abrirSi={editingId}
        onSubmit={handleSubmit}
      >
        <div className="form-grid">
          {canSeeField("inventory_status_code") && (
          <label className="field">
            <span>{t("fields.inventory_status.inventory_status_code")}</span>
            <input name="inventory_status_code" type="text" maxLength={50} value={formData.inventory_status_code ?? ""} onChange={handleChange} placeholder={t("fields.inventory_status.inventory_status_code")} aria-invalid={Boolean(fieldErrors["inventory_status_code"])} {...inputPropsForField("inventory_status_code", validationRules["inventory_status_code"], "text")} />
            {fieldErrors["inventory_status_code"] && <span className="field-error">{formatFieldError("inventory_status_code")}</span>}
          </label>
          )}
          {canSeeField("inventory_status_description") && (
          <label className="field">
            <span>{t("fields.inventory_status.inventory_status_description")}</span>
            <input name="inventory_status_description" type="text" maxLength={120} value={formData.inventory_status_description ?? ""} onChange={handleChange} placeholder={t("fields.inventory_status.inventory_status_description")} aria-invalid={Boolean(fieldErrors["inventory_status_description"])} {...inputPropsForField("inventory_status_description", validationRules["inventory_status_description"], "text")} />
            {fieldErrors["inventory_status_description"] && <span className="field-error">{formatFieldError("inventory_status_description")}</span>}
          </label>
          )}
          {canSeeField("color") && (
          <label className="field">
            <span>{t("fields.inventory_status.color")}</span>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <input name="color" type="text" maxLength={20} value={formData.color ?? ""} onChange={handleChange} placeholder="#16a34a" aria-invalid={Boolean(fieldErrors["color"])} {...inputPropsForField("color", validationRules["color"], "text")} />
              <input name="color" type="color" value={/^#([0-9a-f]{6})$/i.test(String(formData.color || "")) ? formData.color : "#16a34a"} onChange={handleChange} aria-label={t("common.select_color", "Seleccionar color")} title={t("common.select_color", "Seleccionar color")} />
              <small style={{ whiteSpace: "nowrap", fontWeight: 700 }}>{t("common.select_color", "Seleccionar color")}</small>
            </div>
            {fieldErrors["color"] && <span className="field-error">{formatFieldError("color")}</span>}
          </label>
          )}
          {canSeeField("entity_scope") && (
          <label className="field">
            <span>{t("fields.inventory_status.entity_scope")}</span>
            <select name="entity_scope" value={formData.entity_scope ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["entity_scope"])} {...inputPropsForField("entity_scope", validationRules["entity_scope"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option value="product">{t("menu.product", "Producto")} (product)</option>
            </select>
            {fieldErrors["entity_scope"] && <span className="field-error">{formatFieldError("entity_scope")}</span>}
          </label>
          )}
          {canSeeField("flow_scope") && (
          <label className="field">
            <span>{t("fields.inventory_status.flow_scope")}</span>
            <select name="flow_scope" value={formData.flow_scope ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["flow_scope"])} {...inputPropsForField("flow_scope", validationRules["flow_scope"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option value="inventory">{t("menu.inventory_status", "Inventario")} (inventory)</option>
            </select>
            {fieldErrors["flow_scope"] && <span className="field-error">{formatFieldError("flow_scope")}</span>}
          </label>
          )}
          {canSeeField("id_department") && (
          <label className="field">
            <span>{t("fields.inventory_status.id_department")}</span>
            <select name="id_department" value={formData.id_department ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_department"])} {...inputPropsForField("id_department", validationRules["id_department"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {departmentOptions.map((item) => (
                <option key={item.id_department ?? item.id ?? JSON.stringify(item)} value={item.id_department ?? item.id ?? ""}>
                  {getOptionLabel(item, "department")}
                </option>
              ))}
            </select>
            {fieldErrors["id_department"] && <span className="field-error">{formatFieldError("id_department")}</span>}
          </label>
          )}
          {canSeeField("id_subdepartment") && (
          <label className="field">
            <span>{t("fields.inventory_status.id_subdepartment")}</span>
            <select name="id_subdepartment" value={formData.id_subdepartment ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_subdepartment"])} {...inputPropsForField("id_subdepartment", validationRules["id_subdepartment"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {subdepartmentOptions.map((item) => (
                <option key={item.id_subdepartment ?? item.id ?? JSON.stringify(item)} value={item.id_subdepartment ?? item.id ?? ""}>
                  {getOptionLabel(item, "subdepartment")}
                </option>
              ))}
            </select>
            {fieldErrors["id_subdepartment"] && <span className="field-error">{formatFieldError("id_subdepartment")}</span>}
          </label>
          )}
          {canSeeField("id_minimum_level") && (
          <label className="field">
            <span>{t("fields.inventory_status.id_minimum_level")}</span>
            <select name="id_minimum_level" value={formData.id_minimum_level ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_minimum_level"])} {...inputPropsForField("id_minimum_level", validationRules["id_minimum_level"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {levelOptions.map((item) => (
                <option key={item.id_level ?? item.id ?? JSON.stringify(item)} value={item.id_level ?? item.id ?? ""}>
                  {getOptionLabel(item, "level")}
                </option>
              ))}
            </select>
            {fieldErrors["id_minimum_level"] && <span className="field-error">{formatFieldError("id_minimum_level")}</span>}
          </label>
          )}
          {canSeeField("is_active") && (
          <label className="field checkbox-field">
            <span>{t("fields.inventory_status.is_active")}</span>
            <input name="is_active" type="checkbox" checked={Boolean(formData.is_active)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["is_active"])} {...inputPropsForField("is_active", validationRules["is_active"], "checkbox")} />
            {fieldErrors["is_active"] && <span className="field-error">{formatFieldError("is_active")}</span>}
          </label>
          )}
          {canSeeField("is_terminal") && (
          <label className="field checkbox-field">
            <span>{t("fields.inventory_status.is_terminal")}</span>
            <input name="is_terminal" type="checkbox" checked={Boolean(formData.is_terminal)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["is_terminal"])} {...inputPropsForField("is_terminal", validationRules["is_terminal"], "checkbox")} />
            {fieldErrors["is_terminal"] && <span className="field-error">{formatFieldError("is_terminal")}</span>}
          </label>
          )}
          {canSeeField("visible_to_other_departments") && (
          <label className="field checkbox-field">
            <span>{t("fields.inventory_status.visible_to_other_departments")}</span>
            <input name="visible_to_other_departments" type="checkbox" checked={Boolean(formData.visible_to_other_departments)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["visible_to_other_departments"])} {...inputPropsForField("visible_to_other_departments", validationRules["visible_to_other_departments"], "checkbox")} />
            {fieldErrors["visible_to_other_departments"] && <span className="field-error">{formatFieldError("visible_to_other_departments")}</span>}
          </label>
          )}
          {canSeeField("sort_order") && (
          <label className="field">
            <span>{t("fields.inventory_status.sort_order")}</span>
            <input name="sort_order" type="number" value={formData.sort_order ?? ""} onChange={handleChange} placeholder={t("fields.inventory_status.sort_order")} aria-invalid={Boolean(fieldErrors["sort_order"])} {...inputPropsForField("sort_order", validationRules["sort_order"], "number")} />
            {fieldErrors["sort_order"] && <span className="field-error">{formatFieldError("sort_order")}</span>}
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
              {canSeeField("id_inventory_status") && <th>{t("fields.inventory_status.id_inventory_status")}</th>}
              {canSeeField("inventory_status_code") && <th>{t("fields.inventory_status.inventory_status_code")}</th>}
              {canSeeField("inventory_status_description") && <th>{t("fields.inventory_status.inventory_status_description")}</th>}
              {canSeeField("color") && <th>{t("fields.inventory_status.color")}</th>}
              {canSeeField("entity_scope") && <th>{t("fields.inventory_status.entity_scope")}</th>}
              {canSeeField("flow_scope") && <th>{t("fields.inventory_status.flow_scope")}</th>}
              {canSeeField("id_department") && <th>{t("fields.inventory_status.id_department")}</th>}
              {canSeeField("id_subdepartment") && <th>{t("fields.inventory_status.id_subdepartment")}</th>}
              {canSeeField("id_minimum_level") && <th>{t("fields.inventory_status.id_minimum_level")}</th>}
              {canSeeField("is_active") && <th>{t("fields.inventory_status.is_active")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_inventory_status}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_inventory_status") && <td><pre className="cell-value">{formatTableValue(item.id_inventory_status)}</pre></td>}
              {canSeeField("inventory_status_code") && <td><pre className="cell-value">{formatTableValue(item.inventory_status_code)}</pre></td>}
              {canSeeField("inventory_status_description") && <td><pre className="cell-value">{formatTableValue(item.inventory_status_description)}</pre></td>}
              {canSeeField("color") && <td><pre className="cell-value">{formatTableValue(item.color)}</pre></td>}
              {canSeeField("entity_scope") && <td><pre className="cell-value">{formatTableValue(item.entity_scope)}</pre></td>}
              {canSeeField("flow_scope") && <td><pre className="cell-value">{formatTableValue(item.flow_scope)}</pre></td>}
              {canSeeField("id_department") && <td><pre className="cell-value">{formatTableValue(item.id_department)}</pre></td>}
              {canSeeField("id_subdepartment") && <td><pre className="cell-value">{formatTableValue(item.id_subdepartment)}</pre></td>}
              {canSeeField("id_minimum_level") && <td><pre className="cell-value">{formatTableValue(item.id_minimum_level)}</pre></td>}
              {canSeeField("is_active") && <td><pre className="cell-value">{formatTableValue(item.is_active)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_inventory_status}><strong>{String(item.inventory_status_code ?? item.id_inventory_status)}</strong><small>#{item.id_inventory_status}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

      <Pagination
        page={page}
        pages={paginacion.pages}
        total={paginacion.total}
        perPage={paginacion.perPage}
        loading={loading}
        onChange={setPage}
      />
    </section>
  );
}
