import { Fragment, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getAttendanceIncidences } from "../api";

// Pestaña "Incidencias" de Asistencias: retardos, faltas y checadas incompletas
// por empleado segun su horario. Es solo un reporte para que los
// administrativos tomen sus medidas: los retardos no cambian la nomina. La regla
// vive en el backend (services/attendance_rules.py).

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
    d.absence && t("kronos.incidences.absence"),
    d.late && `${t("kronos.incidences.late")} (${d.late_minutes} min)`,
    d.incomplete && t("kronos.incidences.incomplete"),
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
                <th>{t("kronos.incidences.incompletes")}</th><th>{t("kronos.incidences.paid_days")}</th>
              </tr></thead>
              <tbody>
                {empleados.length ? empleados.map((e) => (
                  <Fragment key={e.id_user}>
                    <tr onClick={() => setAbierto(abierto === e.id_user ? null : e.id_user)} style={{ cursor: "pointer" }}>
                      <td><strong>{e.full_name}</strong>{!e.has_schedule && <small>{t("kronos.incidences.no_schedule")}</small>}</td>
                      <td>{e.workdays}</td><td>{e.attended}</td>
                      <td>{e.absences ? <strong>{e.absences}</strong> : 0}</td>
                      <td>{e.late}</td><td>{e.late_minutes}</td><td>{e.incomplete}</td><td>{e.paid_days}</td>
                    </tr>
                    {abierto === e.id_user && (
                      <tr>
                        <td colSpan="8">
                          <table>
                            <thead><tr><th>{t("kronos.csv.headers.date")}</th><th>{t("kronos.incidences.schedule")}</th><th>{t("kronos.csv.headers.first")}</th><th>{t("kronos.csv.headers.last")}</th><th>{t("kronos.incidences.what")}</th></tr></thead>
                            <tbody>{e.days.filter((d) => etiquetasDelDia(d).length).map((d) => (
                              <tr key={d.date}>
                                <td>{d.date}</td>
                                <td>{d.start ? `${d.start}–${d.end}` : "—"}</td>
                                <td>{d.first || "—"}</td><td>{d.last || "—"}</td>
                                <td>{etiquetasDelDia(d).join(" · ")}</td>
                              </tr>
                            ))}</tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )) : <tr><td colSpan="8" className="kronos-empty">{t("kronos.incidences.empty")}</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
