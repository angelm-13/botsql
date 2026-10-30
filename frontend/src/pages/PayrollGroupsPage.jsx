import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import {
  createEmployeePayrollGroup, createEmployeeSalary, createPayrollGroup, deleteEmployeePayrollGroup, deleteEmployeeSalary,
  deletePayrollGroup, getAllEmployeePayrollGroup, getAllEmployeeSalary, getAllPayrollGroup, getAttendanceEmployeeOptions,
  getMyPermissions, updateEmployeePayrollGroup, updateEmployeeSalary, updatePayrollGroup,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import { useDialogo } from "../dialogo/useDialogo.js";
import "../styles/kronos.css";

// Grupos de pago: cada grupo cobra semanal, catorcenal, quincenal o mensual, y
// cada empleado pertenece a uno con vigencia. El periodo de nomina de un grupo
// calcula solo a sus empleados con la tarifa de su periodicidad; quien no tiene
// grupo asignado cae en el grupo por omision. Las reglas las valida el backend
// (services/payroll_group_service.py).
//
// Pestaña "Sueldos": como gana cada empleado -por dia, por hora o fijo por
// semana/catorcena/quincena/mes-, con vigencia (historial de aumentos). Quien no
// tiene forma capturada sigue con su salario diario (services/salary_service.py).

const PERIODICIDADES = ["weekly", "biweekly", "semimonthly", "monthly"];
const FORMAS = ["daily", "hourly", "fixed"];

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

export default function PayrollGroupsPage() {
  const { t } = useI18n();
  const dialogo = useDialogo();
  const traducir = useRef(t);
  traducir.current = t;
  const [view, setView] = useState("groups");
  const [grupos, setGrupos] = useState([]);
  const [asignaciones, setAsignaciones] = useState([]);
  const [empleados, setEmpleados] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [formGrupo, setFormGrupo] = useState(null);
  const [formAsignacion, setFormAsignacion] = useState(null);
  const [sueldos, setSueldos] = useState([]);
  const [formSueldo, setFormSueldo] = useState(null);

  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
  const puede = (entidad, campo) => privilegiado || Number(permisos.find((p) => p.entity_name === entidad)?.[campo] || 0) !== 0;

  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    return clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
  }, []);

  // Recargar no borra el aviso de error: se llama justo despues de un guardado
  // que fallo, y si lo borrara el usuario nunca veria por que no se guardo.
  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const vivos = (r) => (r?.items || []).filter((x) => !x.deletion_date);
      const [g, a, s] = await Promise.all([getAllPayrollGroup({ per_page: 1000 }), getAllEmployeePayrollGroup({ per_page: 5000 }),
        getAllEmployeeSalary({ per_page: 5000 }).catch(() => ({ items: [] }))]);
      setGrupos(vivos(g)); setAsignaciones(vivos(a)); setSueldos(vivos(s));
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

  const fechaHoy = hoy();
  const vigente = (a) => a.valid_from <= fechaHoy && (!a.valid_to || a.valid_to >= fechaHoy);
  const nombreGrupo = (id) => grupos.find((g) => g.id_payroll_group === id)?.group_name || `#${id}`;
  const nombreEmpleado = (id) => empleados.find((e) => e.id_user === id)?.full_name || `#${id}`;
  // Cuantos empleados cobran hoy en cada grupo: los asignados, y en el de por
  // omision tambien los que no tienen grupo.
  const conGrupoHoy = new Set(asignaciones.filter(vigente).map((a) => a.id_user));
  const cuantos = (g) => asignaciones.filter((a) => vigente(a) && a.id_payroll_group === g.id_payroll_group).length
    + (g.is_default ? empleados.filter((e) => !conGrupoHoy.has(e.id_user)).length : 0);

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

  async function guardarGrupo(event) {
    event.preventDefault();
    const { id_payroll_group: id, group_name, pay_frequency, is_default } = formGrupo;
    const cuerpo = { group_name, pay_frequency, is_default: Boolean(is_default) };
    const ok = await guardar(() => (id ? updatePayrollGroup(id, cuerpo) : createPayrollGroup(cuerpo)), "payroll_groups.saved");
    if (ok) setFormGrupo(null);
  }

  async function guardarAsignacion(event) {
    event.preventDefault();
    const { id_employee_payroll_group: id, ...datos } = formAsignacion;
    const cuerpo = { id_user: Number(datos.id_user), id_payroll_group: Number(datos.id_payroll_group), valid_from: datos.valid_from, valid_to: datos.valid_to || null };
    const ok = await guardar(() => (id ? updateEmployeePayrollGroup(id, cuerpo) : createEmployeePayrollGroup(cuerpo)), "payroll_groups.saved");
    if (ok) setFormAsignacion(null);
  }

  async function guardarSueldo(event) {
    event.preventDefault();
    const { id_employee_salary: id, ...datos } = formSueldo;
    const cuerpo = { id_user: Number(datos.id_user), salary_type: datos.salary_type, amount: Number(datos.amount),
      fixed_frequency: datos.salary_type === "fixed" ? datos.fixed_frequency : null, valid_from: datos.valid_from, valid_to: datos.valid_to || null };
    const ok = await guardar(() => (id ? updateEmployeeSalary(id, cuerpo) : createEmployeeSalary(cuerpo)), "payroll_groups.saved");
    if (ok) setFormSueldo(null);
  }

  const money = (v) => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(v || 0));
  const comoGana = (s) => s.salary_type === "fixed"
    ? `${money(s.amount)} ${t(`salaries.per_${s.fixed_frequency}`)}`
    : `${money(s.amount)} ${t(`salaries.per_${s.salary_type}`)}`;

  async function borrar(accion) {
    if (!(await dialogo.confirmar(t("payroll_groups.confirm_delete")))) return;
    await guardar(accion, "payroll_groups.deleted");
  }

  const pestana = (clave) => (
    <button type="button" role="tab" aria-selected={view === clave} className={view === clave ? "active" : ""} onClick={() => setView(clave)}>{t(`payroll_groups.tab_${clave}`)}</button>
  );
  const campo = (form, set, nombre, props = {}) => (
    <input {...props} value={form[nombre] ?? ""} onChange={(e) => set((f) => ({ ...f, [nombre]: e.target.value }))} />
  );

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("payroll_groups.eyebrow")} titulo={t("payroll_groups.title")} subtitulo={t("payroll_groups.subtitle")}>
        <button className="button ghost" onClick={() => { setError(""); cargar(); }} disabled={loading}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>
      <div className="kronos-tabs" role="tablist">{pestana("groups")}{pestana("assignments")}{pestana("salaries")}</div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {view === "groups" && (
        <>
          {formGrupo && (
            <form className="form-card" onSubmit={guardarGrupo}>
              <h3>{formGrupo.id_payroll_group ? t("common.edit") : t("payroll_groups.new_group")}</h3>
              <div className="form-grid">
                <label className="field">{t("payroll_groups.name")}{campo(formGrupo, setFormGrupo, "group_name", { required: true, maxLength: 120 })}</label>
                <label className="field">{t("payroll_groups.frequency")}
                  <select required value={formGrupo.pay_frequency} onChange={(e) => setFormGrupo((f) => ({ ...f, pay_frequency: e.target.value }))}>
                    {PERIODICIDADES.map((p) => <option key={p} value={p}>{t(`payroll_groups.frequency_${p}`)}</option>)}
                  </select>
                </label>
                <label className="field checkbox-field">
                  <input type="checkbox" checked={Boolean(formGrupo.is_default)} disabled={formGrupo.era_por_omision}
                    onChange={(e) => setFormGrupo((f) => ({ ...f, is_default: e.target.checked }))} />
                  {t("payroll_groups.is_default")}
                </label>
              </div>
              <p className="muted">{t("payroll_groups.default_hint")}</p>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormGrupo(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("payroll_groups.tab_groups")}</p><h3>{t("payroll_groups.groups_title")}</h3></div>
              {puede("payroll_group", "scope_create") && <button className="button" type="button" onClick={() => setFormGrupo({ group_name: "", pay_frequency: "weekly", is_default: false })}><Plus size={16} /> {t("payroll_groups.new_group")}</button>}
            </div>
            <table>
              <thead><tr><th>{t("payroll_groups.name")}</th><th>{t("payroll_groups.frequency")}</th><th>{t("payroll_groups.employees")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{grupos.length ? grupos.map((g) => (
                <tr key={g.id_payroll_group}>
                  <td><strong>{g.group_name}</strong>{g.is_default && <> <span className="quotation-status-badge status-approved">{t("payroll_groups.default_badge")}</span></>}</td>
                  <td>{t(`payroll_groups.frequency_${g.pay_frequency}`)}</td>
                  <td>{cuantos(g)}</td>
                  <td className="row-actions">
                    {puede("payroll_group", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => setFormGrupo({ ...g, era_por_omision: g.is_default })}><Pencil size={15} /></button>}
                    {puede("payroll_group", "scope_delete") && !g.is_default && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deletePayrollGroup(g.id_payroll_group))}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              )) : <tr><td colSpan="4" className="kronos-empty">{t("payroll_groups.no_groups")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}

      {view === "assignments" && (
        <>
          {formAsignacion && (
            <form className="form-card" onSubmit={guardarAsignacion}>
              <h3>{formAsignacion.id_employee_payroll_group ? t("common.edit") : t("payroll_groups.new_assignment")}</h3>
              <div className="form-grid">
                <label className="field">{t("payroll_groups.employee")}
                  <select required value={formAsignacion.id_user} onChange={(e) => setFormAsignacion((f) => ({ ...f, id_user: e.target.value }))}>
                    <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                    {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
                  </select>
                </label>
                <label className="field">{t("payroll_groups.group")}
                  <select required value={formAsignacion.id_payroll_group} onChange={(e) => setFormAsignacion((f) => ({ ...f, id_payroll_group: e.target.value }))}>
                    <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                    {grupos.map((g) => <option key={g.id_payroll_group} value={g.id_payroll_group}>{g.group_name} · {t(`payroll_groups.frequency_${g.pay_frequency}`)}</option>)}
                  </select>
                </label>
                <label className="field">{t("payroll_groups.from")}{campo(formAsignacion, setFormAsignacion, "valid_from", { required: true, type: "date" })}</label>
                <label className="field">{t("payroll_groups.to")}{campo(formAsignacion, setFormAsignacion, "valid_to", { type: "date" })}</label>
              </div>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormAsignacion(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("payroll_groups.tab_assignments")}</p><h3>{t("payroll_groups.assignments_title")}</h3></div>
              {puede("employee_payroll_group", "scope_create") && <button className="button" type="button" onClick={() => setFormAsignacion({ id_user: "", id_payroll_group: "", valid_from: fechaHoy, valid_to: "" })}><Plus size={16} /> {t("payroll_groups.new_assignment")}</button>}
            </div>
            <p className="muted">{t("payroll_groups.assignments_hint")}</p>
            <table>
              <thead><tr><th>{t("payroll_groups.employee")}</th><th>{t("payroll_groups.group")}</th><th>{t("payroll_groups.from")}</th><th>{t("payroll_groups.to")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{asignaciones.length ? [...asignaciones].sort((a, b) => nombreEmpleado(a.id_user).localeCompare(nombreEmpleado(b.id_user)) || a.valid_from.localeCompare(b.valid_from)).map((a) => (
                <tr key={a.id_employee_payroll_group}>
                  <td><strong>{nombreEmpleado(a.id_user)}</strong></td>
                  <td>{nombreGrupo(a.id_payroll_group)}</td>
                  <td>{a.valid_from}</td>
                  <td>{a.valid_to || t("payroll_groups.no_end")}</td>
                  <td className="row-actions">
                    {puede("employee_payroll_group", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => setFormAsignacion({ ...a, valid_to: a.valid_to || "" })}><Pencil size={15} /></button>}
                    {puede("employee_payroll_group", "scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deleteEmployeePayrollGroup(a.id_employee_payroll_group))}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              )) : <tr><td colSpan="5" className="kronos-empty">{t("payroll_groups.no_assignments")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}

      {view === "salaries" && (
        <>
          {formSueldo && (
            <form className="form-card" onSubmit={guardarSueldo}>
              <h3>{formSueldo.id_employee_salary ? t("common.edit") : t("salaries.new")}</h3>
              <div className="form-grid">
                <label className="field">{t("payroll_groups.employee")}
                  <select required value={formSueldo.id_user} onChange={(e) => setFormSueldo((f) => ({ ...f, id_user: e.target.value }))}>
                    <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                    {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
                  </select>
                </label>
                <label className="field">{t("salaries.type")}
                  <select required value={formSueldo.salary_type} onChange={(e) => setFormSueldo((f) => ({ ...f, salary_type: e.target.value }))}>
                    {FORMAS.map((f) => <option key={f} value={f}>{t(`salaries.type_${f}`)}</option>)}
                  </select>
                </label>
                <label className="field">{t(`salaries.amount_${formSueldo.salary_type}`)}{campo(formSueldo, setFormSueldo, "amount", { required: true, type: "number", min: 0.01, step: "0.01" })}</label>
                {formSueldo.salary_type === "fixed" && (
                  <label className="field">{t("salaries.frequency")}
                    <select required value={formSueldo.fixed_frequency} onChange={(e) => setFormSueldo((f) => ({ ...f, fixed_frequency: e.target.value }))}>
                      {PERIODICIDADES.map((p) => <option key={p} value={p}>{t(`payroll_groups.frequency_${p}`)}</option>)}
                    </select>
                  </label>
                )}
                <label className="field">{t("payroll_groups.from")}{campo(formSueldo, setFormSueldo, "valid_from", { required: true, type: "date" })}</label>
                <label className="field">{t("payroll_groups.to")}{campo(formSueldo, setFormSueldo, "valid_to", { type: "date" })}</label>
              </div>
              <p className="muted">{t(`salaries.hint_${formSueldo.salary_type}`)}</p>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormSueldo(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("payroll_groups.tab_salaries")}</p><h3>{t("salaries.title")}</h3></div>
              {puede("employee_salary", "scope_create") && <button className="button" type="button" onClick={() => setFormSueldo({ id_user: "", salary_type: "daily", amount: "", fixed_frequency: "semimonthly", valid_from: fechaHoy, valid_to: "" })}><Plus size={16} /> {t("salaries.new")}</button>}
            </div>
            <p className="muted">{t("salaries.list_hint")}</p>
            <table>
              <thead><tr><th>{t("payroll_groups.employee")}</th><th>{t("salaries.type")}</th><th>{t("salaries.how")}</th><th>{t("payroll_groups.from")}</th><th>{t("payroll_groups.to")}</th><th>{t("common.actions")}</th></tr></thead>
              <tbody>{sueldos.length ? [...sueldos].sort((a, b) => nombreEmpleado(a.id_user).localeCompare(nombreEmpleado(b.id_user)) || a.valid_from.localeCompare(b.valid_from)).map((s) => (
                <tr key={s.id_employee_salary}>
                  <td><strong>{nombreEmpleado(s.id_user)}</strong></td>
                  <td>{t(`salaries.type_${s.salary_type}`)}</td>
                  <td>{comoGana(s)}</td>
                  <td>{s.valid_from}</td>
                  <td>{s.valid_to || t("payroll_groups.no_end")}</td>
                  <td className="row-actions">
                    {puede("employee_salary", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => setFormSueldo({ ...s, fixed_frequency: s.fixed_frequency || "semimonthly", valid_to: s.valid_to || "" })}><Pencil size={15} /></button>}
                    {puede("employee_salary", "scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deleteEmployeeSalary(s.id_employee_salary))}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              )) : <tr><td colSpan="6" className="kronos-empty">{t("salaries.empty")}</td></tr>}</tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
