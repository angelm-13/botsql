import { useEffect, useState } from 'react';
import { ArrowLeft, Banknote, CheckCircle2, CreditCard, Delete, DollarSign, Landmark, Layers, Loader2, Lock, Percent } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { EmptyState } from '../../components/shared/EmptyState';
import { RefreshButton } from '../../components/shared/RefreshButton';
import { money, placeLabel, distributeProportionally } from '../../utils/format';
import { t_table } from '../kitchen/KitchenBoard';
import { CorrectPaymentModal } from '../waiter/WaiterApp';
import { ReceiptScreen, type SaleReceiptData } from './Receipts';
import type { Translations } from '../../i18n/translations';
import type { Order, OrderItem, PaymentMethod, User } from '../../types/api';


// Al cobrar una mesa junta, se pierde de vista de quien era cada platillo
// en cuanto se aplana orders[].items en un solo arreglo -- estos dos
// helpers evitan eso: cada item queda marcado con el comensal al que
// pertenecia, y se guarda aparte el subtotal (solo consumo, sin
// propina/IVA/descuento todavia) de cada comensal, para poder mostrar
// "cuanto le toca a cada quien" en PayScreen y en el recibo.
// Platillos cancelados nunca se cobran (ver Order.subtotal en el backend,
// que ya los excluye), pero seguian pasandose tal cual a PayScreen/
// SaleReceipt para "listar" los items de la cuenta -- ambos los mostraban
// con su precio como si formaran parte de lo cobrado, contradiciendo el
// subtotal real (que SI los excluye) en el mismo recibo impreso al
// cliente. Se usa este helper en todos los lugares que arman `items` para
// pantalla de cobro/recibo.
function billableItems(items: OrderItem[] | undefined): OrderItem[] {
  return (items || []).filter(it => it.status !== 'cancelado');
}
function taggedItemsByDiner(orders: Order[]): (OrderItem & { diner_index: number })[] {
  return orders.flatMap(o => billableItems(o.items).map(it => ({ ...it, diner_index: o.diner_index })));
}
function dinerSubtotals(orders: Order[]): { diner_index: number; subtotal: number }[] {
  return orders.map(o => ({ diner_index: o.diner_index, subtotal: Number(o.subtotal || 0) }));
}

type PayTarget =
  | { mode: 'together'; visitId: number; visitDailyNumber: number | null | undefined; tableNumber: number | null; isTakeout: boolean; customerName: string | null; subtotal: number; items: (OrderItem & { diner_index: number })[]; diners: { diner_index: number; subtotal: number }[] }
  | { mode: 'single'; order: Order; visitDailyNumber?: number | null; tableNumber: number | null; isTakeout: boolean; customerName: string | null; subtotal: number; items: OrderItem[] };

interface VisitGroup {
  visitId: number
  visitDailyNumber?: number
  tableNumber: number | null
  isTakeout?: boolean
  customerName: string | null
  orders: Order[]
}

