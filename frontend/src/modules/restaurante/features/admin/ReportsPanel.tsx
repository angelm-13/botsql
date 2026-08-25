import { useEffect, useState } from 'react';
import { Download, FileBarChart, Receipt } from 'lucide-react';
import { jsPDF } from 'jspdf';
import 'jspdf-autotable';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { DemoLockedNote } from '../../components/shared/DemoLockedNote';
import { money, fmtLocalDate, DATE_RANGE_PRESETS } from '../../utils/format';
import { drawLogoPdf } from './pdfHelpers';
import { ReceiptModal, ReportReceipt } from './Receipts';
import type { Translations } from '../../i18n/translations';
import type { SalesReport, DemoStatus } from '../../types/api';

// Version freemium: solo se puede consultar el reporte de hoy/ayer (ver
// backend/app/demo.py -- el bloqueo real es solo del lado del frontend
// aqui, /cashier/reports no tiene limite propio en el backend, igual que
// el resto de los reportes historicos bloqueados en Dashboard.tsx).
const DEMO_ALLOWED_PRESET_KEYS = new Set(['today', 'yesterday']);

function buildReportPdf(report: SalesReport, start: string, end: string, t: Translations) {
  const doc = new jsPDF();
  const rangeLabel = start || end
    ? `${t.from}: ${start || '-'}   ${t.to}: ${end || '-'}`
    : `${t.reports}`;

  drawLogoPdf(doc, 14, 10, t);
  doc.setDrawColor(113, 113, 122);
  doc.setLineWidth(0.4);
  doc.line(14, 24, 196, 24);

  doc.setTextColor(20);
  doc.setFontSize(16);
  doc.text(t.reports, 14, 33);
  doc.setFontSize(10);
  doc.setTextColor(90);
  doc.text(rangeLabel, 14, 40);
  doc.text(`${new Date().toLocaleString()}`, 14, 45);

  doc.setTextColor(20);
  doc.setFontSize(11);
  doc.text(`${t.totalSales}: ${money(report.total_sales)}`, 14, 56);
  doc.text(`${t.tips}: ${money(report.total_tips)}`, 90, 56);
  doc.text(`${t.orders}: ${report.total_orders}`, 150, 56);

  doc.autoTable({
    startY: 64,
    head: [[t.day, t.orders, t.totalSales, t.tips]],
    body: (report.days || []).map(d => [d.date, String(d.orders), money(d.sales), money(d.tips)]),
    styles: { fontSize: 9 },
    headStyles: { fillColor: [243, 201, 107], textColor: 30 },
  });

  const suffix = `${start || 'inicio'}_a_${end || 'hoy'}`;
  doc.save(`reporte_ventas_${suffix}.pdf`);
}

