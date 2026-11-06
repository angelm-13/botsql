import { useEffect, useState } from "react";
import { AlertTriangle, FileSpreadsheet, Search } from "lucide-react";
import { downloadAttendanceReport, getAttendanceCorrectionsLog, getAttendanceReport } from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import { rangoAnterior, rangoDe } from "../utils/rangosDeAsistencia.js";

// Reporte de asistencia para RH: semana o quincena, una fila por empleado y las
// alertas de patrones. Solo lectura; las reglas y los limites viven en el backend
// (services/reporte_de_asistencia.py) y los limites se ajustan en Ajustes de nomina.

const TONO = { high: "status-rejected", medium: "status-partially_approved" };
const horas = (min) => (min ? `${Math.floor(min / 60)}:${String(min % 60).padStart(2, "0")} h` : "—");

export default function AttendanceReportPage() {
  const { t } = useI18n();
  const [rango, setRango] = useState(() => rangoDe("biweekly"));
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  // "report" = reporte con alertas; "log" = bitacora de correcciones de checadas (quien movio que).
  const [vista, setVista] = useState("report");
  const [bitacora, setBitacora] = useState(null);
  const [supervisor, setSupervisor] = useState("");

  const describir = (e) => {
    const clave = e?.payload?.error_key || e?.message;
    return clave ? t(clave, t("errors.request_failed")) : t("errors.request_failed");
  };

  async function ver(r = rango, v = vista, sup = supervisor) {
    setCargando(true);
    setError("");
    try {
      if (v === "log") setBitacora(await getAttendanceCorrectionsLog({ ...r, supervisor: sup }));
      else setDatos(await getAttendanceReport(r));
    } catch (e) {
      setError(e?.payload?.meta?.reason === "range" ? t(v === "log" ? "attendance_report.log_range_error" : "attendance_report.range_error") : describir(e));
      if (v === "log") setBitacora(null); else setDatos(null);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { ver(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function elegir(r) {
    setRango(r);
    ver(r);
  }

  function cambiarVista(v) {
    setVista(v);
    ver(rango, v);
  }

  async function descargar() {
    try {
      const blob = await downloadAttendanceReport(rango);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `asistencia_${rango.start}_${rango.end}.xlsx`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      setError(describir(e));
    }
  }

  return (
    <section className="entity-page">
      <PageHeader eyebrow={t("attendance_report.eyebrow")} titulo={t("attendance_report.title")} subtitulo={t("attendance_report.subtitle")} />
      <div className="toolbar" role="tablist" style={{ marginTop: 0 }}>
        <button type="button" role="tab" aria-selected={vista === "report"} className={vista === "report" ? "button active" : "button"} onClick={() => cambiarVista("report")}>{t("attendance_report.tab_report")}</button>
        <button type="button" role="tab" aria-selected={vista === "log"} className={vista === "log" ? "button active" : "button"} onClick={() => cambiarVista("log")}>{t("attendance_report.tab_log")}</button>
      </div>
      <div className="form-card">
        <div className="toolbar" style={{ marginTop: 0 }}>
          <button type="button" className="button" onClick={() => elegir(rangoAnterior("week"))}>{t("attendance_report.last_week")}</button>
          <button type="button" className="button" onClick={() => elegir(rangoAnterior("biweekly"))}>{t("attendance_report.last_fortnight")}</button>
          <button type="button" className="button" onClick={() => elegir(rangoDe("week"))}>{t("attendance_report.this_week")}</button>
          <button type="button" className="button" onClick={() => elegir(rangoDe("biweekly"))}>{t("attendance_report.this_fortnight")}</button>
        </div>
        <div className="toolbar">
          <label className="field">
            <span>{t("attendance_report.from")}</span>
            <input type="date" value={rango.start} onChange={(e) => setRango({ ...rango, start: e.target.value })} />
          </label>
          <label className="field">
            <span>{t("attendance_report.to")}</span>
            <input type="date" value={rango.end} onChange={(e) => setRango({ ...rango, end: e.target.value })} />
          </label>
          {vista === "log" && (
            <label className="field">
              <span>{t("attendance_report.log_by")}</span>
              <select value={supervisor} onChange={(e) => { setSupervisor(e.target.value); ver(rango, "log", e.target.value); }}>
                <option value="">{t("attendance_report.log_everyone")}</option>
                {(bitacora?.supervisors || []).map((s) => <option key={s.id_user} value={s.id_user}>{s.full_name}</option>)}
              </select>
            </label>
          )}
          <button type="button" className="button primary" onClick={() => ver()} disabled={cargando}><Search size={15} /> {t("attendance_report.show")}</button>
          {vista === "report" && <button type="button" className="button" onClick={descargar} disabled={!datos}><FileSpreadsheet size={15} /> {t("attendance_report.download")}</button>}
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>{t(vista === "log" ? "attendance_report.log_hint" : "attendance_report.hint")}</p>
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}
      {cargando && <div className="alert">{t("common.loading")}</div>}

      {vista === "log" && bitacora && (
        <div className="table-card">
          {bitacora.corrections.length ? (
            <table>
              <thead><tr>
                <th>{t("attendance_report.log_date")}</th><th>{t("attendance_report.employee")}</th><th>{t("attendance_report.log_change")}</th>
                <th>{t("attendance_report.log_reason")}</th><th>{t("attendance_report.log_by")}</th><th>{t("attendance_report.log_when")}</th>
              </tr></thead>
              <tbody>{bitacora.corrections.map((c) => (
                <tr key={c.id_attendance_correction}>
                  <td>{c.date}</td>
                  <td><strong>{c.employee}</strong></td>
                  <td>{c.added ? t("attendance_report.log_added").replace("{hora}", c.new_time) : `${c.previous_time} → ${c.new_time}`}
                    {c.is_exception && <span className="quotation-status-badge status-partially_approved" style={{ marginLeft: 6 }}>{t("attendance_report.log_exception")}</span>}
                  </td>
                  <td><small>{c.kind && <strong>{t(`kronos.corrections.kind_${c.kind}`)}: </strong>}{c.reason}</small></td>
                  <td>{c.by}</td>
                  <td><small className="muted">{(c.created_at || "").replace("T", " ")}</small></td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p style={{ padding: 16 }}>{t("attendance_report.log_empty")}</p>}
        </div>
      )}

      {vista === "report" && datos && (<>
        <div className={`alert ${datos.with_alerts ? "error" : "success"}`} role="status">
          <AlertTriangle size={16} style={{ verticalAlign: "-3px" }} />{" "}
          {t("attendance_report.with_alerts").replace("{n}", datos.with_alerts).replace("{total}", datos.employees.length)}
        </div>
        <div className="table-card">
          {datos.employees.length ? (
            <table>
              <thead><tr>
                <th>{t("attendance_report.employee")}</th><th>{t("attendance_report.late")}</th><th>{t("attendance_report.absences")}</th>
                <th>{t("attendance_report.pending")}</th><th>{t("attendance_report.leave_days")}</th><th>{t("attendance_report.manual")}</th>
                <th>{t("attendance_report.overtime")}</th><th>{t("attendance_report.alerts")}</th>
              </tr></thead>
              <tbody>{datos.employees.map((f) => (
                <tr key={f.id_user}>
                  <td><strong>{f.full_name}</strong></td>
                  <td>{f.late}{f.late_minutes ? <small className="muted"> · {f.late_minutes} min</small> : null}</td>
                  <td>{f.absences}{f.absences_next_to_rest ? <small className="muted"> · {t("attendance_report.next_to_rest_short").replace("{n}", f.absences_next_to_rest)}</small> : null}</td>
                  <td>{f.pending_justification}</td>
                  <td>{f.leave_days}</td>
                  <td>
                    {f.manual_checks}{f.manual_exceptions ? <small className="muted"> · {f.manual_exceptions} {t("attendance_report.exceptions")}</small> : null}
                    {f.manual_reasons.length > 0 && (
                      <details><summary className="muted">{t("attendance_report.reasons")}</summary>
                        <ul style={{ margin: "4px 0 0", paddingLeft: 16 }}>
                          {f.manual_reasons.map((m, i) => <li key={i}><small>{m.date} · {m.by}: {m.kind && <strong>{t(`kronos.corrections.kind_${m.kind}`)}. </strong>}{m.reason}</small></li>)}
                        </ul>
                      </details>
                    )}
                  </td>
                  <td>{horas(f.overtime_minutes)}{f.overtime_pending_minutes ? <small className="muted"><br />{t("attendance_report.pending_hr")}: {horas(f.overtime_pending_minutes)}</small> : null}</td>
                  <td>{f.alerts.length ? f.alerts.map((a) => (
                    <span key={a.code} className={`quotation-status-badge ${TONO[a.level]}`} style={{ marginRight: 4, display: "inline-block", marginBottom: 4 }}>
                      {t(`attendance_report.alert_${a.code}`)} ({a.value})
                    </span>
                  )) : <span className="muted">—</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p style={{ padding: 16 }}>{t("attendance_report.empty")}</p>}
        </div>
        {datos.supervisors.length > 0 && (
          <div className="table-card">
            <h3 style={{ padding: "16px 16px 0" }}>{t("attendance_report.supervisors_title")}</h3>
            <p className="muted" style={{ padding: "0 16px" }}>{t("attendance_report.supervisors_hint").replace("{n}", datos.limits.report_alert_supervisor_manual)}</p>
            <table>
              <thead><tr><th>{t("attendance_report.supervisor")}</th><th>{t("attendance_report.manual")}</th><th>{t("attendance_report.alerts")}</th></tr></thead>
              <tbody>{datos.supervisors.map((s) => (
                <tr key={s.id_user}>
                  <td>{s.full_name}</td><td>{s.manual_checks}</td>
                  <td>{s.alert ? <span className="quotation-status-badge status-partially_approved">{t("attendance_report.alert_supervisor")}</span> : <span className="muted">—</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </>)}
    </section>
  );
}
