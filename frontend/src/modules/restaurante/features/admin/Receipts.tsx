import { useState, type ReactNode } from 'react';
import { ArrowLeft, FileText, Receipt } from 'lucide-react';
import { Portal } from '../../components/shared/Portal';
import { FlameMark } from '../../components/shared/Brand';
import { money } from '../../utils/format';
import { InvoiceModal } from './Invoicing';
import type { Translations } from '../../i18n/translations';
import type { CashSession, PaymentMethod, PayVisitResult, SalesReport } from '../../types/api';

// Estructura de un ticket de venta armada por PendingPayments (PayScreen)
// tras cobrar una cuenta -- no es el to_dict() de ningun modelo del backend,
// sino una vista ya combinada de Order+Visit+resultado de /pay o /visits/:id/pay,
// pensada para imprimirse/mostrarse tal cual en SaleReceipt de aqui abajo.
export interface ReceiptLineItem {
  quantity: number
  unit_price: number
  dish?: { title: string } | null
  diner_index?: number
}

export interface SaleReceiptData {
  tableNumber: number | null
  isTakeout: boolean
  customerName: string | null
  visitLabelId: number | null
  folioIds: number[]
  dinerLabel: string | null
  items: ReceiptLineItem[]
  subtotal: number
  tax_amount: number
  discount_amount: number
  tip_amount: number
  total: number
  change_amount: number | null
  payment_method: PaymentMethod | null
  received_amount: number | null
  cash_amount: number | null
  paid_at: string | null
  cashierUsername?: string
  dinerBreakdown?: PayVisitResult['orders_breakdown']
  visitId: number | null
  orderIds: number[]
}

/** Pantalla de ticket tras cobrar, tambien de pagina completa (no ventana
 * flotante), con boton para imprimir y otro para "Corregir cobro" (deshacer
 * el pago y volver a la pantalla de cobro con la misma cuenta), en vez de
 * dar el cobro por cerrado sin remedio. */
export function ReceiptScreen({ t, data, onClose, onCorrect }: { t: Translations; data: SaleReceiptData; onClose: () => void; onCorrect: () => void }) {
  const [showInvoice, setShowInvoice] = useState(false);
  return <main className="page pay-page">
    <button className="ghost" onClick={onClose}><ArrowLeft size={16} /> {t.backToPending}</button>
    <div className="pay-card" style={{ maxWidth: 420, margin: '0 auto' }}>
      <SaleReceipt t={t} data={data} />
      <div className="receipt-modal-actions no-print" style={{ marginTop: 18 }}>
        <button className="primary" onClick={() => window.print()}><Receipt size={16} /> {t.printTicket}</button>
        <button className="ghost" onClick={() => setShowInvoice(true)}><FileText size={16} /> {t.invoiceAction}</button>
        <button className="ghost" onClick={onCorrect}>{t.correctPayment}</button>
        <button className="ghost" onClick={onClose}>{t.close}</button>
      </div>
    </div>
    {showInvoice && <InvoiceModal t={t} orderIds={data.orderIds} onClose={() => setShowInvoice(false)} />}
  </main>;
}

/* ------------------- Impresion en ticket termico (58mm) ------------------- */

/** Modal generico para previsualizar/imprimir un ticket de 58mm. El contenido
 * (children) debe tener la clase "receipt-print"; los botones e chrome del
 * modal llevan "no-print" para no aparecer en el papel impreso. */
export function ReceiptModal({ t, onClose, children }: { t: Translations; onClose: () => void; children: ReactNode }) {
  return <Portal><div className="modal">
    <div className="ticket-panel no-print-shell" style={{ width: 'min(360px,100%)' }}>
      <button className="close no-print" onClick={onClose}>&times;</button>
      {children}
      <div className="receipt-modal-actions no-print">
        <button className="primary" onClick={() => window.print()}><Receipt size={16} /> {t.printTicket}</button>
        <button className="ghost" onClick={onClose}>{t.close}</button>
      </div>
    </div>
  </div></Portal>;
}

