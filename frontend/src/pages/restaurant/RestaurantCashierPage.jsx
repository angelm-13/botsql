/* eslint-disable react/prop-types */
import React, { useEffect, useState } from "react";
import { Banknote, CircleDollarSign, Clock3, FileText, Store } from "lucide-react";
import { closeRestaurantRegister, getRestaurantCashierWorkspace, getRestaurantReports, openRestaurantRegister, payRestaurantOrder } from "../../api";
import { useI18n } from "../../i18n";
import { EmptyState, money, Notice, RestaurantHeader } from "./RestaurantUi";
import "../../styles/restaurant.css";

export default function RestaurantCashierPage() {
  const { t } = useI18n();
  const [data, setData] = useState({ kpis: {}, pending_payments: [], register_history: [] });
  const [report, setReport] = useState(null);
  const [amount, setAmount] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
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
  const kpis = [
    { key: "accumulated_sales", value: money(data.kpis.total_sales), icon: CircleDollarSign },
    { key: "tips", value: money(data.kpis.tips), icon: Banknote },
    { key: "average_ticket", value: money(data.kpis.avg_ticket), icon: FileText },
    { key: "active_tables", value: data.kpis.active_tables || 0, icon: Store },
  ];
  return <main className="rest-page">
    <RestaurantHeader eyebrow={t("restaurant.cashier_eyebrow")} title={t("restaurant.cashier_title")} detail={t("restaurant.cashier_detail")} loading={loading} onRefresh={load} />
    <Notice error={error} />
    <section className="rest-kpis">{kpis.map((item) => { const Icon = item.icon; return <article key={item.key}><Icon size={21} /><span>{t(`restaurant.${item.key}`)}</span><strong>{item.value}</strong></article>; })}</section>
    <section className="rest-cashier-layout">
      <div className="rest-panel"><div className="rest-panel-heading"><div><span>{t("restaurant.open_accounts")}</span><h2>{t("restaurant.pending_payment")}</h2></div><span>{data.pending_payments.length}</span></div><div className="rest-payment-list">{data.pending_payments.map((order) => <article key={order.id_restaurant_order}><div><strong>{t("restaurant.table")} {order.visit?.table?.number} · {t("restaurant.diner")} {order.diner_index}</strong><span>{order.items.map((item) => `${item.quantity}× ${item.dish?.title}`).join(", ")}</span></div><b>{money(order.subtotal)}</b><PaymentButton order={order} onPay={(payload) => act(() => payRestaurantOrder(order.id_restaurant_order, payload))} /></article>)}{!data.pending_payments.length && <EmptyState>{t("restaurant.no_pending_accounts")}</EmptyState>}</div></div>
      <div className="rest-panel rest-register"><div className="rest-panel-heading"><div><span>{t("restaurant.current_shift")}</span><h2>{t(data.current_register ? "restaurant.register_open" : "restaurant.register_closed")}</h2></div><Clock3 size={22} /></div>{data.current_register && <div className="rest-register-summary"><span>{t("restaurant.opening_amount")}</span><strong>{money(data.current_register.opening_amount)}</strong><small>{t("restaurant.opened")} {new Date(data.current_register.opened_at).toLocaleString(document.documentElement.lang || "es")}</small></div>}<label className="rest-field"><span>{t(data.current_register ? "restaurant.closing_cash" : "restaurant.opening_amount")}</span><input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label><button className={data.current_register ? "rest-danger" : "rest-primary"} onClick={() => act(() => data.current_register ? closeRestaurantRegister({ closing_amount: amount }) : openRestaurantRegister({ opening_amount: amount }))}>{t(data.current_register ? "restaurant.close_register" : "restaurant.open_register")}</button></div>
    </section>
    <ReportPanel report={report} onSearch={async (params) => { try { setReport(await getRestaurantReports(params)); } catch (reason) { setError(reason); } }} />
  </main>;
}

function PaymentButton({ order, onPay }) {
  const { t } = useI18n();
  const [tip, setTip] = useState(10);
  return <div className="rest-pay-controls"><label><span>{t("restaurant.tip_percent")}</span><input type="number" min="0" value={tip} onChange={(event) => setTip(Number(event.target.value))} /></label><button className="rest-primary" onClick={() => onPay({ tip_type: "porcentaje", tip_percent: tip })}>{t("restaurant.charge")} {money(Number(order.subtotal) * (1 + tip / 100))}</button></div>;
}

function ReportPanel({ report, onSearch }) {
  const { t } = useI18n();
  const [dates, setDates] = useState({ start: "", end: "" });
  return <section className="rest-panel rest-report"><div className="rest-panel-heading"><div><span>{t("restaurant.analysis")}</span><h2>{t("restaurant.sales_report")}</h2></div><div className="rest-date-range"><input type="date" value={dates.start} onChange={(event) => setDates({ ...dates, start: event.target.value })} /><input type="date" value={dates.end} onChange={(event) => setDates({ ...dates, end: event.target.value })} /><button className="rest-secondary" onClick={() => onSearch(dates)}>{t("restaurant.search_report")}</button></div></div>{report && <><div className="rest-report-summary"><strong>{money(report.total_sales)}</strong><span>{report.total_orders} {t("restaurant.accounts")} · {money(report.total_tips)} {t("restaurant.in_tips")}</span></div><table className="rest-data-table"><thead><tr><th>{t("restaurant.date")}</th><th>{t("restaurant.accounts")}</th><th>{t("restaurant.sale")}</th><th>{t("restaurant.tip")}</th></tr></thead><tbody>{report.days.map((day) => <tr key={day.date}><td>{day.date}</td><td>{day.orders}</td><td>{money(day.sales)}</td><td>{money(day.tips)}</td></tr>)}</tbody></table></>}</section>;
}
