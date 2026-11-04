import { Fragment, useState } from "react";
import PropTypes from "prop-types";
import { Pencil, RefreshCw } from "lucide-react";
import { createAttendanceCorrection, getAttendanceCorrections, getAttendanceIncidences } from "../api";

// Pestaña "Incidencias" de Asistencias: retardos, faltas y checadas incompletas
// por empleado segun su horario, y los dias de vacaciones, permisos e
// incapacidades (employee_leave), que no son falta. Es solo un reporte para que los
// administrativos tomen sus medidas: los retardos no cambian la nomina. La regla
// vive en el backend (services/attendance_rules.py).
//
// El supervisor del empleado o RH corrigen aqui una checada o agregan la que
// falta, con motivo. Un dia con una sola checada queda pendiente de justificar
// (no se paga). Hay un limite de correcciones por mes; despues solo RH, como
// excepcion (services/attendance_correction_service.py). El contador solo lo ve
// quien puede corregir: al empleado el backend no se lo da.

function fechaLocal(d) {
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export default function IncidenciasAsistencia({ t, describirError }) {
  const hoy = new Date();
  const [periodo, setPeriodo] = useState({ startDate: fechaLocal(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), endDate: fechaLocal(hoy) });
  const [empleados, setEmpleados] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [abierto, setAbierto] = useState(null);
  const [contador, setContador] = useState(null);
  const [correccion, setCorreccion] = useState(null);
  const [aviso, setAviso] = useState("");
  const mes = periodo.startDate.slice(0, 7);

  async function cargarContador(idUser) {
    try {
      setContador(await getAttendanceCorrections(idUser, mes));
    } catch {
      setContador(null);   // no es su supervisor ni RH: no corrige ni ve el contador
    }
  }

  function abrir(idUser) {
    setCorreccion(null);
    setAviso("");
    if (abierto === idUser) { setAbierto(null); return; }
    setAbierto(idUser);
    setContador(null);
    cargarContador(idUser);
  }

  async function recargar() {
    const data = await getAttendanceIncidences(periodo);
    setEmpleados(data.employees || []);
  }

  async function guardarCorreccion(event) {
    event.preventDefault();
    setError("");
    const c = correccion;
    const cuerpo = { new_time: `${c.date}T${c.time}`, reason: c.reason,
      ...(c.id_attendance_record ? { id_attendance_record: Number(c.id_attendance_record) } : { id_user: c.id_user }) };
    try {
      const hecha = await createAttendanceCorrection(cuerpo);
      setCorreccion(null);
      setAviso(hecha.is_exception ? t("kronos.corrections.saved_exception") : t("kronos.corrections.saved"));
      await recargar();
      await cargarContador(c.id_user);
    } catch (e) {
      setError(describirError(e));
    }
  }

  async function generar(event) {
    event.preventDefault();
    setCargando(true);
    setError("");
    try {
      const data = await getAttendanceIncidences(periodo);
      setEmpleados(data.employees || []);
    } catch (e) {
      setError(describirError(e));
    } finally {
      setCargando(false);
    }
  }

  const etiquetasDelDia = (d) => [
    d.leave && t(`employee_leaves.type_${d.leave}`),
    d.checked_during_leave && t("kronos.incidences.checked_during_leave"),
    d.absence && t("kronos.incidences.absence"),
    d.late && `${t("kronos.incidences.late")} (${d.late_minutes} min)`,
    d.pending_justification ? t("kronos.corrections.pending") : d.incomplete && t("kronos.incidences.incomplete"),
    d.worked_on_rest_day && t("kronos.incidences.rest_day_worked"),
    d.holiday && t("kronos.incidences.holiday"),
  ].filter(Boolean);

  return (
    <>
      <form className="form-card kronos-filter" onSubmit={generar}>
        <label className="field">{t("kronos.filter.from")}<input required type="date" value={periodo.startDate} onChange={(e) => setPeriodo((p) => ({ ...p, startDate: e.target.value }))} /></label>
        <label className="field">{t("kronos.filter.to")}<input required type="date" value={periodo.endDate} onChange={(e) => setPeriodo((p) => ({ ...p, endDate: e.target.value }))} /></label>
        <div className="kronos-filter-actions">
          <button type="submit" className="button" disabled={cargando}><RefreshCw size={16} /> {t("kronos.filter.generate")}</button>
        </div>
      </form>
      <p className="muted">{t("kronos.incidences.hint")}</p>
      {error && <div className="alert error" role="alert">{error}</div>}
      {empleados && (
        <section className="table-card kronos-table-card">
          <div className="kronos-table-heading">
            <div><p className="eyebrow">{t("kronos.incidences.eyebrow")}</p><h3>{t("kronos.incidences.title")}</h3></div>
          </div>
          <div className="kronos-table-scroll">
            <table>
              <thead><tr>
                <th>{t("kronos.incidences.employee")}</th><th>{t("kronos.incidences.workdays")}</th><th>{t("kronos.incidences.attended")}</th>
                <th>{t("kronos.incidences.absences")}</th><th>{t("kronos.incidences.lates")}</th><th>{t("kronos.incidences.late_minutes")}</th>
                <th>{t("kronos.incidences.incompletes")}</th><th>{t("kronos.incidences.vacation")}</th>
                <th>{t("kronos.incidences.leave")}</th><th>{t("kronos.incidences.disability")}</th><th>{t("kronos.incidences.paid_days")}</th>
              </tr></thead>
              <tbody>
                {empleados.length ? empleados.map((e) => (
                  <Fragment key={e.id_user}>
                    <tr onClick={() => abrir(e.id_user)} style={{ cursor: "pointer" }}>
                      <td><strong>{e.full_name}</strong>{!e.has_schedule && <small>{t("kronos.incidences.no_schedule")}</small>}</td>
                      <td>{e.workdays}</td><td>{e.attended}</td>
                      <td>{e.absences ? <strong>{e.absences}</strong> : 0}</td>
                      <td>{e.late}</td><td>{e.late_minutes}</td><td>{e.incomplete}</td>
                      <td>{e.vacation_days || 0}</td><td>{(e.paid_leave_days || 0) + (e.unpaid_leave_days || 0)}</td><td>{e.disability_days || 0}</td>
                      <td>{e.paid_days}</td>
                    </tr>
                    {abierto === e.id_user && (
                      <tr>
                        <td colSpan="11">
                          {contador && (
                            <p className={contador.remaining !== 0 ? "muted" : "field-error"}>
                              {t("kronos.corrections.counter")} {contador.month}: {contador.used}{contador.limit ? ` / ${contador.limit}` : ` · ${t("kronos.corrections.no_limit")}`}
                              {contador.remaining === 0 && ` · ${t("kronos.corrections.limit_reached")}`}
                            </p>
                          )}
                          {aviso && <div className="alert success" role="status">{aviso}</div>}
                          {correccion && (
                            <form className="form-card" onSubmit={guardarCorreccion}>
                              <h3>{t("kronos.corrections.title")} · {correccion.date}</h3>
                              <div className="form-grid">
                                <label className="field">{t("kronos.corrections.which")}
                                  <select value={correccion.id_attendance_record} onChange={(ev) => setCorreccion((c) => ({ ...c, id_attendance_record: ev.target.value }))}>
                                    {correccion.checks.map((ch) => <option key={ch.id} value={ch.id}>{t("kronos.corrections.check_at")} {ch.time}</option>)}
                                    <option value="">{t("kronos.corrections.add_missing")}</option>
                                  </select>
                                </label>
                                <label className="field">{t("kronos.corrections.new_time")}
                                  <input required type="time" value={correccion.time} onChange={(ev) => setCorreccion((c) => ({ ...c, time: ev.target.value }))} />
                                </label>
                                <label className="field">{t("kronos.corrections.reason")}
                                  <input required maxLength={300} value={correccion.reason} onChange={(ev) => setCorreccion((c) => ({ ...c, reason: ev.target.value }))} />
                                </label>
                              </div>
                              <p className="muted">{t("kronos.corrections.hint")}</p>
                              <div className="form-actions">
                                <button className="button primary" type="submit">{t("common.save")}</button>
                                <button className="button" type="button" onClick={() => setCorreccion(null)}>{t("common.cancel")}</button>
                              </div>
                            </form>
                          )}
                          <table>
                            <thead><tr><th>{t("kronos.csv.headers.date")}</th><th>{t("kronos.incidences.schedule")}</th><th>{t("kronos.csv.headers.first")}</th><th>{t("kronos.csv.headers.last")}</th><th>{t("kronos.incidences.what")}</th>{contador && <th>{t("common.actions")}</th>}</tr></thead>
                            <tbody>{e.days.filter((d) => etiquetasDelDia(d).length).map((d) => (
                              <tr key={d.date}>
                                <td>{d.date}</td>
                                <td>{d.start ? `${d.start}–${d.end}` : "—"}</td>
                                <td>{d.first || "—"}</td><td>{d.last || "—"}</td>
                                <td>{etiquetasDelDia(d).join(" · ")}</td>
                                {contador && (
                                  <td className="row-actions">
                                    <button type="button" title={t("kronos.corrections.title")} aria-label={`${t("kronos.corrections.title")} ${d.date}`}
                                      onClick={() => setCorreccion({ id_user: e.id_user, date: d.date, checks: d.checks || [],
                                        id_attendance_record: d.checks?.length ? String(d.checks[0].id) : "",
                                        time: d.checks?.[0]?.time || d.start || "09:00", reason: "" })}><Pencil size={15} /></button>
                                  </td>
                                )}
                              </tr>
                            ))}</tbody>
                          </table>
                          {contador?.corrections?.length > 0 && (
                            <table>
                              <thead><tr><th>{t("kronos.csv.headers.date")}</th><th>{t("kronos.corrections.before")}</th><th>{t("kronos.corrections.after")}</th><th>{t("kronos.corrections.reason")}</th><th>{t("kronos.corrections.by")}</th></tr></thead>
                              <tbody>{contador.corrections.map((c) => (
                                <tr key={c.id_attendance_correction}>
                                  <td>{c.check_date}</td>
                                  <td>{c.previous_time ? c.previous_time.slice(11, 16) : t("kronos.corrections.added")}</td>
                                  <td>{c.new_time.slice(11, 16)}</td>
                                  <td><small>{c.reason}</small></td>
                                  <td><small>{c.created_by_name}{c.is_exception && ` · ${t("kronos.corrections.exception")}`}</small></td>
                                </tr>
                              ))}</tbody>
                            </table>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )) : <tr><td colSpan="11" className="kronos-empty">{t("kronos.incidences.empty")}</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

IncidenciasAsistencia.propTypes = {
  t: PropTypes.func.isRequired,
  describirError: PropTypes.func.isRequired,
};
