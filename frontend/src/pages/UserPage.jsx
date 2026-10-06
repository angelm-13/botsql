import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllUser, createUser, updateUser, deleteUser, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllPermission, getAllProyect, getAllStatus } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";

const emptyForm = { date_born: "", date_start: "", email: "", first_name: "", id_permission: "", full_name: "", id_proyect: "", last_name_father: "", last_name_mother: "", national_id: "", password: "", principal_phone: "", secundary_phone: "", ssn: "", supervisor: "", base_salary: "", hire_date: "", id_status: "", tax_id: "", title: "", user_type: "", username: "", puesto: "", is_employee: false, accepts_marketing: false };
const validationRules = allValidationRules["user"] || {};
const ENTITY_KEY = "user";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_user', 'created_by', 'creation_date', 'date_born', 'date_start', 'deletion_date', 'email', 'first_name', 'id_permission', 'full_name'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function UserPage() {
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
  const [permissionOptions, setPermissionOptions] = useState([]);
  const [proyectOptions, setProyectOptions] = useState([]);
  const [userOptions, setUserOptions] = useState([]);
  const [statusOptions, setStatusOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllUser({ page, per_page: perPage, q: query || undefined });
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
      if (canSeeField("id_permission")) {
        try {
          const permissionData = await getAllPermission({ page: 1, per_page: 100 });
          setPermissionOptions(Array.isArray(permissionData) ? permissionData : (permissionData.items || []));
        } catch (_) {
          setPermissionOptions([]);
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
      if (canSeeField("supervisor")) {
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


  function resolveLabel(id, options, idKey, entityName) {
    if (id === null || id === undefined || id === "") return "";
    const found = (options || []).find((opt) => String(opt[idKey] ?? opt.id ?? "") === String(id));
    if (!found) return String(id);
    return getOptionLabel(found, entityName);
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
    const fieldLabel = t(`fields.user.${fieldName}`, fieldName);
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
    const validation = validateForm("user", submitPayload, validationRules);
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
      if (editingId) await updateUser(editingId, submitPayload);
      else await createUser(submitPayload);
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
    setEditingId(item.id_user);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteUser(item.id_user); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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
    const fieldLabel = errorMeta?.field ? t(`fields.user.${errorMeta.field}`, errorMeta.field) : "";
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
    const key = resolveLabel(item.id_status, statusOptions, "id_status", "status") || t("common.unclassified");
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang, statusOptions]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.user")}
        subtitulo={t("page.user.subtitle", "")}
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
          {canSeeField("date_born") && (
          <label className="field">
            <span>{t("fields.user.date_born")}</span>
            <input name="date_born" type="datetime-local" value={formData.date_born ?? ""} onChange={handleChange} placeholder={t("fields.user.date_born")} aria-invalid={Boolean(fieldErrors["date_born"])} {...inputPropsForField("date_born", validationRules["date_born"], "datetime-local")} />
            {fieldErrors["date_born"] && <span className="field-error">{formatFieldError("date_born")}</span>}
          </label>
          )}
          {canSeeField("date_start") && (
          <label className="field">
            <span>{t("fields.user.date_start")}</span>
            <input name="date_start" type="datetime-local" value={formData.date_start ?? ""} onChange={handleChange} placeholder={t("fields.user.date_start")} aria-invalid={Boolean(fieldErrors["date_start"])} {...inputPropsForField("date_start", validationRules["date_start"], "datetime-local")} />
            {fieldErrors["date_start"] && <span className="field-error">{formatFieldError("date_start")}</span>}
          </label>
          )}
          {canSeeField("email") && (
          <label className="field">
            <span>{t("fields.user.email")}</span>
            <input name="email" type="email" maxLength={100} value={formData.email ?? ""} onChange={handleChange} placeholder={t("fields.user.email")} aria-invalid={Boolean(fieldErrors["email"])} {...inputPropsForField("email", validationRules["email"], "email")} />
            {fieldErrors["email"] && <span className="field-error">{formatFieldError("email")}</span>}
          </label>
          )}
          {canSeeField("first_name") && (
          <label className="field">
            <span>{t("fields.user.first_name")}</span>
            <input name="first_name" type="text" maxLength={50} value={formData.first_name ?? ""} onChange={handleChange} placeholder={t("fields.user.first_name")} aria-invalid={Boolean(fieldErrors["first_name"])} {...inputPropsForField("first_name", validationRules["first_name"], "text")} />
            {fieldErrors["first_name"] && <span className="field-error">{formatFieldError("first_name")}</span>}
          </label>
          )}
          {canSeeField("id_permission") && (
          <label className="field">
            <span>{t("fields.user.id_permission")}</span>
            <select name="id_permission" value={formData.id_permission ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_permission"])} {...inputPropsForField("id_permission", validationRules["id_permission"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {permissionOptions.map((item) => (
                <option key={item.id_permission ?? item.id ?? JSON.stringify(item)} value={item.id_permission ?? item.id ?? ""}>
                  {getOptionLabel(item, "permission")}
                </option>
              ))}
            </select>
            {fieldErrors["id_permission"] && <span className="field-error">{formatFieldError("id_permission")}</span>}
          </label>
          )}
          {canSeeField("full_name") && (
          <label className="field">
            <span>{t("fields.user.full_name")}</span>
            <input name="full_name" type="text" maxLength={150} value={formData.full_name ?? ""} onChange={handleChange} placeholder={t("fields.user.full_name")} aria-invalid={Boolean(fieldErrors["full_name"])} {...inputPropsForField("full_name", validationRules["full_name"], "text")} />
            {fieldErrors["full_name"] && <span className="field-error">{formatFieldError("full_name")}</span>}
          </label>
          )}
          {canSeeField("id_proyect") && (
          <label className="field">
            <span>{t("fields.user.id_proyect")}</span>
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
          {canSeeField("last_name_father") && (
          <label className="field">
            <span>{t("fields.user.last_name_father")}</span>
            <input name="last_name_father" type="text" maxLength={50} value={formData.last_name_father ?? ""} onChange={handleChange} placeholder={t("fields.user.last_name_father")} aria-invalid={Boolean(fieldErrors["last_name_father"])} {...inputPropsForField("last_name_father", validationRules["last_name_father"], "text")} />
            {fieldErrors["last_name_father"] && <span className="field-error">{formatFieldError("last_name_father")}</span>}
          </label>
          )}
          {canSeeField("last_name_mother") && (
          <label className="field">
            <span>{t("fields.user.last_name_mother")}</span>
            <input name="last_name_mother" type="text" maxLength={50} value={formData.last_name_mother ?? ""} onChange={handleChange} placeholder={t("fields.user.last_name_mother")} aria-invalid={Boolean(fieldErrors["last_name_mother"])} {...inputPropsForField("last_name_mother", validationRules["last_name_mother"], "text")} />
            {fieldErrors["last_name_mother"] && <span className="field-error">{formatFieldError("last_name_mother")}</span>}
          </label>
          )}
          {canSeeField("national_id") && (
          <label className="field">
            <span>{t("fields.user.national_id")}</span>
            <input name="national_id" type="text" maxLength={50} value={formData.national_id ?? ""} onChange={handleChange} placeholder={t("fields.user.national_id")} aria-invalid={Boolean(fieldErrors["national_id"])} {...inputPropsForField("national_id", validationRules["national_id"], "text")} />
            {fieldErrors["national_id"] && <span className="field-error">{formatFieldError("national_id")}</span>}
          </label>
          )}
          {canSeeField("password") && (
          <label className="field">
            <span>{t("fields.user.password")}</span>
            <input name="password" type="password" maxLength={256} required={!editingId} value={formData.password ?? ""} onChange={handleChange} placeholder={t("fields.user.password")} aria-invalid={Boolean(fieldErrors["password"])} {...inputPropsForField("password", validationRules["password"], "password")} />
            {fieldErrors["password"] && <span className="field-error">{formatFieldError("password")}</span>}
          </label>
          )}
          {canSeeField("principal_phone") && (
          <label className="field">
            <span>{t("fields.user.principal_phone")}</span>
            <input name="principal_phone" type="text" maxLength={15} value={formData.principal_phone ?? ""} onChange={handleChange} placeholder={t("fields.user.principal_phone")} aria-invalid={Boolean(fieldErrors["principal_phone"])} {...inputPropsForField("principal_phone", validationRules["principal_phone"], "text")} />
            {fieldErrors["principal_phone"] && <span className="field-error">{formatFieldError("principal_phone")}</span>}
          </label>
          )}
          {canSeeField("secundary_phone") && (
          <label className="field">
            <span>{t("fields.user.secundary_phone")}</span>
            <input name="secundary_phone" type="text" maxLength={15} value={formData.secundary_phone ?? ""} onChange={handleChange} placeholder={t("fields.user.secundary_phone")} aria-invalid={Boolean(fieldErrors["secundary_phone"])} {...inputPropsForField("secundary_phone", validationRules["secundary_phone"], "text")} />
            {fieldErrors["secundary_phone"] && <span className="field-error">{formatFieldError("secundary_phone")}</span>}
          </label>
          )}
          {canSeeField("ssn") && (
          <label className="field">
            <span>{t("fields.user.ssn")}</span>
            <input name="ssn" type="text" maxLength={50} value={formData.ssn ?? ""} onChange={handleChange} placeholder={t("fields.user.ssn")} aria-invalid={Boolean(fieldErrors["ssn"])} {...inputPropsForField("ssn", validationRules["ssn"], "text")} />
            {fieldErrors["ssn"] && <span className="field-error">{formatFieldError("ssn")}</span>}
          </label>
          )}
          {canSeeField("supervisor") && (
          <label className="field">
            <span>{formData.user_type === "client" ? t("fields.user.vendor", "Vendedor") : t("fields.user.supervisor")}</span>
            <select name="supervisor" value={formData.supervisor ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["supervisor"])} {...inputPropsForField("supervisor", validationRules["supervisor"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {userOptions.map((item) => (
                <option key={item.id_user ?? item.id ?? JSON.stringify(item)} value={item.id_user ?? item.id ?? ""}>
                  {getOptionLabel(item, "user")}
                </option>
              ))}
            </select>
            {fieldErrors["supervisor"] && <span className="field-error">{formatFieldError("supervisor")}</span>}
          </label>
          )}
          {canSeeField("base_salary") && (
          <label className="field">
            <span>{t("fields.user.base_salary")}</span>
            <input name="base_salary" type="number" value={formData.base_salary ?? ""} onChange={handleChange} placeholder={t("fields.user.base_salary")} aria-invalid={Boolean(fieldErrors["base_salary"])} {...inputPropsForField("base_salary", validationRules["base_salary"], "number")} />
            {fieldErrors["base_salary"] && <span className="field-error">{formatFieldError("base_salary")}</span>}
          </label>
          )}
          {canSeeField("hire_date") && (
          <label className="field">
            <span>{t("fields.user.hire_date")}</span>
            <input name="hire_date" type="date" value={formData.hire_date ?? ""} onChange={handleChange} placeholder={t("fields.user.hire_date")} aria-invalid={Boolean(fieldErrors["hire_date"])} {...inputPropsForField("hire_date", validationRules["hire_date"], "date")} />
            {fieldErrors["hire_date"] && <span className="field-error">{formatFieldError("hire_date")}</span>}
          </label>
          )}
          {canSeeField("id_status") && (
          <label className="field">
            <span>{t("common.status", "Estado")}</span>
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
          {canSeeField("tax_id") && (
          <label className="field">
            <span>{t("fields.user.tax_id")}</span>
            <input name="tax_id" type="text" maxLength={50} value={formData.tax_id ?? ""} onChange={handleChange} placeholder={t("fields.user.tax_id")} aria-invalid={Boolean(fieldErrors["tax_id"])} {...inputPropsForField("tax_id", validationRules["tax_id"], "text")} />
            {fieldErrors["tax_id"] && <span className="field-error">{formatFieldError("tax_id")}</span>}
          </label>
          )}
          {canSeeField("title") && (
          <label className="field">
            <span>{t("fields.user.title")}</span>
            <input name="title" type="text" maxLength={50} value={formData.title ?? ""} onChange={handleChange} placeholder={t("fields.user.title")} aria-invalid={Boolean(fieldErrors["title"])} {...inputPropsForField("title", validationRules["title"], "text")} />
            {fieldErrors["title"] && <span className="field-error">{formatFieldError("title")}</span>}
          </label>
          )}
          {canSeeField("user_type") && (
          <label className="field">
            <span>{t("fields.user.user_type")}</span>
            <select name="user_type" value={formData.user_type ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["user_type"])} {...inputPropsForField("user_type", validationRules["user_type"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="admin" value="admin">admin</option>
              <option key="client" value="client">client</option>
              <option key="supplier" value="supplier">supplier</option>
              <option key="employee" value="employee">employee</option>
              <option key="web_shopper" value="web_shopper">web_shopper</option>
            </select>
            {fieldErrors["user_type"] && <span className="field-error">{formatFieldError("user_type")}</span>}
          </label>
          )}
          {canSeeField("username") && (
          <label className="field">
            <span>{t("fields.user.username")}</span>
            <input name="username" type="text" maxLength={50} required={!editingId} value={formData.username ?? ""} onChange={handleChange} placeholder={t("fields.user.username")} aria-invalid={Boolean(fieldErrors["username"])} {...inputPropsForField("username", validationRules["username"], "text")} />
            {fieldErrors["username"] && <span className="field-error">{formatFieldError("username")}</span>}
          </label>
          )}
          {canSeeField("puesto") && (
          <label className="field">
            <span>{t("fields.user.puesto")}</span>
            <input name="puesto" type="text" maxLength={50} value={formData.puesto ?? ""} onChange={handleChange} placeholder={t("fields.user.puesto")} aria-invalid={Boolean(fieldErrors["puesto"])} {...inputPropsForField("puesto", validationRules["puesto"], "text")} />
            {fieldErrors["puesto"] && <span className="field-error">{formatFieldError("puesto")}</span>}
          </label>
          )}
          {canSeeField("is_employee") && (
          <label className="field checkbox-field">
            <span>{t("fields.user.is_employee", "Es empleado")}</span>
            <input name="is_employee" type="checkbox" checked={Boolean(formData.is_employee)} onChange={handleChange} />
          </label>
          )}
          {canSeeField("accepts_marketing") && (
          <label className="field checkbox-field">
            <span>{t("fields.user.accepts_marketing")}</span>
            <input name="accepts_marketing" type="checkbox" checked={Boolean(formData.accepts_marketing)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["accepts_marketing"])} {...inputPropsForField("accepts_marketing", validationRules["accepts_marketing"], "checkbox")} />
            {fieldErrors["accepts_marketing"] && <span className="field-error">{formatFieldError("accepts_marketing")}</span>}
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
              {canSeeField("id_user") && <th>{t("fields.user.id_user")}</th>}
              {canSeeField("created_by") && <th>{t("fields.user.created_by")}</th>}
              {canSeeField("creation_date") && <th>{t("fields.user.creation_date")}</th>}
              {canSeeField("date_born") && <th>{t("fields.user.date_born")}</th>}
              {canSeeField("date_start") && <th>{t("fields.user.date_start")}</th>}
              {canSeeField("deletion_date") && <th>{t("fields.user.deletion_date")}</th>}
              {canSeeField("email") && <th>{t("fields.user.email")}</th>}
              {canSeeField("username") && <th>{t("fields.user.username")}</th>}
              {canSeeField("id_permission") && <th>{t("fields.user.id_permission")}</th>}
              {canSeeField("full_name") && <th>{t("fields.user.full_name")}</th>}
              {canSeeField("id_status") && <th>{t("common.status", "Estado")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_user}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_user") && <td><pre className="cell-value">{formatTableValue(item.id_user)}</pre></td>}
              {canSeeField("created_by") && <td><pre className="cell-value">{formatTableValue(item.created_by)}</pre></td>}
              {canSeeField("creation_date") && <td><pre className="cell-value">{formatTableValue(item.creation_date)}</pre></td>}
              {canSeeField("date_born") && <td><pre className="cell-value">{formatTableValue(item.date_born)}</pre></td>}
              {canSeeField("date_start") && <td><pre className="cell-value">{formatTableValue(item.date_start)}</pre></td>}
              {canSeeField("deletion_date") && <td><pre className="cell-value">{formatTableValue(item.deletion_date)}</pre></td>}
              {canSeeField("email") && <td><pre className="cell-value">{formatTableValue(item.email)}</pre></td>}
              {canSeeField("username") && <td><pre className="cell-value">{formatTableValue(item.username)}</pre></td>}
              {canSeeField("id_permission") && <td><pre className="cell-value">{resolveLabel(item.id_permission, permissionOptions, "id_permission", "permission")}</pre></td>}
              {canSeeField("full_name") && <td><pre className="cell-value">{formatTableValue(item.full_name)}</pre></td>}
              {canSeeField("id_status") && <td><pre className="cell-value">{resolveLabel(item.id_status, statusOptions, "id_status", "status")}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_user}><strong>{String(item.full_name ?? item.id_user)}</strong><small>#{item.id_user}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

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
