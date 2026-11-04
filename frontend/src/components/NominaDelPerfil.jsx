import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  changeEmployeePayrollGroup, changeEmployeeSalary, changeEmployeeSchedule, getAllEmployeePayrollGroup,
  getAllEmployeeSalary, getAllEmployeeSchedule, getAllPayrollGroup, getAllWorkSchedule, getMyPermissions,
} from "../api";
import { useI18n } from "../i18n";

// "Nomina y asistencia" dentro del perfil del usuario (pantalla Usuario): asignar
// horario, grupo de pago y forma de salario sin ir a otras pantallas. Muestra lo
// vigente hoy y, si RH lo cambia, lo guarda "a partir de" la fecha elegida: el
// backend cierra lo anterior el dia antes (services/vigencias.py). Cada renglon
// lo decide el Gestor: se ve con el permiso de lectura de su entidad y se edita
// con alta y actualizacion. Los catalogos y el historial siguen en "Horarios" y
// "Grupos de pago".

const FORMAS = ["daily", "hourly", "fixed"];
const PERIODICIDADES = ["weekly", "biweekly", "semimonthly", "monthly"];

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function ordenadas(filas) {
  return (filas || []).filter((f) => !f.deletion_date).sort((a, b) => String(a.valid_from).localeCompare(String(b.valid_from)));
}

// La asignacion vigente hoy; si no hay, la proxima que ya esta capturada.
function vigente(filas, fecha) {
  const vivas = ordenadas(filas);
  return vivas.find((f) => f.valid_from <= fecha && (!f.valid_to || f.valid_to >= fecha))
    || vivas.find((f) => f.valid_from > fecha) || null;
}

// Un cambio ya programado despues de la vigente (ej. un aumento desde el dia 16).
function siguiente(filas, actual) {
  return actual ? ordenadas(filas).find((f) => f.valid_from > actual.valid_from) || null : null;
}

