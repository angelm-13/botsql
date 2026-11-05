import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Check, Plus, RefreshCw, Trash2, X } from "lucide-react";
import { createOvertime, deleteOvertime, getMyPermissions, getOvertime, reviewOvertime } from "../api";
import { useDialogo } from "../dialogo/useDialogo.js";

// Pestaña "Horas extra" de Asistencias. El supervisor del empleado o RH las
// autoriza antes, aprueba el tiempo no autorizado que marcan las checadas o
// (solo RH) las captura a mano con motivo. Lo que se paga es lo autorizado con
// tope en lo checado; cada registro muestra lo checado y su estado. Las reglas
// -verificar, dobles y triples, la parte exenta, cuando se pagan- viven en el
// backend (services/overtime_service.py).
//
// El descanso o festivo trabajado (pago doble ademas del dia) usa el mismo
// registro (`kind` = rest_day) y la misma autorizacion; la prima dominical es
// automatica y la calcula la nomina.

function fechaLocal(d) {
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

const horas = (minutos) => `${Math.floor(minutos / 60)}:${String(minutos % 60).padStart(2, "0")} h`;
const TONO = { verified: "status-approved", partial: "status-partially_approved", not_worked: "status-rejected", manual: "status-sent" };
// Costo estimado en pesos mexicanos (formato de Mexico).
const dinero = (v) => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(v || 0));
// Jefe y luego RH: solo lo que RH confirma se paga.
const TONO_RH = { pending_hr: "status-sent", approved: "status-approved", rejected: "status-rejected" };

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

