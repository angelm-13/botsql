import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Calculator, FileDown, Plus, RefreshCw, Trash2 } from "lucide-react";
import {
  addTerminationLine, createEmployeeTermination, deleteEmployeeTermination, deleteTerminationLine, downloadTerminationSettlement, getAllEmployeeTermination,
  getAttendanceEmployeeOptions, getMyPermissions, getTerminationSettlement,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import { useDialogo } from "../dialogo/useDialogo.js";
import "../styles/kronos.css";

// Bajas: RH registra que alguien deja la empresa (fecha y motivo) y el sistema
// calcula su finiquito o liquidacion con los datos del dia, concepto por
// concepto, y lo imprime para firmar. Las reglas (LFT y LISR) viven en el
// backend (services/termination_service.py). Desactivar al usuario es aparte.

const MOTIVOS = ["resignation", "mutual_agreement", "justified_dismissal", "unjustified_dismissal"];
const RENGLON_VACIO = { line_kind: "earning", description: "", amount: "", taxable: true };

function hoy() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

export default function TerminationsPage() {
  const { lang, t } = useI18n();
  const dialogo = useDialogo();
  const traducir = useRef(t);
  traducir.current = t;
  const [bajas, setBajas] = useState([]);
  const [empleados, setEmpleados] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [form, setForm] = useState(null);
  const [calculo, setCalculo] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [renglon, setRenglon] = useState(RENGLON_VACIO);

  const actor = useMemo(actorGuardado, []);
  const privilegiado = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
  const puede = (campo) => privilegiado || Number(permisos.find((p) => p.entity_name === "employee_termination")?.[campo] || 0) !== 0;
  const money = (v) => new Intl.NumberFormat(lang === "es" ? "es-MX" : lang, { style: "currency", currency: "MXN" }).format(Number(v || 0));
  const nombre = (id) => empleados.find((e) => e.id_user === id)?.full_name || `#${id}`;

  const describirError = useCallback((e) => {
    const tr = traducir.current;
    const clave = e?.payload?.error_key || e?.message;
    return clave ? tr(clave, tr("errors.request_failed")) : tr("errors.request_failed");
  }, []);

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getAllEmployeeTermination({ per_page: 1000 });
      setBajas((r?.items || []).filter((x) => !x.deletion_date));
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

  async function guardar(event) {
    event.preventDefault();
    setError("");
    try {
      const creada = await createEmployeeTermination({ ...form, id_user: Number(form.id_user), notes: form.notes || null });
      setForm(null);
      setNotice(t("terminations.saved"));
      await cargar();
      await ver(creada);
    } catch (e) {
      setError(describirError(e));
    }
  }

  async function ver(b) {
    setError("");
    try {
      setCalculo(await getTerminationSettlement(b.id_employee_termination));
    } catch (e) {
      setCalculo(null);
      setError(describirError(e));
    }
  }

  async function imprimir(b) {
    try {
      const blob = await downloadTerminationSettlement(b.id_employee_termination);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      setError(describirError(e));
    }
  }

  // Otros pagos y descuentos que RH captura a mano (como en el Excel de la contadora).
  async function agregarRenglon(event) {
    event.preventDefault();
    setError("");
    try {
      await addTerminationLine(calculo.id_employee_termination, {
        ...renglon, amount: Number(renglon.amount), taxable: renglon.line_kind === "earning" && Boolean(renglon.taxable) });
      setRenglon(RENGLON_VACIO);
      await ver(calculo);
    } catch (e) {
      setError(describirError(e));
    }
  }

  async function quitarRenglon(linea) {
    if (!(await dialogo.confirmar(t("terminations.confirm_remove_line").replace("{concepto}", linea.description)))) return;
    try {
      await deleteTerminationLine(calculo.id_employee_termination, linea.id_employee_termination_line);
      await ver(calculo);
    } catch (e) {
      setError(describirError(e));
    }
  }

  const etiqueta = (c) => (c.code === "extra" ? c.description : t(`terminations.code_${c.code}`));

  async function borrar(b) {
    if (!(await dialogo.confirmar(t("terminations.confirm_delete")))) return;
    try {
      await deleteEmployeeTermination(b.id_employee_termination);
      if (calculo?.id_employee_termination === b.id_employee_termination) setCalculo(null);
      await cargar();
    } catch (e) {
      setError(describirError(e));
    }
  }

  const campo = (nombreCampo, props = {}) => (
    <input {...props} value={form[nombreCampo] ?? ""} onChange={(e) => setForm((f) => ({ ...f, [nombreCampo]: e.target.value }))} />
  );

  return (
    <section className="entity-page kronos-page">
      <PageHeader eyebrow={t("terminations.eyebrow")} titulo={t("terminations.title")} subtitulo={t("terminations.subtitle")}>
        <button className="button ghost" onClick={() => { setError(""); cargar(); }} disabled={loading}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {form && (
        <form className="form-card" onSubmit={guardar}>
          <h3>{t("terminations.new")}</h3>
          <div className="form-grid">
            <label className="field">{t("terminations.employee")}
              <select required value={form.id_user} onChange={(e) => setForm((f) => ({ ...f, id_user: e.target.value }))}>
                <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                {empleados.map((e) => <option key={e.id_user} value={e.id_user}>{e.full_name || e.username}</option>)}
              </select>
            </label>
            <label className="field">{t("terminations.date")}{campo("termination_date", { required: true, type: "date" })}</label>
            <label className="field">{t("terminations.reason")}
              <select required value={form.reason} onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}>
                {MOTIVOS.map((m) => <option key={m} value={m}>{t(`terminations.reason_${m}`)}</option>)}
              </select>
            </label>
            {form.reason === "unjustified_dismissal" && (
              <label className="field checkbox-field">
                <input type="checkbox" checked={Boolean(form.pay_twenty_days)} onChange={(e) => setForm((f) => ({ ...f, pay_twenty_days: e.target.checked }))} />
                {t("terminations.twenty_days")}
              </label>
            )}
            <label className="field">{t("terminations.notes")}{campo("notes", { maxLength: 300 })}</label>
          </div>
          <p className="muted">{t("terminations.form_hint")}</p>
          <div className="form-actions">
            <button className="button primary" type="submit">{t("terminations.calculate")}</button>
            <button className="button" type="button" onClick={() => setForm(null)}>{t("common.cancel")}</button>
          </div>
        </form>
      )}

      {calculo && (
        <div className="table-card kronos-table-card">
          <div className="kronos-table-heading">
            <div><p className="eyebrow">{t(calculo.reason === "unjustified_dismissal" ? "terminations.liquidation" : "terminations.settlement")}</p>
              <h3>{calculo.full_name} · {calculo.termination_date}</h3></div>
            <button className="button" type="button" onClick={() => imprimir(calculo)}><FileDown size={16} /> PDF</button>
          </div>
          <div className="kronos-metrics">
            <div><span>{t("terminations.daily")}</span><strong>{money(calculo.daily_salary)}</strong></div>
            <div><span>{t("terminations.integrated")}</span><strong>{money(calculo.integrated_daily_salary)}</strong></div>
            <div><span>{t("terminations.years")}</span><strong>{calculo.years_of_service}</strong></div>
            <div><span>{t("terminations.pending_from")}</span><strong>{calculo.pending_from} ({calculo.pending_paid_days})</strong></div>
          </div>
          <table>
            <thead><tr><th>{t("terminations.concept")}</th><th>{t("terminations.amount")}</th></tr></thead>
            <tbody>
              {calculo.earnings.map((c, i) => <tr key={`p${i}`}><td>{etiqueta(c)}</td><td>{money(c.amount)}</td></tr>)}
              {calculo.deductions.map((c, i) => <tr key={`d${i}`}><td>− {etiqueta(c)}</td><td>− {money(c.amount)}</td></tr>)}
            </tbody>
            <tfoot><tr><td><strong>{t("terminations.net")}</strong></td><td><strong>{money(calculo.net_pay)}</strong></td></tr></tfoot>
          </table>
          {calculo.taxable_severance > 0 && <p className="muted" style={{ padding: "0 18px" }}>{t("terminations.severance_hint")} {money(calculo.taxable_severance)} ({calculo.severance_tax_rate} %)</p>}
          <div style={{ padding: "0 18px 18px" }}>
            <h4 style={{ margin: "12px 0 4px" }}>{t("terminations.extra_title")}</h4>
            <p className="muted" style={{ margin: "0 0 8px" }}>{t("terminations.extra_hint")}</p>
            {(calculo.extra_lines || []).length > 0 && (
              <ul style={{ margin: "0 0 10px", paddingLeft: 18 }}>
                {calculo.extra_lines.map((l) => (
                  <li key={l.id_employee_termination_line}>
                    {t(`terminations.kind_${l.line_kind}`)}: {l.description} · {money(l.amount)}
                    {l.line_kind === "earning" && <small className="muted"> · {t(l.taxable ? "terminations.taxable" : "terminations.not_taxable")}</small>}
                    {puede("scope_update") && <button type="button" className="button ghost" style={{ marginLeft: 8, padding: "2px 8px" }}
                      title={t("common.delete")} aria-label={`${t("common.delete")} ${l.description}`} onClick={() => quitarRenglon(l)}><Trash2 size={13} /></button>}
                  </li>
                ))}
              </ul>
            )}
            {puede("scope_update") && (
              <form className="form-grid" onSubmit={agregarRenglon}>
                <label className="field">{t("terminations.kind")}
                  <select value={renglon.line_kind} onChange={(e) => setRenglon((r) => ({ ...r, line_kind: e.target.value }))}>
                    <option value="earning">{t("terminations.kind_earning")}</option>
                    <option value="deduction">{t("terminations.kind_deduction")}</option>
                  </select>
                </label>
                <label className="field">{t("terminations.concept")}
                  <input required maxLength={120} placeholder={t(renglon.line_kind === "earning" ? "terminations.earning_example" : "terminations.deduction_example")}
                    value={renglon.description} onChange={(e) => setRenglon((r) => ({ ...r, description: e.target.value }))} />
                </label>
                <label className="field">{t("terminations.amount")}
                  <input required type="number" min="0.01" step="0.01" value={renglon.amount} onChange={(e) => setRenglon((r) => ({ ...r, amount: e.target.value }))} />
                </label>
                {renglon.line_kind === "earning" && (
                  <label className="field checkbox-field">
                    <input type="checkbox" checked={renglon.taxable} onChange={(e) => setRenglon((r) => ({ ...r, taxable: e.target.checked }))} />
                    {t("terminations.taxable")}
                  </label>
                )}
                <div className="form-actions"><button className="button" type="submit"><Plus size={15} /> {t("terminations.add_line")}</button></div>
              </form>
            )}
          </div>
        </div>
      )}

      <div className="table-card">
        <div className="kronos-table-heading">
          <div><p className="eyebrow">{t("terminations.eyebrow")}</p><h3>{t("terminations.list_title")}</h3></div>
          {puede("scope_create") && <button className="button" type="button" onClick={() => setForm({ id_user: "", termination_date: hoy(), reason: "resignation", pay_twenty_days: false, notes: "" })}><Plus size={16} /> {t("terminations.new")}</button>}
        </div>
        <table>
          <thead><tr><th>{t("terminations.employee")}</th><th>{t("terminations.date")}</th><th>{t("terminations.reason")}</th><th>{t("terminations.notes")}</th><th>{t("common.actions")}</th></tr></thead>
          <tbody>{bajas.length ? bajas.map((b) => (
            <tr key={b.id_employee_termination}>
              <td><strong>{nombre(b.id_user)}</strong></td><td>{b.termination_date}</td>
              <td>{t(`terminations.reason_${b.reason}`)}{b.pay_twenty_days && <small> · {t("terminations.twenty_days_short")}</small>}</td>
              <td><small>{b.notes || "—"}</small></td>
              <td className="row-actions">
                <button type="button" title={t("terminations.calculate")} onClick={() => ver(b)}><Calculator size={15} /></button>
                <button type="button" title="PDF" onClick={() => imprimir(b)}><FileDown size={15} /></button>
                {puede("scope_delete") && <button type="button" title={t("common.delete")} onClick={() => borrar(b)}><Trash2 size={15} /></button>}
              </td>
            </tr>
          )) : <tr><td colSpan="5" className="kronos-empty">{t("terminations.empty")}</td></tr>}</tbody>
        </table>
      </div>
    </section>
  );
}
