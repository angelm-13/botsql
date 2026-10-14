import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { getAllTheme, createTheme, updateTheme, deleteTheme, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";
import { formatearFechaHora } from "../utils/fechas";

const emptyForm = { tenant_id: "", primary_color: "", secondary_color: "", background_color: "", text_color: "", highlight_color: "", success_color: "", error_color: "" };
const validationRules = allValidationRules["theme"] || {};
const ENTITY_KEY = "theme";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_theme', 'created_by', 'creation_date', 'last_update_date', 'deletion_date', 'tenant_id', 'primary_color', 'secondary_color', 'background_color', 'text_color'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function ThemePage() {
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


  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllTheme({ page, per_page: perPage, q: query || undefined });
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
      return;
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
    const fieldLabel = t(`fields.theme.${fieldName}`, fieldName);
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
    const validation = validateForm("theme", submitPayload, validationRules);
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
      if (editingId) await updateTheme(editingId, submitPayload);
      else await createTheme(submitPayload);
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
    setEditingId(item.id_theme);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deleteTheme(item.id_theme); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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

  function renderError() {
    if (!errorKey) return "";
    const fieldLabel = errorMeta?.field ? t(`fields.theme.${errorMeta.field}`, errorMeta.field) : "";
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
    const key = String(item.id_theme ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.theme")}
        subtitulo={t("page.theme.subtitle", "")}
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
          {canSeeField("tenant_id") && (
          <label className="field">
            <span>{t("fields.theme.tenant_id")}</span>
            <input name="tenant_id" type="number" value={formData.tenant_id ?? ""} onChange={handleChange} placeholder={t("fields.theme.tenant_id")} aria-invalid={Boolean(fieldErrors["tenant_id"])} {...inputPropsForField("tenant_id", validationRules["tenant_id"], "number")} />
            {fieldErrors["tenant_id"] && <span className="field-error">{formatFieldError("tenant_id")}</span>}
          </label>
          )}
          {canSeeField("primary_color") && (
          <label className="field">
            <span>{t("fields.theme.primary_color")}</span>
            <input name="primary_color" type="text" maxLength={10} value={formData.primary_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.primary_color")} aria-invalid={Boolean(fieldErrors["primary_color"])} {...inputPropsForField("primary_color", validationRules["primary_color"], "text")} />
            {fieldErrors["primary_color"] && <span className="field-error">{formatFieldError("primary_color")}</span>}
          </label>
          )}
          {canSeeField("secondary_color") && (
          <label className="field">
            <span>{t("fields.theme.secondary_color")}</span>
            <input name="secondary_color" type="text" maxLength={10} value={formData.secondary_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.secondary_color")} aria-invalid={Boolean(fieldErrors["secondary_color"])} {...inputPropsForField("secondary_color", validationRules["secondary_color"], "text")} />
            {fieldErrors["secondary_color"] && <span className="field-error">{formatFieldError("secondary_color")}</span>}
          </label>
          )}
          {canSeeField("background_color") && (
          <label className="field">
            <span>{t("fields.theme.background_color")}</span>
            <input name="background_color" type="text" maxLength={10} value={formData.background_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.background_color")} aria-invalid={Boolean(fieldErrors["background_color"])} {...inputPropsForField("background_color", validationRules["background_color"], "text")} />
            {fieldErrors["background_color"] && <span className="field-error">{formatFieldError("background_color")}</span>}
          </label>
          )}
          {canSeeField("text_color") && (
          <label className="field">
            <span>{t("fields.theme.text_color")}</span>
            <input name="text_color" type="text" maxLength={10} value={formData.text_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.text_color")} aria-invalid={Boolean(fieldErrors["text_color"])} {...inputPropsForField("text_color", validationRules["text_color"], "text")} />
            {fieldErrors["text_color"] && <span className="field-error">{formatFieldError("text_color")}</span>}
          </label>
          )}
          {canSeeField("highlight_color") && (
          <label className="field">
            <span>{t("fields.theme.highlight_color")}</span>
            <input name="highlight_color" type="text" maxLength={10} value={formData.highlight_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.highlight_color")} aria-invalid={Boolean(fieldErrors["highlight_color"])} {...inputPropsForField("highlight_color", validationRules["highlight_color"], "text")} />
            {fieldErrors["highlight_color"] && <span className="field-error">{formatFieldError("highlight_color")}</span>}
          </label>
          )}
          {canSeeField("success_color") && (
          <label className="field">
            <span>{t("fields.theme.success_color")}</span>
            <input name="success_color" type="text" maxLength={10} value={formData.success_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.success_color")} aria-invalid={Boolean(fieldErrors["success_color"])} {...inputPropsForField("success_color", validationRules["success_color"], "text")} />
            {fieldErrors["success_color"] && <span className="field-error">{formatFieldError("success_color")}</span>}
          </label>
          )}
          {canSeeField("error_color") && (
          <label className="field">
            <span>{t("fields.theme.error_color")}</span>
            <input name="error_color" type="text" maxLength={10} value={formData.error_color ?? ""} onChange={handleChange} placeholder={t("fields.theme.error_color")} aria-invalid={Boolean(fieldErrors["error_color"])} {...inputPropsForField("error_color", validationRules["error_color"], "text")} />
            {fieldErrors["error_color"] && <span className="field-error">{formatFieldError("error_color")}</span>}
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
              {canSeeField("id_theme") && <th>{t("fields.theme.id_theme")}</th>}
              {canSeeField("created_by") && <th>{t("fields.theme.created_by")}</th>}
              {canSeeField("creation_date") && <th>{t("fields.theme.creation_date")}</th>}
              {canSeeField("last_update_date") && <th>{t("fields.theme.last_update_date")}</th>}
              {canSeeField("deletion_date") && <th>{t("fields.theme.deletion_date")}</th>}
              {canSeeField("tenant_id") && <th>{t("fields.theme.tenant_id")}</th>}
              {canSeeField("primary_color") && <th>{t("fields.theme.primary_color")}</th>}
              {canSeeField("secondary_color") && <th>{t("fields.theme.secondary_color")}</th>}
              {canSeeField("background_color") && <th>{t("fields.theme.background_color")}</th>}
              {canSeeField("text_color") && <th>{t("fields.theme.text_color")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_theme}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_theme") && <td><pre className="cell-value">{formatTableValue(item.id_theme)}</pre></td>}
              {canSeeField("created_by") && <td><pre className="cell-value">{formatTableValue(item.created_by)}</pre></td>}
              {canSeeField("creation_date") && <td><pre className="cell-value">{formatTableValue(item.creation_date)}</pre></td>}
              {canSeeField("last_update_date") && <td><pre className="cell-value">{formatTableValue(item.last_update_date)}</pre></td>}
              {canSeeField("deletion_date") && <td><pre className="cell-value">{formatTableValue(item.deletion_date)}</pre></td>}
              {canSeeField("tenant_id") && <td><pre className="cell-value">{formatTableValue(item.tenant_id)}</pre></td>}
              {canSeeField("primary_color") && <td><pre className="cell-value">{formatTableValue(item.primary_color)}</pre></td>}
              {canSeeField("secondary_color") && <td><pre className="cell-value">{formatTableValue(item.secondary_color)}</pre></td>}
              {canSeeField("background_color") && <td><pre className="cell-value">{formatTableValue(item.background_color)}</pre></td>}
              {canSeeField("text_color") && <td><pre className="cell-value">{formatTableValue(item.text_color)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_theme}><strong>{String(item.id_theme ?? item.id_theme)}</strong><small>#{item.id_theme}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

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
