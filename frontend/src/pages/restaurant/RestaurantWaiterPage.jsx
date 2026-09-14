/* eslint-disable react/prop-types */
import { useEffect, useState } from "react";
import { CalendarPlus, Check, DoorClosed, Minus, Plus, Send, ShoppingBag, Users } from "lucide-react";
import { addRestaurantDiner, addRestaurantOrderItem, closeRestaurantVisit, createRestaurantReservation, createRestaurantTakeout, createRestaurantVisit, deliverRestaurantOrder, getRestaurantWaiterWorkspace, removeRestaurantDiner, removeRestaurantOrderItem, sendRestaurantOrder } from "../../api";
import { useI18n } from "../../i18n";
import { EmptyState, money, Notice, RestaurantHeader, Status } from "./RestaurantUi";
import "../../styles/restaurant.css";

// serialize() del backend entrega table_number plano (no un objeto table),
// y para las ordenes para llevar no hay mesa sino folio del dia.
function visitLabel(visit, t) {
  if (!visit) return "";
  if (visit.service_type === "para_llevar") {
    return `${t("restaurant.takeout")} #${visit.daily_number}${visit.customer_name ? ` · ${visit.customer_name}` : ""}`;
  }
  return `${t("restaurant.table")} ${visit.table_number ?? ""}`.trim();
}

