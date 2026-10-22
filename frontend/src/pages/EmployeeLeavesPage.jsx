import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import {
  createEmployeeLeave, deleteEmployeeLeave, getAllEmployeeLeave, getAttendanceEmployeeOptions,
  getEmployeeLeaveBalances, getMyPermissions, updateEmployeeLeave,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import "../styles/kronos.css";

// Vacaciones, permisos e incapacidades. Un dia dentro de una ausencia no es
// falta; si se paga o no lo decide services/attendance_rules.py. El saldo de
// vacaciones, que no se enciman y que no caigan en un periodo cerrado los valida
// el backend (services/employee_leave_service.py).

const TIPOS = ["vacation", "paid_leave", "unpaid_leave", "disability"];

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

export default function EmployeeLeavesPage() {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [view, setView] = useState("leaves");
  const [ausencias, setAusencias] = useState([]);
  const [saldos, setSaldos] = useState([]);
  const [empleados, setEmpleados] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(null);

  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1" || actor.user_type === "admin");
  const puede = (campo) => privilegiado || Number(permisos.find((p) => p.entity_name === "employee_leave")?.[campo] || 0) !== 0;

  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    const meta = e?.payload?.meta || {};
    let texto = clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
    // Los datos que manda el backend completan el mensaje (saldo, aniversario).
    if (clave === "errors.employee_leave_insufficient_balance") {
      texto += ` — ${tr("employee_leaves.available")}: ${meta.available}, ${tr("employee_leaves.requested")}: ${meta.requested}`;
    }
    if (clave === "errors.employee_leave_crosses_anniversary" && meta.anniversary) texto += ` (${meta.anniversary})`;
    if (clave === "errors.employee_leave_first_year" && meta.first_anniversary) texto += ` (${meta.first_anniversary})`;
    return texto;
  }, []);

  // Recargar no borra el aviso de error: se llama justo despues de un guardado
  // que fallo, y si lo borrara el usuario nunca veria por que no se guardo.
  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const [a, s] = await Promise.all([getAllEmployeeLeave({ per_page: 5000 }), getEmployeeLeaveBalances()]);
      setAusencias((a?.items || []).filter((x) => !x.deletion_date));
      setSaldos(s?.employees || []);
    } catch (e) {
      setError(describirError(e));
    } finally {
      setLoading(false);
    }
  }, [describirError]);

  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    getMyPermissions().then((p) => setPermisos(p?.entity_permissions || [])).catch(() => setPermisos([]));
    getAttendanceEmployeeOptions().then((r) => setEmpleados(r?.employees || [])).catch(() => setEmpleados([]));
  }, []);

  const nombreEmpleado = (id) => empleados.find((e) => e.id_user === id)?.full_name
    || saldos.find((s) => s.id_user === id)?.full_name || `#${id}`;

  async function guardar(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    const { id_employee_leave: id, ...datos } = form;
    const cuerpo = { id_user: Number(datos.id_user), leave_type: datos.leave_type, start_date: datos.start_date,
      end_date: datos.end_date, notes: datos.notes || null };
    try {
      if (id) await updateEmployeeLeave(id, cuerpo);
      else await createEmployeeLeave(cuerpo);
      setNotice(t("employee_leaves.saved"));
      setForm(null);
    } catch (e) {
      setError(describirError(e));
    }
    await cargar();
  }

  async function borrar(a) {
    if (!window.confirm(t("employee_leaves.confirm_delete"))) return;
    setError("");
    setNotice("");
    try {
      await deleteEmployeeLeave(a.id_employee_leave);
      setNotice(t("employee_leaves.deleted"));
    } catch (e) {
      setError(describirError(e));
    }
    await cargar();
  }

  const pestana = (clave) => (
    <button type="button" role="tab" aria-selected={view === clave} className={view === clave ? "active" : ""} onClick={() => setView(clave)}>{t(`employee_leaves.tab_${clave}`)}</button>
  );
  const campo = (nombre, props = {}) => (
    <input {...props} value={form[nombre] ?? ""} onChange={(e) => setForm((f) => ({ ...f, [nombre]: e.target.value }))} />
  );
  const ordenadas = [...ausencias].sort((a, b) => b.start_date.localeCompare(a.start_date));

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("employee_leaves.eyebrow")} titulo={t("employee_leaves.title")} subtitulo={t("employee_leaves.subtitle")}>
        <button className="button ghost" onClick={() => { setError(""); cargar(); }} disabled={loading}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>
      <div className="kronos-tabs" role="tablist">{pestana("leaves")}{pestana("balances")}</div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {view === "leaves" && (
        <>
          {form && (
            <form className="form-card" onSubmit={guardar}>
              <h3>{form.id_employee_leave ? t("common.edit") : t("employee_leaves.new_leave")}</h3>
              <div className="form-grid">
                <label className="field">{t("employee_leaves.employee")}
                  <select required value={form.id_user} onChange={(e) => setForm((f) => ({ ...f, id_user: e.target.value }))}>
                    <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                    {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
                  </select>
                </label>
                <label className="field">{t("employee_leaves.type")}
                  <select required value={form.leave_type} onChange={(e) => setForm((f) => ({ ...f, leave_type: e.target.value }))}>
                    {TIPOS.map((tipo) => <option key={tipo} value={tipo}>{t(`employee_leaves.type_${tipo}`)}</option>)}
                  </select>
                </label>
                <label className="field">{t("employee_leaves.from")}{campo("start_date", { required: true, type: "date" })}</label>
                <label className="field">{t("employee_leaves.to")}{campo("end_date", { required: true, type: "date", min: form.start_date || undefined })}</label>
                <label className="field">{t("employee_leaves.notes")}{campo("notes", { maxLength: 300 })}</label>
              </div>
              <p className="muted">{t(`employee_leaves.hint_${form.leave_type}`)}</p>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setForm(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("employee_leaves.tab_leaves")}</p><h3>{t("employee_leaves.leaves_title")}</h3></div>
              {puede("scope_create") && <button className="button" type="button" onClick={() => setForm({ id_user: "", leave_type: "vacation", start_date: hoy(), end_date: hoy(), notes: "" })}><Plus size={16} /> {t("employee_leaves.new_leave")}</button>}
            </div>
            <table>
              <thead><tr><th>{t("employee_leaves.employee")}</th><th>{t("employee_leaves.type")}</th><th>{t("employee_leaves.from")}</th><th>{t("employee_leaves.to")}</th><th>{t("employee_leaves.notes")}</th><th>{t("my_leaves.status")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{ordenadas.length ? ordenadas.map((a) => (
                <tr key={a.id_employee_leave}>
                  <td><strong>{nombreEmpleado(a.id_user)}</strong></td>
                  <td>{t(`employee_leaves.type_${a.leave_type}`)}</td>
                  <td>{a.start_date}</td>
                  <td>{a.end_date}</td>
                  <td><small>{a.notes || "—"}</small></td>
                  <td>{t(`my_leaves.status_${a.leave_status || "approved"}`)}</td>
                  <td className="row-actions">
                    {puede("scope_update") && <button type="button" title={t("common.edit")} onClick={() => setForm({ ...a, notes: a.notes || "" })}><Pencil size={15} /></button>}
                    {puede("scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(a)}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              )) : <tr><td colSpan="7" className="kronos-empty">{t("employee_leaves.no_leaves")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}

      {view === "balances" && (
        <div className="table-card">
          <div className="kronos-table-heading">
            <div><p className="eyebrow">{t("employee_leaves.tab_balances")}</p><h3>{t("employee_leaves.balances_title")}</h3></div>
          </div>
          <p className="muted">{t("employee_leaves.balances_hint")}</p>
          <table>
            <thead><tr><th>{t("employee_leaves.employee")}</th><th>{t("employee_leaves.hire_date")}</th><th>{t("employee_leaves.service_years")}</th><th>{t("employee_leaves.service_year")}</th><th>{t("employee_leaves.entitled")}</th><th>{t("employee_leaves.taken")}</th><th>{t("my_leaves.pending")}</th><th>{t("employee_leaves.available")}</th></tr></thead>
            <tbody>{saldos.length ? saldos.map((s) => (
              <tr key={s.id_user}>
                <td><strong>{s.full_name || `#${s.id_user}`}</strong></td>
                <td>{s.hire_date || <small>{t("employee_leaves.no_hire_date")}</small>}</td>
                <td>{s.service_years}</td>
                <td><small>{s.year_start ? `${s.year_start} – ${s.year_end}` : "—"}</small></td>
                <td>{s.entitled}</td>
                <td>{s.taken}</td>
                <td>{s.pending || 0}</td>
                <td><strong>{s.available}</strong></td>
              </tr>
            )) : <tr><td colSpan="8" className="kronos-empty">{t("employee_leaves.no_employees")}</td></tr>}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
