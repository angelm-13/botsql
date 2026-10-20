import { useEffect, useMemo, useState } from "react";
import { Calculator, Eye, FileDown, Lock, Unlock, RefreshCw, Search, Trash2, Pencil } from "lucide-react";
import { useI18n } from "../i18n";
import { calculatePayrollPeriod, closePayrollPeriod, downloadPayrollReceipt, getPayrollPeriodSummary, reopenPayrollPeriod, getAllPayrollPeriod, createPayrollPeriod, updatePayrollPeriod, deletePayrollPeriod, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, getAllStatus } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import Pagination from "../components/Pagination.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";
import { formatearFechaHora } from "../utils/fechas";

const emptyForm = { period_start: "", period_end: "", payment_date: "", id_status: "", includes_aguinaldo: false };
const validationRules = allValidationRules["payroll_period"] || {};
const ENTITY_KEY = "payroll_period";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_payroll_period', 'period_start', 'period_end', 'payment_date', 'id_status', 'includes_aguinaldo', 'created_by', 'creation_date', 'last_update_date', 'deletion_date'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function PayrollPeriodPage() {
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
  // Resultado del ultimo "Calcular nomina" (payroll_calculation_service).
  const [calculation, setCalculation] = useState(null);
  const [notice, setNotice] = useState("");

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
  // Tambien para quien solo consulta: ve el estado del periodo y su resultado.
  const showRowActions = canRead;
  const [statusOptions, setStatusOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllPayrollPeriod({ page, per_page: perPage, q: query || undefined });
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
    const fieldLabel = t(`fields.payroll_period.${fieldName}`, fieldName);
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
    const validation = validateForm("payroll_period", submitPayload, validationRules);
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
      if (editingId) await updatePayrollPeriod(editingId, submitPayload);
      else await createPayrollPeriod(submitPayload);
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
    setEditingId(item.id_payroll_period);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);

    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!window.confirm(t("common.confirm_delete"))) return;
    try { await deletePayrollPeriod(item.id_payroll_period); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
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
    const fieldLabel = errorMeta?.field ? t(`fields.payroll_period.${errorMeta.field}`, errorMeta.field) : "";
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

  // Abierto -> Calculado -> Cerrado. Las reglas viven en el backend
  // (payroll_calculation_service.py); aqui solo se ofrecen los botones que
  // tienen sentido para cada estado.
  async function periodAction(action, { confirmKey, doneKey, reload } = {}) {
    if (confirmKey && !window.confirm(t(confirmKey))) return;
    setErrorKey("");
    setErrorMeta(null);
    setNotice("");
    try {
      const result = await action();
      if (doneKey) setNotice(t(doneKey));
      if (reload) await loadData();
      return result;
    } catch (error) {
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(error.payload?.meta || null);
      return null;
    }
  }

  async function runCalculation(item) {
    setCalculation(null);
    const result = await periodAction(() => calculatePayrollPeriod(item.id_payroll_period), { reload: true });
    if (result) setCalculation(result);
  }

  async function viewCalculation(item) {
    setCalculation(null);
    const result = await periodAction(() => getPayrollPeriodSummary(item.id_payroll_period));
    if (result) setCalculation(result);
  }

  async function closePeriod(item) {
    await periodAction(() => closePayrollPeriod(item.id_payroll_period),
      { confirmKey: "payroll_calc.confirm_close", doneKey: "payroll_calc.closed_done", reload: true });
    if (calculation?.id_payroll_period === item.id_payroll_period) setCalculation({ ...calculation, period_state: "closed" });
  }

  async function reopenPeriod(item) {
    await periodAction(() => reopenPayrollPeriod(item.id_payroll_period),
      { confirmKey: "payroll_calc.confirm_reopen", doneKey: "payroll_calc.reopened_done", reload: true });
    if (calculation?.id_payroll_period === item.id_payroll_period) setCalculation({ ...calculation, period_state: "calculated" });
  }

  async function openReceipt(idUser) {
    const blob = await periodAction(() => downloadPayrollReceipt(calculation.id_payroll_period, idUser));
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  const stateBadge = (state) => {
    const value = state || "open";
    const tone = value === "closed" ? "status-converted" : value === "calculated" ? "status-sent" : "";
    return <span className={`quotation-status-badge ${tone}`}>{t(`payroll_calc.state_${value}`)}</span>;
  };

  const money = (value) => new Intl.NumberFormat(lang, { style: "currency", currency: "MXN" }).format(Number(value || 0));

  const groups = useMemo(() => filtered.reduce((acc, item) => {
    const key = String(item.id_status ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);
  // Las columnas de aguinaldo y prima solo se muestran si alguien las cobra en el periodo.
  const conPrestaciones = Boolean(calculation?.employees.some((row) => row.aguinaldo || row.vacation_premium));

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.payroll_period")}
        subtitulo={t("page.payroll_period.subtitle", "")}
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
          {canSeeField("period_start") && (
          <label className="field">
            <span>{t("fields.payroll_period.period_start")}</span>
            <input name="period_start" type="date" value={formData.period_start ?? ""} onChange={handleChange} placeholder={t("fields.payroll_period.period_start")} aria-invalid={Boolean(fieldErrors["period_start"])} {...inputPropsForField("period_start", validationRules["period_start"], "date")} />
            {fieldErrors["period_start"] && <span className="field-error">{formatFieldError("period_start")}</span>}
          </label>
          )}
          {canSeeField("period_end") && (
          <label className="field">
            <span>{t("fields.payroll_period.period_end")}</span>
            <input name="period_end" type="date" value={formData.period_end ?? ""} onChange={handleChange} placeholder={t("fields.payroll_period.period_end")} aria-invalid={Boolean(fieldErrors["period_end"])} {...inputPropsForField("period_end", validationRules["period_end"], "date")} />
            {fieldErrors["period_end"] && <span className="field-error">{formatFieldError("period_end")}</span>}
          </label>
          )}
          {canSeeField("payment_date") && (
          <label className="field">
            <span>{t("fields.payroll_period.payment_date")}</span>
            <input name="payment_date" type="date" value={formData.payment_date ?? ""} onChange={handleChange} placeholder={t("fields.payroll_period.payment_date")} aria-invalid={Boolean(fieldErrors["payment_date"])} {...inputPropsForField("payment_date", validationRules["payment_date"], "date")} />
            {fieldErrors["payment_date"] && <span className="field-error">{formatFieldError("payment_date")}</span>}
          </label>
          )}
          {canSeeField("includes_aguinaldo") && (
          <label className="checkbox-inline">
            <input name="includes_aguinaldo" type="checkbox" checked={Boolean(formData.includes_aguinaldo)} onChange={handleChange} />
            <span>{t("fields.payroll_period.includes_aguinaldo")}</span>
          </label>
          )}
          {canSeeField("id_status") && (
          <label className="field">
            <span>{t("fields.payroll_period.id_status")}</span>
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
      {notice && <div className="alert success" role="status">{notice}</div>}
      {calculation && (
        <div className="table-card">
          <h3>{t("payroll_calc.title")} · #{calculation.id_payroll_period} {stateBadge(calculation.period_state)}</h3>
          <p className="muted">{t("payroll_calc.hint")}</p>
          <p className="muted">{t("payroll_calc.tax_hint")}</p>
          <p className="muted">{t("payroll_calc.aguinaldo_hint")}</p>
          {calculation.employees.length ? (
            <table>
              <thead><tr>
                <th>{t("payroll_calc.employee")}</th><th>{t("payroll_calc.days")}</th><th>{t("payroll_calc.absences")}</th><th>{t("payroll_calc.daily")}</th>
                <th>{t("payroll_calc.salary")}</th>{conPrestaciones && <><th>{t("payroll_calc.aguinaldo")}</th><th>{t("payroll_calc.vacation_premium")}</th></>}<th>{t("payroll_calc.earnings")}</th><th>ISR</th><th>IMSS</th><th>{t("payroll_calc.deductions")}</th><th>{t("payroll_calc.net")}</th>
                <th>{t("payroll_calc.receipt")}</th>
              </tr></thead>
              <tbody>{calculation.employees.map((row) => (
                <tr key={row.id_user}>
                  <td>{row.full_name}</td><td>{row.days_worked}</td><td>{row.absences || 0}</td><td>{money(row.daily_salary)}</td>
                  <td>{money(row.salary)}</td>{conPrestaciones && <><td>{money(row.aguinaldo)}</td><td title={row.vacation_days ? `${row.vacation_days} d` : undefined}>{money(row.vacation_premium)}</td></>}<td>{money(row.total_earnings)}</td><td title={row.employment_subsidy ? `${t("payroll_calc.isr_hint")}: ${money(row.isr_before_subsidy)} - ${money(row.employment_subsidy)}` : undefined}>{money(row.isr)}</td><td title={row.sbc ? `SBC ${money(row.sbc)}` : undefined}>{money(row.imss)}</td><td>{money(row.total_deductions)}</td><td><strong>{money(row.net_pay)}</strong></td>
                  <td><button type="button" className="button ghost" onClick={() => openReceipt(row.id_user)} aria-label={`${t("payroll_calc.receipt")} ${row.full_name}`}><FileDown size={15} /> PDF</button></td>
                </tr>
              ))}</tbody>
              <tfoot><tr><td colSpan={conPrestaciones ? 11 : 9}><strong>{t("payroll_calc.total")}</strong></td><td><strong>{money(calculation.total_net_pay)}</strong></td><td /></tr></tfoot>
            </table>
          ) : <p>{t("payroll_calc.empty")}</p>}
          {calculation.without_hire_date?.length > 0 && (
            <p className="muted">{t("payroll_calc.without_hire_date")}: {calculation.without_hire_date.map((row) => row.full_name).join(", ")}</p>
          )}
          {calculation.without_salary.length > 0 && (
            <p className="muted">{t("payroll_calc.without_salary")}: {calculation.without_salary.map((row) => row.full_name).join(", ")}</p>
          )}
        </div>
      )}
      {permissionReady && !canRead && !canCreate && <div className="empty"><strong>{t("security.permission.read_denied", "Sin permiso de lectura")}</strong><p>{t("common.module_hidden_hint", "Este módulo no tiene acciones seleccionadas; quedará oculto y sus campos no se mostrarán.")}</p></div>}
      {canRead && !loading && filtered.length === 0 && <div className="empty"><strong>{t("common.empty_title")}</strong><p>{t("common.empty_body")}</p></div>}


      {canRead && view === "table" && filtered.length > 0 && <div className="table-card"><table><thead><tr>{showRowActions && <th>{t("common.actions")}</th>}
              {canSeeField("id_payroll_period") && <th>{t("fields.payroll_period.id_payroll_period")}</th>}
              {canSeeField("period_start") && <th>{t("fields.payroll_period.period_start")}</th>}
              {canSeeField("period_end") && <th>{t("fields.payroll_period.period_end")}</th>}
              {canSeeField("payment_date") && <th>{t("fields.payroll_period.payment_date")}</th>}
              {canSeeField("id_status") && <th>{t("fields.payroll_period.id_status")}</th>}
              {canSeeField("created_by") && <th>{t("fields.payroll_period.created_by")}</th>}
              {canSeeField("creation_date") && <th>{t("fields.payroll_period.creation_date")}</th>}
              {canSeeField("last_update_date") && <th>{t("fields.payroll_period.last_update_date")}</th>}
              {canSeeField("deletion_date") && <th>{t("fields.payroll_period.deletion_date")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_payroll_period}>{showRowActions && <td className="row-actions">{stateBadge(item.period_state)}{canUpdate && item.period_state !== "closed" && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && item.period_state !== "closed" && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{canUpdate && item.period_state !== "closed" && <button type="button" onClick={() => runCalculation(item)} title={t("payroll_calc.button")} aria-label={`${t("payroll_calc.button")} #${item.id_payroll_period}`}><Calculator size={15} /></button>}{item.period_state && item.period_state !== "open" && <button type="button" onClick={() => viewCalculation(item)} title={t("payroll_calc.view")} aria-label={`${t("payroll_calc.view")} #${item.id_payroll_period}`}><Eye size={15} /></button>}{canUpdate && item.period_state === "calculated" && <button type="button" onClick={() => closePeriod(item)} title={t("payroll_calc.close")} aria-label={`${t("payroll_calc.close")} #${item.id_payroll_period}`}><Lock size={15} /></button>}{canDelete && item.period_state === "closed" && <button type="button" onClick={() => reopenPeriod(item)} title={t("payroll_calc.reopen")} aria-label={`${t("payroll_calc.reopen")} #${item.id_payroll_period}`}><Unlock size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_payroll_period") && <td><pre className="cell-value">{formatTableValue(item.id_payroll_period)}</pre></td>}
              {canSeeField("period_start") && <td><pre className="cell-value">{formatTableValue(item.period_start)}</pre></td>}
              {canSeeField("period_end") && <td><pre className="cell-value">{formatTableValue(item.period_end)}</pre></td>}
              {canSeeField("payment_date") && <td><pre className="cell-value">{formatTableValue(item.payment_date)}</pre></td>}
              {canSeeField("id_status") && <td><pre className="cell-value">{formatTableValue(item.id_status)}</pre></td>}
              {canSeeField("created_by") && <td><pre className="cell-value">{formatTableValue(item.created_by)}</pre></td>}
              {canSeeField("creation_date") && <td><pre className="cell-value">{formatTableValue(item.creation_date)}</pre></td>}
              {canSeeField("last_update_date") && <td><pre className="cell-value">{formatTableValue(item.last_update_date)}</pre></td>}
              {canSeeField("deletion_date") && <td><pre className="cell-value">{formatTableValue(item.deletion_date)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card" key={item.id_payroll_period}><strong>{String(item.id_payroll_period ?? item.id_payroll_period)}</strong><small>#{item.id_payroll_period}</small>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

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