export default function RestaurantWaiterPage() {
  const { t } = useI18n();
  const [data, setData] = useState({ tables: [], visits: [], menu: { dishes: [], guisados: [] }, delivery: [], waiters: [], reservations: [] });
  const [selectedVisit, setSelectedVisit] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [guisado, setGuisado] = useState("");
  const [takeoutName, setTakeoutName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const load = async () => { setLoading(true); setError(null); try { const result = await getRestaurantWaiterWorkspace(); setData(result); const visit = result.visits.find((item) => item.id_restaurant_visit === selectedVisit?.id_restaurant_visit); if (visit) { setSelectedVisit(visit); setSelectedOrder(visit.orders.find((order) => order.id_restaurant_order === selectedOrder?.id_restaurant_order) || visit.orders[0]); } } catch (reason) { setError(reason); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (operation) => { setError(null); try { await operation(); await load(); } catch (reason) { setError(reason); } };
  const chooseTable = async (table) => {
    const visit = data.visits.find((item) => item.id_restaurant_table === table.id_restaurant_table);
    if (visit) { setSelectedVisit(visit); setSelectedOrder(visit.orders[0]); return; }
    await act(async () => { const created = await createRestaurantVisit({ id_restaurant_table: table.id_restaurant_table, diners_count: 1, id_restaurant_waiter: data.waiters[0]?.id_restaurant_waiter || null }); setSelectedVisit(created); setSelectedOrder(created.orders[0]); });
  };
  const takeoutVisits = data.visits.filter((item) => item.service_type === "para_llevar");
  const addDish = (dish) => act(() => addRestaurantOrderItem(selectedOrder.id_restaurant_order, { id_restaurant_dish: dish.id_restaurant_dish, id_guisado_1: dish.requires_guisado ? Number(guisado) : null, quantity: 1 }));
  return <main className="rest-page">
    <RestaurantHeader eyebrow={t("restaurant.waiter_eyebrow")} title={t("restaurant.waiter_title")} detail={t("restaurant.waiter_detail")} loading={loading} onRefresh={load} />
    <Notice error={error} />
    <section className="rest-waiter-layout">
      <div className="rest-panel rest-floor"><div className="rest-panel-heading"><div><span>{t("restaurant.service_map")}</span><h2>{t("restaurant.tables")}</h2></div><span>{data.visits.length} {t("restaurant.active_plural")}</span></div>
        <div className="rest-table-grid">{data.tables.map((table) => { const visit = data.visits.find((item) => item.id_restaurant_table === table.id_restaurant_table); return <button key={table.id_restaurant_table} className={`rest-table ${visit ? "is-busy" : ""} ${selectedVisit?.id_restaurant_table === table.id_restaurant_table ? "is-selected" : ""}`} onClick={() => chooseTable(table)}><strong>{table.number}</strong><span>{visit ? `${visit.diners_count} ${t("restaurant.diners")}` : `${table.capacity} ${t("restaurant.places")}`}</span></button>; })}</div>
        <form className="rest-quick-add" onSubmit={(event) => { event.preventDefault(); if (!takeoutName.trim()) return; act(async () => { const created = await createRestaurantTakeout({ customer_name: takeoutName, id_restaurant_waiter: data.waiters[0]?.id_restaurant_waiter || null }); setTakeoutName(""); setSelectedVisit(created); setSelectedOrder(created.orders[0]); }); }}>
          <label className="rest-quick-add-field"><span>{t("restaurant.new_takeout")}</span><input value={takeoutName} onChange={(event) => setTakeoutName(event.target.value)} placeholder={t("restaurant.customer_name")} /></label>
          <button className="rest-secondary" type="submit"><ShoppingBag size={15} /> {t("restaurant.takeout")}</button>
        </form>
        {takeoutVisits.length > 0 && <div className="rest-takeout-list">{takeoutVisits.map((visit) => <button key={visit.id_restaurant_visit} className={`rest-takeout-card ${selectedVisit?.id_restaurant_visit === visit.id_restaurant_visit ? "is-selected" : ""}`} onClick={() => { setSelectedVisit(visit); setSelectedOrder(visit.orders[0]); }}><div><strong>#{visit.daily_number}</strong><span>{visit.customer_name}</span></div><b>{money(visit.total)}</b></button>)}</div>}
      </div>
      <div className="rest-panel rest-order">
        {!selectedVisit ? <EmptyState>{t("restaurant.select_table")}</EmptyState> : <>
          <div className="rest-panel-heading"><div><span>{t("restaurant.active_order")}</span><h2>{visitLabel(selectedVisit, t)}</h2></div>{selectedVisit.service_type !== "para_llevar" && <div className="rest-inline-actions"><button className="rest-icon-button" title={t("restaurant.remove_diner")} disabled={selectedVisit.diners_count <= 1} onClick={() => act(() => removeRestaurantDiner(selectedVisit.id_restaurant_visit, selectedVisit.diners_count))}><Minus size={17} /></button><span><Users size={16} /> {selectedVisit.diners_count}</span><button className="rest-icon-button" title={t("restaurant.add_diner")} onClick={() => act(() => addRestaurantDiner(selectedVisit.id_restaurant_visit))}><Plus size={17} /></button></div>}</div>
          <div className="rest-diner-tabs">{selectedVisit.orders.map((order) => <button key={order.id_restaurant_order} className={selectedOrder?.id_restaurant_order === order.id_restaurant_order ? "active" : ""} onClick={() => setSelectedOrder(order)}>{t("restaurant.diner")} {order.diner_index}</button>)}</div>
          <CloseVisitBar visit={selectedVisit} onClose={() => act(async () => {
            await closeRestaurantVisit(selectedVisit.id_restaurant_visit);
            setSelectedVisit(null);
            setSelectedOrder(null);
          })} />
          {selectedOrder?.status === "borrador" && <><label className="rest-field rest-guisado"><span>{t("restaurant.stew_label")}</span><select value={guisado} onChange={(event) => setGuisado(event.target.value)}><option value="">{t("restaurant.select")}</option>{data.menu.guisados.map((item) => <option key={item.id_restaurant_guisado} value={item.id_restaurant_guisado}>{item.name}</option>)}</select></label><div className="rest-menu-grid">{data.menu.dishes.map((dish) => <button key={dish.id_restaurant_dish} onClick={() => addDish(dish)} disabled={dish.requires_guisado && !guisado}><span>{data.menu.categories?.find((cat) => cat.slug === dish.category)?.label || dish.category.replaceAll("_", " ")}</span><strong>{dish.title}</strong><b>{money(dish.price)}</b></button>)}</div></>}
          <div className="rest-ticket"><div className="rest-ticket-head"><strong>{t("restaurant.detail")}</strong><Status value={selectedOrder?.status} /></div>{selectedOrder?.items?.length ? selectedOrder.items.map((item) => <div className="rest-ticket-row" key={item.id_restaurant_order_item}><span>{item.quantity} × {item.dish?.title}{item.guisado_1?.name ? ` · ${item.guisado_1.name}` : ""}</span><b>{money(Number(item.unit_price) * item.quantity)}</b>{selectedOrder.status === "borrador" && <button className="rest-icon-button" title={t("restaurant.remove")} onClick={() => act(() => removeRestaurantOrderItem(selectedOrder.id_restaurant_order, item.id_restaurant_order_item))}><Minus size={15} /></button>}</div>) : <EmptyState>{t("restaurant.empty_order")}</EmptyState>}<div className="rest-ticket-total"><span>{t("restaurant.total")}</span><strong>{money(selectedOrder?.subtotal)}</strong></div>{selectedOrder?.status === "borrador" && <button className="rest-primary" disabled={!selectedOrder.items?.length} onClick={() => act(() => sendRestaurantOrder(selectedOrder.id_restaurant_order))}><Send size={17} /> {t("restaurant.send_kitchen")}</button>}</div>
        </>}
      </div>
    </section>
    <section className="rest-bottom-grid"><div className="rest-panel"><div className="rest-panel-heading"><div><span>{t("restaurant.kitchen_output")}</span><h2>{t("restaurant.lane_ready")}</h2></div></div><div className="rest-delivery-list">{data.delivery.filter((order) => order.status === "listo_para_entrega").map((order) => <div key={order.id_restaurant_order}><div><strong>{order.table_number ? `${t("restaurant.table")} ${order.table_number}` : t("restaurant.takeout")} · {t("restaurant.diner")} {order.diner_index}</strong><span>{order.items.map((item) => `${item.quantity} ${item.dish?.title}`).join(", ")}</span></div><button className="rest-primary" onClick={() => act(() => deliverRestaurantOrder(order.id_restaurant_order))}><Check size={16} /> {t("restaurant.deliver")}</button></div>)}{!data.delivery.some((order) => order.status === "listo_para_entrega") && <EmptyState>{t("restaurant.no_delivery")}</EmptyState>}</div></div>
      <ReservationBox onSave={(payload) => act(() => createRestaurantReservation(payload))} />
    </section>
  </main>;
}

function CloseVisitBar({ visit, onClose }) {
  const { t } = useI18n();
  // Una cuenta con platillos sin cobrar impide cerrar; las vacias no (una
  // mesa abierta por error se puede liberar sin mas).
  const porCobrar = visit.orders.filter((order) => order.items?.length && order.status !== "pagado");
  return <div className="rest-close-visit">
    <span className="rest-muted">
      {porCobrar.length
        ? `${porCobrar.length} ${porCobrar.length === 1 ? t("restaurant.account") : t("restaurant.accounts")} ${t("restaurant.still_unpaid")}`
        : t("restaurant.ready_to_close")}
    </span>
    <button className="rest-danger" disabled={porCobrar.length > 0} onClick={onClose}>
      <DoorClosed size={16} /> {visit.service_type === "para_llevar" ? t("restaurant.close_takeout") : t("restaurant.close_table")}
    </button>
  </div>;
}

function ReservationBox({ onSave }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", reservation_date: "", reservation_time: "", guests: 2 });
  const submit = (event) => { event.preventDefault(); onSave(form); setForm({ name: "", reservation_date: "", reservation_time: "", guests: 2 }); };
  return <form className="rest-panel rest-form" onSubmit={submit}><div className="rest-panel-heading"><div><span>{t("restaurant.upcoming_visits")}</span><h2>{t("restaurant.new_reservation")}</h2></div><CalendarPlus size={22} /></div><div className="rest-form-grid"><label className="rest-field"><span>{t("restaurant.name")}</span><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label className="rest-field"><span>{t("restaurant.people")}</span><input required min="1" type="number" value={form.guests} onChange={(event) => setForm({ ...form, guests: Number(event.target.value) })} /></label><label className="rest-field"><span>{t("restaurant.date")}</span><input required type="date" value={form.reservation_date} onChange={(event) => setForm({ ...form, reservation_date: event.target.value })} /></label><label className="rest-field"><span>{t("restaurant.time")}</span><input required type="time" value={form.reservation_time} onChange={(event) => setForm({ ...form, reservation_time: event.target.value })} /></label></div><button className="rest-secondary" type="submit">{t("restaurant.save_reservation")}</button></form>;
}