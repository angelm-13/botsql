import { useEffect, useState, type ReactNode } from 'react';
import {
  Banknote, Check, ClipboardList, Clock, CreditCard, DollarSign, Landmark, Layers,
  Minus as MinusIcon, ShoppingCart, TrendingDown, TrendingUp, Users,
} from 'lucide-react';
import { api } from '../../services/api';
import { useCategories } from '../../contexts/CategoriesContext';
import { AnimatedNumber } from '../../components/shared/AnimatedNumber';
import { CatIcon } from '../../components/shared/CatIcon';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { DemoLockedNote } from '../../components/shared/DemoLockedNote';
import { RegisterOpenTooLongWarning } from '../../components/shared/RegisterOpenTooLongWarning';
import { money, labelStatus, placeLabel, STATUS_VAR } from '../../utils/format';
import type { Translations } from '../../i18n/translations';
import type { DashboardData, KpisData, DayMetrics, DemoStatus } from '../../types/api';


const DONUT_COLORS = ['--status-pedido', '--status-preparacion', '--status-listo', '--status-entregado', '--status-pagado', '--status-borrador', '--status-cancelado'];

function StatusDonut({ t, distribution }: { t: Translations; distribution: Record<string, number> | undefined }) {
  const entries = Object.entries(distribution || {}).filter(([, v]) => v > 0);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  if (!total) return <p className="empty-hint">{t.noData}</p>;
  const r = 40, circumference = 2 * Math.PI * r;
  let offset = 0;
  return <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
    <svg width="140" height="140" viewBox="0 0 100 100" className="donut-svg">
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="16" />
      {entries.map(([status, value], idx) => {
        const fraction = value / total;
        const length = fraction * circumference;
        const dashArray = `${length} ${circumference - length}`;
        const rotation = (offset / circumference) * 360 - 90;
        offset += length;
        const color = `var(${DONUT_COLORS[idx % DONUT_COLORS.length]})`;
        return <circle key={status} className="donut-segment" style={{ animationDelay: `${idx * 120}ms` }} cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="16"
          strokeDasharray={dashArray} transform={`rotate(${rotation} 50 50)`} />;
      })}
      <text x="50" y="54" textAnchor="middle" fontSize="18" fontWeight="900" fill="var(--text)">{total}</text>
    </svg>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {entries.map(([status, value], idx) => <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: `var(${DONUT_COLORS[idx % DONUT_COLORS.length]})`, display: 'inline-block' }} />
        <span style={{ color: 'var(--muted)' }}>{labelStatus(status, t)}</span>
        <strong>{value}</strong>
      </div>)}
    </div>
  </div>;
}

function HourlyBarChart({ ordersByHour }: { ordersByHour: { hour: number; count: number }[] | undefined }) {
  const visibleHours = (ordersByHour || []).filter(h => h.hour >= 7 && h.hour <= 22);
  const max = Math.max(1, ...visibleHours.map(h => h.count));
  return <div className="chart-vertical" style={{ height: 160 }}>
    {visibleHours.map(h => <div className="col-bar" key={h.hour}>
      <div className="col" style={{ height: `${(h.count / max) * 100}%`, background: 'linear-gradient(180deg,var(--gold),#8a3f20)' }}>
        {h.count > 0 && <span className="col-val">{h.count}</span>}
      </div>
      <span className="col-label">{h.hour}h</span>
    </div>)}
  </div>;
}

/** Flecha + variacion porcentual vs. el mismo indicador ayer (dato real,
 * viene de dash.previous_day -- no inventado). `invert` es para metricas
 * donde bajar es una mejora (ej. tiempo de preparacion). */
function KpiTrend({ t, current, previous, invert = false }: { t: Translations; current: number | undefined; previous: number | undefined; invert?: boolean }) {
  const cur = Number(current) || 0;
  const prev = Number(previous) || 0;
  if (prev === 0 && cur === 0) return null;
  if (prev === 0) return <span className="kpi-trend kpi-trend-up"><TrendingUp size={12} /> {t.trendNew}</span>;
  const pct = Math.round(((cur - prev) / prev) * 100);
  const flat = cur === prev;
  const improved = invert ? cur < prev : cur > prev;
  const Icon = flat ? MinusIcon : (improved ? TrendingUp : TrendingDown);
  const cls = flat ? 'kpi-trend-flat' : (improved ? 'kpi-trend-up' : 'kpi-trend-down');
  return <span className={`kpi-trend ${cls}`}><Icon size={12} /> {flat ? t.trendFlat : `${pct > 0 ? '+' : ''}${pct}%`} <span className="kpi-trend-hint">{t.vsYesterday}</span></span>;
}

