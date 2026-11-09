import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Calculator, FileDown, Gift, Plus, Send, Trash2 } from "lucide-react";
import {
  addPayrollSimulationBonuses, calculatePayrollSimulation, downloadPayrollSimulationPdf, getAttendanceEmployeeOptions,
  getMyPermissions, getPayrollSimulatorEmployee,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import "../styles/kronos.css";

// Simulador de nomina: RH escribe (o toma de un empleado real) el sueldo y lo que
// paso en el periodo, agrega bonos y premios, y ve el recibo que saldria, con las
// mismas reglas del calculo real (services/payroll_simulator_service.py). No
// guarda nada; solo "Agregar los bonos a su nomina" escribe en un periodo real.

const PERIODICIDADES = ["weekly", "biweekly", "semimonthly", "monthly"];
const FORMAS = ["daily", "hourly", "fixed"];
const SUGERENCIAS = ["halloween", "christmas", "birthday", "punctuality"];

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

const VACIO = {
  id_user: "", full_name: "", date: hoy(), pay_frequency: "semimonthly", salary_type: "daily", amount: "",
  fixed_frequency: "semimonthly", hire_date: "", day_hours: "8", absences: "0", overtime_double_hours: "0",
  overtime_triple_hours: "0", sundays_worked: "0", rest_days_worked: "0",
};

export default function PayrollSimulatorPage() {
  const { lang, t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [datos, setDatos] = useState(VACIO);
  const [bonos, setBonos] = useState([]);
  const [empleados, setEmpleados] = useState([]);
  const [periodos, setPeriodos] = useState([]);
  const [periodo, setPeriodo] = useState("");
  const [permisos, setPermisos] = useState([]);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [trabajando, setTrabajando] = useState(false);

  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin);
  const puedeMovimientos = privilegiado
    || Number(permisos.find((p) => p.entity_name === "payroll_movement")?.scope_create || 0) !== 0;
  const money = (v) => new Intl.NumberFormat(lang === "es" ? "es-MX" : lang, { style: "currency", currency: "MXN" }).format(Number(v || 0));

  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    const campo = e?.payload?.meta?.field;
    const texto = clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
    return campo ? `${texto} (${tr(`payroll_simulator.field_${String(campo).split(".")[0]}`, campo)})` : texto;
  }, []);

  useEffect(() => {
    getMyPermissions().then((p) => setPermisos(p?.entity_permissions || [])).catch(() => setPermisos([]));
    getAttendanceEmployeeOptions().then((r) => setEmpleados(r?.employees || [])).catch(() => setEmpleados([]));
  }, []);

  async function elegirEmpleado(id) {
    setResultado(null);
    setError("");
    setNotice("");
    if (!id) {
      setDatos((d) => ({ ...d, id_user: "", full_name: "" }));
      setPeriodos([]);
      return;
    }
    try {
      const e = await getPayrollSimulatorEmployee(id);
      setDatos((d) => ({
        ...d, id_user: String(e.id_user), full_name: e.full_name, salary_type: e.salary_type, amount: String(e.amount || ""),
        fixed_frequency: e.fixed_frequency || e.pay_frequency, pay_frequency: e.pay_frequency,
        hire_date: e.hire_date || "", day_hours: String(e.day_hours || 8),
      }));
      setPeriodos(e.open_periods || []);
      setPeriodo(e.open_periods?.[0]?.id_payroll_period ? String(e.open_periods[0].id_payroll_period) : "");
    } catch (err) {
      setError(describirError(err));
    }
  }

  const cuerpo = () => ({
    ...datos, hire_date: datos.hire_date || null,
    bonuses: bonos.filter((b) => b.name.trim() || b.amount).map((b) => ({ name: b.name.trim(), amount: b.amount })),
  });

  async function calcular(event) {
    event?.preventDefault();
    setError("");
    setNotice("");
    setTrabajando(true);
    try {
      setResultado(await calculatePayrollSimulation(cuerpo()));
    } catch (err) {
      setResultado(null);
      setError(describirError(err));
    } finally {
      setTrabajando(false);
    }
  }

  async function imprimir() {
    try {
      const blob = await downloadPayrollSimulationPdf(cuerpo());
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      setError(describirError(err));
    }
  }

  async function pasarBonos() {
    setError("");
    setNotice("");
    try {
      await addPayrollSimulationBonuses({ id_user: Number(datos.id_user), id_payroll_period: Number(periodo), bonuses: cuerpo().bonuses });
      setNotice(t("payroll_simulator.bonuses_added"));
    } catch (err) {
      setError(describirError(err));
    }
  }

  const poner = (campo) => (e) => setDatos((d) => ({ ...d, [campo]: e.target.value }));
  const campo = (nombre, props = {}) => <input {...props} value={datos[nombre]} onChange={poner(nombre)} />;
  const ponerBono = (i, campoBono) => (e) => setBonos((lista) => lista.map((b, j) => (j === i ? { ...b, [campoBono]: e.target.value } : b)));
  const hayBonos = bonos.some((b) => b.name.trim() && Number(b.amount) > 0);

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("payroll_simulator.eyebrow")} titulo={t("payroll_simulator.title")} subtitulo={t("payroll_simulator.subtitle")} />
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      <form className="form-card" onSubmit={calcular}>
        <h3>{t("payroll_simulator.base")}</h3>
        <div className="form-grid">
          <label className="field">{t("payroll_simulator.employee")}
            <select value={datos.id_user} onChange={(e) => elegirEmpleado(e.target.value)}>
              <option value="">{t("payroll_simulator.no_employee")}</option>
              {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
            </select>
          </label>
          <label className="field">{t("payroll_simulator.date")}{campo("date", { type: "date", required: true })}</label>
          <label className="field">{t("payroll_simulator.frequency")}
            <select value={datos.pay_frequency} onChange={poner("pay_frequency")}>
              {PERIODICIDADES.map((p) => <option key={p} value={p}>{t(`payroll_groups.frequency_${p}`)}</option>)}
            </select>
          </label>
          <label className="field">{t("salaries.type")}
            <select value={datos.salary_type} onChange={poner("salary_type")}>
              {FORMAS.map((f) => <option key={f} value={f}>{t(`salaries.type_${f}`)}</option>)}
            </select>
          </label>
          <label className="field">{t(`salaries.amount_${datos.salary_type}`)}{campo("amount", { type: "number", min: "0.01", step: "0.01", required: true })}</label>
          {datos.salary_type === "fixed" && (
            <label className="field">{t("salaries.frequency")}
              <select value={datos.fixed_frequency} onChange={poner("fixed_frequency")}>
                {PERIODICIDADES.map((p) => <option key={p} value={p}>{t(`payroll_groups.frequency_${p}`)}</option>)}
              </select>
            </label>
          )}
          <label className="field">{t("payroll_simulator.day_hours")}{campo("day_hours", { type: "number", min: "1", max: "24", step: "0.5" })}</label>
          <label className="field">{t("payroll_simulator.hire_date")}{campo("hire_date", { type: "date" })}</label>
        </div>

        <h3>{t("payroll_simulator.period")}</h3>
        <div className="form-grid">
          <label className="field">{t("payroll_simulator.absences")}{campo("absences", { type: "number", min: "0", step: "1" })}</label>
          <label className="field">{t("payroll_simulator.double_hours")}{campo("overtime_double_hours", { type: "number", min: "0", step: "0.5" })}</label>
          <label className="field">{t("payroll_simulator.triple_hours")}{campo("overtime_triple_hours", { type: "number", min: "0", step: "0.5" })}</label>
          <label className="field">{t("payroll_simulator.sundays")}{campo("sundays_worked", { type: "number", min: "0", max: "5", step: "1" })}</label>
          <label className="field">{t("payroll_simulator.rest_days")}{campo("rest_days_worked", { type: "number", min: "0", step: "1" })}</label>
        </div>

        <h3><Gift size={16} /> {t("payroll_simulator.bonuses")}</h3>
        <p className="muted">{t("payroll_simulator.bonuses_hint")}</p>
        {bonos.map((b, i) => (
          <div className="form-grid" key={i}>
            <label className="field">{t("payroll_simulator.bonus_name")}<input maxLength={120} value={b.name} onChange={ponerBono(i, "name")} /></label>
            <label className="field">{t("payroll_simulator.bonus_amount")}<input type="number" min="0" step="0.01" value={b.amount} onChange={ponerBono(i, "amount")} /></label>
            <div><button className="button ghost" type="button" style={{ width: "auto", marginTop: 24 }} title={t("common.delete")} onClick={() => setBonos((l) => l.filter((_, j) => j !== i))}><Trash2 size={15} /> {t("common.delete")}</button></div>
          </div>
        ))}
        <div className="kronos-actions">
          <button className="button" type="button" onClick={() => setBonos((l) => [...l, { name: "", amount: "" }])}><Plus size={16} /> {t("payroll_simulator.add_bonus")}</button>
          {SUGERENCIAS.map((s) => (
            <button key={s} className="button ghost" type="button" onClick={() => setBonos((l) => [...l, { name: t(`payroll_simulator.suggestion_${s}`), amount: "" }])}>
              + {t(`payroll_simulator.suggestion_${s}`)}
            </button>
          ))}
        </div>

        <div className="form-actions">
          <button className="button primary" type="submit" disabled={trabajando}><Calculator size={16} /> {t("payroll_simulator.calculate")}</button>
          <button className="button" type="button" onClick={() => { setDatos({ ...VACIO, date: hoy() }); setBonos([]); setResultado(null); setPeriodos([]); }}>{t("payroll_simulator.clear")}</button>
        </div>
      </form>

      {resultado && (
        <div className="table-card kronos-table-card">
          <div className="kronos-table-heading">
            <div><p className="eyebrow">{t("payroll_simulator.result")}</p>
              <h3>{datos.full_name || t("payroll_simulator.no_employee")} · {t(`payroll_groups.frequency_${resultado.pay_frequency}`)}</h3></div>
            <button className="button" type="button" onClick={imprimir}><FileDown size={16} /> PDF</button>
          </div>
          <div className="kronos-metrics">
            <div><span>{t("payroll_simulator.daily")}</span><strong>{money(resultado.daily_salary)}</strong></div>
            <div><span>{t("payroll_simulator.paid_days")}</span><strong>{resultado.paid_days}</strong></div>
            <div><span>{t("payroll_simulator.sbc")}</span><strong>{money(resultado.sbc)}</strong></div>
            <div><span>{t("payroll_simulator.net")}</span><strong>{money(resultado.net_pay)}</strong></div>
          </div>
          <table>
            <thead><tr><th>{t("payroll_simulator.concept")}</th><th>{t("payroll_simulator.amount")}</th></tr></thead>
            <tbody>
              {resultado.earnings.map((c, i) => <tr key={`p${i}`}><td>{c.code === "BONO" ? c.description : t(`payroll_simulator.code_${c.code}`, c.description)}</td><td>{money(c.amount)}</td></tr>)}
              {resultado.deductions.map((c) => <tr key={c.code}><td>− {t(`payroll_simulator.code_${c.code}`, c.description)}</td><td>− {money(c.amount)}</td></tr>)}
            </tbody>
            <tfoot><tr><td><strong>{t("payroll_simulator.net")}</strong></td><td><strong>{money(resultado.net_pay)}</strong></td></tr></tfoot>
          </table>
          <p className="muted" style={{ padding: "0 18px" }}>
            {t("payroll_simulator.taxable")}: {money(resultado.taxable_income)} · {t("payroll_simulator.isr_before")}: {money(resultado.isr_before_subsidy)} · {t("payroll_simulator.subsidy")}: {money(resultado.employment_subsidy)}
          </p>
          {datos.id_user && hayBonos && puedeMovimientos && (
            <div className="kronos-table-heading" style={{ borderTop: "1px solid #e2e8f0", borderBottom: 0 }}>
              <div><h3>{t("payroll_simulator.to_payroll")}</h3><p className="muted" style={{ margin: 0 }}>{t("payroll_simulator.to_payroll_hint")}</p></div>
              {periodos.length ? (
                <div className="kronos-actions">
                  <select value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
                    {periodos.map((p) => <option key={p.id_payroll_period} value={p.id_payroll_period}>{p.period_start} → {p.period_end}</option>)}
                  </select>
                  <button className="button primary" type="button" onClick={pasarBonos} disabled={!periodo}><Send size={16} /> {t("payroll_simulator.add_to_payroll")}</button>
                </div>
              ) : <span className="muted">{t("payroll_simulator.no_open_periods")}</span>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