const NominaDelPerfil = forwardRef(function NominaDelPerfil({ idUser }, ref) {
  const { lang, t } = useI18n();
  const fecha = useMemo(hoy, []);
  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin);
  const [permisos, setPermisos] = useState([]);
  const [horarios, setHorarios] = useState([]);
  const [grupos, setGrupos] = useState([]);
  const [actual, setActual] = useState({ horario: null, grupo: null, sueldo: null });
  const [programado, setProgramado] = useState({ horario: null, grupo: null, sueldo: null });
  const [borrador, setBorrador] = useState(null);

  const scope = (entidad, campo) => privilegiado
    || Number(permisos.find((p) => p.entity_name === entidad)?.[campo] || 0) !== 0;
  const ve = (entidad) => scope(entidad, "scope_read");
  const edita = (entidad) => scope(entidad, "scope_create") && scope(entidad, "scope_update");
  const money = (v) => new Intl.NumberFormat(lang === "es" ? "es-MX" : lang, { style: "currency", currency: "MXN" }).format(Number(v || 0));

  useEffect(() => {
    getMyPermissions().then((p) => setPermisos(p?.entity_permissions || [])).catch(() => setPermisos([]));
    getAllWorkSchedule({ per_page: 1000 }).then((r) => setHorarios((r?.items || []).filter((x) => !x.deletion_date))).catch(() => setHorarios([]));
    getAllPayrollGroup({ per_page: 1000 }).then((r) => setGrupos((r?.items || []).filter((x) => !x.deletion_date))).catch(() => setGrupos([]));
  }, []);

  const cargar = useCallback(async () => {
    const filtro = { id_user: idUser, per_page: 200 };
    const [h, g, s] = idUser
      ? await Promise.all([
        getAllEmployeeSchedule(filtro).catch(() => null),
        getAllEmployeePayrollGroup(filtro).catch(() => null),
        getAllEmployeeSalary(filtro).catch(() => null),
      ])
      : [null, null, null];
    const ahora = { horario: vigente(h?.items, fecha), grupo: vigente(g?.items, fecha), sueldo: vigente(s?.items, fecha) };
    setActual(ahora);
    setProgramado({ horario: siguiente(h?.items, ahora.horario), grupo: siguiente(g?.items, ahora.grupo),
      sueldo: siguiente(s?.items, ahora.sueldo) });
    setBorrador({
      horario: { id_work_schedule: ahora.horario?.id_work_schedule ?? "", valid_from: fecha },
      grupo: { id_payroll_group: ahora.grupo?.id_payroll_group ?? "", valid_from: fecha },
      sueldo: {
        salary_type: ahora.sueldo?.salary_type ?? "daily", amount: ahora.sueldo?.amount ?? "",
        fixed_frequency: ahora.sueldo?.fixed_frequency ?? "semimonthly", valid_from: fecha,
      },
    });
  }, [idUser, fecha]);

  useEffect(() => { cargar(); }, [cargar]);

  // Que renglones cambiaron respecto a lo vigente (solo esos se guardan).
  function cambios() {
    if (!borrador) return [];
    const lista = [];
    const { horario, grupo, sueldo } = borrador;
    if (ve("employee_schedule") && edita("employee_schedule") && horario.id_work_schedule
        && String(horario.id_work_schedule) !== String(actual.horario?.id_work_schedule ?? "")) {
      lista.push((id) => changeEmployeeSchedule({ id_user: id, id_work_schedule: Number(horario.id_work_schedule), valid_from: horario.valid_from }));
    }
    if (ve("employee_payroll_group") && edita("employee_payroll_group") && grupo.id_payroll_group
        && String(grupo.id_payroll_group) !== String(actual.grupo?.id_payroll_group ?? "")) {
      lista.push((id) => changeEmployeePayrollGroup({ id_user: id, id_payroll_group: Number(grupo.id_payroll_group), valid_from: grupo.valid_from }));
    }
    const fijo = sueldo.salary_type === "fixed";
    const otroSueldo = !actual.sueldo || sueldo.salary_type !== actual.sueldo.salary_type
      || Number(sueldo.amount) !== Number(actual.sueldo.amount)
      || (fijo && sueldo.fixed_frequency !== actual.sueldo.fixed_frequency);
    if (ve("employee_salary") && edita("employee_salary") && sueldo.amount !== "" && otroSueldo) {
      lista.push((id) => changeEmployeeSalary({
        id_user: id, salary_type: sueldo.salary_type, amount: sueldo.amount,
        fixed_frequency: fijo ? sueldo.fixed_frequency : null, valid_from: sueldo.valid_from,
      }));
    }
    return lista;
  }

  // La pantalla Usuario llama esto despues de guardar al usuario.
  useImperativeHandle(ref, () => ({
    async guardar(id) {
      for (const paso of cambios()) await paso(id);
    },
  }));

  const visibles = ["employee_schedule", "employee_payroll_group", "employee_salary"].filter(ve);
  if (!borrador || visibles.length === 0) return null;

  const poner = (bloque, campo) => (e) => setBorrador((b) => ({ ...b, [bloque]: { ...b[bloque], [campo]: e.target.value } }));
  const desde = (bloque, entidad) => (
    <label className="field">
      <span>{t("user_payroll.from")}</span>
      <input type="date" value={borrador[bloque].valid_from} onChange={poner(bloque, "valid_from")} disabled={!edita(entidad)} />
    </label>
  );
  const desdeCuando = (fila) => (fila && fila.valid_from > fecha ? ` (${t("user_payroll.starts")} ${fila.valid_from})` : "");
  const textoHorario = (fila) => fila && `${horarios.find((h) => String(h.id_work_schedule) === String(fila.id_work_schedule))?.schedule_name || `#${fila.id_work_schedule}`}`;
  const textoGrupo = (fila) => {
    const g = fila && grupos.find((x) => String(x.id_payroll_group) === String(fila.id_payroll_group));
    return g ? `${g.group_name} · ${t(`payroll_groups.frequency_${g.pay_frequency}`)}` : fila && `#${fila.id_payroll_group}`;
  };
  const textoSueldo = (fila) => fila && `${t(`salaries.type_${fila.salary_type}`)} · ${money(fila.amount)}${
    fila.salary_type === "fixed" ? ` · ${t(`payroll_groups.frequency_${fila.fixed_frequency}`)}` : ""}`;
  // "Hoy: ..." y, si ya hay un cambio capturado despues, "desde el 16: ...".
  const ahora = (bloque, texto) => (
    <small className="muted">
      {t("user_payroll.current")}: {texto(actual[bloque]) ? `${texto(actual[bloque])}${desdeCuando(actual[bloque])}` : t("user_payroll.none")}
      {programado[bloque] && ` · ${t("user_payroll.scheduled")} ${programado[bloque].valid_from}: ${texto(programado[bloque])}`}
    </small>
  );

  return (
    <div style={{ borderTop: "1px solid #e2e8f0", marginTop: 14, paddingTop: 14 }}>
      <h3 style={{ margin: "0 0 4px" }}>{t("user_payroll.title")}</h3>
      <p className="muted" style={{ margin: "0 0 12px" }}>{t("user_payroll.hint")}</p>
      <div className="form-grid">
        {ve("employee_schedule") && (<>
          <label className="field">
            <span>{t("user_payroll.schedule")}</span>
            <select value={borrador.horario.id_work_schedule} onChange={poner("horario", "id_work_schedule")} disabled={!edita("employee_schedule")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {horarios.map((h) => <option key={h.id_work_schedule} value={h.id_work_schedule}>{h.schedule_name}</option>)}
            </select>
            {ahora("horario", textoHorario)}
            <small className="muted">{t("user_payroll.schedule_hint")}</small>
          </label>
          {desde("horario", "employee_schedule")}
          <div />
        </>)}
        {ve("employee_payroll_group") && (<>
          <label className="field">
            <span>{t("user_payroll.group")}</span>
            <select value={borrador.grupo.id_payroll_group} onChange={poner("grupo", "id_payroll_group")} disabled={!edita("employee_payroll_group")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {grupos.map((g) => <option key={g.id_payroll_group} value={g.id_payroll_group}>{g.group_name} · {t(`payroll_groups.frequency_${g.pay_frequency}`)}</option>)}
            </select>
            {ahora("grupo", textoGrupo)}
            <small className="muted">{t("user_payroll.group_hint")}</small>
          </label>
          {desde("grupo", "employee_payroll_group")}
          <div />
        </>)}
        {ve("employee_salary") && (<>
          <label className="field">
            <span>{t("salaries.type")}</span>
            <select value={borrador.sueldo.salary_type} onChange={poner("sueldo", "salary_type")} disabled={!edita("employee_salary")}>
              {FORMAS.map((f) => <option key={f} value={f}>{t(`salaries.type_${f}`)}</option>)}
            </select>
            {ahora("sueldo", textoSueldo)}
          </label>
          <label className="field">
            <span>{t(`salaries.amount_${borrador.sueldo.salary_type}`)}</span>
            <input type="number" min="0.01" step="0.01" value={borrador.sueldo.amount} onChange={poner("sueldo", "amount")} disabled={!edita("employee_salary")} />
          </label>
          {borrador.sueldo.salary_type === "fixed" && (
            <label className="field">
              <span>{t("salaries.frequency")}</span>
              <select value={borrador.sueldo.fixed_frequency} onChange={poner("sueldo", "fixed_frequency")} disabled={!edita("employee_salary")}>
                {PERIODICIDADES.map((p) => <option key={p} value={p}>{t(`payroll_groups.frequency_${p}`)}</option>)}
              </select>
            </label>
          )}
          {desde("sueldo", "employee_salary")}
        </>)}
      </div>
    </div>
  );
});

NominaDelPerfil.propTypes = {
  idUser: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
};

export default NominaDelPerfil;
