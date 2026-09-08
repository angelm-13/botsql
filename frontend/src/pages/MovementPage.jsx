import { useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllMovement, createMovement, updateMovement, deleteMovement, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllFiscalAccount } from "../api";
import Pagination from "../components/Pagination.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";

const emptyForm = { id_fiscal_account: "", date: "", type: "", amount: "", currency: "", type_exchange_rate: "" };
const validationRules = allValidationRules["movement"] || {};
const ENTITY_KEY = "movement";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_movement', 'id_fiscal_account', 'date', 'type', 'amount', 'currency', 'type_exchange_rate', 'created_by', 'creation_date', 'last_update_date'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function MovementPage() {
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
  const [fiscalAccountOptions, setFiscalAccountOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllMovement({ page, per_page: perPage });
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

  useEffect(() => { loadData(); }, [page, perPage, permissionReady, canRead]);
  useEffect(() => {
    async function loadFormOptions() {
      if (!permissionReady || (!canSubmitForm && !canRead)) return;
      if (canSeeField("id_fiscal_account")) {
        try {
          const fiscalAccountData = await getAllFiscalAccount({ page: 1, per_page: 100 });
          setFiscalAccountOptions(Array.isArray(fiscalAccountData) ? fiscalAccountData : (fiscalAccountData.items || []));
        } catch (_) {
          setFiscalAccountOptions([]);
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
    const fieldLabel = t(`fields.movement.${fieldName}`, fieldName);
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
    const validation = validateForm("movement", submitPayload, validationRules);
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
      if (editingId) await updateMovement(editingId, submitPayload);
      else await createMovement(submitPayload);
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
    setEditingId(item.id_movement);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteMovement(item.id_movement); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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
    const fieldLabel = errorMeta?.field ? t(`fields.movement.${errorMeta.field}`, errorMeta.field) : "";
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
    const key = String(item.type ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <div className="page-heading">
        <div><p className="eyebrow">{t("common.module")}</p><h2>{t("menu.movement")}</h2></div>
        <button className="button ghost" onClick={loadData} disabled={!canRead}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </div>

      {canSubmitForm && <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-header"><Plus size={18} /><strong>{editingId ? t("common.edit") : t("common.new")}</strong></div>
        <div className="form-grid">
          {canSeeField("id_fiscal_account") && (
          <label className="field">
            <span>{t("fields.movement.id_fiscal_account")}</span>
            <select name="id_fiscal_account" value={formData.id_fiscal_account ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_fiscal_account"])} {...inputPropsForField("id_fiscal_account", validationRules["id_fiscal_account"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {fiscalAccountOptions.map((item) => (
                <option key={item.id_fiscal_account ?? item.id ?? JSON.stringify(item)} value={item.id_fiscal_account ?? item.id ?? ""}>
                  {getOptionLabel(item, "fiscal_account")}
                </option>
              ))}
            </select>
            {fieldErrors["id_fiscal_account"] && <span className="field-error">{formatFieldError("id_fiscal_account")}</span>}
          </label>
          )}
          {canSeeField("date") && (
          <label className="field">
            <span>{t("fields.movement.date")}</span>
            <input name="date" type="datetime-local" value={formData.date ?? ""} onChange={handleChange} placeholder={t("fields.movement.date")} aria-invalid={Boolean(fieldErrors["date"])} {...inputPropsForField("date", validationRules["date"], "datetime-local")} />
            {fieldErrors["date"] && <span className="field-error">{formatFieldError("date")}</span>}
          </label>
          )}
          {canSeeField("type") && (
          <label className="field">
            <span>{t("fields.movement.type")}</span>
            <select name="type" value={formData.type ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["type"])} {...inputPropsForField("type", validationRules["type"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="income" value="income">income</option>
              <option key="expense" value="expense">expense</option>
            </select>
            {fieldErrors["type"] && <span className="field-error">{formatFieldError("type")}</span>}
          </label>
          )}
          {canSeeField("amount") && (
          <label className="field">
            <span>{t("fields.movement.amount")}</span>
            <input name="amount" type="number" value={formData.amount ?? ""} onChange={handleChange} placeholder={t("fields.movement.amount")} aria-invalid={Boolean(fieldErrors["amount"])} {...inputPropsForField("amount", validationRules["amount"], "number")} />
            {fieldErrors["amount"] && <span className="field-error">{formatFieldError("amount")}</span>}
          </label>
          )}
          {canSeeField("currency") && (
          <label className="field">
            <span>{t("fields.movement.currency")}</span>
            <select name="currency" value={formData.currency ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["currency"])} {...inputPropsForField("currency", validationRules["currency"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              <option key="usd" value="usd">usd</option>
              <option key="mxn" value="mxn">mxn</option>
              <option key="eur" value="eur">eur</option>
            </select>
            {fieldErrors["currency"] && <span className="field-error">{formatFieldError("currency")}</span>}
          </label>
          )}
          {canSeeField("type_exchange_rate") && (
          <label className="field">
            <span>{t("fields.movement.type_exchange_rate")}</span>
            <input name="type_exchange_rate" type="number" value={formData.type_exchange_rate ?? ""} onChange={handleChange} placeholder={t("fields.movement.type_exchange_rate")} aria-invalid={Boolean(fieldErrors["type_exchange_rate"])} {...inputPropsForField("type_exchange_rate", validationRules["type_exchange_rate"], "number")} />
            {fieldErrors["type_exchange_rate"] && <span className="field-error">{formatFieldError("type_exchange_rate")}</span>}
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


      {canRead && view === "table" && filtered.length > 0 && <div className="table-card"><table><thead><tr>{showRowActions && <th>{t("common.actions")}</th>}
              {canSeeField("id_movement") && <th>{t("fields.movement.id_movement")}</th>}
              {canSeeField("id_fiscal_account") && <th>{t("fields.movement.id_fiscal_account")}</th>}
              {canSeeField("date") && <th>{t("fields.movement.date")}</th>}
              {canSeeField("type") && <th>{t("fields.movement.type")}</th>}
              {canSeeField("amount") && <th>{t("fields.movement.amount")}</th>}
              {canSeeField("currency") && <th>{t("fields.movement.currency")}</th>}
              {canSeeField("type_exchange_rate") && <th>{t("fields.movement.type_exchange_rate")}</th>}
              {canSeeField("created_by") && <th>{t("fields.movement.created_by")}</th>}
              {canSeeField("creation_date") && <th>{t("fields.movement.creation_date")}</th>}
              {canSeeField("last_update_date") && <th>{t("fields.movement.last_update_date")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_movement}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_movement") && <td><pre className="cell-value">{formatTableValue(item.id_movement)}</pre></td>}
              {canSeeField("id_fiscal_account") && <td><pre className="cell-value">{formatTableValue(item.id_fiscal_account)}</pre></td>}
              {canSeeField("date") && <td><pre className="cell-value">{formatTableValue(item.date)}</pre></td>}
              {canSeeField("type") && <td><pre className="cell-value">{formatTableValue(item.type)}</pre></td>}
              {canSeeField("amount") && <td><pre className="cell-value">{formatTableValue(item.amount)}</pre></td>}
              {canSeeField("currency") && <td><pre className="cell-value">{formatTableValue(item.currency)}</pre></td>}
              {canSeeField("type_exchange_rate") && <td><pre className="cell-value">{formatTableValue(item.type_exchange_rate)}</pre></td>}
              {canSeeField("created_by") && <td><pre className="cell-value">{formatTableValue(item.created_by)}</pre></td>}
              {canSeeField("creation_date") && <td><pre className="cell-value">{formatTableValue(item.creation_date)}</pre></td>}
              {canSeeField("last_update_date") && <td><pre className="cell-value">{formatTableValue(item.last_update_date)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_movement}><strong>{String(item.id_movement ?? item.id_movement)}</strong><small>#{item.id_movement}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

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
