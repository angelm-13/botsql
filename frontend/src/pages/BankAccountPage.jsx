import { LLAVE_BORRADO_BLOQUEADO, mensajeDeBorradoBloqueado } from "../utils/registrosRelacionados.js";
import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllBankAccount, createBankAccount, updateBankAccount, deleteBankAccount, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllBank } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";
import { formatearFechaHora } from "../utils/fechas";
import { useDialogo } from "../dialogo/useDialogo.js";

const emptyForm = { id_bank: "", bank_account_description: "", branch: "", type: "", ordinary_interest: "", moratorium_interest: "", anuality: "", reimbursement: "" };
const validationRules = allValidationRules["bank_account"] || {};
const ENTITY_KEY = "bank_account";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_bank_account', 'id_bank', 'bank_account_description', 'branch', 'type', 'ordinary_interest', 'moratorium_interest', 'anuality', 'reimbursement', 'created_by'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function BankAccountPage() {
  const { lang, t } = useI18n();
  const dialogo = useDialogo();
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
  const [bankOptions, setBankOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllBankAccount({ page, per_page: perPage, q: query || undefined });
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
      if (canSeeField("id_bank")) {
        try {
          const bankData = await getAllBank({ page: 1, per_page: 100 });
          setBankOptions(Array.isArray(bankData) ? bankData : (bankData.items || []));
        } catch (_) {
          setBankOptions([]);
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
    const fieldLabel = t(`fields.bank_account.${fieldName}`, fieldName);
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
    const validation = validateForm("bank_account", submitPayload, validationRules);
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
      if (editingId) await updateBankAccount(editingId, submitPayload);
      else await createBankAccount(submitPayload);
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
    setEditingId(item.id_bank_account);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!(await dialogo.confirmar(t("common.confirm_delete")))) return;
    try { await deleteBankAccount(item.id_bank_account); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
  }



  async function resetMfaForItem(item) {
    if (ENTITY_KEY !== "user") return;
    const targetId = item.id_user ?? item.id;
    if (!targetId) return;
    if (!(await dialogo.confirmar(t("common.mfa_reset_confirm", "¿Restablecer MFA de este usuario?")))) return;
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
      const formateada = formatearFechaHora(value, locale);
      if (formateada) return formateada;
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
    const fieldLabel = errorMeta?.field ? t(`fields.bank_account.${errorMeta.field}`, errorMeta.field) : "";
    if (errorKey === "errors.field_too_long" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel} (${errorMeta.actual_length}/${errorMeta.max_length})`;
    }
    if (errorKey === "errors.invalid_field" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel}`;
    }
    return errorKey === LLAVE_BORRADO_BLOQUEADO ? mensajeDeBorradoBloqueado(t, errorMeta) : t(errorKey, errorKey);
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
    const key = String(item.type ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.bank_account")}
        subtitulo={t("page.bank_account.subtitle", "")}
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
          {canSeeField("id_bank") && (
          <label className="field">
            <span>{t("fields.bank_account.id_bank")}</span>
            <select name="id_bank" value={formData.id_bank ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_bank"])} {...inputPropsForField("id_bank", validationRules["id_bank"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {bankOptions.map((item) => (
                <option key={item.id_bank ?? item.id ?? JSON.stringify(item)} value={item.id_bank ?? item.id ?? ""}>
                  {getOptionLabel(item, "bank")}
                </option>
              ))}
            </select>
            {fieldErrors["id_bank"] && <span className="field-error">{formatFieldError("id_bank")}</span>}
          </label>
          )}
          {canSeeField("bank_account_description") && (
          <label className="field">
            <span>{t("fields.bank_account.bank_account_description")}</span>
            <input name="bank_account_description" type="text" maxLength={200} value={formData.bank_account_description ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.bank_account_description")} aria-invalid={Boolean(fieldErrors["bank_account_description"])} {...inputPropsForField("bank_account_description", validationRules["bank_account_description"], "text")} />
            {fieldErrors["bank_account_description"] && <span className="field-error">{formatFieldError("bank_account_description")}</span>}
          </label>
          )}
          {canSeeField("branch") && (
          <label className="field">
            <span>{t("fields.bank_account.branch")}</span>
            <input name="branch" type="text" maxLength={30} value={formData.branch ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.branch")} aria-invalid={Boolean(fieldErrors["branch"])} {...inputPropsForField("branch", validationRules["branch"], "text")} />
            {fieldErrors["branch"] && <span className="field-error">{formatFieldError("branch")}</span>}
          </label>
          )}
          {canSeeField("type") && (
          <label className="field">
            <span>{t("fields.bank_account.type")}</span>
            <input name="type" type="text" maxLength={30} value={formData.type ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.type")} aria-invalid={Boolean(fieldErrors["type"])} {...inputPropsForField("type", validationRules["type"], "text")} />
            {fieldErrors["type"] && <span className="field-error">{formatFieldError("type")}</span>}
          </label>
          )}
          {canSeeField("ordinary_interest") && (
          <label className="field">
            <span>{t("fields.bank_account.ordinary_interest")}</span>
            <input name="ordinary_interest" type="number" value={formData.ordinary_interest ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.ordinary_interest")} aria-invalid={Boolean(fieldErrors["ordinary_interest"])} {...inputPropsForField("ordinary_interest", validationRules["ordinary_interest"], "number")} />
            {fieldErrors["ordinary_interest"] && <span className="field-error">{formatFieldError("ordinary_interest")}</span>}
          </label>
          )}
          {canSeeField("moratorium_interest") && (
          <label className="field">
            <span>{t("fields.bank_account.moratorium_interest")}</span>
            <input name="moratorium_interest" type="number" value={formData.moratorium_interest ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.moratorium_interest")} aria-invalid={Boolean(fieldErrors["moratorium_interest"])} {...inputPropsForField("moratorium_interest", validationRules["moratorium_interest"], "number")} />
            {fieldErrors["moratorium_interest"] && <span className="field-error">{formatFieldError("moratorium_interest")}</span>}
          </label>
          )}
          {canSeeField("anuality") && (
          <label className="field">
            <span>{t("fields.bank_account.anuality")}</span>
            <input name="anuality" type="number" value={formData.anuality ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.anuality")} aria-invalid={Boolean(fieldErrors["anuality"])} {...inputPropsForField("anuality", validationRules["anuality"], "number")} />
            {fieldErrors["anuality"] && <span className="field-error">{formatFieldError("anuality")}</span>}
          </label>
          )}
          {canSeeField("reimbursement") && (
          <label className="field">
            <span>{t("fields.bank_account.reimbursement")}</span>
            <input name="reimbursement" type="number" value={formData.reimbursement ?? ""} onChange={handleChange} placeholder={t("fields.bank_account.reimbursement")} aria-invalid={Boolean(fieldErrors["reimbursement"])} {...inputPropsForField("reimbursement", validationRules["reimbursement"], "number")} />
            {fieldErrors["reimbursement"] && <span className="field-error">{formatFieldError("reimbursement")}</span>}
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
              {canSeeField("id_bank_account") && <th>{t("fields.bank_account.id_bank_account")}</th>}
              {canSeeField("id_bank") && <th>{t("fields.bank_account.id_bank")}</th>}
              {canSeeField("bank_account_description") && <th>{t("fields.bank_account.bank_account_description")}</th>}
              {canSeeField("branch") && <th>{t("fields.bank_account.branch")}</th>}
              {canSeeField("type") && <th>{t("fields.bank_account.type")}</th>}
              {canSeeField("ordinary_interest") && <th>{t("fields.bank_account.ordinary_interest")}</th>}
              {canSeeField("moratorium_interest") && <th>{t("fields.bank_account.moratorium_interest")}</th>}
              {canSeeField("anuality") && <th>{t("fields.bank_account.anuality")}</th>}
              {canSeeField("reimbursement") && <th>{t("fields.bank_account.reimbursement")}</th>}
              {canSeeField("created_by") && <th>{t("fields.bank_account.created_by")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_bank_account}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_bank_account") && <td><pre className="cell-value">{formatTableValue(item.id_bank_account)}</pre></td>}
              {canSeeField("id_bank") && <td><pre className="cell-value">{formatTableValue(item.id_bank)}</pre></td>}
              {canSeeField("bank_account_description") && <td><pre className="cell-value">{formatTableValue(item.bank_account_description)}</pre></td>}
              {canSeeField("branch") && <td><pre className="cell-value">{formatTableValue(item.branch)}</pre></td>}
              {canSeeField("type") && <td><pre className="cell-value">{formatTableValue(item.type)}</pre></td>}
              {canSeeField("ordinary_interest") && <td><pre className="cell-value">{formatTableValue(item.ordinary_interest)}</pre></td>}
              {canSeeField("moratorium_interest") && <td><pre className="cell-value">{formatTableValue(item.moratorium_interest)}</pre></td>}
              {canSeeField("anuality") && <td><pre className="cell-value">{formatTableValue(item.anuality)}</pre></td>}
              {canSeeField("reimbursement") && <td><pre className="cell-value">{formatTableValue(item.reimbursement)}</pre></td>}
              {canSeeField("created_by") && <td><pre className="cell-value">{formatTableValue(item.created_by)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_bank_account}><strong>{String(item.bank_account_description ?? item.id_bank_account)}</strong><small>#{item.id_bank_account}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

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
