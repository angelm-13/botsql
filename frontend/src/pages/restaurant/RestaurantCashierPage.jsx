/* eslint-disable react/prop-types */
import { useEffect, useMemo, useState } from "react";
import { Banknote, CircleDollarSign, Clock3, FileText, Printer, Store, Users, X } from "lucide-react";
import { closeRestaurantRegister, getRestaurantCashierWorkspace, getRestaurantReports, openRestaurantRegister, payRestaurantOrder, payRestaurantVisit } from "../../api";
import { useI18n } from "../../i18n";
import { EmptyState, money, Notice, RestaurantHeader } from "./RestaurantUi";
import RestaurantPaymentModal from "./RestaurantPaymentModal";
import RestaurantTicket from "./RestaurantTicket";
import "../../styles/restaurant.css";
import "../../styles/restaurant-print.css";

// serialize() del backend entrega table_number plano; las ordenes para
// llevar no traen mesa sino el folio del dia.
function orderLabel(order, t) {
  if (order.table_number) return `${t("restaurant.table")} ${order.table_number}`;
  return t("restaurant.takeout");
}

export default function RestaurantCashierPage() {
  const { t } = useI18n();
  const [data, setData] = useState({ kpis: {}, pending_payments: [], register_history: [] });
  const [report, setReport] = useState(null);
  const [amount, setAmount] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cobro, setCobro] = useState(null);   // { orders, label, visitId? }
  const [ticket, setTicket] = useState(null); // { orders, label, payment }
  const [avisos, setAvisos] = useState([]);   // avisos de inventario del ultimo cobro

  const load = async () => {
    setLoading(true);
    try { setData(await getRestaurantCashierWorkspace()); setError(null); }
    catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (operation) => {
    try { await operation(); await load(); }
    catch (reason) { setError(reason); }
  };

  // Las cuentas llegan planas; se agrupan por visita para poder ofrecer el
  // cobro conjunto de la mesa además del cobro por comensal.
  const cuentas = useMemo(() => {
    const grupos = new Map();
    for (const order of data.pending_payments || []) {
      const clave = order.id_restaurant_visit;
      if (!grupos.has(clave)) {
        grupos.set(clave, { visitId: clave, label: orderLabel(order, t), orders: [] });
      }
      grupos.get(clave).orders.push(order);
    }
    return [...grupos.values()];
  }, [data.pending_payments, t]);

  const imprimir = (payload) => {
    setTicket(payload);
    // Esperar a que el ticket esté en el DOM antes de abrir el diálogo.
    setTimeout(() => window.print(), 60);
  };

  const confirmarCobro = async (payload) => {
    const { orders, label, visitId, conjunto } = cobro;
    let resultado = null;
    await act(async () => {
      resultado = conjunto
        ? await payRestaurantVisit(visitId, payload)
        : await payRestaurantOrder(orders[0].id_restaurant_order, payload);
    });
    setCobro(null);
    setAvisos(resultado?.inventory_warnings || []);
    imprimir({
      orders,
      label,
      payment: {
        payment_method: payload.payment_method,
        received_amount: payload.received_amount ?? null,
        cash_total: resultado?.cash_total,
        change_amount: resultado?.change_amount ?? 0,
      },
    });
  };

  const kpis = [
    { key: "accumulated_sales", value: money(data.kpis.total_sales), icon: CircleDollarSign },
    { key: "tips", value: money(data.kpis.tips), icon: Banknote },
    { key: "average_ticket", value: money(data.kpis.avg_ticket), icon: FileText },
    { key: "active_tables", value: data.kpis.active_tables || 0, icon: Store },
  ];

  return <main className="rest-page">
    <RestaurantHeader eyebrow={t("restaurant.cashier_eyebrow")} title={t("restaurant.cashier_title")} detail={t("restaurant.cashier_detail")} loading={loading} onRefresh={load} />
    <Notice error={error} />
    {!data.current_register && <div className="rest-notice">{t("restaurant.register_closed_warning")}</div>}
    <InventoryWarnings avisos={avisos} onDismiss={() => setAvisos([])} />
    <section className="rest-kpis">{kpis.map((item) => { const Icon = item.icon; return <article key={item.key}><Icon size={21} /><span>{t(`restaurant.${item.key}`)}</span><strong>{item.value}</strong></article>; })}</section>
    <section className="rest-cashier-layout">
      <div className="rest-panel">
        <div className="rest-panel-heading"><div><span>{t("restaurant.open_accounts")}</span><h2>{t("restaurant.pending_payment")}</h2></div><span>{data.pending_payments.length}</span></div>
        <div className="rest-payment-list">
          {cuentas.map((grupo) => {
            const total = grupo.orders.reduce((s, o) => s + Number(o.subtotal || 0), 0);
            return <article key={grupo.visitId}>
              <div>
                <strong>{grupo.label}</strong>
                <span>{grupo.orders.length} {grupo.orders.length === 1 ? t("restaurant.account") : t("restaurant.accounts")} · {money(total)}</span>
              </div>
              <div className="rest-pay-group">
                {grupo.orders.length > 1 && <button className="rest-primary" onClick={() => setCobro({ ...grupo, conjunto: true })}>
                  <Users size={15} /> {t("restaurant.charge_together")}
                </button>}
                {grupo.orders.map((order) => <button
                  key={order.id_restaurant_order}
                  className="rest-secondary"
                  onClick={() => setCobro({ orders: [order], label: `${grupo.label} · ${t("restaurant.diner")} ${order.diner_index}`, conjunto: false })}
                >{grupo.orders.length > 1 ? `${t("restaurant.diner")} ${order.diner_index}` : t("restaurant.charge")} · {money(order.subtotal)}</button>)}
              </div>
            </article>;
          })}
          {!data.pending_payments.length && <EmptyState>{t("restaurant.no_pending_accounts")}</EmptyState>}
        </div>
      </div>
      <div className="rest-panel rest-register">
        <div className="rest-panel-heading"><div><span>{t("restaurant.current_shift")}</span><h2>{t(data.current_register ? "restaurant.register_open" : "restaurant.register_closed")}</h2></div><Clock3 size={22} /></div>
        {data.current_register && <div className="rest-register-summary"><span>{t("restaurant.opening_amount")}</span><strong>{money(data.current_register.opening_amount)}</strong><small>{t("restaurant.opened")} {new Date(data.current_register.opened_at).toLocaleString(document.documentElement.lang || "es")}</small></div>}
        <label className="rest-field"><span>{t(data.current_register ? "restaurant.closing_cash" : "restaurant.opening_amount")}</span><input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label>
        <button className={data.current_register ? "rest-danger" : "rest-primary"} onClick={() => act(() => data.current_register ? closeRestaurantRegister({ closing_amount: amount }) : openRestaurantRegister({ opening_amount: amount }))}>{t(data.current_register ? "restaurant.close_register" : "restaurant.open_register")}</button>
      </div>
    </section>
    <ReportPanel report={report} onSearch={async (params) => { try { setReport(await getRestaurantReports(params)); } catch (reason) { setError(reason); } }} />

    {cobro && <RestaurantPaymentModal
      orders={cobro.orders}
      label={cobro.label}
      onCancel={() => setCobro(null)}
      onConfirm={confirmarCobro}
    />}
    {ticket && <>
      <RestaurantTicket orders={ticket.orders} label={ticket.label} payment={ticket.payment} />
      <div className="rest-reprint"><button className="rest-secondary" onClick={() => window.print()}><Printer size={15} /> {t("restaurant.reprint_ticket")}</button></div>
    </>}
  </main>;
}

