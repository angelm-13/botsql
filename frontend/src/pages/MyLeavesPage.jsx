import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Plus, RefreshCw, X } from "lucide-react";
import {
  approveEmployeeLeave, cancelEmployeeLeave, getMyEmployeeLeaves, getPendingEmployeeLeaves,
  rejectEmployeeLeave, requestEmployeeLeave,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import "../styles/kronos.css";

// "Mis vacaciones": el empleado ve SU saldo y SUS solicitudes, pide vacaciones o
// permisos y cancela lo pendiente. "Por autorizar": su jefe (o RH) aprueba o
// rechaza. Quien puede ver o revisar que lo decide el backend
// (services/employee_leave_service.py); aqui solo se muestra lo que contesta.

const TIPOS = ["vacation", "paid_leave", "unpaid_leave"];

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export default function MyLeavesPage() {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [view, setView] = useState("mine");
  const [mias, setMias] = useState(null);
  const [pendientes, setPendientes] = useState([]);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    const meta = e?.payload?.meta || {};
    let texto = clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
    if (clave === "errors.employee_leave_insufficient_balance") {
      texto += ` — ${tr("employee_leaves.available")}: ${meta.available}, ${tr("employee_leaves.requested")}: ${meta.requested}`;
    }
    if (clave === "errors.employee_leave_crosses_anniversary" && meta.anniversary) texto += ` (${meta.anniversary})`;
    if (clave === "errors.employee_leave_first_year" && meta.first_anniversary) texto += ` (${meta.first_anniversary})`;
    return texto;
  }, []);

  // Recargar no borra el aviso de error: se llama despues de una accion que pudo fallar.
  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const [m, p] = await Promise.all([getMyEmployeeLeaves(), getPendingEmployeeLeaves()]);
      setMias(m || null);
      setPendientes(p?.requests || []);
    } catch (e) {
      setError(describirError(e));
    } finally {
      setLoading(false);
    }
  }, [describirError]);

  useEffect(() => { cargar(); }, [cargar]);

  async function accion(hacer, mensaje) {
    setError("");
    setNotice("");
    try {
      await hacer();
      setNotice(t(mensaje));
      await cargar();
      return true;
    } catch (e) {
      setError(describirError(e));
      await cargar();
      return false;
    }
  }

  async function pedir(event) {
    event.preventDefault();
    const ok = await accion(() => requestEmployeeLeave({ ...form, notes: form.notes || null }), "my_leaves.requested_done");
    if (ok) setForm(null);
  }

  function rechazar(s) {
    const nota = window.prompt(t("my_leaves.reject_note"), "");
    if (nota === null) return;
    accion(() => rejectEmployeeLeave(s.id_employee_leave, { review_note: nota }), "my_leaves.rejected_done");
  }

  // Mismas insignias de estado que cotizaciones y periodos de nomina.
  const TONO = { requested: "status-sent", approved: "status-approved", rejected: "status-rejected", cancelled: "" };
  const estado = (s) => <span className={`quotation-status-badge ${TONO[s] || ""}`}>{t(`my_leaves.status_${s}`)}</span>;
  const campo = (nombre, props = {}) => (
    <input {...props} value={form[nombre] ?? ""} onChange={(e) => setForm((f) => ({ ...f, [nombre]: e.target.value }))} />
  );
  const pestana = (clave, extra = "") => (
    <button type="button" role="tab" aria-selected={view === clave} className={view === clave ? "active" : ""} onClick={() => setView(clave)}>{t(`my_leaves.tab_${clave}`)}{extra}</button>
  );
  const saldo = mias?.balance;

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("employee_leaves.eyebrow")} titulo={t("my_leaves.title")} subtitulo={t("my_leaves.subtitle")}>
        <button className="button ghost" onClick={() => { setError(""); cargar(); }} disabled={loading}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>
      <div className="kronos-tabs" role="tablist">{pestana("mine")}{pestana("review", pendientes.length ? ` (${pendientes.length})` : "")}</div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {view === "mine" && mias && !mias.is_employee && <div className="empty"><p>{t("my_leaves.not_employee")}</p></div>}
      {view === "mine" && mias?.is_employee && (
        <>
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("employee_leaves.tab_balances")}</p><h3>{t("my_leaves.balance_title")}</h3></div>
              <button className="button" type="button" onClick={() => setForm({ leave_type: "vacation", start_date: hoy(), end_date: hoy(), notes: "" })}><Plus size={16} /> {t("my_leaves.new_request")}</button>
            </div>
            {saldo?.hire_date ? (
              <table>
                <thead><tr><th>{t("employee_leaves.entitled")}</th><th>{t("employee_leaves.taken")}</th><th>{t("my_leaves.pending")}</th><th>{t("employee_leaves.available")}</th><th>{t("employee_leaves.service_year")}</th></tr></thead>
                <tbody><tr><td>{saldo.entitled}</td><td>{saldo.taken}</td><td>{saldo.pending}</td><td><strong>{saldo.available}</strong></td><td><small>{saldo.year_start ? `${saldo.year_start} – ${saldo.year_end}` : "—"}</small></td></tr></tbody>
              </table>
            ) : <p className="muted">{t("employee_leaves.no_hire_date")}</p>}
          </div>
          {form && (
            <form className="form-card" onSubmit={pedir}>
              <h3>{t("my_leaves.new_request")}</h3>
              <div className="form-grid">
                <label className="field">{t("employee_leaves.type")}
                  <select required value={form.leave_type} onChange={(e) => setForm((f) => ({ ...f, leave_type: e.target.value }))}>
                    {TIPOS.map((tipo) => <option key={tipo} value={tipo}>{t(`employee_leaves.type_${tipo}`)}</option>)}
                  </select>
                </label>
                <label className="field">{t("employee_leaves.from")}{campo("start_date", { required: true, type: "date" })}</label>
                <label className="field">{t("employee_leaves.to")}{campo("end_date", { required: true, type: "date", min: form.start_date || undefined })}</label>
                <label className="field">{t("employee_leaves.notes")}{campo("notes", { maxLength: 300 })}</label>
              </div>
              <p className="muted">{t("my_leaves.request_hint")}</p>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("my_leaves.send")}</button>
                <button className="button" type="button" onClick={() => setForm(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading"><div><p className="eyebrow">{t("my_leaves.tab_mine")}</p><h3>{t("my_leaves.mine_title")}</h3></div></div>
            <table>
              <thead><tr><th>{t("employee_leaves.type")}</th><th>{t("employee_leaves.from")}</th><th>{t("employee_leaves.to")}</th><th>{t("my_leaves.status")}</th><th>{t("my_leaves.review_note")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{mias.leaves.length ? mias.leaves.map((a) => (
                <tr key={a.id_employee_leave}>
                  <td>{t(`employee_leaves.type_${a.leave_type}`)}</td><td>{a.start_date}</td><td>{a.end_date}</td>
                  <td>{estado(a.leave_status)}</td><td><small>{a.review_note || "—"}</small></td>
                  <td className="row-actions">{a.leave_status === "requested" && <button type="button" title={t("my_leaves.cancel_request")} onClick={() => accion(() => cancelEmployeeLeave(a.id_employee_leave), "my_leaves.cancelled_done")}><X size={15} /></button>}</td>
                </tr>
              )) : <tr><td colSpan="6" className="kronos-empty">{t("my_leaves.no_requests")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}

      {view === "review" && (
        <div className="table-card">
          <div className="kronos-table-heading"><div><p className="eyebrow">{t("my_leaves.tab_review")}</p><h3>{t("my_leaves.review_title")}</h3></div></div>
          <p className="muted">{t("my_leaves.review_hint")}</p>
          <table>
            <thead><tr><th>{t("employee_leaves.employee")}</th><th>{t("employee_leaves.type")}</th><th>{t("employee_leaves.from")}</th><th>{t("employee_leaves.to")}</th><th>{t("employee_leaves.notes")}</th><th>{t("employee_leaves.available")}</th><th>{t("common.actions")}</th></tr></thead>
            <tbody>{pendientes.length ? pendientes.map((s) => (
              <tr key={s.id_employee_leave}>
                <td><strong>{s.full_name}</strong></td><td>{t(`employee_leaves.type_${s.leave_type}`)}</td>
                <td>{s.start_date}</td><td>{s.end_date}</td><td><small>{s.notes || "—"}</small></td><td>{s.available}</td>
                <td className="row-actions">
                  <button type="button" title={t("my_leaves.approve")} aria-label={`${t("my_leaves.approve")} ${s.full_name}`} onClick={() => accion(() => approveEmployeeLeave(s.id_employee_leave), "my_leaves.approved_done")}><Check size={15} /></button>
                  <button type="button" title={t("my_leaves.reject")} aria-label={`${t("my_leaves.reject")} ${s.full_name}`} onClick={() => rechazar(s)}><X size={15} /></button>
                </td>
              </tr>
            )) : <tr><td colSpan="7" className="kronos-empty">{t("my_leaves.no_pending")}</td></tr>}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
