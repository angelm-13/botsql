import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { FileSpreadsheet, FlaskConical, Plus, Save, X } from "lucide-react";
import { downloadPayrollSheet, getPayrollSheet, savePayrollSheet, simulatePayrollSheet } from "../api";

// Pestaña "Hoja" del periodo de nomina (puntos 6 y 7 de RH): ingresos a un lado,
// egresos al otro y el neto, como en Excel. Las celdas grises las calcula el
// sistema; las blancas se escriben y, al salir de la celda, se guardan como
// movimiento y se recalcula el periodo (ISR incluido). En modo simulacion nada se
// guarda hasta "Pasar a la nomina". Las reglas viven en el backend
// (services/payroll_sheet_service.py).
export default function HojaDeNomina({ t, money, idPeriodo, puedeEscribir, ejecutar, onGuardado }) {
  const [hoja, setHoja] = useState(null);
  const [simulando, setSimulando] = useState(false);
  const [cambios, setCambios] = useState({});
  const [extra, setExtra] = useState([]);
  const [ocupado, setOcupado] = useState(false);
  const [recien, setRecien] = useState(null); // celda que se acaba de guardar: el aviso va junto a ella

  async function cargar() {
    const datos = await ejecutar(() => getPayrollSheet(idPeriodo));
    if (datos) setHoja(datos);
  }

  useEffect(() => {
    setSimulando(false);
    setCambios({});
    setExtra([]);
    cargar();
  }, [idPeriodo]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!hoja) return null;
  const cerrado = hoja.period_state === "closed";
  const escribible = puedeEscribir && !cerrado;
  const columnas = [...hoja.columns, ...hoja.available.filter((c) => extra.includes(c.id_payroll_concept))];
  const ingresos = columnas.filter((c) => c.type === "earning");
  const egresos = columnas.filter((c) => c.type === "deduction");
  const disponibles = hoja.available.filter((c) => !extra.includes(c.id_payroll_concept));
  const lista = (mapa) => Object.entries(mapa).map(([clave, amount]) => {
    const [id_user, id_payroll_concept] = clave.split(":").map(Number);
    return { id_user, id_payroll_concept, amount };
  });

  async function escribir(fila, col, texto) {
    const monto = texto === "" ? 0 : Number(texto);
    const actual = Number(fila.amounts[col.id_payroll_concept] || 0);
    if (!Number.isFinite(monto) || monto < 0 || monto === actual || ocupado) return;
    setOcupado(true);
    const celda = { [`${fila.id_user}:${col.id_payroll_concept}`]: monto };
    if (simulando) {
      const todos = { ...cambios, ...celda };
      const datos = await ejecutar(() => simulatePayrollSheet(idPeriodo, lista(todos)));
      if (datos) { setCambios(todos); setHoja(datos); }
    } else {
      const datos = await ejecutar(() => savePayrollSheet(idPeriodo, lista(celda)));
      if (datos) {
        setHoja(datos); onGuardado?.();
        const clave = Object.keys(celda)[0];
        setRecien(clave);
        setTimeout(() => setRecien((v) => (v === clave ? null : v)), 3000);
      }
    }
    setOcupado(false);
  }

  async function salirDeSimulacion() {
    setSimulando(false);
    setCambios({});
    await cargar();
  }

  async function pasarALaNomina() {
    const datos = await ejecutar(() => savePayrollSheet(idPeriodo, lista(cambios)),
      { confirmKey: "payroll_sheet.apply_confirm", doneKey: "payroll_sheet.applied" });
    if (datos) { setHoja(datos); setSimulando(false); setCambios({}); onGuardado?.(); }
  }

  async function descargar() {
    const blob = await ejecutar(() => downloadPayrollSheet(idPeriodo));
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nomina_periodo_${idPeriodo}.xlsx`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  const celda = (fila, col) => {
    const valor = fila.amounts[col.id_payroll_concept] || 0;
    if (!col.editable || !escribible) {
      return <td key={col.id_payroll_concept} className={`num${col.editable ? "" : " calculada"}`}>{money(valor)}</td>;
    }
    const cambiada = `${fila.id_user}:${col.id_payroll_concept}` in cambios;
    return (
      <td key={col.id_payroll_concept} className={`celda-editable${cambiada ? " cambiada" : ""}`}>
        <input key={`${valor}-${simulando}`} type="number" min="0" step="0.01" defaultValue={valor || ""} disabled={ocupado}
          aria-label={`${col.description} · ${fila.full_name}`}
          onBlur={(e) => escribir(fila, col, e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }} />
        {recien === `${fila.id_user}:${col.id_payroll_concept}` && <small className="celda-guardada" role="status">✓ {t("payroll_sheet.saved_short")}</small>}
      </td>
    );
  };

  const encabezado = (c) => (
    <th key={c.id_payroll_concept} className="num">{c.description}
      {/* Una columna agregada y aun sin montos se puede quitar. */}
      {extra.includes(c.id_payroll_concept) && hoja.available.some((a) => a.id_payroll_concept === c.id_payroll_concept) && (
        <button type="button" className="quitar-columna" title={t("payroll_sheet.remove_column")} aria-label={`${t("payroll_sheet.remove_column")} ${c.description}`}
          onClick={() => setExtra(extra.filter((x) => x !== c.id_payroll_concept))}><X size={12} /></button>
      )}
    </th>
  );

  return (
    <div className="hoja-nomina">
      <div className="hoja-barra">
        {escribible && !simulando && (
          <button type="button" className="button" onClick={() => { setSimulando(true); setCambios({}); }}>
            <FlaskConical size={15} /> {t("payroll_sheet.simulate")}
          </button>
        )}
        {simulando && <>
          <span className="simulando">{t("payroll_sheet.simulating")}</span>
          <button type="button" className="button primary" disabled={!Object.keys(cambios).length || ocupado} onClick={pasarALaNomina}>
            <Save size={15} /> {t("payroll_sheet.apply")}
          </button>
          <button type="button" className="button" onClick={salirDeSimulacion}><X size={15} /> {t("payroll_sheet.discard")}</button>
        </>}
        {escribible && disponibles.length > 0 && (
          <label className="button ghost">
            <Plus size={15} />
            <select value="" aria-label={t("payroll_sheet.add_concept")}
              onChange={(e) => e.target.value && setExtra([...extra, Number(e.target.value)])}>
              <option value="">{t("payroll_sheet.add_concept")}</option>
              {disponibles.map((c) => (
                <option key={c.id_payroll_concept} value={c.id_payroll_concept}>
                  {c.description} · {t(c.type === "earning" ? "payroll_sheet.earnings" : "payroll_sheet.deductions")}
                </option>
              ))}
            </select>
          </label>
        )}
        {escribible && disponibles.length === 0 && <small className="muted">{t("payroll_sheet.no_more_concepts")}</small>}
        <button type="button" className="button" onClick={descargar}><FileSpreadsheet size={15} /> {t("payroll_sheet.download")}</button>
      </div>
      <p className="muted" style={{ margin: "0 16px 12px" }}>{t(cerrado ? "payroll_sheet.closed_hint" : "payroll_sheet.hint")}</p>
      {hoja.rows.length ? (
        <table>
          <thead>
            <tr>
              <th colSpan={2} />
              <th colSpan={ingresos.length + 1} className="bloque ingresos">{t("payroll_sheet.earnings")}</th>
              <th colSpan={egresos.length + 1} className="bloque egresos">{t("payroll_sheet.deductions")}</th>
              <th />
            </tr>
            <tr>
              <th>{t("payroll_calc.employee")}</th><th className="num">{t("payroll_calc.days")}</th>
              {ingresos.map(encabezado)}
              <th className="num">{t("payroll_sheet.total")}</th>
              {egresos.map(encabezado)}
              <th className="num">{t("payroll_sheet.total")}</th>
              <th className="num">{t("payroll_calc.net")}</th>
            </tr>
          </thead>
          <tbody>{hoja.rows.map((fila) => (
            <tr key={fila.id_user}>
              <td>{fila.full_name}</td><td className="num">{fila.days_worked}</td>
              {ingresos.map((c) => celda(fila, c))}
              <td className="num ingreso-total">{money(fila.total_earnings)}</td>
              {egresos.map((c) => celda(fila, c))}
              <td className="num egreso-total">{money(fila.total_deductions)}</td>
              <td className="num"><strong>{money(fila.net_pay)}</strong></td>
            </tr>
          ))}</tbody>
          <tfoot>
            <tr>
              <td colSpan={2}>{t("payroll_calc.total")}</td>
              {ingresos.map((c) => <td key={c.id_payroll_concept} className="num">{money(hoja.totals[c.id_payroll_concept])}</td>)}
              <td className="num ingreso-total">{money(hoja.totals.total_earnings)}</td>
              {egresos.map((c) => <td key={c.id_payroll_concept} className="num">{money(hoja.totals[c.id_payroll_concept])}</td>)}
              <td className="num egreso-total">{money(hoja.totals.total_deductions)}</td>
              <td className="num">{money(hoja.totals.net_pay)}</td>
            </tr>
          </tfoot>
        </table>
      ) : <p style={{ padding: "0 16px 16px" }}>{t("payroll_calc.empty")}</p>}
    </div>
  );
}

HojaDeNomina.propTypes = {
  t: PropTypes.func.isRequired,
  money: PropTypes.func.isRequired,
  idPeriodo: PropTypes.number.isRequired,
  puedeEscribir: PropTypes.bool,
  ejecutar: PropTypes.func.isRequired,
  onGuardado: PropTypes.func,
};
