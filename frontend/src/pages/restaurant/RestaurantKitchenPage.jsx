import React, { useEffect, useState } from "react";
import { CheckCircle2, ChefHat, Flame } from "lucide-react";
import { getRestaurantKitchenBoard, updateRestaurantKitchenOrder } from "../../api";
import { useI18n } from "../../i18n";
import { EmptyState, Notice, RestaurantHeader } from "./RestaurantUi";
import "../../styles/restaurant.css";

const lanes = [{ status: "pedido", titleKey: "lane_pending", icon: ChefHat, next: "en_preparacion", actionKey: "start" }, { status: "en_preparacion", titleKey: "lane_preparing", icon: Flame, next: "listo_para_entrega", actionKey: "mark_ready" }, { status: "listo_para_entrega", titleKey: "lane_ready", icon: CheckCircle2 }];
export default function RestaurantKitchenPage() {
  const { t } = useI18n();
  const [orders, setOrders] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(null);
  const load = async () => { setLoading(true); try { setOrders((await getRestaurantKitchenBoard()).items || []); setError(null); } catch (reason) { setError(reason); } finally { setLoading(false); } };
  useEffect(() => { load(); const timer = window.setInterval(load, 30000); return () => window.clearInterval(timer); }, []);
  const advance = async (order, status) => { try { await updateRestaurantKitchenOrder(order.id_restaurant_order, status); await load(); } catch (reason) { setError(reason); } };
  return <main className="rest-page rest-kitchen"><RestaurantHeader eyebrow={t("restaurant.kitchen_eyebrow")} title={t("restaurant.kitchen_title")} detail={t("restaurant.kitchen_detail")} loading={loading} onRefresh={load} /><Notice error={error} /><div className="rest-kitchen-board">{lanes.map((lane) => { const items = orders.filter((order) => order.status === lane.status); const Icon = lane.icon; return <section className={`rest-kitchen-lane lane-${lane.status}`} key={lane.status}><header><Icon size={21} /><h2>{t(`restaurant.${lane.titleKey}`)}</h2><span>{items.length}</span></header><div>{items.map((order) => <article className="rest-kitchen-ticket" key={order.id_restaurant_order}><div className="rest-kitchen-ticket-head"><strong>{t("restaurant.table")} {order.visit?.table?.number}</strong><span>{t("restaurant.diner")} {order.diner_index}</span></div><ul>{order.items.map((item) => <li key={item.id_restaurant_order_item}><b>{item.quantity}×</b><span>{item.dish?.title}<small>{[item.guisado_1?.name, item.guisado_2?.name, item.note].filter(Boolean).join(" · ")}</small></span></li>)}</ul>{lane.next && <button className="rest-primary" onClick={() => advance(order, lane.next)}>{t(`restaurant.${lane.actionKey}`)}</button>}</article>)}{!items.length && <EmptyState>{t("restaurant.kitchen_empty")}</EmptyState>}</div></section>; })}</div></main>;
}