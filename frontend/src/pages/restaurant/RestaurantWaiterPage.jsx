/* eslint-disable react/prop-types */
import React, { useEffect, useState } from "react";
import { CalendarPlus, Check, Minus, Plus, Send, Users } from "lucide-react";
import { addRestaurantDiner, addRestaurantOrderItem, createRestaurantReservation, createRestaurantVisit, deliverRestaurantOrder, getRestaurantWaiterWorkspace, removeRestaurantDiner, removeRestaurantOrderItem, sendRestaurantOrder } from "../../api";
import { useI18n } from "../../i18n";
import { EmptyState, money, Notice, RestaurantHeader, Status } from "./RestaurantUi";
import "../../styles/restaurant.css";

export default function RestaurantWaiterPage() {
  const { t } = useI18n();
  const [data, setData] = useState({ tables: [], visits: [], menu: { dishes: [], guisados: [] }, delivery: [], waiters: [], reservations: [] });
  const [selectedVisit, setSelectedVisit] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [guisado, setGuisado] = useState("");
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
  const addDish = (dish) => act(() => addRestaurantOrderItem(selectedOrder.id_restaurant_order, { id_restaurant_dish: dish.id_restaurant_dish, id_guisado_1: dish.requires_guisado ? Number(guisado) : null, quantity: 1 }));
  return <main className="rest-page">
    <RestaurantHeader eyebrow={t("restaurant.waiter_eyebrow")} title={t("restaurant.waiter_title")} detail={t("restaurant.waiter_detail")} loading={loading} onRefresh={load} />
    <Notice error={error} />
    <section className="rest-waiter-layout">
      <div className="rest-panel rest-floor"><div className="rest-panel-heading"><div><span>{t("restaurant.service_map")}</span><h2>{t("restaurant.tables")}</h2></div><span>{data.visits.length} {t("restaurant.active_plural")}</span></div>
        <div className="rest-table-grid">{data.tables.map((table) => { const visit = data.visits.find((item) => item.id_restaurant_table === table.id_restaurant_table); return <button key={table.id_restaurant_table} className={`rest-table ${visit ? "is-busy" : ""} ${selectedVisit?.id_restaurant_table === table.id_restaurant_table ? "is-selected" : ""}`} onClick={() => chooseTable(table)}><strong>{table.number}</strong><span>{visit ? `${visit.diners_count} ${t("restaurant.diners")}` : `${table.capacity} ${t("restaurant.places")}`}</span></button>; })}</div>
      </div>
      <div className="rest-panel rest-order">
        {!selectedVisit ? <EmptyState>{t("restaurant.select_table")}</EmptyState> : <>
          <div className="rest-panel-heading"><div><span>{t("restaurant.active_order")}</span><h2>{t("restaurant.table")} {selectedVisit.table?.number}</h2></div><div className="rest-inline-actions"><button className="rest-icon-button" title={t("restaurant.remove_diner")} disabled={selectedVisit.diners_count <= 1} onClick={() => act(() => removeRestaurantDiner(selectedVisit.id_restaurant_visit, selectedVisit.diners_count))}><Minus size={17} /></button><span><Users size={16} /> {selectedVisit.diners_count}</span><button className="rest-icon-button" title={t("restaurant.add_diner")} onClick={() => act(() => addRestaurantDiner(selectedVisit.id_restaurant_visit))}><Plus size={17} /></button></div></div>
          <div className="rest-diner-tabs">{selectedVisit.orders.map((order) => <button key={order.id_restaurant_order} className={selectedOrder?.id_restaurant_order === order.id_restaurant_order ? "active" : ""} onClick={() => setSelectedOrder(order)}>{t("restaurant.diner")} {order.diner_index}</button>)}</div>
          {selectedOrder?.status === "borrador" && <><label className="rest-field rest-guisado"><span>{t("restaurant.stew_label")}</span><select value={guisado} onChange={(event) => setGuisado(event.target.value)}><option value="">{t("restaurant.select")}</option>{data.menu.guisados.map((item) => <option key={item.id_restaurant_guisado} value={item.id_restaurant_guisado}>{item.name}</option>)}</select></label><div className="rest-menu-grid">{data.menu.dishes.map((dish) => <button key={dish.id_restaurant_dish} onClick={() => addDish(dish)} disabled={dish.requires_guisado && !guisado}><span>{dish.category.replaceAll("_", " ")}</span><strong>{dish.title}</strong><b>{money(dish.price)}</b></button>)}</div></>}
          <div className="rest-ticket"><div className="rest-ticket-head"><strong>{t("restaurant.detail")}</strong><Status value={selectedOrder?.status} /></div>{selectedOrder?.items?.length ? selectedOrder.items.map((item) => <div className="rest-ticket-row" key={item.id_restaurant_order_item}><span>{item.quantity} × {item.dish?.title}{item.guisado_1?.name ? ` · ${item.guisado_1.name}` : ""}</span><b>{money(Number(item.unit_price) * item.quantity)}</b>{selectedOrder.status === "borrador" && <button className="rest-icon-button" title={t("restaurant.remove")} onClick={() => act(() => removeRestaurantOrderItem(selectedOrder.id_restaurant_order, item.id_restaurant_order_item))}><Minus size={15} /></button>}</div>) : <EmptyState>{t("restaurant.empty_order")}</EmptyState>}<div className="rest-ticket-total"><span>{t("restaurant.total")}</span><strong>{money(selectedOrder?.subtotal)}</strong></div>{selectedOrder?.status === "borrador" && <button className="rest-primary" disabled={!selectedOrder.items?.length} onClick={() => act(() => sendRestaurantOrder(selectedOrder.id_restaurant_order))}><Send size={17} /> {t("restaurant.send_kitchen")}</button>}</div>
        </>}
      </div>
    </section>
    <section className="rest-bottom-grid"><div className="rest-panel"><div className="rest-panel-heading"><div><span>{t("restaurant.kitchen_output")}</span><h2>{t("restaurant.lane_ready")}</h2></div></div><div className="rest-delivery-list">{data.delivery.filter((order) => order.status === "listo_para_entrega").map((order) => <div key={order.id_restaurant_order}><div><strong>{t("restaurant.table")} {order.visit?.table?.number} · {t("restaurant.diner")} {order.diner_index}</strong><span>{order.items.map((item) => `${item.quantity} ${item.dish?.title}`).join(", ")}</span></div><button className="rest-primary" onClick={() => act(() => deliverRestaurantOrder(order.id_restaurant_order))}><Check size={16} /> {t("restaurant.deliver")}</button></div>)}{!data.delivery.some((order) => order.status === "listo_para_entrega") && <EmptyState>{t("restaurant.no_delivery")}</EmptyState>}</div></div>
      <ReservationBox onSave={(payload) => act(() => createRestaurantReservation(payload))} />
    </section>
  </main>;
}

function ReservationBox({ onSave }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", reservation_date: "", reservation_time: "", guests: 2 });
  const submit = (event) => { event.preventDefault(); onSave(form); setForm({ name: "", reservation_date: "", reservation_time: "", guests: 2 }); };
  return <form className="rest-panel rest-form" onSubmit={submit}><div className="rest-panel-heading"><div><span>{t("restaurant.upcoming_visits")}</span><h2>{t("restaurant.new_reservation")}</h2></div><CalendarPlus size={22} /></div><div className="rest-form-grid"><label className="rest-field"><span>{t("restaurant.name")}</span><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label className="rest-field"><span>{t("restaurant.people")}</span><input required min="1" type="number" value={form.guests} onChange={(event) => setForm({ ...form, guests: Number(event.target.value) })} /></label><label className="rest-field"><span>{t("restaurant.date")}</span><input required type="date" value={form.reservation_date} onChange={(event) => setForm({ ...form, reservation_date: event.target.value })} /></label><label className="rest-field"><span>{t("restaurant.time")}</span><input required type="time" value={form.reservation_time} onChange={(event) => setForm({ ...form, reservation_time: event.target.value })} /></label></div><button className="rest-secondary" type="submit">{t("restaurant.save_reservation")}</button></form>;
}