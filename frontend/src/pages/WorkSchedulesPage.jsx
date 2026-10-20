import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import {
  createEmployeeSchedule, createPayrollHoliday, createWorkSchedule, createWorkScheduleDay,
  deleteEmployeeSchedule, deletePayrollHoliday, deleteWorkScheduleDay, getAllEmployeeSchedule,
  getAllPayrollHoliday, getAllWorkSchedule, getAllWorkScheduleDay, getAttendanceEmployeeOptions,
  getMyPermissions, updateEmployeeSchedule, updateWorkSchedule, updateWorkScheduleDay,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import "../styles/kronos.css";

// Horarios de trabajo, su asignacion a empleados y los dias festivos. Con ellos
// Asistencias detecta retardos y faltas, y la nomina paga los dias del periodo
// menos las faltas (services/attendance_rules.py). Las reglas -horas, que no se
// enciman las asignaciones, un festivo por fecha- las valida el backend.

const DIAS = [0, 1, 2, 3, 4, 5, 6];

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function horarioVacio() {
  return {
    schedule_name: "", tolerance_minutes: 10,
    dias: Object.fromEntries(DIAS.map((d) => [d, { on: d < 5, start_time: "09:00", end_time: "18:00" }])),
  };
}

export default function WorkSchedulesPage() {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [view, setView] = useState("schedules");
  const [horarios, setHorarios] = useState([]);
  const [dias, setDias] = useState([]);
  const [asignaciones, setAsignaciones] = useState([]);
  const [festivos, setFestivos] = useState([]);
  const [empleados, setEmpleados] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [formHorario, setFormHorario] = useState(null);
  const [formAsignacion, setFormAsignacion] = useState(null);
  const [formFestivo, setFormFestivo] = useState(null);

  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1" || actor.user_type === "admin");
  const puede = (entidad, campo) => privilegiado || Number(permisos.find((p) => p.entity_name === entidad)?.[campo] || 0) !== 0;

  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    return clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
  }, []);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const vivos = (r) => (r?.items || []).filter((x) => !x.deletion_date);
      const [h, d, a, f] = await Promise.all([
        getAllWorkSchedule({ per_page: 1000 }), getAllWorkScheduleDay({ per_page: 5000 }),
        getAllEmployeeSchedule({ per_page: 5000 }), getAllPayrollHoliday({ per_page: 1000 }),
      ]);
      setHorarios(vivos(h)); setDias(vivos(d)); setAsignaciones(vivos(a)); setFestivos(vivos(f));
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

  const diasDe = (idHorario) => dias.filter((d) => d.id_work_schedule === idHorario).sort((a, b) => a.weekday - b.weekday);
  const nombreHorario = (id) => horarios.find((h) => h.id_work_schedule === id)?.schedule_name || `#${id}`;
  const nombreEmpleado = (id) => empleados.find((e) => e.id_user === id)?.full_name || `#${id}`;
  const resumenDias = (idHorario) => diasDe(idHorario)
    .map((d) => `${t(`work_schedules.weekday_short_${d.weekday}`)} ${d.start_time}–${d.end_time}`).join(" · ") || t("work_schedules.no_days");

  async function guardar(accion, mensaje) {
    setError("");
    setNotice("");
    try {
      await accion();
      setNotice(t(mensaje));
      await cargar();
      return true;
    } catch (e) {
      setError(describirError(e));
      await cargar();
      return false;
    }
  }

  function editarHorario(h) {
    const actuales = Object.fromEntries(diasDe(h.id_work_schedule).map((d) => [d.weekday, d]));
    setFormHorario({
      id_work_schedule: h.id_work_schedule, schedule_name: h.schedule_name, tolerance_minutes: h.tolerance_minutes,
      dias: Object.fromEntries(DIAS.map((d) => [d, actuales[d]
        ? { on: true, start_time: actuales[d].start_time, end_time: actuales[d].end_time, id: actuales[d].id_work_schedule_day }
        : { on: false, start_time: "09:00", end_time: "18:00" }])),
    });
  }

  async function guardarHorario(event) {
    event.preventDefault();
    const f = formHorario;
    const ok = await guardar(async () => {
      const datos = { schedule_name: f.schedule_name, tolerance_minutes: Number(f.tolerance_minutes) };
      const horario = f.id_work_schedule ? await updateWorkSchedule(f.id_work_schedule, datos) : await createWorkSchedule(datos);
      const id = horario.id_work_schedule;
      // Se sincronizan los dias: los marcados se crean o actualizan, los desmarcados se quitan.
      for (const d of DIAS) {
        const dia = f.dias[d];
        if (dia.on && dia.id) await updateWorkScheduleDay(dia.id, { start_time: dia.start_time, end_time: dia.end_time });
        else if (dia.on) await createWorkScheduleDay({ id_work_schedule: id, weekday: d, start_time: dia.start_time, end_time: dia.end_time });
        else if (dia.id) await deleteWorkScheduleDay(dia.id);
      }
    }, "work_schedules.saved");
    if (ok) setFormHorario(null);
  }

  async function guardarAsignacion(event) {
    event.preventDefault();
    const { id_employee_schedule: id, ...datos } = formAsignacion;
    const cuerpo = { id_user: Number(datos.id_user), id_work_schedule: Number(datos.id_work_schedule), valid_from: datos.valid_from, valid_to: datos.valid_to || null };
    const ok = await guardar(() => (id ? updateEmployeeSchedule(id, cuerpo) : createEmployeeSchedule(cuerpo)), "work_schedules.saved");
    if (ok) setFormAsignacion(null);
  }

  async function guardarFestivo(event) {
    event.preventDefault();
    const ok = await guardar(() => createPayrollHoliday({ ...formFestivo, source: formFestivo.source || null }), "work_schedules.saved");
    if (ok) setFormFestivo(null);
  }

  async function borrar(accion) {
    if (!window.confirm(t("work_schedules.confirm_delete"))) return;
    await guardar(accion, "work_schedules.deleted");
  }

  const pestana = (clave) => (
    <button type="button" role="tab" aria-selected={view === clave} className={view === clave ? "active" : ""} onClick={() => setView(clave)}>{t(`work_schedules.tab_${clave}`)}</button>
  );
  const campo = (form, set, nombre, props = {}) => (
    <input {...props} value={form[nombre] ?? ""} onChange={(e) => set((f) => ({ ...f, [nombre]: e.target.value }))} />
  );
  const fechaHoy = hoy();

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("work_schedules.eyebrow")} titulo={t("work_schedules.title")} subtitulo={t("work_schedules.subtitle")}>
        <button className="button ghost" onClick={cargar} disabled={loading}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>
      <div className="kronos-tabs" role="tablist">{pestana("schedules")}{pestana("assignments")}{pestana("holidays")}</div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {view === "schedules" && (
        <>
          {formHorario && (
            <form className="form-card" onSubmit={guardarHorario}>
              <h3>{formHorario.id_work_schedule ? t("common.edit") : t("work_schedules.new_schedule")}</h3>
              <div className="form-grid">
                <label className="field">{t("work_schedules.name")}{campo(formHorario, setFormHorario, "schedule_name", { required: true, maxLength: 120 })}</label>
                <label className="field">{t("work_schedules.tolerance")}{campo(formHorario, setFormHorario, "tolerance_minutes", { required: true, type: "number", min: 0, max: 240 })}</label>
              </div>
              <table>
                <thead><tr><th>{t("work_schedules.day")}</th><th>{t("work_schedules.works")}</th><th>{t("work_schedules.start")}</th><th>{t("work_schedules.end")}</th></tr></thead>
                <tbody>{DIAS.map((d) => {
                  const dia = formHorario.dias[d];
                  const cambiar = (cambios) => setFormHorario((f) => ({ ...f, dias: { ...f.dias, [d]: { ...f.dias[d], ...cambios } } }));
                  return (
                    <tr key={d}>
                      <td>{t(`work_schedules.weekday_${d}`)}</td>
                      <td><input type="checkbox" aria-label={t(`work_schedules.weekday_${d}`)} checked={dia.on} onChange={(e) => cambiar({ on: e.target.checked })} /></td>
                      <td><input type="time" disabled={!dia.on} value={dia.start_time} onChange={(e) => cambiar({ start_time: e.target.value })} /></td>
                      <td><input type="time" disabled={!dia.on} value={dia.end_time} onChange={(e) => cambiar({ end_time: e.target.value })} /></td>
                    </tr>
                  );
                })}</tbody>
              </table>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormHorario(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("work_schedules.tab_schedules")}</p><h3>{t("work_schedules.schedules_title")}</h3></div>
              {puede("work_schedule", "scope_create") && <button className="button" type="button" onClick={() => setFormHorario(horarioVacio())}><Plus size={16} /> {t("work_schedules.new_schedule")}</button>}
            </div>
            <table>
              <thead><tr><th>{t("work_schedules.name")}</th><th>{t("work_schedules.days")}</th><th>{t("work_schedules.tolerance")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{horarios.length ? horarios.map((h) => (
                <tr key={h.id_work_schedule}>
                  <td><strong>{h.schedule_name}</strong></td>
                  <td><small>{resumenDias(h.id_work_schedule)}</small></td>
                  <td>{h.tolerance_minutes} min</td>
                  <td className="row-actions">{puede("work_schedule", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => editarHorario(h)}><Pencil size={15} /></button>}</td>
                </tr>
              )) : <tr><td colSpan="4" className="kronos-empty">{t("work_schedules.no_schedules")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}

      {view === "assignments" && (
        <>
          {formAsignacion && (
            <form className="form-card" onSubmit={guardarAsignacion}>
              <h3>{formAsignacion.id_employee_schedule ? t("common.edit") : t("work_schedules.new_assignment")}</h3>
              <div className="form-grid">
                <label className="field">{t("work_schedules.employee")}
                  <select required value={formAsignacion.id_user} onChange={(e) => setFormAsignacion((f) => ({ ...f, id_user: e.target.value }))}>
                    <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                    {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
                  </select>
                </label>
                <label className="field">{t("work_schedules.schedule")}
                  <select required value={formAsignacion.id_work_schedule} onChange={(e) => setFormAsignacion((f) => ({ ...f, id_work_schedule: e.target.value }))}>
                    <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                    {horarios.map((h) => <option key={h.id_work_schedule} value={h.id_work_schedule}>{h.schedule_name}</option>)}
                  </select>
                </label>
                <label className="field">{t("work_schedules.from")}{campo(formAsignacion, setFormAsignacion, "valid_from", { required: true, type: "date" })}</label>
                <label className="field">{t("work_schedules.to")}{campo(formAsignacion, setFormAsignacion, "valid_to", { type: "date" })}</label>
              </div>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormAsignacion(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("work_schedules.tab_assignments")}</p><h3>{t("work_schedules.assignments_title")}</h3></div>
              {puede("employee_schedule", "scope_create") && <button className="button" type="button" onClick={() => setFormAsignacion({ id_user: "", id_work_schedule: horarios[0]?.id_work_schedule || "", valid_from: fechaHoy, valid_to: "" })}><Plus size={16} /> {t("work_schedules.new_assignment")}</button>}
            </div>
            <table>
              <thead><tr><th>{t("work_schedules.employee")}</th><th>{t("work_schedules.schedule")}</th><th>{t("work_schedules.from")}</th><th>{t("work_schedules.to")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{asignaciones.length ? [...asignaciones].sort((a, b) => nombreEmpleado(a.id_user).localeCompare(nombreEmpleado(b.id_user))).map((a) => (
                <tr key={a.id_employee_schedule}>
                  <td><strong>{nombreEmpleado(a.id_user)}</strong></td>
                  <td>{nombreHorario(a.id_work_schedule)}</td>
                  <td>{a.valid_from}</td>
                  <td>{a.valid_to || t("work_schedules.no_end")}</td>
                  <td className="row-actions">
                    {puede("employee_schedule", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => setFormAsignacion({ ...a, valid_to: a.valid_to || "" })}><Pencil size={15} /></button>}
                    {puede("employee_schedule", "scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deleteEmployeeSchedule(a.id_employee_schedule))}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              )) : <tr><td colSpan="5" className="kronos-empty">{t("work_schedules.no_assignments")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}

      {view === "holidays" && (
        <>
          {formFestivo && (
            <form className="form-card" onSubmit={guardarFestivo}>
              <h3>{t("work_schedules.new_holiday")}</h3>
              <div className="form-grid">
                <label className="field">{t("work_schedules.date")}{campo(formFestivo, setFormFestivo, "holiday_date", { required: true, type: "date" })}</label>
                <label className="field">{t("work_schedules.description")}{campo(formFestivo, setFormFestivo, "description", { required: true, maxLength: 150 })}</label>
                <label className="field">{t("work_schedules.source")}{campo(formFestivo, setFormFestivo, "source", { maxLength: 200 })}</label>
              </div>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormFestivo(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("work_schedules.tab_holidays")}</p><h3>{t("work_schedules.holidays_title")}</h3></div>
              {puede("payroll_holiday", "scope_create") && <button className="button" type="button" onClick={() => setFormFestivo({ holiday_date: "", description: "", source: "Ley Federal del Trabajo, art. 74" })}><Plus size={16} /> {t("work_schedules.new_holiday")}</button>}
            </div>
            <table>
              <thead><tr><th>{t("work_schedules.date")}</th><th>{t("work_schedules.description")}</th><th>{t("work_schedules.source")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{festivos.length ? [...festivos].sort((a, b) => a.holiday_date.localeCompare(b.holiday_date)).map((f) => (
                <tr key={f.id_payroll_holiday}>
                  <td>{f.holiday_date}</td>
                  <td><strong>{f.description}</strong></td>
                  <td><small>{f.source || "—"}</small></td>
                  <td className="row-actions">{puede("payroll_holiday", "scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deletePayrollHoliday(f.id_payroll_holiday))}><Trash2 size={15} /></button>}</td>
                </tr>
              )) : <tr><td colSpan="4" className="kronos-empty">{t("work_schedules.no_holidays")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