export function PendingPayments({ t, user, onGoToRegister }: { t: Translations; user: User | null; onGoToRegister?: () => void }) {
  const toast = useToast();
  const [orders, setOrders] = useState<Order[]>([]);
  const [registerOpen, setRegisterOpen] = useState(true); // optimista hasta confirmar con el backend
  const [payTarget, setPayTarget] = useState<PayTarget | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [receipt, setReceipt] = useState<SaleReceiptData | null>(null); // datos del ticket a mostrar/imprimir tras cobrar
  const [showCorrectModal, setShowCorrectModal] = useState(false);

  // Carga las cuentas por cobrar Y el estado real de la caja. No se puede
  // cobrar (ni junto ni por separado) si no hay una caja abierta: el
  // backend tambien lo valida (409 register_closed), pero aqui lo
  // reflejamos en la interfaz para que el cajero no intente cobrar en vano.
  async function load() {
    const [ordersData, registerData] = await Promise.all([
      api.orders('?status=entregado&per_page=100'),
      api.registerCurrent(),
    ]);
    setOrders(ordersData.items || []);
    setRegisterOpen(!!registerData);
  }
  useEffect(() => {
    load().catch(console.error);
    const id = setInterval(() => load().catch(console.error), 10000);
    return () => clearInterval(id);
  }, []);

  const groups: Record<number, VisitGroup> = {};
  orders.forEach(o => {
    const key = o.visit_id;
    if (!groups[key]) groups[key] = { visitId: key, visitDailyNumber: o.visit_daily_number, tableNumber: o.table_number ?? null, isTakeout: o.is_takeout, customerName: o.customer_name ?? null, orders: [] };
    groups[key].orders.push(o);
  });
  // Mesas primero (ordenadas por numero), pedidos para llevar despues
  // (ordenados por antiguedad): table_number es null en para llevar, y
  // comparar null - null da NaN si se ordenara igual que las mesas.
  const groupList = Object.values(groups).sort((a, b) => (Number(a.isTakeout) - Number(b.isTakeout)) || ((a.tableNumber || 0) - (b.tableNumber || 0)) || (a.visitId - b.visitId));

  async function confirmPay(payload: Record<string, unknown>) {
    try {
      let receiptData: SaleReceiptData;
      let orderIds: number[];
      if (payTarget!.mode === 'together') {
        const target = payTarget!;
        const result = await api.payVisit(target.visitId, payload);
        orderIds = result.orders_paid || [];
        receiptData = {
          tableNumber: target.tableNumber, isTakeout: target.isTakeout, customerName: target.customerName, visitLabelId: target.visitDailyNumber ?? target.visitId,
          folioIds: result.orders_daily_numbers || orderIds,
          dinerLabel: null, items: target.items,
          subtotal: result.subtotal, tax_amount: result.tax_amount, discount_amount: result.discount_amount,
          tip_amount: result.tip_amount, total: result.total, change_amount: result.change_amount,
          payment_method: payload.payment_method as PaymentMethod, received_amount: payload.received_amount as number ?? null, cash_amount: payload.cash_amount as number ?? null,
          paid_at: new Date().toISOString(), cashierUsername: user?.username,
          dinerBreakdown: result.orders_breakdown,
          visitId: null, orderIds: [],
        };
      } else {
        const target = payTarget!;
        const result = await api.pay(target.order.id, payload);
        orderIds = [target.order.id];
        receiptData = {
          tableNumber: target.tableNumber, isTakeout: target.isTakeout, customerName: target.customerName, visitLabelId: target.visitDailyNumber ?? target.order.visit_id,
          folioIds: [result.daily_number ?? target.order.id],
          dinerLabel: target.isTakeout ? null : `${t.diner} ${target.order.diner_index}`, items: target.items,
          subtotal: result.subtotal ?? 0, tax_amount: result.tax_amount, discount_amount: result.discount_amount,
          tip_amount: result.tip_amount, total: result.total ?? 0, change_amount: null,
          payment_method: result.payment_method, received_amount: result.received_amount, cash_amount: result.cash_amount,
          paid_at: result.paid_at, cashierUsername: user?.username,
          visitId: null, orderIds: [],
        };
      }
      // Se guarda como parte del ticket para poder "Corregir cobro" despues,
      // sin tener que volver a buscar que ordenes fueron las que se cobraron.
      receiptData.visitId = payTarget!.mode === 'together' ? payTarget!.visitId : null;
      receiptData.orderIds = orderIds;
      setPayTarget(null);
      setReceipt(receiptData);
      load().catch(console.error);
    } catch (e) {
      toast.error((e as Error).message);
      load().catch(console.error);
    }
  }

  // Deshace el cobro que se acaba de mostrar en el ticket, y regresa
  // directamente a la pantalla de pago con la misma cuenta para volver a
  // cobrarla bien (por si el cliente cambia de metodo de pago, o el cajero
  // se equivoco en el monto/propina). Pide motivo obligatorio (CorrectPaymentModal),
  // igual que cancelar un platillo.
  function correctPayment() { setShowCorrectModal(true); }

  async function doCorrectPayment(reason: string) {
    const r = receipt!;
    if (r.visitId) {
      await api.unpayVisit(r.visitId, r.orderIds, reason);
    } else {
      await api.unpay(r.orderIds[0], reason);
    }
    const data = await api.orders('?status=entregado&per_page=100');
    setOrders(data.items || []);
    const items = r.visitId
      ? (data.items || []).filter(o => o.visit_id === r.visitId)
      : (data.items || []).filter(o => o.id === r.orderIds[0]);
    if (r.visitId) {
      setPayTarget({ mode: 'together', visitId: r.visitId, visitDailyNumber: r.visitLabelId, tableNumber: r.tableNumber, isTakeout: r.isTakeout, customerName: r.customerName, subtotal: items.reduce((s, o) => s + Number(o.subtotal || 0), 0), items: taggedItemsByDiner(items), diners: dinerSubtotals(items) });
    } else if (items[0]) {
      setPayTarget({ mode: 'single', order: items[0], visitDailyNumber: r.visitLabelId, tableNumber: r.tableNumber, isTakeout: r.isTakeout, customerName: r.customerName, subtotal: Number(items[0].subtotal || 0), items: billableItems(items[0].items) });
    }
    setShowCorrectModal(false);
    setReceipt(null);
  }

  // Cobrar reemplaza toda esta pestana por su propia pantalla completa (en
  // vez de una ventana flotante), para que nunca dependa del tamano del
  // contenedor de "cuentas por cobrar" y siempre se vea a tamano completo.
  if (payTarget) {
    return <PayScreen
      t={t}
      subtotal={payTarget.subtotal}
      items={payTarget.items}
      diners={payTarget.mode === 'together' ? payTarget.diners : null}
      label={payTarget.mode === 'together' ? `${t.combinedBill} - ${placeLabel(t, { is_takeout: payTarget.isTakeout, table_number: payTarget.tableNumber, customer_name: payTarget.customerName, visit_id: payTarget.visitId, visit_daily_number: payTarget.visitDailyNumber ?? undefined })}` : t_table(t, payTarget.order)}
      onCancel={() => setPayTarget(null)}
      onConfirm={confirmPay}
    />;
  }
  if (receipt) {
    return <>
      <ReceiptScreen t={t} data={receipt} onClose={() => setReceipt(null)} onCorrect={correctPayment} />
      {showCorrectModal && <CorrectPaymentModal t={t} onConfirm={doCorrectPayment} onClose={() => setShowCorrectModal(false)} />}
    </>;
  }

  return <section className="orders-list">
    <div className="board-refresh-row"><RefreshButton t={t} onClick={load} /></div>
    {!registerOpen && <div className="register-closed-banner"><Lock size={18} /><span>{t.registerClosedPayHint}</span>{onGoToRegister && <button className="ghost" onClick={onGoToRegister}>{t.goToRegister}</button>}</div>}
    {groupList.length === 0 && <EmptyState icon={CheckCircle2} title={t.empty} />}
    {groupList.map(g => {
      const combined = g.orders.reduce((sum, o) => sum + Number(o.subtotal || 0), 0);
      const isExpanded = !!expanded[g.visitId];
      const hasMultipleDiners = g.orders.length >= 2;
      return <div className="table-bill-card" key={g.visitId}>
        <div className="table-bill-header">
          <span>{placeLabel(t, { is_takeout: g.isTakeout, table_number: g.tableNumber, customer_name: g.customerName, visit_id: g.visitId, visit_daily_number: g.visitDailyNumber })} &middot; {g.orders.length} {g.orders.length === 1 ? t.diner : t.diners}</span>
          <strong>{money(combined)}</strong>
        </div>
        <div className="table-bill-actions">
          {hasMultipleDiners ? <>
            <button className="primary" disabled={!registerOpen} onClick={() => setPayTarget({ mode: 'together', visitId: g.visitId, visitDailyNumber: g.visitDailyNumber, tableNumber: g.tableNumber, isTakeout: !!g.isTakeout, customerName: g.customerName, subtotal: combined, items: taggedItemsByDiner(g.orders), diners: dinerSubtotals(g.orders) })}>{t.payTogether}</button>
            <button className="ghost" onClick={() => setExpanded(e => ({ ...e, [g.visitId]: !isExpanded }))}>{isExpanded ? t.hideDiners : t.paySeparate}</button>
          </> : <button className="primary" disabled={!registerOpen} onClick={() => setPayTarget({ mode: 'single', order: g.orders[0], visitDailyNumber: g.visitDailyNumber, tableNumber: g.tableNumber, isTakeout: !!g.isTakeout, customerName: g.customerName, subtotal: Number(g.orders[0].subtotal || 0), items: billableItems(g.orders[0].items) })}>{t.pay}</button>}
        </div>
        {hasMultipleDiners && isExpanded && <div className="table-bill-diners">
          {g.orders.map(o => <div className="order-line" key={o.id}>
            <span>{t.diner} {o.diner_index}</span>
            <strong>{money(o.subtotal)}</strong>
            <button disabled={!registerOpen} onClick={() => setPayTarget({ mode: 'single', order: o, tableNumber: g.tableNumber, isTakeout: !!g.isTakeout, customerName: g.customerName, subtotal: Number(o.subtotal || 0), items: billableItems(o.items) })}>{t.pay}</button>
          </div>)}
        </div>}
      </div>;
    })}
  </section>;
}

