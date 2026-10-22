import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import {
  createPayrollIsrBracket, createPayrollParameter, deletePayrollIsrBracket, deletePayrollParameter,
  getAllPayrollIsrBracket, getAllPayrollParameter, getMyPermissions, updatePayrollIsrBracket, updatePayrollParameter,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import "../styles/kronos.css";

// Cifras oficiales que usa el calculo de nomina (payroll_calculation_service.py):
// parametros con vigencia y la tarifa del ISR. Las reglas -que clave existe,
// rangos, vigencias que no se enciman- las valida el backend; aqui solo se
// muestran ordenadas y se capturan.

// Orden y unidad en que se muestran. Una clave que no este aqui igual se ve, al final.
const PARAMETROS = [
  ["uma_daily", "money"], ["uma_monthly", "money"], ["minimum_wage_daily", "money"],
  ["subsidy_pct", "pct"], ["subsidy_income_limit", "money"],
  ["imss_em_cash_pct", "pct"], ["imss_em_pensioners_pct", "pct"], ["imss_iv_pct", "pct"], ["imss_cv_pct", "pct"],
  ["imss_em_surplus_pct", "pct"], ["imss_surplus_umas", "uma"], ["sbc_cap_umas", "uma"],
  ["aguinaldo_days", "days"], ["vacation_premium_pct", "pct"],
  ["aguinaldo_exempt_umas", "uma"], ["vacation_premium_exempt_umas", "uma"],
];
const PERIODICIDADES = [1, 7, 10, 15, 30];
const PARAMETRO_VACIO = { parameter_key: "uma_daily", value: "", valid_from: "", valid_to: "", source: "" };
const TRAMO_VACIO = { lower_limit: "", upper_limit: "", fixed_fee: "", rate_pct: "", source: "" };

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export default function PayrollSettingsPage() {
  const { lang, t } = useI18n();
  const [view, setView] = useState("parameters");
  const [parametros, setParametros] = useState([]);
  const [tramos, setTramos] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [formParametro, setFormParametro] = useState(null);
  const [formTramo, setFormTramo] = useState(null);
  const [anio, setAnio] = useState(new Date().getFullYear());
  const [periodicidad, setPeriodicidad] = useState(15);

  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
  const puede = (entidad, campo) => privilegiado
    || Number(permisos.find((p) => p.entity_name === entidad)?.[campo] || 0) !== 0;

  const money = (v) => new Intl.NumberFormat(lang, { style: "currency", currency: "MXN" }).format(Number(v || 0));
  const formato = (unidad, v) => {
    if (unidad === "money") return money(v);
    if (unidad === "pct") return `${Number(v)} %`;
    if (unidad === "uma") return `${Number(v)} UMA`;
    if (unidad === "days") return `${Number(v)} ${t("payroll_settings.days")}`;
    return String(v);
  };

  // `t` cambia de identidad en cada render: si la carga dependiera de el, cada
  // render la volveria a disparar y la pantalla pediria los datos sin fin.
  const traducir = useRef(t);
  traducir.current = t;
  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    return clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
  }, []);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [p, b] = await Promise.all([
        getAllPayrollParameter({ per_page: 1000 }), getAllPayrollIsrBracket({ per_page: 1000 }),
      ]);
      setParametros((p?.items || []).filter((x) => !x.deletion_date));
      setTramos((b?.items || []).filter((x) => !x.deletion_date));
    } catch (e) {
      setError(describirError(e));
    } finally {
      setLoading(false);
    }
  }, [describirError]);

  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    getMyPermissions().then((p) => setPermisos(p?.entity_permissions || [])).catch(() => setPermisos([]));
  }, []);

  const fechaHoy = hoy();
  const porClave = useMemo(() => {
    const grupos = new Map(PARAMETROS.map(([k]) => [k, []]));
    for (const fila of parametros) {
      if (!grupos.has(fila.parameter_key)) grupos.set(fila.parameter_key, []);
      grupos.get(fila.parameter_key).push(fila);
    }
    for (const filas of grupos.values()) filas.sort((a, b) => String(b.valid_from).localeCompare(String(a.valid_from)));
    return grupos;
  }, [parametros]);
  const unidadDe = (clave) => PARAMETROS.find(([k]) => k === clave)?.[1] || "number";
  const vigente = (fila) => fila.valid_from <= fechaHoy && (!fila.valid_to || fila.valid_to >= fechaHoy);

  const anios = useMemo(() => {
    const lista = [...new Set(tramos.map((x) => Number(x.valid_year)))];
    if (!lista.includes(anio)) lista.push(anio);
    return lista.sort((a, b) => b - a);
  }, [tramos, anio]);
  const tabla = useMemo(() => tramos
    .filter((x) => Number(x.valid_year) === Number(anio) && Number(x.period_days) === Number(periodicidad))
    .sort((a, b) => Number(a.lower_limit) - Number(b.lower_limit)), [tramos, anio, periodicidad]);
  const fuenteDeLaTabla = tabla.find((x) => x.source)?.source;

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
      return false;
    }
  }

  async function guardarParametro(event) {
    event.preventDefault();
    const { id_payroll_parameter: id, ...datos } = formParametro;
    const cuerpo = { ...datos, valid_to: datos.valid_to || null, source: datos.source || null };
    const ok = await guardar(() => (id ? updatePayrollParameter(id, cuerpo) : createPayrollParameter(cuerpo)), "payroll_settings.saved");
    if (ok) setFormParametro(null);
  }

  async function guardarTramo(event) {
    event.preventDefault();
    const { id_payroll_isr_bracket: id, ...datos } = formTramo;
    const cuerpo = { ...datos, period_days: periodicidad, valid_year: anio, upper_limit: datos.upper_limit === "" ? null : datos.upper_limit, source: datos.source || null };
    const ok = await guardar(() => (id ? updatePayrollIsrBracket(id, cuerpo) : createPayrollIsrBracket(cuerpo)), "payroll_settings.saved");
    if (ok) setFormTramo(null);
  }

  async function borrar(accion) {
    if (!window.confirm(t("payroll_settings.confirm_delete"))) return;
    await guardar(accion, "payroll_settings.deleted");
  }

  const campo = (form, set, nombre, props = {}) => (
    <input {...props} value={form[nombre] ?? ""} onChange={(e) => set((f) => ({ ...f, [nombre]: e.target.value }))} />
  );

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("payroll_settings.eyebrow")} titulo={t("payroll_settings.title")} subtitulo={t("payroll_settings.subtitle")}>
        <button className="button ghost" onClick={cargar} disabled={loading}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>

      <div className="kronos-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={view === "parameters"} className={view === "parameters" ? "active" : ""} onClick={() => setView("parameters")}>{t("payroll_settings.tab_parameters")}</button>
        <button type="button" role="tab" aria-selected={view === "isr"} className={view === "isr" ? "active" : ""} onClick={() => setView("isr")}>{t("payroll_settings.tab_isr")}</button>
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {view === "parameters" && (
        <>
          {formParametro && (
            <form className="form-card" onSubmit={guardarParametro}>
              <h3>{formParametro.id_payroll_parameter ? t("common.edit") : t("payroll_settings.new_value")}</h3>
              <div className="form-grid">
                <label className="field">{t("payroll_settings.field_key")}
                  <select value={formParametro.parameter_key} disabled={Boolean(formParametro.id_payroll_parameter)} onChange={(e) => setFormParametro((f) => ({ ...f, parameter_key: e.target.value }))}>
                    {PARAMETROS.map(([k]) => <option key={k} value={k}>{t(`payroll_settings.keys.${k}`)}</option>)}
                  </select>
                </label>
                <label className="field">{t("payroll_settings.field_value")}{campo(formParametro, setFormParametro, "value", { required: true, type: "number", step: "any", min: 0 })}</label>
                <label className="field">{t("payroll_settings.field_from")}{campo(formParametro, setFormParametro, "valid_from", { required: true, type: "date" })}</label>
                <label className="field">{t("payroll_settings.field_to")}{campo(formParametro, setFormParametro, "valid_to", { type: "date" })}</label>
                <label className="field">{t("payroll_settings.field_source")}{campo(formParametro, setFormParametro, "source", { maxLength: 200 })}</label>
              </div>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormParametro(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("payroll_settings.tab_parameters")}</p><h3>{t("payroll_settings.parameters_title")}</h3></div>
              {puede("payroll_parameter", "scope_create") && <button className="button" type="button" onClick={() => setFormParametro({ ...PARAMETRO_VACIO, valid_from: fechaHoy })}><Plus size={16} /> {t("payroll_settings.new_value")}</button>}
            </div>
            <table>
              <thead><tr>
                <th>{t("payroll_settings.field_key")}</th><th>{t("payroll_settings.field_value")}</th><th>{t("payroll_settings.field_from")}</th>
                <th>{t("payroll_settings.field_to")}</th><th>{t("payroll_settings.field_source")}</th><th>{t("common.actions")}</th>
              </tr></thead>
              <tbody>
                {[...porClave.entries()].flatMap(([clave, filas]) => (filas.length ? filas : [null]).map((fila, i) => (
                  <tr key={fila ? fila.id_payroll_parameter : clave}>
                    {i === 0 && <td rowSpan={Math.max(filas.length, 1)}><strong>{t(`payroll_settings.keys.${clave}`, clave)}</strong></td>}
                    {fila ? (
                      <>
                        <td>{formato(unidadDe(clave), fila.value)} {vigente(fila) && <span className="quotation-status-badge status-approved">{t("payroll_settings.current")}</span>}</td>
                        <td>{fila.valid_from}</td>
                        <td>{fila.valid_to || t("payroll_settings.no_end")}</td>
                        <td><small>{fila.source || "—"}</small></td>
                        <td className="row-actions">
                          {puede("payroll_parameter", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => setFormParametro({ ...fila, valid_to: fila.valid_to || "", source: fila.source || "" })}><Pencil size={15} /></button>}
                          {puede("payroll_parameter", "scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deletePayrollParameter(fila.id_payroll_parameter))}><Trash2 size={15} /></button>}
                        </td>
                      </>
                    ) : <td colSpan="5" className="kronos-empty">{t("payroll_settings.missing")}</td>}
                  </tr>
                )))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {view === "isr" && (
        <>
          <form className="form-card kronos-filter" onSubmit={(e) => e.preventDefault()}>
            <label className="field">{t("payroll_settings.year")}
              <select value={anio} onChange={(e) => setAnio(Number(e.target.value))}>{anios.map((a) => <option key={a} value={a}>{a}</option>)}</select>
            </label>
            <label className="field">{t("payroll_settings.periodicity")}
              <select value={periodicidad} onChange={(e) => setPeriodicidad(Number(e.target.value))}>
                {PERIODICIDADES.map((d) => <option key={d} value={d}>{t(`payroll_settings.period_${d}`)}</option>)}
              </select>
            </label>
          </form>
          {formTramo && (
            <form className="form-card" onSubmit={guardarTramo}>
              <h3>{formTramo.id_payroll_isr_bracket ? t("common.edit") : t("payroll_settings.new_bracket")} · {anio} · {t(`payroll_settings.period_${periodicidad}`)}</h3>
              <div className="form-grid">
                <label className="field">{t("payroll_settings.lower")}{campo(formTramo, setFormTramo, "lower_limit", { required: true, type: "number", step: "0.01", min: 0 })}</label>
                <label className="field">{t("payroll_settings.upper")}{campo(formTramo, setFormTramo, "upper_limit", { type: "number", step: "0.01", min: 0, placeholder: t("payroll_settings.onwards") })}</label>
                <label className="field">{t("payroll_settings.fixed_fee")}{campo(formTramo, setFormTramo, "fixed_fee", { required: true, type: "number", step: "0.01", min: 0 })}</label>
                <label className="field">{t("payroll_settings.rate")}{campo(formTramo, setFormTramo, "rate_pct", { required: true, type: "number", step: "0.001", min: 0, max: 100 })}</label>
                <label className="field">{t("payroll_settings.field_source")}{campo(formTramo, setFormTramo, "source", { maxLength: 200 })}</label>
              </div>
              <div className="form-actions">
                <button className="button primary" type="submit">{t("common.save")}</button>
                <button className="button" type="button" onClick={() => setFormTramo(null)}>{t("common.cancel")}</button>
              </div>
            </form>
          )}
          <div className="table-card">
            <div className="kronos-table-heading">
              <div><p className="eyebrow">{t("payroll_settings.tab_isr")}</p><h3>{anio} · {t(`payroll_settings.period_${periodicidad}`)}</h3>{fuenteDeLaTabla && <small>{fuenteDeLaTabla}</small>}</div>
              {puede("payroll_isr_bracket", "scope_create") && <button className="button" type="button" onClick={() => setFormTramo({ ...TRAMO_VACIO, source: fuenteDeLaTabla || "" })}><Plus size={16} /> {t("payroll_settings.new_bracket")}</button>}
            </div>
            <table>
              <thead><tr>
                <th>{t("payroll_settings.lower")}</th><th>{t("payroll_settings.upper")}</th><th>{t("payroll_settings.fixed_fee")}</th>
                <th>{t("payroll_settings.rate")}</th><th>{t("common.actions")}</th>
              </tr></thead>
              <tbody>
                {tabla.length ? tabla.map((tramo) => (
                  <tr key={tramo.id_payroll_isr_bracket}>
                    <td>{money(tramo.lower_limit)}</td>
                    <td>{tramo.upper_limit === null || tramo.upper_limit === undefined ? t("payroll_settings.onwards") : money(tramo.upper_limit)}</td>
                    <td>{money(tramo.fixed_fee)}</td>
                    <td>{Number(tramo.rate_pct)} %</td>
                    <td className="row-actions">
                      {puede("payroll_isr_bracket", "scope_update") && <button type="button" title={t("common.edit")} onClick={() => setFormTramo({ ...tramo, upper_limit: tramo.upper_limit ?? "", source: tramo.source || "" })}><Pencil size={15} /></button>}
                      {puede("payroll_isr_bracket", "scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(() => deletePayrollIsrBracket(tramo.id_payroll_isr_bracket))}><Trash2 size={15} /></button>}
                    </td>
                  </tr>
                )) : <tr><td colSpan="5" className="kronos-empty">{t("payroll_settings.no_table")}</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