/** Mini comparacion de dos barras (ayer vs. hoy) que se revela al hacer
 * click en una tarjeta de KPI -- la parte "interactiva" de las tarjetas:
 * no solo el numero de hoy, tambien de donde viene. */
function KpiCompareDetail({ t, currentLabel, current, previous, format }: { t: Translations; currentLabel: string; current: number | undefined; previous: number | undefined; format?: (v: number) => ReactNode }) {
  const cur = Number(current) || 0;
  const prev = Number(previous) || 0;
  const max = Math.max(1, cur, prev);
  const fmt = format || ((v: number) => v);
  return <div className="kpi-compare" onClick={e => e.stopPropagation()}>
    <div className="kpi-compare-bar">
      <div className="kpi-compare-col-wrap"><div className="kpi-compare-col" style={{ height: `${(prev / max) * 100}%` }} /></div>
      <span className="kpi-compare-val">{fmt(prev)}</span>
      <span className="kpi-compare-label">{t.rangeYesterday}</span>
    </div>
    <div className="kpi-compare-bar">
      <div className="kpi-compare-col-wrap"><div className="kpi-compare-col kpi-compare-col-current" style={{ height: `${(cur / max) * 100}%` }} /></div>
      <span className="kpi-compare-val">{fmt(cur)}</span>
      <span className="kpi-compare-label">{currentLabel}</span>
    </div>
  </div>;
}

