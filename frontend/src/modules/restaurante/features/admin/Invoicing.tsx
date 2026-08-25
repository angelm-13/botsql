import { useEffect, useState } from 'react';
import { Ban, Download, FileText, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { Portal } from '../../components/shared/Portal';
import { RefreshButton } from '../../components/shared/RefreshButton';
import { DemoLockedNote } from '../../components/shared/DemoLockedNote';
import { money, fmtStamp, fmtLocalDate, DATE_RANGE_PRESETS } from '../../utils/format';
import type { Translations } from '../../i18n/translations';
import type { Invoice, InvoiceSalesSummary, CancelStatus, DemoStatus } from '../../types/api';

interface InvoiceCatalogs {
  regimen_fiscal: Record<string, string>
  uso_cfdi: Record<string, string>
  motivo_cancelacion: Record<string, string>
  [key: string]: unknown
}

interface ReceptorForm {
  rfc: string
  nombre: string
  regimen_fiscal: string
  cp_fiscal: string
  uso_cfdi: string
  email: string
}

/** Formulario del receptor + timbrado, abierto desde ReceiptScreen justo
 * despues de cobrar una cuenta. Primero valida con /preview (sin gastar
 * folio ni llamar al PAC) y solo timbra cuando el cajero confirma. */
export function InvoiceModal({ t, orderIds, onClose }: { t: Translations; orderIds: number[]; onClose: () => void }) {
  const toast = useToast();
  const [catalogs, setCatalogs] = useState<InvoiceCatalogs | null>(null);
  const [form, setForm] = useState<ReceptorForm>({ rfc: '', nombre: '', regimen_fiscal: '', cp_fiscal: '', uso_cfdi: 'G03', email: '' });
  const [step, setStep] = useState<'form' | 'preview' | 'done'>('form');
  const [preview, setPreview] = useState<{ ok: boolean; subtotal: number; iva: number; total: number; [key: string]: unknown } | null>(null);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);

  useEffect(() => { api.invoiceCatalogs().then(c => setCatalogs(c as InvoiceCatalogs)).catch(e => toast.error(e.message)); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.demoStatus().then(setDemoStatus).catch(() => {}); }, []);
  const atInvoiceCap = !!(demoStatus?.enabled && demoStatus.invoices_used_this_month >= demoStatus.max_invoices_per_month);

  async function doPreview() {
    setBusy(true); setErrors([]);
    try {
      const data = await api.previewInvoice({ order_ids: orderIds, receptor: form });
      if (!data.ok) { setErrors((data.errors as string[]) || []); return; }
      setPreview(data as unknown as { ok: boolean; subtotal: number; iva: number; total: number });
      setStep('preview');
    } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  }

  async function doStamp() {
    setBusy(true);
    try {
      const inv = await api.createInvoice({ order_ids: orderIds, receptor: form });
      setInvoice(inv);
      setStep('done');
    } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  }

  async function viewPdf() {
    try { window.open(URL.createObjectURL(await api.invoiceFileBlob(invoice!.id, 'pdf')), '_blank'); }
    catch (e) { toast.error((e as Error).message); }
  }
  async function downloadXml() {
    try {
      const url = URL.createObjectURL(await api.invoiceFileBlob(invoice!.id, 'xml'));
      const a = document.createElement('a'); a.href = url; a.download = `CFDI_${invoice!.uuid || invoice!.id}.xml`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch (e) { toast.error((e as Error).message); }
  }

  return <Portal><div className="modal"><div className="ticket-panel" style={{ width: 'min(480px,95vw)' }}>
    <button className="close" onClick={onClose}>&times;</button>
    <h2>{t.invoiceModalTitle}</h2>
    {step === 'form' && atInvoiceCap && <DemoLockedNote text={t.demoInvoiceLimitReached} />}
    {step === 'form' && !atInvoiceCap && (!catalogs ? <LoadingPanel /> : <>
      <div className="dish-edit-row">
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.invoiceRfc}</span><input value={form.rfc} onChange={e => setForm({ ...form, rfc: e.target.value.toUpperCase() })} /></label>
        <label className="dish-edit-field dish-edit-field-wide"><span>{t.invoiceRazonSocial}</span><input value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} /></label>
      </div>
      <div className="dish-edit-row">
        <label className="dish-edit-field"><span>{t.invoiceRegimenFiscal}</span>
          <select value={form.regimen_fiscal} onChange={e => setForm({ ...form, regimen_fiscal: e.target.value })}>
            <option value="">-</option>
            {Object.entries(catalogs.regimen_fiscal).map(([k, v]) => <option key={k} value={k}>{k} - {v}</option>)}
          </select>
        </label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.invoiceCpFiscal}</span><input value={form.cp_fiscal} onChange={e => setForm({ ...form, cp_fiscal: e.target.value })} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.invoiceUsoCfdi}</span>
          <select value={form.uso_cfdi} onChange={e => setForm({ ...form, uso_cfdi: e.target.value })}>
            {Object.entries(catalogs.uso_cfdi).map(([k, v]) => <option key={k} value={k}>{k} - {v}</option>)}
          </select>
        </label>
      </div>
      <label className="dish-edit-field dish-edit-field-wide"><span>{t.invoiceEmail}</span><input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label>
      {errors.length > 0 && <div style={{ color: 'var(--danger)', fontSize: 13, margin: '8px 0' }}>{errors.map((e, i) => <p key={i} style={{ margin: '2px 0' }}>{e}</p>)}</div>}
      <button className="primary big" disabled={busy} onClick={doPreview}>{busy ? <><Loader2 size={18} className="spin" /> {t.processing}</> : t.invoiceSubmit}</button>
    </>)}
    {step === 'preview' && preview && <>
      <div className="pay-summary">
        <div className="pay-summary-row"><span>{t.subtotal}</span><span>{money(preview.subtotal)}</span></div>
        <div className="pay-summary-row"><span>{t.tax}</span><span>{money(preview.iva)}</span></div>
        <div className="pay-total-row"><span>{t.total}</span><strong>{money(preview.total)}</strong></div>
      </div>
      <button className="primary big" disabled={busy} onClick={doStamp}>{busy ? <><Loader2 size={18} className="spin" /> {t.invoiceStamping}</> : t.invoiceSubmit}</button>
      <button className="ghost" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} disabled={busy} onClick={() => setStep('form')}>{t.cancel}</button>
    </>}
    {step === 'done' && invoice && <>
      <p style={{ color: 'var(--green)' }}>{t.invoiceSuccess}</p>
      <p><strong>{t.invoiceUuid}:</strong> {invoice.uuid}</p>
      <div className="receipt-modal-actions">
        <button className="primary" onClick={viewPdf}><FileText size={16} /> {t.invoiceViewPdf}</button>
        <button className="ghost" onClick={downloadXml}><Download size={16} /> {t.invoiceDownloadXml}</button>
        <button className="ghost" onClick={onClose}>{t.close}</button>
      </div>
    </>}
  </div></div></Portal>;
}