export default function HorasExtra({ t, describirError, empleados }) {
  const dialogo = useDialogo();
  const hoy = new Date();
  const [rango, setRango] = useState({ from: fechaLocal(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), to: fechaLocal(hoy) });
  const [datos, setDatos] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [cargando, setCargando] = useState(false);
  const [permisos, setPermisos] = useState([]);
  const actor = useMemo(actorGuardado, []);
  // RH es quien edita las checadas en el Gestor (attendance_record), igual que en el backend.
  const esRh = Boolean(actor.is_superuser || actor.is_bootstrap_admin)
    || Number(permisos.find((p) => p.entity_name === "attendance_record")?.scope_update || 0) !== 0;

  useEffect(() => {
    getMyPermissions().then((p) => setPermisos(p?.entity_permissions || [])).catch(() => setPermisos([]));
  }, []);

  async function cargar(event) {
    event?.preventDefault();
    setCargando(true);
    setError("");
    try {
      setDatos(await getOvertime(rango));
    } catch (e) {
      setError(describirError(e));
    } finally {
      setCargando(false);
    }
  }

  async function guardar(event) {
    event.preventDefault();
    setError("");
    const { horasTexto, ...cuerpo } = form;
    const [h, m = "0"] = String(horasTexto).split(":");
    try {
      const minutos = cuerpo.kind === "rest_day" ? undefined : Number(h) * 60 + Number(m);
      await createOvertime({ ...cuerpo, id_user: Number(cuerpo.id_user), minutes: minutos, notes: cuerpo.notes || null });
      setForm(null);
      setAviso(t("overtime.saved"));
      await cargar();
    } catch (e) {
      setError(describirError(e));
    }
  }

  async function revisarRh(r, aprobar) {
    const notas = aprobar ? "" : await dialogo.pedirTexto(t("overtime.reject_note"));
    if (notas === null) return;
    try {
      await reviewOvertime(r.id_overtime, { approve: aprobar, notes: notas || null });
      setAviso(t(aprobar ? "overtime.confirmed_done" : "overtime.rejected_done"));
      await cargar();
    } catch (e) {
      setError(describirError(e));
    }
  }

  async function quitar(r) {
    if (!(await dialogo.confirmar(t("overtime.confirm_delete")))) return;
    try {
      await deleteOvertime(r.id_overtime);
      await cargar();
    } catch (e) {
      setError(describirError(e));
    }
  }

  const nuevo = (extra = {}) => setForm({ id_user: "", work_date: rango.to, horasTexto: "1:00", kind: "overtime", origin: "authorized", settlement: "pay", notes: "", ...extra });

  return (
    <>
      <form className="form-card kronos-filter" onSubmit={cargar}>
        <label className="field">{t("kronos.filter.from")}<input required type="date" value={rango.from} onChange={(e) => setRango((r) => ({ ...r, from: e.target.value }))} /></label>
        <label className="field">{t("kronos.filter.to")}<input required type="date" value={rango.to} onChange={(e) => setRango((r) => ({ ...r, to: e.target.value }))} /></label>
        <div className="kronos-filter-actions">
          <button type="submit" className="button" disabled={cargando}><RefreshCw size={16} /> {t("kronos.filter.generate")}</button>
          <button type="button" className="button" onClick={() => nuevo()}><Plus size={16} /> {t("overtime.new")}</button>
        </div>
      </form>
      <p className="muted">{t("overtime.hint")}</p>
      {error && <div className="alert error" role="alert">{error}</div>}
      {aviso && <div className="alert success" role="status">{aviso}</div>}

      {form && (
        <form className="form-card" onSubmit={guardar}>
          <h3>{form.origin === "detected" ? t("overtime.approve_title") : t("overtime.new")}</h3>
          <div className="form-grid">
            <label className="field">{t("overtime.employee")}
              <select required value={form.id_user} disabled={form.origin === "detected"} onChange={(e) => setForm((f) => ({ ...f, id_user: e.target.value }))}>
                <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
              </select>
            </label>
            <label className="field">{t("overtime.date")}<input required type="date" value={form.work_date} disabled={form.origin === "detected"} onChange={(e) => setForm((f) => ({ ...f, work_date: e.target.value }))} /></label>
            <label className="field">{t("overtime.kind")}
              <select value={form.kind} disabled={form.origin === "detected"} onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}>
                <option value="overtime">{t("overtime.kind_overtime")}</option>
                <option value="rest_day">{t("overtime.kind_rest_day")}</option>
              </select>
            </label>
            {form.kind === "overtime" && <label className="field">{t("overtime.hours")}<input required pattern="\d{1,2}(:[0-5]\d)?" value={form.horasTexto} onChange={(e) => setForm((f) => ({ ...f, horasTexto: e.target.value }))} /></label>}
            {form.origin !== "detected" && (
              <label className="field">{t("overtime.origin")}
                <select value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))}>
                  <option value="authorized">{t("overtime.origin_authorized")}</option>
                  <option value="manual">{t("overtime.origin_manual")}</option>
                </select>
              </label>
            )}
            <label className="field">{t("overtime.settlement")}
              <select value={form.settlement} onChange={(e) => setForm((f) => ({ ...f, settlement: e.target.value }))}>
                <option value="pay">{t("overtime.settlement_pay")}</option>
                <option value="compensate">{t("overtime.settlement_compensate")}</option>
              </select>
            </label>
            <label className="field">{t("overtime.notes")}{(form.origin === "manual" || form.settlement === "compensate") && " *"}
              <input maxLength={300} required={form.origin === "manual" || form.settlement === "compensate"} value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
            </label>
          </div>
          <p className="muted">{t("overtime.form_hint")}</p>
          <div className="form-actions">
            <button className="button primary" type="submit">{t("common.save")}</button>
            <button className="button" type="button" onClick={() => setForm(null)}>{t("common.cancel")}</button>
          </div>
        </form>
      )}

      {datos && (
        <>
          <section className="table-card kronos-table-card">
            <div className="kronos-table-heading"><div><p className="eyebrow">{t("overtime.eyebrow")}</p><h3>{t("overtime.unauthorized_title")}</h3></div></div>
            <p className="muted">{t("overtime.unauthorized_hint")} ({datos.tolerance_minutes} min)</p>
            <table>
              <thead><tr><th>{t("overtime.employee")}</th><th>{t("overtime.date")}</th><th>{t("overtime.extra_time")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{datos.unauthorized.length ? datos.unauthorized.map((u) => (
                <tr key={`${u.id_user}-${u.work_date}`}>
                  <td><strong>{u.full_name}</strong></td><td>{u.work_date}</td><td>{horas(u.minutes)}</td>
                  <td className="row-actions"><button type="button" title={t("overtime.approve")} aria-label={`${t("overtime.approve")} ${u.full_name} ${u.work_date}`}
                    onClick={() => nuevo({ id_user: String(u.id_user), work_date: u.work_date, horasTexto: horas(u.minutes).replace(" h", ""), origin: "detected" })}><Check size={15} /></button></td>
                </tr>
              )) : <tr><td colSpan="4" className="kronos-empty">{t("overtime.no_unauthorized")}</td></tr>}</tbody>
            </table>
          </section>
          <section className="table-card kronos-table-card">
            <div className="kronos-table-heading"><div><p className="eyebrow">{t("overtime.eyebrow")}</p><h3>{t("overtime.rest_title")}</h3></div></div>
            <p className="muted">{t("overtime.rest_hint")}</p>
            <table>
              <thead><tr><th>{t("overtime.employee")}</th><th>{t("overtime.date")}</th><th>{t("overtime.day_type")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{(datos.unauthorized_rest_days || []).length ? datos.unauthorized_rest_days.map((u) => (
                <tr key={`d-${u.id_user}-${u.work_date}`}>
                  <td><strong>{u.full_name}</strong></td><td>{u.work_date}</td><td>{u.holiday ? t("overtime.holiday") : t("overtime.rest_day")}</td>
                  <td className="row-actions"><button type="button" title={t("overtime.approve")} aria-label={`${t("overtime.approve")} ${u.full_name} ${u.work_date}`}
                    onClick={() => nuevo({ id_user: String(u.id_user), work_date: u.work_date, kind: "rest_day", origin: "detected" })}><Check size={15} /></button></td>
                </tr>
              )) : <tr><td colSpan="4" className="kronos-empty">{t("overtime.no_rest_days")}</td></tr>}</tbody>
            </table>
          </section>
          <section className="table-card kronos-table-card">
            <div className="kronos-table-heading"><div><p className="eyebrow">{t("overtime.eyebrow")}</p><h3>{t("overtime.registered_title")}</h3></div></div>
            {/* Lo que espera a RH y cuanto costaria, para decidir antes de que se trabaje. */}
            {datos.pending_hr > 0 && (
              <p className="field-error" style={{ margin: "0 16px 12px" }}>
                {t("overtime.pending_summary").replace("{n}", datos.pending_hr).replace("{costo}", dinero(datos.pending_hr_cost))}
              </p>
            )}
            <table>
              <thead><tr><th>{t("overtime.employee")}</th><th>{t("overtime.date")}</th><th>{t("overtime.authorized")}</th><th>{t("overtime.checked")}</th><th>{t("overtime.payable")}</th><th>{t("overtime.status")}</th><th>{t("overtime.estimated_cost")}</th><th>{t("overtime.notes")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{datos.overtime.length ? datos.overtime.map((r) => (
                <tr key={r.id_overtime}>
                  <td><strong>{r.full_name}</strong></td><td>{r.work_date}</td>
                  <td>{r.kind === "rest_day" ? t("overtime.kind_rest_day") : horas(r.minutes)}<br /><small className="muted">{t(`overtime.origin_${r.origin}`)}</small></td>
                  <td>{r.origin === "manual" ? "—" : r.kind === "rest_day" ? (r.status === "verified" ? t("overtime.came") : "—") : horas(r.checked_minutes)}</td>
                  <td>{r.settlement === "compensate" ? <small>{t("overtime.settlement_compensate")}</small> : r.kind === "rest_day" ? (r.payable_minutes ? t("overtime.double_day") : "—") : horas(r.payable_minutes)}</td>
                  <td>{/* Confirmada pero sin checada: un solo mensaje, no "No se quedo" en rojo junto a "Confirmada" en verde. */}
                    {r.status === "not_worked" && r.approval_status === "approved"
                      ? <span className="quotation-status-badge status-partially_approved">{t("overtime.approved_not_worked")}</span>
                      : <><span className={`quotation-status-badge ${TONO[r.status] || ""}`}>{t(`overtime.status_${r.status}`)}</span><br /><span className={`quotation-status-badge ${TONO_RH[r.approval_status] || ""}`}>{t(`overtime.approval_${r.approval_status}`)}</span></>}
                    {r.id_payroll_period && <><br /><small className="muted">{t("overtime.paid_in")} #{r.id_payroll_period}</small></>}</td>
                  <td>{r.estimated_cost ? dinero(r.estimated_cost) : "—"}</td>
                  <td><small>{r.notes || "—"}</small></td>
                  <td className="row-actions">
                    {esRh && r.approval_status === "pending_hr" && <button type="button" title={t("overtime.confirm_hr")} onClick={() => revisarRh(r, true)}><Check size={15} /></button>}
                    {esRh && r.approval_status === "pending_hr" && <button type="button" title={t("overtime.reject_hr")} onClick={() => revisarRh(r, false)}><X size={15} /></button>}
                    {!r.id_payroll_period && <button type="button" title={t("common.delete")} onClick={() => quitar(r)}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              )) : <tr><td colSpan="9" className="kronos-empty">{t("overtime.no_registered")}</td></tr>}</tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}

HorasExtra.propTypes = {
  t: PropTypes.func.isRequired,
  describirError: PropTypes.func.isRequired,
  empleados: PropTypes.arrayOf(PropTypes.object).isRequired,
};
