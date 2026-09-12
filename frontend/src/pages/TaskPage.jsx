import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllTask, createTask, updateTask, deleteTask, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllUser, getAllProyect } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";

const emptyForm = { task_code: "", start_date: "", duration: "", type: "", owner: "", analyst: "", dependency: "", leader: "", validation: "", task_description: "", estimated_effort: "", task_status: "", fase: "", priority: "", title: "", id_proyect: "" };
const validationRules = allValidationRules["task"] || {};
const ENTITY_KEY = "task";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_task', 'task_code', 'start_date', 'duration', 'type', 'owner', 'analyst', 'dependency', 'leader', 'validation'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function TaskPage() {
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
  const [userOptions, setUserOptions] = useState([]);
  const [proyectOptions, setProyectOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllTask({ page, per_page: perPage, q: query || undefined });
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
      if (canSeeField("owner")) {
        try {
          const userData = await getAllUser({ page: 1, per_page: 100 });
          setUserOptions(Array.isArray(userData) ? userData : (userData.items || []));
        } catch (_) {
          setUserOptions([]);
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
    const fieldLabel = t(`fields.task.${fieldName}`, fieldName);
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
    const validation = validateForm("task", submitPayload, validationRules);
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
      if (editingId) await updateTask(editingId, submitPayload);
      else await createTask(submitPayload);
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
    setEditingId(item.id_task);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteTask(item.id_task); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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
    const fieldLabel = errorMeta?.field ? t(`fields.task.${errorMeta.field}`, errorMeta.field) : "";
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
    const key = String(item.task_status ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.task")}
        subtitulo={t("page.task.subtitle", "")}
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
          {canSeeField("task_code") && (
          <label className="field">
            <span>{t("fields.task.task_code")}</span>
            <input name="task_code" type="text" maxLength={11} value={formData.task_code ?? ""} onChange={handleChange} placeholder={t("fields.task.task_code")} aria-invalid={Boolean(fieldErrors["task_code"])} {...inputPropsForField("task_code", validationRules["task_code"], "text")} />
            {fieldErrors["task_code"] && <span className="field-error">{formatFieldError("task_code")}</span>}
          </label>
          )}
          {canSeeField("start_date") && (
          <label className="field">
            <span>{t("fields.task.start_date")}</span>
            <input name="start_date" type="datetime-local" value={formData.start_date ?? ""} onChange={handleChange} placeholder={t("fields.task.start_date")} aria-invalid={Boolean(fieldErrors["start_date"])} {...inputPropsForField("start_date", validationRules["start_date"], "datetime-local")} />
            {fieldErrors["start_date"] && <span className="field-error">{formatFieldError("start_date")}</span>}
          </label>
          )}
          {canSeeField("duration") && (
          <label className="field">
            <span>{t("fields.task.duration")}</span>
            <input name="duration" type="number" value={formData.duration ?? ""} onChange={handleChange} placeholder={t("fields.task.duration")} aria-invalid={Boolean(fieldErrors["duration"])} {...inputPropsForField("duration", validationRules["duration"], "number")} />
            {fieldErrors["duration"] && <span className="field-error">{formatFieldError("duration")}</span>}
          </label>
          )}
          {canSeeField("type") && (
          <label className="field">
            <span>{t("fields.task.type")}</span>
            <select name="type" value={formData.type ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["type"])} {...inputPropsForField("type", validationRules["type"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="personal" value="personal">personal</option>
              <option key="business" value="business">business</option>
            </select>
            {fieldErrors["type"] && <span className="field-error">{formatFieldError("type")}</span>}
          </label>
          )}
          {canSeeField("owner") && (
          <label className="field">
            <span>{t("fields.task.owner")}</span>
            <select name="owner" value={formData.owner ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["owner"])} {...inputPropsForField("owner", validationRules["owner"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {userOptions.map((item) => (
                <option key={item.id_user ?? item.id ?? JSON.stringify(item)} value={item.id_user ?? item.id ?? ""}>
                  {getOptionLabel(item, "user")}
                </option>
              ))}
            </select>
            {fieldErrors["owner"] && <span className="field-error">{formatFieldError("owner")}</span>}
          </label>
          )}
          {canSeeField("analyst") && (
          <label className="field">
            <span>{t("fields.task.analyst")}</span>
            <input name="analyst" type="number" value={formData.analyst ?? ""} onChange={handleChange} placeholder={t("fields.task.analyst")} aria-invalid={Boolean(fieldErrors["analyst"])} {...inputPropsForField("analyst", validationRules["analyst"], "number")} />
            {fieldErrors["analyst"] && <span className="field-error">{formatFieldError("analyst")}</span>}
          </label>
          )}
          {canSeeField("dependency") && (
          <label className="field">
            <span>{t("fields.task.dependency")}</span>
            <input name="dependency" type="number" value={formData.dependency ?? ""} onChange={handleChange} placeholder={t("fields.task.dependency")} aria-invalid={Boolean(fieldErrors["dependency"])} {...inputPropsForField("dependency", validationRules["dependency"], "number")} />
            {fieldErrors["dependency"] && <span className="field-error">{formatFieldError("dependency")}</span>}
          </label>
          )}
          {canSeeField("leader") && (
          <label className="field">
            <span>{t("fields.task.leader")}</span>
            <input name="leader" type="number" value={formData.leader ?? ""} onChange={handleChange} placeholder={t("fields.task.leader")} aria-invalid={Boolean(fieldErrors["leader"])} {...inputPropsForField("leader", validationRules["leader"], "number")} />
            {fieldErrors["leader"] && <span className="field-error">{formatFieldError("leader")}</span>}
          </label>
          )}
          {canSeeField("validation") && (
          <label className="field">
            <span>{t("fields.task.validation")}</span>
            <input name="validation" type="number" value={formData.validation ?? ""} onChange={handleChange} placeholder={t("fields.task.validation")} aria-invalid={Boolean(fieldErrors["validation"])} {...inputPropsForField("validation", validationRules["validation"], "number")} />
            {fieldErrors["validation"] && <span className="field-error">{formatFieldError("validation")}</span>}
          </label>
          )}
          {canSeeField("task_description") && (
          <label className="field">
            <span>{t("fields.task.task_description")}</span>
            <input name="task_description" type="text" maxLength={200} value={formData.task_description ?? ""} onChange={handleChange} placeholder={t("fields.task.task_description")} aria-invalid={Boolean(fieldErrors["task_description"])} {...inputPropsForField("task_description", validationRules["task_description"], "text")} />
            {fieldErrors["task_description"] && <span className="field-error">{formatFieldError("task_description")}</span>}
          </label>
          )}
          {canSeeField("estimated_effort") && (
          <label className="field">
            <span>{t("fields.task.estimated_effort")}</span>
            <input name="estimated_effort" type="text" maxLength={50} value={formData.estimated_effort ?? ""} onChange={handleChange} placeholder={t("fields.task.estimated_effort")} aria-invalid={Boolean(fieldErrors["estimated_effort"])} {...inputPropsForField("estimated_effort", validationRules["estimated_effort"], "text")} />
            {fieldErrors["estimated_effort"] && <span className="field-error">{formatFieldError("estimated_effort")}</span>}
          </label>
          )}
          {canSeeField("task_status") && (
          <label className="field">
            <span>{t("fields.task.task_status")}</span>
            <input name="task_status" type="text" maxLength={20} value={formData.task_status ?? ""} onChange={handleChange} placeholder={t("fields.task.task_status")} aria-invalid={Boolean(fieldErrors["task_status"])} {...inputPropsForField("task_status", validationRules["task_status"], "text")} />
            {fieldErrors["task_status"] && <span className="field-error">{formatFieldError("task_status")}</span>}
          </label>
          )}
          {canSeeField("fase") && (
          <label className="field">
            <span>{t("fields.task.fase")}</span>
            <input name="fase" type="text" maxLength={100} value={formData.fase ?? ""} onChange={handleChange} placeholder={t("fields.task.fase")} aria-invalid={Boolean(fieldErrors["fase"])} {...inputPropsForField("fase", validationRules["fase"], "text")} />
            {fieldErrors["fase"] && <span className="field-error">{formatFieldError("fase")}</span>}
          </label>
          )}
          {canSeeField("priority") && (
          <label className="field">
            <span>{t("fields.task.priority")}</span>
            <input name="priority" type="text" maxLength={50} value={formData.priority ?? ""} onChange={handleChange} placeholder={t("fields.task.priority")} aria-invalid={Boolean(fieldErrors["priority"])} {...inputPropsForField("priority", validationRules["priority"], "text")} />
            {fieldErrors["priority"] && <span className="field-error">{formatFieldError("priority")}</span>}
          </label>
          )}
          {canSeeField("title") && (
          <label className="field">
            <span>{t("fields.task.title")}</span>
            <input name="title" type="text" maxLength={50} value={formData.title ?? ""} onChange={handleChange} placeholder={t("fields.task.title")} aria-invalid={Boolean(fieldErrors["title"])} {...inputPropsForField("title", validationRules["title"], "text")} />
            {fieldErrors["title"] && <span className="field-error">{formatFieldError("title")}</span>}
          </label>
          )}
          {canSeeField("id_proyect") && (
          <label className="field">
            <span>{t("fields.task.id_proyect")}</span>
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
              {canSeeField("id_task") && <th>{t("fields.task.id_task")}</th>}
              {canSeeField("task_code") && <th>{t("fields.task.task_code")}</th>}
              {canSeeField("start_date") && <th>{t("fields.task.start_date")}</th>}
              {canSeeField("duration") && <th>{t("fields.task.duration")}</th>}
              {canSeeField("type") && <th>{t("fields.task.type")}</th>}
              {canSeeField("owner") && <th>{t("fields.task.owner")}</th>}
              {canSeeField("analyst") && <th>{t("fields.task.analyst")}</th>}
              {canSeeField("dependency") && <th>{t("fields.task.dependency")}</th>}
              {canSeeField("leader") && <th>{t("fields.task.leader")}</th>}
              {canSeeField("validation") && <th>{t("fields.task.validation")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_task}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_task") && <td><pre className="cell-value">{formatTableValue(item.id_task)}</pre></td>}
              {canSeeField("task_code") && <td><pre className="cell-value">{formatTableValue(item.task_code)}</pre></td>}
              {canSeeField("start_date") && <td><pre className="cell-value">{formatTableValue(item.start_date)}</pre></td>}
              {canSeeField("duration") && <td><pre className="cell-value">{formatTableValue(item.duration)}</pre></td>}
              {canSeeField("type") && <td><pre className="cell-value">{formatTableValue(item.type)}</pre></td>}
              {canSeeField("owner") && <td><pre className="cell-value">{formatTableValue(item.owner)}</pre></td>}
              {canSeeField("analyst") && <td><pre className="cell-value">{formatTableValue(item.analyst)}</pre></td>}
              {canSeeField("dependency") && <td><pre className="cell-value">{formatTableValue(item.dependency)}</pre></td>}
              {canSeeField("leader") && <td><pre className="cell-value">{formatTableValue(item.leader)}</pre></td>}
              {canSeeField("validation") && <td><pre className="cell-value">{formatTableValue(item.validation)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_task}><strong>{String(item.task_description ?? item.id_task)}</strong><small>#{item.id_task}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

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