export function DashboardSummary({ t }: { t: Translations }) {
  const { categories } = useCategories();
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  useEffect(() => {
    function load() { api.dashboard().then(setDash).catch(console.error); }
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);
  if (!dash) return <LoadingPanel label={t.loadingDashboard} />;
  const maxCatQty = Math.max(1, ...(dash.category_breakdown || []).map(c => c.quantity));
  const prev: Partial<DayMetrics> = dash.previous_day || {};
  function toggle(key: string) { setExpanded(k => k === key ? null : key); }
  return <>
    <div className="section-title" style={{ padding: '4px 0 18px' }}>
      <h1 style={{ fontSize: 26 }}>{t.dashboardTitle}</h1>
      <span style={{ color: 'var(--muted)', fontSize: 13 }}>{dash.date}</span>
    </div>
    <section className="dashboard-stat-grid">
      <div className={`kpi kpi-primary kpi-clickable ${expanded === 'orders' ? 'expanded' : ''}`} onClick={() => toggle('orders')}>
        <ClipboardList size={18} style={{ color: 'var(--gold)' }} /><div className="kpi-label">{t.ordersToday}</div><div className="kpi-value"><AnimatedNumber value={dash.orders_today} /></div>
        <KpiTrend t={t} current={dash.orders_today} previous={prev.orders} />
        {expanded === 'orders' && <KpiCompareDetail t={t} currentLabel={t.today} current={dash.orders_today} previous={prev.orders} />}
      </div>
      <div className={`kpi kpi-secondary kpi-clickable ${expanded === 'items' ? 'expanded' : ''}`} onClick={() => toggle('items')}>
        <ShoppingCart size={18} style={{ color: 'var(--green)' }} /><div className="kpi-label">{t.itemsRequestedToday}</div><div className="kpi-value"><AnimatedNumber value={dash.items_requested_today} /></div>
        <KpiTrend t={t} current={dash.items_requested_today} previous={prev.items_requested} />
        {expanded === 'items' && <KpiCompareDetail t={t} currentLabel={t.today} current={dash.items_requested_today} previous={prev.items_requested} />}
      </div>
      <div className={`kpi kpi-tertiary kpi-clickable ${expanded === 'tables' ? 'expanded' : ''}`} onClick={() => toggle('tables')}>
        <Users size={18} style={{ color: 'var(--purple)' }} /><div className="kpi-label">{t.tablesServedToday}</div><div className="kpi-value"><AnimatedNumber value={dash.tables_served_today} /></div>
        <KpiTrend t={t} current={dash.tables_served_today} previous={prev.tables_served} />
        {expanded === 'tables' && <KpiCompareDetail t={t} currentLabel={t.today} current={dash.tables_served_today} previous={prev.tables_served} />}
      </div>
      <div className={`kpi kpi-quaternary kpi-clickable ${expanded === 'prep' ? 'expanded' : ''}`} onClick={() => toggle('prep')}>
        <Clock size={18} style={{ color: 'var(--danger)' }} /><div className="kpi-label">{t.avgPrepTime}</div><div className="kpi-value"><AnimatedNumber value={dash.avg_prep_minutes_today} decimals={1} format={v => `${v} m`} /></div>
        <KpiTrend t={t} current={dash.avg_prep_minutes_today} previous={prev.avg_prep_minutes} invert />
        {expanded === 'prep' && <KpiCompareDetail t={t} currentLabel={t.today} current={dash.avg_prep_minutes_today} previous={prev.avg_prep_minutes} format={v => `${v}m`} />}
      </div>
      <div className={`kpi kpi-primary kpi-clickable ${expanded === 'ready' ? 'expanded' : ''}`} onClick={() => toggle('ready')}>
        <Check size={18} style={{ color: 'var(--gold)' }} /><div className="kpi-label">{t.itemsReadyToday}</div><div className="kpi-value"><AnimatedNumber value={dash.items_ready_today} /></div>
        <KpiTrend t={t} current={dash.items_ready_today} previous={prev.items_ready} />
        {expanded === 'ready' && <KpiCompareDetail t={t} currentLabel={t.today} current={dash.items_ready_today} previous={prev.items_ready} />}
      </div>
    </section>
    <section className="dash-grid">
      <div className="chart"><h2>{t.ordersByHour}</h2><HourlyBarChart ordersByHour={dash.orders_by_hour} /></div>
      <div className="chart"><h2>{t.statusDistribution}</h2><StatusDonut t={t} distribution={dash.status_distribution} /></div>
    </section>
    <section className="chart" style={{ marginTop: 18 }}>
      <h2>{t.recentOrders}</h2>
      {(dash.recent_orders || []).length === 0 ? <p className="empty-hint">{t.noData}</p> : <table className="report-table">
        <thead><tr><th>{t.orderCol}</th><th>{t.table}</th><th>{t.hourCol}</th><th>{t.itemsCol}</th><th>{t.statusCol}</th></tr></thead>
        <tbody>{dash.recent_orders.map(o => <tr key={o.id}>
          <td>#{o.daily_number ?? o.id}</td>
          <td>{placeLabel(t, o)}</td>
          <td>{o.time ? new Date(o.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}</td>
          <td>{o.items_summary}</td>
          <td><span className="status-pill" style={{ background: `var(${STATUS_VAR[o.status]})33`, color: `var(${STATUS_VAR[o.status]})` }}>{labelStatus(o.status, t)}</span></td>
        </tr>)}</tbody>
      </table>}
    </section>
    <section className="chart" style={{ marginTop: 18 }}>
      <h2>{t.categorySummary}</h2>
      {(dash.category_breakdown || []).length === 0 ? <p className="empty-hint">{t.noData}</p> : (dash.category_breakdown || []).map(c => <div className="bar" key={c.category}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><CatIcon category={c.category} size={14} /> {categories.find(cat => cat.slug === c.category)?.name || c.category}</span>
        <div><i style={{ width: `${(c.quantity / maxCatQty) * 100}%` }} /></div>
        <span>{c.percent}%</span>
      </div>)}
    </section>
  </>;
}

const PAYMENT_METHOD_ICON: Record<string, typeof Banknote> = { efectivo: Banknote, tarjeta: CreditCard, transferencia: Landmark, mixto: Layers };

export function KpisPanel({ t }: { t: Translations }) {
  const [kpis, setKpis] = useState<KpisData | null>(null);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  useEffect(() => {
    function load() { api.kpis().then(setKpis).catch(console.error); }
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => { api.demoStatus().then(setDemoStatus).catch(() => {}); }, []);
  const demoLocksHistoricKpis = !!demoStatus?.enabled;
  if (!kpis) return <LoadingPanel label={t.loadingKpis} />;
  const totalSales = Number(kpis.total_sales || 0);
  const totalTips = Number(kpis.tips || 0);
  const avgTicket = Number(kpis.avg_ticket || 0);
  const activeTables = kpis.active_tables || 0;
  const avgTime = Number(kpis.avg_minutes_from_ready_to_delivered || 0);
  const topDishesData: [string, number][] = (kpis.top_dishes || []).map(x => [x.dish, x.quantity]);
  const topTablesData: [string, number][] = (kpis.top_tables || []).map(x => [`Mesa ${x.table}`, x.services]);
  const waiterServicesData: [string, number][] = (kpis.services_by_waiter || []).map(x => [x.waiter, x.services]);
  const paymentBreakdown = Object.entries(kpis.payment_breakdown || {});
  const registerOpen = !!kpis.register_open;
  return <>
    <DashboardSummary t={t} />
    <div className="section-title" style={{ padding: '24px 0 4px' }}><h1 style={{ fontSize: 22 }}>{t.cashier}</h1></div>
    <p className="scope-hint">{t.sessionScopeHint}</p>
    {kpis.register_open_too_long && <RegisterOpenTooLongWarning t={t} />}
    <section className="kpi-grid">
      <div className="kpi kpi-primary">
        <div className="kpi-label">{t.totalSales}</div>
        <div className="kpi-value"><AnimatedNumber value={totalSales} decimals={2} format={money} /></div>
        <div className="kpi-meta">
          {registerOpen
            ? `${t.registerOpen} ${kpis.register_opened_at ? new Date(kpis.register_opened_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}`
            : t.registerClosedHint}
        </div>
      </div>
      <div className="kpi kpi-secondary"><div className="kpi-label">{t.tips}</div><div className="kpi-value"><AnimatedNumber value={totalTips} decimals={2} format={money} /></div></div>
      <div className="kpi kpi-tertiary"><div className="kpi-label">{t.avgTicket}</div><div className="kpi-value"><AnimatedNumber value={avgTicket} decimals={2} format={money} /></div><div className="kpi-meta">{activeTables} {activeTables === 1 ? t.activeTable : t.activeTables}</div></div>
      <div className="kpi kpi-quaternary"><div className="kpi-label">{t.avgTime}</div><div className="kpi-value"><AnimatedNumber value={avgTime} format={v => `${v}m`} /></div></div>
    </section>
    <section className="chart" style={{ marginTop: 4 }}>
      <h2>{t.paymentBreakdown}</h2>
      {paymentBreakdown.length === 0 ? <p className="empty-hint">{t.noPayments}</p> : <div className="payment-breakdown-row">
        {paymentBreakdown.map(([method, amount]) => {
          const Icon = PAYMENT_METHOD_ICON[method] || DollarSign;
          return <div className="payment-breakdown-chip" key={method}>
            <Icon size={16} />
            <span className="pb-label">{t[method === 'efectivo' ? 'cash' : method === 'tarjeta' ? 'card' : method === 'transferencia' ? 'transfer' : method === 'mixto' ? 'mixed' : 'total'] || method}</span>
            <span className="pb-amount">{money(amount)}</span>
          </div>;
        })}
      </div>}
    </section>
    <p className="scope-hint" style={{ marginTop: 20 }}>{t.historicScopeHint}</p>
    {demoLocksHistoricKpis ? <DemoLockedNote text={t.demoLockedKpis} /> : <>
      <section className="dash-grid">
        <Chart title={t.topDishes} data={topDishesData} type="horizontal" />
        <Chart title={t.topTables} data={topTablesData} type="vertical" />
      </section>
      {waiterServicesData.length > 0 && <section className="dash-grid" style={{ marginTop: 18 }}>
        <Chart title={t.servicesByWaiter} data={waiterServicesData} type="horizontal" />
      </section>}
    </>}
  </>;
}

function Chart({ title, data, type = 'horizontal' }: { title: string; data: [string, number][]; type?: 'horizontal' | 'vertical' }) {
  const max = Math.max(1, ...data.map(x => x[1]));
  return <div className="chart"><h2>{title}</h2>
    {data.length === 0 ? <p>-</p> : type === 'vertical'
      ? <div className="chart-vertical">{data.slice(0, 5).map(([label, value]) => <div className="col-bar" key={label}><div className="col" style={{ height: `${(value / max) * 100}%`, background: 'linear-gradient(180deg,var(--gold),#d4a94a)' }}><span className="col-val">{value}</span></div><span className="col-label">{label}</span></div>)}</div>
      : <div className="chart-horizontal">{data.slice(0, 5).map(([label, value]) => <div className="row-bar" key={label}><span className="row-label">{label}</span><div className="row-container"><div className="row" style={{ width: `${(value / max) * 100}%`, background: 'linear-gradient(90deg,var(--green),#28a84f)' }}><span className="row-val">{value}</span></div></div></div>)}</div>}
  </div>;
}