export function ReportsPanel({ t }: { t: Translations }) {
  const toast = useToast();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [activePreset, setActivePreset] = useState<string | null>('all');
  const [report, setReport] = useState<SalesReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showTicket, setShowTicket] = useState(false);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const demoLocksReports = !!demoStatus?.enabled;
  async function fetchReport(s = start, e = end) {
    const params = [`tz_offset_minutes=${new Date().getTimezoneOffset()}`];
    if (s) params.push(`start=${s}`);
    if (e) params.push(`end=${e}`);
    const data = await api.reports(`?${params.join('&')}`);
    setReport(data);
    return data;
  }
  async function reload(s = start, e = end) {
    setLoading(true);
    try { await fetchReport(s, e); } catch (err) { console.error(err); toast.error((err as Error).message); } finally { setLoading(false); }
  }
  // Botones de rango rapido: calculan las fechas y disparan la consulta de
  // inmediato, para que el cajero no tenga que picar dos calendarios cada
  // vez que quiere ver "hoy" o "este mes".
  function applyPreset(key: string) {
    setActivePreset(key);
    if (key === 'all') { setStart(''); setEnd(''); reload('', ''); return; }
    const today = new Date();
    let s = today, e = today;
    if (key === 'yesterday') { s = e = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1); }
    else if (key === 'week') {
      const dow = today.getDay();
      s = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (dow === 0 ? 6 : dow - 1));
    } else if (key === 'month') { s = new Date(today.getFullYear(), today.getMonth(), 1); }
    const sStr = fmtLocalDate(s), eStr = fmtLocalDate(e);
    setStart(sStr); setEnd(eStr);
    reload(sStr, eStr);
  }
  function editStart(v: string) { setStart(v); setActivePreset(null); }
  function editEnd(v: string) { setEnd(v); setActivePreset(null); }
  async function generateAndDownload() {
    // Sin esta validacion, invertir el rango (start > end) no daba ningun
    // error: el backend simplemente no encontraba filas y regresaba
    // days:[], indistinguible en la UI de "no hubo ventas en el rango".
    if (start && end && start > end) { toast.error(t.invalidDateRange); return; }
    setGenerating(true);
    try {
      const data = await fetchReport();
      buildReportPdf(data, start, end, t);
    } catch (err) {
      console.error('No se pudo generar el PDF del reporte:', err);
      toast.error(t.pdfError + ((err as Error)?.message ? ` (${(err as Error).message})` : ''));
    } finally {
      setGenerating(false);
    }
  }
  useEffect(() => {
    api.demoStatus().then(status => {
      setDemoStatus(status);
      // Si la version freemium ya limita los reportes, arranca en "hoy" en
      // vez de "todo el historico" -- evita que se alcance a ver el reporte
      // completo un instante antes de que este efecto sepa que hay un limite.
      applyPreset(status.enabled ? 'today' : 'all');
    }).catch(() => applyPreset('all'));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // CSV para abrir el reporte en Excel/Sheets, ademas del PDF -- se arma en
  // el navegador (sin libreria nueva) a partir de los mismos dias que ya
  // trae `report`, no una consulta aparte.
  function downloadCsv() {
    if (!report) return;
    const rows = [[t.day, t.orders, t.totalSales, t.tips], ...report.days.map(d => [d.date, d.orders, d.sales, d.tips])];
    const csv = rows.map(row => row.map(cell => {
      const s = String(cell);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(',')).join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporte_ventas_${start || 'inicio'}_a_${end || 'hoy'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const maxDaily = report ? Math.max(1, ...report.days.map(d => Number(d.sales) || 0)) : 1;

  const visiblePresets = demoLocksReports ? DATE_RANGE_PRESETS.filter(p => DEMO_ALLOWED_PRESET_KEYS.has(p.key)) : DATE_RANGE_PRESETS;
  return <section>
    {demoLocksReports && <DemoLockedNote text={t.demoLockedReports} />}
    <div className="guisado-mode-row">
      {visiblePresets.map(p => <button key={p.key} className={activePreset === p.key ? 'active' : ''} onClick={() => applyPreset(p.key)}>{t[p.label as keyof Translations]}</button>)}
    </div>
    <div className="form-row" style={{ marginTop: 12 }}>
      <div className="field"><label>{t.from}</label><input type="date" value={start} disabled={demoLocksReports} title={demoLocksReports ? t.demoLockedReports : undefined} onChange={e => editStart(e.target.value)} /></div>
      <div className="field"><label>{t.to}</label><input type="date" value={end} disabled={demoLocksReports} title={demoLocksReports ? t.demoLockedReports : undefined} onChange={e => editEnd(e.target.value)} /></div>
      <button className="primary" onClick={generateAndDownload} disabled={generating}><FileBarChart size={16} style={{ marginRight: 6 }} />{generating ? t.generating : t.generate}</button>
      {/* Reporte PDF tamano carta (para archivo/impresora normal) vs. version
          angosta para la impresora termica de 58mm (Vorago) del negocio,
          vs. CSV para abrirlo en Excel/Sheets. */}
      {report && <button onClick={() => setShowTicket(true)}><Receipt size={16} style={{ marginRight: 6 }} />{t.printTicket}</button>}
      {report && report.days.length > 0 && <button onClick={downloadCsv}><Download size={16} style={{ marginRight: 6 }} />{t.exportCsv}</button>}
    </div>
    {loading && !report && <LoadingPanel />}
    {report && <>
      <section className="kpi-grid">
        <div className="kpi kpi-primary"><div className="kpi-label">{t.totalSales}</div><div className="kpi-value">{money(report.total_sales)}</div></div>
        <div className="kpi kpi-secondary"><div className="kpi-label">{t.tips}</div><div className="kpi-value">{money(report.total_tips)}</div></div>
        <div className="kpi kpi-tertiary"><div className="kpi-label">{t.orders}</div><div className="kpi-value">{report.total_orders}</div></div>
      </section>
      {report.days.length > 0 && <div className="chart" style={{ marginTop: 16 }}>
        <h2>{t.dailySalesChart}</h2>
        <div className="chart-vertical" style={{ overflowX: 'auto', justifyContent: report.days.length > 9 ? 'flex-start' : 'space-around' }}>
          {report.days.map(d => <div className="col-bar" key={d.date} style={{ flex: '0 0 52px' }}>
            <div className="col" style={{ height: `${(Number(d.sales) / maxDaily) * 100}%`, background: 'linear-gradient(180deg,var(--brand-primary),var(--brand-secondary))' }}>
              <span className="col-val">{money(d.sales)}</span>
            </div>
            <span className="col-label">{d.date.slice(5)}</span>
          </div>)}
        </div>
      </div>}
      <table className="report-table" style={{ marginTop: 16 }}>
        <thead><tr><th>{t.day}</th><th>{t.orders}</th><th>{t.totalSales}</th><th>{t.tips}</th></tr></thead>
        <tbody>{report.days.map(d => <tr key={d.date}><td>{d.date}</td><td>{d.orders}</td><td>{money(d.sales)}</td><td>{money(d.tips)}</td></tr>)}</tbody>
      </table>
    </>}
    {showTicket && report && <ReceiptModal t={t} onClose={() => setShowTicket(false)}><ReportReceipt t={t} report={report} start={start} end={end} /></ReceiptModal>}
  </section>;
}