interface CancelInvoicePayload {
  reason: string
  motivo: string
  folio_sustitucion?: string
}

/** Motivo (interno) + motivo SAT antes de cancelar una factura, igual que
 * CancelItemModal/CorrectPaymentModal exigen motivo para cualquier reversion. */
function CancelInvoiceModal({ t, catalogs, onConfirm, onClose }: { t: Translations; catalogs: InvoiceCatalogs | null; onConfirm: (payload: CancelInvoicePayload) => Promise<void>; onClose: () => void }) {
  const [reason, setReason] = useState('');
  const [motivo, setMotivo] = useState('02');
  const [folioSustitucion, setFolioSustitucion] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function confirm() {
    const trimmed = reason.trim();
    if (!trimmed) { setError(t.correctPaymentReasonRequired); return; }
    if (motivo === '01' && !folioSustitucion.trim()) { setError(t.invoiceCancelSustitucion); return; }
    setBusy(true);
    try { await onConfirm({ reason: trimmed, motivo, folio_sustitucion: folioSustitucion.trim() || undefined }); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  return <Portal><div className="modal"><div className="ticket-panel">
    <button className="close" onClick={onClose}>&times;</button>
    <h2>{t.invoiceCancelAction}</h2>
    <div className="field">
      <label>{t.invoiceCancelMotivoSat}</label>
      <select value={motivo} onChange={e => setMotivo(e.target.value)}>
        {catalogs && Object.entries(catalogs.motivo_cancelacion).map(([k, v]) => <option key={k} value={k}>{k} - {v}</option>)}
      </select>
    </div>
    {motivo === '01' && <div className="field">
      <label>{t.invoiceCancelSustitucion}</label>
      <input value={folioSustitucion} onChange={e => setFolioSustitucion(e.target.value)} />
    </div>}
    <div className="field">
      <label>{t.invoiceCancelReason}</label>
      <textarea rows={3} placeholder={t.invoiceCancelReasonPlaceholder} value={reason} onChange={e => { setReason(e.target.value); setError(''); }} />
    </div>
    {error && <p style={{ color: 'var(--danger)', fontSize: 13, margin: '0 0 10px' }}>{error}</p>}
    <button className="primary big" disabled={busy} onClick={confirm}>{t.invoiceCancelConfirm}</button>
  </div></div></Portal>;
}

/** Historial de facturas emitidas + resumen de ventas facturadas (mismo
 * patron de KPIs + grafica de barras ya usado en ReportsPanel, pero sobre
 * Invoice en vez de Order). Visible para cajero y admin: ambos pueden
 * facturar y necesitan ver/descargar/cancelar lo ya timbrado. */
export function InvoiceHistoryPanel({ t }: { t: Translations }) {
  const toast = useToast();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [activePreset, setActivePreset] = useState<string | null>('all');
  const [summary, setSummary] = useState<InvoiceSalesSummary | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [catalogs, setCatalogs] = useState<InvoiceCatalogs | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelTarget, setCancelTarget] = useState<Invoice | null>(null);

  async function load(s = start, e = end) {
    const params: string[] = [];
    if (s) params.push(`start=${s}`);
    if (e) params.push(`end=${e}`);
    const qs = params.length ? `?${params.join('&')}` : '';
    const [sum, inv] = await Promise.all([api.invoiceSalesSummary(qs), api.invoices(qs)]);
    setSummary(sum); setInvoices(inv.items || []);
  }
  async function reload(s = start, e = end) {
    setLoading(true);
    try { await load(s, e); } catch (err) { toast.error((err as Error).message); } finally { setLoading(false); }
  }
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
  useEffect(() => {
    reload('', '').catch(console.error);
    api.invoiceCatalogs().then(c => setCatalogs(c as InvoiceCatalogs)).catch(console.error);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function viewPdf(inv: Invoice) {
    try { window.open(URL.createObjectURL(await api.invoiceFileBlob(inv.id, 'pdf')), '_blank'); }
    catch (e) { toast.error((e as Error).message); }
  }
  async function downloadXml(inv: Invoice) {
    try {
      const url = URL.createObjectURL(await api.invoiceFileBlob(inv.id, 'xml'));
      const a = document.createElement('a'); a.href = url; a.download = `CFDI_${inv.uuid || inv.id}.xml`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch (e) { toast.error((e as Error).message); }
  }
  async function confirmCancel(payload: CancelInvoicePayload) {
    await api.cancelInvoice(cancelTarget!.id, payload as unknown as Record<string, unknown>);
    setCancelTarget(null);
    toast.success(t.invoiceCancelSent);
    reload();
  }

  function invoiceStatusLabel(inv: { cancel_status: CancelStatus }) {
    if (inv.cancel_status === 'cancelado') return t.invoiceStatusCancelled;
    if (inv.cancel_status === 'en_proceso') return t.invoiceStatusEnProceso;
    return t.invoiceStatusStamped;
  }

  const maxDaily = summary ? Math.max(1, ...summary.days.map(d => Math.abs(Number(d.sales) || 0))) : 1;

  return <section>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
      <h3 style={{ margin: 0 }}>{t.invoicingTab}</h3>
      <RefreshButton t={t} onClick={() => reload()} />
    </div>
    <div className="guisado-mode-row">
      {DATE_RANGE_PRESETS.map(p => <button key={p.key} className={activePreset === p.key ? 'active' : ''} onClick={() => applyPreset(p.key)}>{t[p.label as keyof Translations]}</button>)}
    </div>
    <div className="form-row" style={{ marginTop: 12 }}>
      <div className="field"><label>{t.from}</label><input type="date" value={start} onChange={e => { setStart(e.target.value); setActivePreset(null); }} /></div>
      <div className="field"><label>{t.to}</label><input type="date" value={end} onChange={e => { setEnd(e.target.value); setActivePreset(null); }} /></div>
      <button className="primary" onClick={() => reload()}>{t.refresh}</button>
    </div>
    {loading && !summary && <LoadingPanel />}
    {summary && <>
      <section className="kpi-grid">
        <div className="kpi kpi-primary"><div className="kpi-label">{t.invoiceTotalSales}</div><div className="kpi-value">{money(summary.total_sales)}</div></div>
        <div className="kpi kpi-secondary"><div className="kpi-label">{t.invoiceCount}</div><div className="kpi-value">{summary.invoice_count}</div></div>
      </section>
      {summary.days.length > 0 && <div className="chart" style={{ marginTop: 16 }}>
        <h2>{t.dailySalesChart}</h2>
        <div className="chart-vertical" style={{ overflowX: 'auto', justifyContent: summary.days.length > 9 ? 'flex-start' : 'space-around' }}>
          {summary.days.map(d => <div className="col-bar" key={d.date} style={{ flex: '0 0 52px' }}>
            <div className="col" style={{ height: `${(Math.abs(Number(d.sales)) / maxDaily) * 100}%`, background: d.sales < 0 ? 'var(--danger)' : 'linear-gradient(180deg,var(--brand-primary),var(--brand-secondary))' }}>
              <span className="col-val">{money(d.sales)}</span>
            </div>
            <span className="col-label">{d.date.slice(5)}</span>
          </div>)}
        </div>
      </div>}
    </>}
    <h3 style={{ marginTop: 24 }}>{t.invoiceHistoryTitle}</h3>
    {!loading && invoices.length === 0 && <p className="empty-hint">{t.invoiceEmpty}</p>}
    {invoices.length > 0 && <table className="report-table">
      <thead><tr><th>{t.auditWhen}</th><th>{t.invoiceRazonSocial}</th><th>{t.invoiceUuid}</th><th>{t.total}</th><th>{t.statusCol}</th><th></th></tr></thead>
      <tbody>{invoices.map(inv => <tr key={inv.id}>
        <td>{fmtStamp(inv.stamped_at)}<br /><span className="meta">{inv.serie}{inv.folio}</span></td>
        <td>{inv.receptor_nombre}<br /><span className="meta">{inv.receptor_rfc}</span></td>
        <td style={{ fontSize: 11 }}>{inv.uuid}</td>
        <td>{inv.cfdi_type === 'E' ? '-' : ''}{money(inv.total)}</td>
        <td><span className="status-pill">{invoiceStatusLabel(inv)}</span></td>
        <td style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <button className="ghost" onClick={() => viewPdf(inv)} title={t.invoiceViewPdf}><FileText size={14} /></button>
          <button className="ghost" onClick={() => downloadXml(inv)} title={t.invoiceDownloadXml}><Download size={14} /></button>
          {/* cancel_status !== 'cancelado' no bastaba: 'en_proceso' (el PAC
              todavia no confirma la cancelacion) tambien debe ocultar el
              boton, o el cajero podia disparar una segunda solicitud de
              cancelacion SAT sobre la misma factura mientras la primera
              seguia pendiente (el backend ya lo bloquea, esto evita el
              intento inutil desde la UI). */}
          {inv.status === 'stamped' && inv.cancel_status !== 'cancelado' && inv.cancel_status !== 'en_proceso' && <button className="ghost" onClick={() => setCancelTarget(inv)} title={t.invoiceCancelAction}><Ban size={14} /></button>}
        </td>
      </tr>)}</tbody>
    </table>}
    {cancelTarget && <CancelInvoiceModal t={t} catalogs={catalogs} onConfirm={confirmCancel} onClose={() => setCancelTarget(null)} />}
  </section>;
}
