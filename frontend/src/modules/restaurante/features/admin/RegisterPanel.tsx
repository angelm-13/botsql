import { useEffect, useState } from 'react';
import { Receipt } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { useConfirmDialog } from '../../contexts/ConfirmContext';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { RegisterOpenTooLongWarning } from '../../components/shared/RegisterOpenTooLongWarning';
import { money, OPENING_AMOUNT_PRESETS } from '../../utils/format';
import { ReceiptModal, RegisterCutReceipt } from './Receipts';
import type { Translations } from '../../i18n/translations';
import type { CashSession } from '../../types/api';

export function RegisterPanel({ t }: { t: Translations }) {
  const toast = useToast();
  const confirmDialog = useConfirmDialog();
  const [current, setCurrent] = useState<CashSession | null | undefined>(undefined);
  const [history, setHistory] = useState<CashSession[]>([]);
  const [openingAmount, setOpeningAmount] = useState<number | string>(0);
  const [closingAmount, setClosingAmount] = useState<number | string>(0);
  const [notes, setNotes] = useState('');
  const [now, setNow] = useState(() => new Date());
  const [cutReceipt, setCutReceipt] = useState<CashSession | null>(null); // corte de caja recien cerrado, o uno reimpreso del historial
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    const [cur, hist] = await Promise.all([api.registerCurrent(), api.registerHistory()]);
    setCurrent(cur); setHistory(hist.items || []);
  }
  useEffect(() => { load().catch(console.error); const id = setInterval(() => load().catch(console.error), 15000); return () => clearInterval(id); }, []);
  // Reloj propio del dispositivo para calcular "abierta desde hace Xh Ym" en vivo,
  // sin depender de otro fetch al backend.
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 30000); return () => clearInterval(id); }, []);

  async function open() {
    if (submitting) return;
    if (Number(openingAmount) < 0) { toast.error(t.negativeAmountError); return; }
    setSubmitting(true);
    try {
      await api.openRegister(Number(openingAmount));
      toast.success(t.registerOpen);
      load().catch(console.error);
    } catch (e) { toast.error((e as Error).message); } finally { setSubmitting(false); }
  }
  async function close() {
    // Sin este guard, doble clic (o un clic mientras la primera peticion
    // seguia en vuelo) disparaba dos POST /register/close: la segunda
    // siempre era rechazada por el backend (409, ya no hay caja abierta),
    // pero el cajero veia un error confuso justo despues de una accion que
    // en apariencia si habia funcionado.
    if (submitting) return;
    if (Number(closingAmount) < 0) { toast.error(t.negativeAmountError); return; }
    // Un solo campo de conteo, pero el cajero ya vio el efectivo esperado
    // en vivo (liveSummary) antes de escribirlo: este dialogo resume la
    // diferencia una ultima vez para evitar un cierre por error, sin
    // agregar un paso/modal nuevo al flujo.
    if (liveSummary) {
      const diff = Number(closingAmount || 0) - liveSummary.cash_expected;
      const diffLabel = diff === 0 ? t.differenceNone : (diff > 0 ? `+${money(diff)}` : money(diff));
      if (!await confirmDialog(`${t.confirmCloseRegisterWithDiff} ${diffLabel}`)) return;
    }
    setSubmitting(true);
    // Sin try/catch, un cierre rechazado por el backend (ej. la caja ya se
    // cerro desde otra pestana) fallaba en silencio: el cajero no via
    // ningun aviso y la pantalla se quedaba como si nada hubiera pasado.
    try {
      const closedSession = await api.closeRegister(Number(closingAmount), notes);
      setNotes('');
      setCutReceipt(closedSession);
      toast.success(t.registerClosed);
      load().catch(console.error);
    } catch (e) { toast.error((e as Error).message); } finally { setSubmitting(false); }
  }

  if (current === undefined) return <LoadingPanel label={t.loadingRegister} />;
  const openedMinutesAgo = current ? Math.max(0, Math.floor((now.getTime() - new Date(current.opened_at).getTime()) / 60000)) : 0;
  const openedHours = Math.floor(openedMinutesAgo / 60);
  const openedMins = openedMinutesAgo % 60;
  const liveSummary = current?.live_summary;
  const closingDiff = liveSummary ? Number(closingAmount || 0) - liveSummary.cash_expected : null;
  return <section>
    {!current ? <div className="hero-card" style={{ maxWidth: 420 }}>
      <h2>{t.registerClosed}</h2>
      <p className="sub-heading" style={{ margin: '0 0 4px' }}>{t.quickAmount}</p>
      <div className="pay-quick-row">
        {OPENING_AMOUNT_PRESETS.map(a => <button key={a} className={Number(openingAmount) === a ? 'pay-quick-suggested' : ''} onClick={() => setOpeningAmount(a)}>${a}</button>)}
      </div>
      <div className="field" style={{ marginTop: 14 }}><label>{t.openingAmount}</label><input type="number" min="0" value={openingAmount} onChange={e => setOpeningAmount(e.target.value)} /></div>
      <button className="primary big" disabled={submitting} onClick={open}>{t.openRegister}</button>
    </div> : <div className="hero-card" style={{ maxWidth: 480 }}>
      <h2>{t.registerOpen}</h2>
      {current.open_too_long && <RegisterOpenTooLongWarning t={t} />}
      <p className="pill-tag">{t.openingAmount}: {money(current.opening_amount)}</p>
      <p className="pill-tag">{t.openedAt} {new Date(current.opened_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ({t.openedSince} {openedHours > 0 ? `${openedHours}h ` : ''}{openedMins}m)</p>
      {/* Desglose EN VIVO de este turno: el cajero ya sabe cuanto se espera
          encontrar en el cajon antes de contarlo, en vez de enterarse solo
          al cerrar. Sigue siendo un solo campo de conteo abajo. */}
      {liveSummary && <div className="register-live-summary">
        <div className="pay-summary-row"><span>{t.totalSalesExpected}</span><span>{money(liveSummary.total_sales)}</span></div>
        <div className="pay-summary-row"><span>{t.tipsExpectedTotal}</span><span>{money(liveSummary.total_tips)}</span></div>
        <div className="pay-summary-row"><span>{t.cashExpected}</span><strong>{money(liveSummary.cash_expected)}</strong></div>
      </div>}
      <div className="field"><label>{t.closingAmount}</label><input type="number" min="0" value={closingAmount} onChange={e => setClosingAmount(e.target.value)} /></div>
      {liveSummary && <p className="pill-tag" style={{ borderColor: closingDiff === 0 ? undefined : ((closingDiff || 0) > 0 ? 'var(--green)' : 'var(--danger)') }}>
        {t.difference}: <strong style={{ color: closingDiff === 0 ? 'inherit' : ((closingDiff || 0) > 0 ? 'var(--green)' : 'var(--danger)') }}>{money(closingDiff)}</strong>
      </p>}
      <div className="field"><label>{t.notes}</label><input value={notes} onChange={e => setNotes(e.target.value)} /></div>
      <button className="primary big" disabled={submitting} onClick={close}>{t.closeRegister}</button>
    </div>}
    <h2 style={{ marginTop: 30 }}>{t.registerHistory}</h2>
    <table className="report-table">
      <thead><tr><th>{t.openedDateCol}</th><th>{t.closedDateCol}</th><th>{t.openingAmount}</th><th>{t.closingAmount}</th><th>{t.expectedAmount}</th><th>{t.difference}</th><th></th></tr></thead>
      <tbody>{history.map(h => <tr key={h.id}>
        <td>{h.opened_at ? new Date(h.opened_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '-'}</td>
        <td>{h.closed_at ? new Date(h.closed_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : t.stillOpen}</td>
        <td>{money(h.opening_amount)}</td><td>{h.closing_amount != null ? money(h.closing_amount) : '-'}</td><td>{h.expected_amount != null ? money(h.expected_amount) : '-'}</td><td>{h.difference != null ? money(h.difference) : '-'}</td>
        <td>{h.closed_at && <button onClick={() => setCutReceipt(h)}><Receipt size={14} /> {t.printTicket}</button>}</td>
      </tr>)}</tbody>
    </table>
    {cutReceipt && <ReceiptModal t={t} onClose={() => setCutReceipt(null)}><RegisterCutReceipt t={t} session={cutReceipt} /></ReceiptModal>}
  </section>;
}