const PAYMENT_METHODS: { key: PaymentMethod; icon: typeof Banknote }[] = [
  { key: 'efectivo', icon: Banknote },
  { key: 'tarjeta', icon: CreditCard },
  { key: 'transferencia', icon: Landmark },
  { key: 'mixto', icon: Layers },
];

const QUICK_CASH_AMOUNTS = [20, 50, 100, 200, 500, 1000];

interface PayScreenProps {
  t: Translations
  subtotal: number
  items: (OrderItem & { diner_index?: number })[]
  diners?: { diner_index: number; subtotal: number }[] | null
  label: string
  onCancel: () => void
  onConfirm: (payload: Record<string, unknown>) => Promise<void>
}

/** Pantalla de cobro. Es una pantalla completa propia (mismo patron que
 * TablesView -> VisitWorkspace), NO una ventana flotante sobre otra
 * pantalla: asi nunca depende ni se ajusta al tamano del contenedor de
 * "cuentas por cobrar" ni de nada mas alrededor. */
export function PayScreen({ t, subtotal, items, diners, label, onCancel, onConfirm }: PayScreenProps) {
  const [paying, setPaying] = useState(false);
  const [tipType, setTipType] = useState<'porcentaje' | 'manual'>('porcentaje');
  const [tipPercent, setTipPercent] = useState(10);
  const [tipManual, setTipManual] = useState<number | string>(0);
  const [applyTax, setApplyTax] = useState(false);
  const [discountInput, setDiscountInput] = useState('0');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('efectivo');
  const [receivedInput, setReceivedInput] = useState('');
  const [mixedCashInput, setMixedCashInput] = useState('');

  const tipAmount = tipType === 'porcentaje' ? subtotal * tipPercent / 100 : Number(tipManual || 0);
  const taxAmount = applyTax ? subtotal * 0.16 : 0;
  const discountAmount = Math.min(Math.max(Number(discountInput || 0), 0), subtotal);
  const total = subtotal + taxAmount - discountAmount + tipAmount;
  // Cuenta combinada de 2+ comensales: el total a cobrar sigue siendo uno
  // solo, pero se muestra ademas cuanto le toca a cada quien (proporcional
  // a lo que consumio), para que el cajero pueda informarlo si alguien
  // pregunta o quiere aportar su parte por separado.
  const dinerTotals = diners && diners.length > 1
    ? distributeProportionally(total, diners.map(d => d.subtotal))
    : null;
  const receivedAmount = Number(receivedInput || 0);
  const changeAmount = receivedAmount - total;
  const isCash = paymentMethod === 'efectivo';
  const isMixed = paymentMethod === 'mixto';
  const mixedCashAmount = Number(mixedCashInput || 0);
  const mixedRemainder = Math.max(0, total - mixedCashAmount);
  const canConfirm = (!isCash || receivedInput === '' || receivedAmount >= total)
    && (!isMixed || (mixedCashInput !== '' && mixedCashAmount >= 0 && mixedCashAmount <= total));

  // Sugerencia de efectivo: redondea el total hacia arriba a un monto
  // "de billete" (10/50/100 segun el tamano del total) para que el
  // cajero casi siempre tenga un boton de un toque, sin usar el teclado.
  // Si el total ya es un monto redondo, no hace falta sugerir nada aparte.
  const cashSuggestion = (() => {
    if (!(total > 0)) return null;
    const step = total < 100 ? 10 : total < 500 ? 50 : 100;
    const rounded = Math.ceil(total / step) * step;
    return rounded > total ? rounded : null;
  })();

  function pressKey(k: string) {
    setReceivedInput(v => {
      if (k === 'back') return v.slice(0, -1);
      if (k === 'clear') return '';
      if (k === '.' && v.includes('.')) return v;
      return (v + k).slice(0, 12);
    });
  }

  async function handleConfirm() {
    setPaying(true);
    try {
      await onConfirm({
        tip_type: tipType, tip_percent: tipPercent, tip_amount: Number(tipManual || 0),
        discount_amount: discountAmount, apply_tax: applyTax,
        payment_method: paymentMethod,
        received_amount: isCash && receivedInput !== '' ? receivedAmount : undefined,
        cash_amount: isMixed ? mixedCashAmount : undefined,
      });
    } finally {
      setPaying(false);
    }
  }

  return <main className="page pay-page">
    <button className="ghost" onClick={onCancel} disabled={paying}><ArrowLeft size={16} /> {t.backToPending}</button>
    <div className="pay-header">
      <div>
        <h2>{label}</h2>
        <span className="status-pill" style={{ background: 'rgba(31,174,92,.14)', color: 'var(--green)' }}>{t.readyToCharge}</span>
      </div>
    </div>
    <div className="pay-card">
      <div className="pay-grid">
        <div className="pay-items">
          <h3>{t.detailBill}</h3>
          <div className="pay-items-list">
            {dinerTotals ? diners!.map((d, idx) => <div key={d.diner_index} className="pay-items-diner-group">
              <div className="pay-items-diner-label"><span>{t.diner} {d.diner_index}</span><span>{money(dinerTotals[idx])}</span></div>
              {(items || []).filter(item => item.diner_index === d.diner_index).map((item, itemIdx) => <div className="pay-item-row" key={itemIdx}>
                <span className="pay-item-name">{item.quantity > 1 ? `${item.quantity} x ` : ''}{item.dish ? item.dish.title : ''}</span>
                <span className="pay-item-amount">{money((item.quantity || 1) * Number(item.unit_price || 0))}</span>
              </div>)}
            </div>) : (items || []).map((item, idx) => <div className="pay-item-row" key={idx}>
              <span className="pay-item-name">{item.quantity > 1 ? `${item.quantity} x ` : ''}{item.dish ? item.dish.title : ''}</span>
              <span className="pay-item-amount">{money((item.quantity || 1) * Number(item.unit_price || 0))}</span>
            </div>)}
            {(!items || items.length === 0) && <p className="empty-hint">{t.empty}</p>}
          </div>

          <h3 className="pay-section-title">{t.paymentMethod}</h3>
          <div className="pay-methods">
            {PAYMENT_METHODS.map(({ key, icon: Icon }) => <button
              key={key}
              className={paymentMethod === key ? 'pay-method-btn active' : 'pay-method-btn'}
              onClick={() => setPaymentMethod(key)}
            ><Icon size={20} /><span>{t[key === 'efectivo' ? 'cash' : key === 'tarjeta' ? 'card' : key === 'transferencia' ? 'transfer' : 'mixed']}</span></button>)}
          </div>

          {isCash && <>
            <h3 className="pay-section-title">{t.quickAmount}</h3>
            <div className="pay-quick-row">
              {cashSuggestion && <button className="pay-quick-suggested" onClick={() => setReceivedInput(String(cashSuggestion))}>${cashSuggestion}</button>}
              {/* Se excluye cashSuggestion de los montos fijos: cuando el total
                  redondea justo a uno de ellos (ej. total $19.80 -> sugerido
                  $20, que tambien es un QUICK_CASH_AMOUNTS fijo), antes se
                  mostraban dos botones idénticos "$20" uno junto al otro. */}
              {QUICK_CASH_AMOUNTS.filter(a => a !== cashSuggestion).map(a => <button key={a} onClick={() => setReceivedInput(String(a))}>${a}</button>)}
              <button onClick={() => setReceivedInput(total.toFixed(2))}>{t.exactAmount}</button>
            </div>
            <div className="pay-received-row">
              <div className="field" style={{ flex: 1, margin: 0 }}>
                <label>{t.received}</label>
                <input value={receivedInput} onChange={e => setReceivedInput(e.target.value.replace(/[^0-9.]/g, ''))} placeholder="0.00" />
              </div>
            </div>
            <div className="pay-keypad">
              {['1','2','3','4','5','6','7','8','9','.','0','back'].map(k => <button key={k} onClick={() => pressKey(k)}>{k === 'back' ? <Delete size={18} /> : k}</button>)}
            </div>
          </>}

          {/* Pago mixto: un solo campo (cuanto en efectivo) -- el resto se
              calcula solo como tarjeta/transferencia, sin pedir un desglose
              completo por metodo. */}
          {isMixed && <>
            <h3 className="pay-section-title">{t.mixedCashReceived}</h3>
            <div className="pay-received-row">
              <div className="field" style={{ flex: 1, margin: 0 }}>
                <label>{t.mixedCashReceived}</label>
                <input value={mixedCashInput} onChange={e => setMixedCashInput(e.target.value.replace(/[^0-9.]/g, ''))} placeholder="0.00" />
              </div>
            </div>
            <div className="pay-summary-row"><span>{t.mixedRemainder}</span><span>{money(mixedRemainder)}</span></div>
          </>}
        </div>

        <div className="pay-summary">
          <h3>{t.paymentSummary}</h3>
          <div className="pay-summary-row"><span>{t.subtotal}</span><span>{money(subtotal)}</span></div>
          <div className="pay-summary-row pay-tax-row">
            <label className="pay-checkbox"><input type="checkbox" checked={applyTax} onChange={e => setApplyTax(e.target.checked)} /> {t.tax}</label>
            <span>{money(taxAmount)}</span>
          </div>
          <div className="pay-summary-row">
            <span>{t.discount}</span>
            <input className="pay-inline-input" type="number" min="0" max={subtotal} value={discountInput} onChange={e => setDiscountInput(e.target.value)} />
          </div>
          {Number(discountInput || 0) > subtotal && <p className="pay-discount-clamped-hint">{t.discountClampedHint}</p>}

          <div className="guisado-mode-row" style={{ marginTop: 14 }}>
            <button className={tipType === 'porcentaje' ? 'active' : ''} onClick={() => setTipType('porcentaje')}><Percent size={14} /> {t.tipPercent}</button>
            <button className={tipType === 'manual' ? 'active' : ''} onClick={() => setTipType('manual')}><DollarSign size={14} /> {t.tipManual}</button>
          </div>
          <p className="sub-heading" style={{ margin: '10px 0 4px' }}>{t.quickTip}</p>
          {tipType === 'porcentaje' ? <div className="guisado-mode-row">
            {[0, 5, 10, 15, 20].map(p => <button key={p} className={tipPercent === p ? 'active' : ''} onClick={() => setTipPercent(p)}>{p}%</button>)}
          </div> : <div className="field"><input type="number" min="0" value={tipManual} onChange={e => setTipManual(e.target.value)} /></div>}
          <div className="pay-summary-row"><span>{t.tipAmount}</span><span>{money(tipAmount)}</span></div>

          <div className="pay-total-row"><span>{t.total}</span><strong>{money(total)}</strong></div>

          {dinerTotals && <div className="pay-diner-breakdown">
            <p className="sub-heading" style={{ margin: '0 0 4px' }}>{t.perDinerAmount}</p>
            {diners!.map((d, idx) => <div className="pay-summary-row" key={d.diner_index}>
              <span>{t.diner} {d.diner_index}</span>
              <span>{money(dinerTotals[idx])}</span>
            </div>)}
          </div>}

          {isCash && receivedInput !== '' && <>
            <div className="pay-summary-row"><span>{t.received}</span><span>{money(receivedAmount)}</span></div>
            <div className="pay-summary-row"><span>{t.change}</span><span style={{ color: changeAmount < 0 ? 'var(--danger)' : 'var(--green)' }}>{money(changeAmount)}</span></div>
          </>}

          <button className="primary big" disabled={!canConfirm || paying} onClick={handleConfirm}>
            {paying ? <><Loader2 size={18} className="spin" /> {t.processing}</> : <>{t.pay} {money(total)}</>}
          </button>
          <button className="ghost" style={{ width: '100%', justifyContent: 'center', marginTop: 10 }} disabled={paying} onClick={onCancel}>{t.cancel}</button>
        </div>
      </div>
    </div>
  </main>;
}