/** Encabezado con el logo de la marca (el mismo FlameMark que usa el resto
 * de la app, en chiquito) para los tres tickets de 58mm: venta, corte de
 * caja y reporte condensado. */
function ReceiptLogoHeader({ t }: { t?: Translations }) {
  return <div className="receipt-logo-head">
    <FlameMark size={26} />
    <h2>{t ? t.welcome : 'MI RESTAURANTE'}</h2>
  </div>;
}

function SaleReceipt({ t, data }: { t: Translations; data: SaleReceiptData }) {
  const when = data.paid_at ? new Date(data.paid_at) : new Date();
  const folio = (data.folioIds || data.orderIds || []).join(',');
  const isMixed = data.payment_method === 'mixto';
  // Cuenta combinada de 2+ comensales: el backend regresa cuanto le toco a
  // cada quien (subtotal + su parte de IVA/descuento/propina, ya repartido
  // de verdad) -- se usa para agrupar el detalle del ticket por comensal
  // en vez de una sola lista de platillos revueltos sin decir de quien era cada uno.
  const dinerBreakdown = data.dinerBreakdown && data.dinerBreakdown.length > 1 ? data.dinerBreakdown : null;
  return <div className="receipt-print">
    <ReceiptLogoHeader t={t} />
    <p className="receipt-sub">{t.tagline}</p>
    <div className="receipt-sep" />
    <p className="receipt-small">{when.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</p>
    {folio && <p className="receipt-small">{t.ticketFolio} #{folio}</p>}
    {data.cashierUsername && <p className="receipt-small">{t.cashierLabel}: {data.cashierUsername}</p>}
    <p className="receipt-bold">{data.isTakeout ? `${t.takeoutLabel} #${data.visitLabelId ?? ''}${data.customerName ? ' - ' + data.customerName : ''}` : `${t.table} ${data.tableNumber}`}{data.dinerLabel ? ` - ${data.dinerLabel}` : ''}</p>
    <div className="receipt-sep" />
    {dinerBreakdown ? dinerBreakdown.map(d => <div key={d.order_id}>
      <div className="receipt-line receipt-bold"><span>{t.diner} {d.diner_index}</span><span>{money(d.total)}</span></div>
      {(data.items || []).filter(it => it.diner_index === d.diner_index).map((it, idx) => <div className="receipt-item receipt-small" key={idx}>
        <span>{it.quantity}x {it.dish ? it.dish.title : ''}</span>
        <span>{money((it.quantity || 0) * Number(it.unit_price || 0))}</span>
      </div>)}
    </div>) : (data.items || []).map((it, idx) => <div className="receipt-item" key={idx}>
      <span>{it.quantity}x {it.dish ? it.dish.title : ''}</span>
      <span>{money((it.quantity || 0) * Number(it.unit_price || 0))}</span>
    </div>)}
    <div className="receipt-sep" />
    <div className="receipt-line"><span>{t.subtotal}</span><span>{money(data.subtotal)}</span></div>
    {Number(data.tax_amount) > 0 && <div className="receipt-line"><span>{t.tax}</span><span>{money(data.tax_amount)}</span></div>}
    {Number(data.discount_amount) > 0 && <div className="receipt-line"><span>{t.discount}</span><span>-{money(data.discount_amount)}</span></div>}
    {Number(data.tip_amount) > 0 && <div className="receipt-line"><span>{t.tipAmount}</span><span>{money(data.tip_amount)}</span></div>}
    <div className="receipt-sep" />
    <div className="receipt-line receipt-total"><span>{t.total}</span><span>{money(data.total)}</span></div>
    <div className="receipt-sep" />
    <p className="receipt-small">{t.paymentMethod}: {data.payment_method || '-'}</p>
    {isMixed && data.cash_amount != null && <>
      <div className="receipt-line receipt-small"><span>{t.cash}</span><span>{money(data.cash_amount)}</span></div>
      <div className="receipt-line receipt-small"><span>{t.mixedRemainder}</span><span>{money(Number(data.total || 0) - Number(data.cash_amount || 0))}</span></div>
    </>}
    {data.received_amount != null && <div className="receipt-line receipt-small"><span>{t.received}</span><span>{money(data.received_amount)}</span></div>}
    {data.change_amount != null && <div className="receipt-line receipt-small"><span>{t.change}</span><span>{money(data.change_amount)}</span></div>}
    <div className="receipt-sep" />
    <p className="receipt-center receipt-small">{t.thanksVisit}</p>
  </div>;
}

export function RegisterCutReceipt({ t, session }: { t: Translations; session: CashSession }) {
  let breakdown: { payment_breakdown?: Record<string, number>; total_sales: number; total_tips: number; orders_count: number } | null = null;
  try { breakdown = session.sales_breakdown_json ? JSON.parse(session.sales_breakdown_json) : null; } catch { breakdown = null; }
  return <div className="receipt-print">
    <ReceiptLogoHeader t={t} />
    <p className="receipt-sub">{t.registerCutTitle}</p>
    <div className="receipt-sep" />
    <p className="receipt-small">{t.openedAt} {session.opened_at ? new Date(session.opened_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '-'}</p>
    <p className="receipt-small">{t.closedDateCol}: {session.closed_at ? new Date(session.closed_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '-'}</p>
    <div className="receipt-sep" />
    <div className="receipt-line"><span>{t.openingAmount}</span><span>{money(session.opening_amount)}</span></div>
    {breakdown && Object.entries(breakdown.payment_breakdown || {}).map(([method, amount]) => (
      <div className="receipt-line" key={method}><span>{method}</span><span>{money(amount)}</span></div>
    ))}
    {breakdown && <div className="receipt-line receipt-bold"><span>{t.totalSales}</span><span>{money(breakdown.total_sales)}</span></div>}
    {breakdown && <div className="receipt-line"><span>{t.tips}</span><span>{money(breakdown.total_tips)}</span></div>}
    {breakdown && <div className="receipt-line receipt-small"><span>{t.orders}</span><span>{breakdown.orders_count}</span></div>}
    <div className="receipt-sep" />
    <div className="receipt-line"><span>{t.expectedAmount}</span><span>{money(session.expected_amount)}</span></div>
    <div className="receipt-line"><span>{t.closingAmount}</span><span>{money(session.closing_amount)}</span></div>
    <div className="receipt-line receipt-total"><span>{t.difference}</span><span>{money(session.difference)}</span></div>
    <div className="receipt-sep" />
    <p className="receipt-center receipt-small">{t.thanksVisit}</p>
  </div>;
}

export function ReportReceipt({ t, report, start, end }: { t: Translations; report: SalesReport; start?: string | null; end?: string | null }) {
  return <div className="receipt-print">
    <ReceiptLogoHeader t={t} />
    <p className="receipt-sub">{t.reports}</p>
    <p className="receipt-small receipt-center">{start || '...'} - {end || t.today}</p>
    <div className="receipt-sep" />
    {(report.days || []).map(d => <div key={d.date} style={{ marginBottom: 6 }}>
      <div className="receipt-line receipt-bold"><span>{d.date}</span><span>{d.orders} {t.orders}</span></div>
      <div className="receipt-line receipt-small"><span>{t.totalSales}</span><span>{money(d.sales)}</span></div>
      <div className="receipt-line receipt-small"><span>{t.tips}</span><span>{money(d.tips)}</span></div>
    </div>)}
    <div className="receipt-sep" />
    <div className="receipt-line receipt-total"><span>{t.orders}</span><span>{report.total_orders}</span></div>
    <div className="receipt-line receipt-bold"><span>{t.totalSales}</span><span>{money(report.total_sales)}</span></div>
    <div className="receipt-line receipt-bold"><span>{t.tips}</span><span>{money(report.total_tips)}</span></div>
  </div>;
}
