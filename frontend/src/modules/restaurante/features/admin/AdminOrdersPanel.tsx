import { useEffect, useState } from 'react';
import { Ban, CheckCircle2, FileBarChart } from 'lucide-react';
import { jsPDF } from 'jspdf';
import 'jspdf-autotable';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { EmptyState } from '../../components/shared/EmptyState';
import { RefreshButton } from '../../components/shared/RefreshButton';
import { labelStatus, placeLabel, fmtStamp, STATUS_VAR } from '../../utils/format';
import { CancelItemModal } from '../waiter/WaiterApp';
import { drawLogoPdf } from './pdfHelpers';
import type { Translations } from '../../i18n/translations';
import type { OrderItem } from '../../types/api';


/**
 * Panel exclusivo del administrador: lista los platillos que todavia se
 * pueden cancelar (pedido/en_preparacion, en cualquier mesa) y el
 * historial de lo ya cancelado (motivo, quien y cuando), para que la
 * decision de cancelar quede centralizada y sea auditable -- ni el mesero
 * ni cocina pueden iniciarla desde sus propias pantallas.
 */
/** Arma el PDF (tamano carta) del historial de cancelaciones, con el mismo
 * logo/estilo que el reporte de ventas (ver drawLogoPdf/buildReportPdf
 * mas abajo en este archivo). Se pide hasta 200 registros al backend (mas de
 * los 20 que se muestran en pantalla) para que el PDF sirva como respaldo
 * completo, no solo de lo ultimo visible en la tabla. */
function buildCancellationsPdf(items: OrderItem[], t: Translations) {
  const doc = new jsPDF();
  drawLogoPdf(doc, 14, 10, t);
  doc.setDrawColor(113, 113, 122);
  doc.setLineWidth(0.4);
  doc.line(14, 24, 196, 24);

  doc.setTextColor(20);
  doc.setFontSize(16);
  doc.text(t.recentCancellations, 14, 33);
  doc.setFontSize(10);
  doc.setTextColor(90);
  doc.text(`${new Date().toLocaleString()}`, 14, 40);
  doc.setTextColor(20);
  doc.setFontSize(11);
  doc.text(`${t.itemsCol}: ${items.length}`, 14, 48);

  doc.autoTable({
    startY: 55,
    head: [[t.table, t.itemsCol, t.cancelItemPrompt, t.cancelledByLabel, t.hourCol]],
    body: items.map(it => [
      placeLabel(t, it, true),
      `${it.quantity > 1 ? it.quantity + ' x ' : ''}${it.dish?.title || ''}`,
      it.cancel_reason || '-',
      it.cancelled_by_username || '-',
      it.cancelled_at ? new Date(it.cancelled_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '-',
    ]),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [138, 74, 74], textColor: 255 },
  });

  doc.save(`cancelaciones_${new Date().toISOString().slice(0, 10)}.pdf`);
}

export function AdminOrdersPanel({ t }: { t: Translations }) {
  const toast = useToast();
  const [items, setItems] = useState<OrderItem[]>([]);
  const [log, setLog] = useState<OrderItem[]>([]);
  const [cancelTarget, setCancelTarget] = useState<OrderItem | null>(null);

  async function loadActive() {
    try {
      const data = await api.kitchenBoard();
      setItems((data.items || []).filter(it => ['pedido', 'en_preparacion'].includes(it.status || '')));
    } catch (e) { console.error(e); }
  }
  async function loadLog() {
    try { const data = await api.cancelledItems(20); setLog(data.items || []); } catch (e) { console.error(e); }
  }
  async function reload() { loadActive(); loadLog(); }
  // reload/loadActive no dependen de ningun prop/estado que cambie entre
  // renders (solo llaman a la API y a los setters, ambos estables) -- se
  // omiten a proposito del arreglo de dependencias: el efecto debe correr
  // una sola vez al montar, no en cada render (que es cuando reload/
  // loadActive cambiarian de identidad, al no estar envueltas en useCallback).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); const id = setInterval(loadActive, 6000); return () => clearInterval(id); }, []);

  async function confirmCancel(reason: string) {
    await api.cancelItem(cancelTarget!.order_id, cancelTarget!.id, reason);
    setCancelTarget(null);
    reload();
  }

  async function downloadPdf() {
    try {
      // Se piden hasta 200 registros para el PDF (el panel en pantalla solo
      // muestra los ultimos 20), asi el PDF sirve como respaldo completo.
      const data = await api.cancelledItems(200);
      buildCancellationsPdf(data.items || [], t);
    } catch (e) {
      toast.error(t.pdfCancelledError + ((e as Error)?.message ? ` (${(e as Error).message})` : ''));
    }
  }

  return <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
      <h3 style={{ margin: 0 }}>{t.activeOrdersAdmin}</h3>
      <RefreshButton t={t} onClick={reload} />
    </div>
    {items.length === 0
      ? <EmptyState icon={CheckCircle2} title={t.noCancellableItems} />
      : <table className="report-table">
        <thead><tr><th>{t.table}</th><th>{t.itemsCol}</th><th>{t.statusCol}</th><th></th></tr></thead>
        <tbody>
          {items.map(it => <tr key={it.id}>
            <td>{placeLabel(t, it, true)}</td>
            <td>{it.quantity > 1 ? `${it.quantity} x ` : ''}{it.dish?.title}</td>
            <td><span className="status-pill" style={{ background: `var(${STATUS_VAR[it.status || 'pedido']})33`, color: `var(${STATUS_VAR[it.status || 'pedido']})` }}>{labelStatus(it.status || 'pedido', t)}</span></td>
            <td><button className="ghost" onClick={() => setCancelTarget(it)}><Ban size={14} /> {t.cancelItem}</button></td>
          </tr>)}
        </tbody>
      </table>}

    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 28 }}>
      <h3 style={{ margin: 0 }}>{t.recentCancellations}</h3>
      <button className="ghost" onClick={downloadPdf}><FileBarChart size={16} style={{ marginRight: 6 }} />{t.generatePdf}</button>
    </div>
    {log.length === 0
      ? <p className="empty-hint">{t.noData}</p>
      : <table className="report-table">
        <thead><tr><th>{t.table}</th><th>{t.itemsCol}</th><th>{t.cancelItemPrompt}</th><th>{t.cancelledByLabel}</th></tr></thead>
        <tbody>
          {log.map(it => <tr key={it.id}>
            <td>{placeLabel(t, it, true)}</td>
            <td>{it.quantity > 1 ? `${it.quantity} x ` : ''}{it.dish?.title}</td>
            <td>{it.cancel_reason}</td>
            <td>{it.cancelled_by_username || '-'}<br /><span className="meta">{fmtStamp(it.cancelled_at)}</span></td>
          </tr>)}
        </tbody>
      </table>}
    {cancelTarget && <CancelItemModal t={t} item={cancelTarget} onConfirm={confirmCancel} onClose={() => setCancelTarget(null)} />}
  </div>;
}