function InventoryWarnings({ avisos, onDismiss }) {
  const { t } = useI18n();
  if (!avisos.length) return null;
  // El cobro nunca se bloquea por inventario, asi que estos avisos son la
  // unica senal de que el descuento no salio limpio.
  return <div className="rest-inventory-warnings">
    <div className="rest-iw-head">
      <strong>{t("restaurant.inventory_warnings")}</strong>
      <button className="rest-icon-button" onClick={onDismiss} title={t("restaurant.dismiss")}><X size={16} /></button>
    </div>
    <ul>
      {avisos.map((a, i) => <li key={i}>
        {a.code === "sin_receta" && `${t("restaurant.warn_no_recipe")}: ${a.dishes.join(", ")}`}
        {a.code === "existencias_insuficientes" && `${t("restaurant.warn_short_stock")}: ${a.item} — ${t("restaurant.warn_needed")} ${a.required}, ${t("restaurant.warn_had")} ${a.available}, ${t("restaurant.missing").toLowerCase()} ${a.short}`}
        {a.code === "unidad_distinta" && `${t("restaurant.warn_unit_mismatch")}: ${a.item} (${a.item_unit} vs ${a.recipe_units.join(", ")})`}
      </li>)}
    </ul>
  </div>;
}

function ReportPanel({ report, onSearch }) {
  const { t } = useI18n();
  const [dates, setDates] = useState({ start: "", end: "" });
  return <section className="rest-panel rest-report"><div className="rest-panel-heading"><div><span>{t("restaurant.analysis")}</span><h2>{t("restaurant.sales_report")}</h2></div><div className="rest-date-range"><input type="date" value={dates.start} onChange={(event) => setDates({ ...dates, start: event.target.value })} /><input type="date" value={dates.end} onChange={(event) => setDates({ ...dates, end: event.target.value })} /><button className="rest-secondary" onClick={() => onSearch(dates)}>{t("restaurant.search_report")}</button></div></div>{report && <><div className="rest-report-summary"><strong>{money(report.total_sales)}</strong><span>{report.total_orders} {t("restaurant.accounts")} · {money(report.total_tips)} {t("restaurant.in_tips")}</span></div><table className="rest-data-table"><thead><tr><th>{t("restaurant.date")}</th><th>{t("restaurant.accounts")}</th><th>{t("restaurant.sale")}</th><th>{t("restaurant.tip")}</th></tr></thead><tbody>{report.days.map((day) => <tr key={day.date}><td>{day.date}</td><td>{day.orders}</td><td>{money(day.sales)}</td><td>{money(day.tips)}</td></tr>)}</tbody></table></>}</section>;
}
