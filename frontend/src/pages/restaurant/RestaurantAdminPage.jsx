/* eslint-disable react/prop-types */
import React, { useEffect, useState } from "react";
import { Boxes, ChefHat, ClipboardList, Plus, Table2, UsersRound, Utensils } from "lucide-react";
import { createRestaurantDish, createRestaurantGuisado, createRestaurantInventoryItem, createRestaurantRecipeItem, createRestaurantTable, createRestaurantWaiter, getRestaurantAdminWorkspace } from "../../api";
import { useI18n } from "../../i18n";
import { EmptyState, money, Notice, RestaurantHeader, Status } from "./RestaurantUi";
import "../../styles/restaurant.css";

const tabs = [
  { key: "dishes", icon: Utensils }, { key: "tables", icon: Table2 }, { key: "waiters", icon: UsersRound },
  { key: "reservations", icon: ClipboardList }, { key: "inventory", icon: Boxes }, { key: "recipes", icon: ChefHat },
];

export default function RestaurantAdminPage() {
  const { t } = useI18n();
  const [data, setData] = useState({ dishes: [], guisados: [], tables: [], waiters: [], reservations: [], inventory: [], recipes: [], categories: [] });
  const [tab, setTab] = useState("dishes");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try { setData(await getRestaurantAdminWorkspace()); setError(null); }
    catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async (operation) => {
    try { await operation(); await load(); }
    catch (reason) { setError(reason); }
  };
  return <main className="rest-page">
    <RestaurantHeader eyebrow={t("restaurant.admin_eyebrow")} title={t("restaurant.admin_title")} detail={t("restaurant.admin_detail")} loading={loading} onRefresh={load} />
    <Notice error={error} />
    <nav className="rest-admin-tabs">{tabs.map((item) => { const Icon = item.icon; return <button key={item.key} className={tab === item.key ? "active" : ""} onClick={() => setTab(item.key)}><Icon size={17} />{t(`restaurant.tab_${item.key}`)}<span>{data[item.key]?.length || 0}</span></button>; })}</nav>
    <section className="rest-admin-workspace">
      {tab === "dishes" && <DishAdmin data={data} save={save} />}
      {tab === "tables" && <TableAdmin items={data.tables} save={save} />}
      {tab === "waiters" && <WaiterAdmin items={data.waiters} save={save} />}
      {tab === "reservations" && <ReservationAdmin items={data.reservations} />}
      {tab === "inventory" && <InventoryAdmin items={data.inventory} save={save} />}
      {tab === "recipes" && <RecipeAdmin data={data} save={save} />}
    </section>
  </main>;
}

function AdminSection({ title, detail, form, children }) {
  return <><div className="rest-admin-list rest-panel"><div className="rest-panel-heading"><div><span>{detail}</span><h2>{title}</h2></div></div>{children}</div><div className="rest-admin-form rest-panel">{form}</div></>;
}

function DishAdmin({ data, save }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ title: "", category: data.categories[0] || "taco", price: 0, production_cost: 0, schedule: "all", requires_guisado: false });
  const [guisadoName, setGuisadoName] = useState("");
  return <AdminSection title={t("restaurant.dishes_title")} detail={t("restaurant.sales_catalog")} form={<SimpleForm title={t("restaurant.new_dish")} onSubmit={() => save(() => createRestaurantDish(form))}>
    <Field label={t("restaurant.name")}><input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field>
    <Field label={t("restaurant.category")}><select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{data.categories.map((item) => <option key={item}>{item}</option>)}</select></Field>
    <Field label={t("restaurant.price")}><input type="number" min="0" step=".01" value={form.price} onChange={(event) => setForm({ ...form, price: Number(event.target.value) })} /></Field>
    <Field label={t("restaurant.cost")}><input type="number" min="0" step=".01" value={form.production_cost} onChange={(event) => setForm({ ...form, production_cost: Number(event.target.value) })} /></Field>
    <label className="rest-check"><input type="checkbox" checked={form.requires_guisado} onChange={(event) => setForm({ ...form, requires_guisado: event.target.checked })} /> {t("restaurant.requires_stew")}</label>
  </SimpleForm>}>
    <form className="rest-quick-add" onSubmit={(event) => { event.preventDefault(); save(() => createRestaurantGuisado({ name: guisadoName })); setGuisadoName(""); }}><label className="rest-quick-add-field"><span>{t("restaurant.new_stew")}</span><input required value={guisadoName} onChange={(event) => setGuisadoName(event.target.value)} /></label><button className="rest-secondary" type="submit"><Plus size={15} /> {t("restaurant.add_stew")}</button></form>
    {data.dishes.map((item) => <div className="rest-catalog-row" key={item.id_restaurant_dish}><div><strong>{item.title}</strong><span>{item.category.replaceAll("_", " ")}</span></div><span>{t("restaurant.cost")} {money(item.production_cost)}</span><b>{money(item.price)}</b></div>)}
  </AdminSection>;
}

function TableAdmin({ items, save }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ number: "", capacity: 4, location_description: t("restaurant.main_dining_room") });
  return <AdminSection title={t("restaurant.table_layout")} detail={t("restaurant.floor_capacity")} form={<SimpleForm title={t("restaurant.new_table")} onSubmit={() => save(() => createRestaurantTable(form))}>
    <Field label={t("restaurant.number")}><input required type="number" value={form.number} onChange={(event) => setForm({ ...form, number: Number(event.target.value) })} /></Field>
    <Field label={t("restaurant.capacity")}><input required type="number" value={form.capacity} onChange={(event) => setForm({ ...form, capacity: Number(event.target.value) })} /></Field>
    <Field label={t("restaurant.location")}><input value={form.location_description} onChange={(event) => setForm({ ...form, location_description: event.target.value })} /></Field>
  </SimpleForm>}><div className="rest-table-grid">{items.map((item) => <div className="rest-table admin" key={item.id_restaurant_table}><strong>{item.number}</strong><span>{item.capacity} {t("restaurant.places")}</span><small>{item.location_description}</small></div>)}</div></AdminSection>;
}

function WaiterAdmin({ items, save }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", nickname: "", max_tables: 15 });
  return <AdminSection title={t("restaurant.floor_team")} detail={t("restaurant.waiter_capacity")} form={<SimpleForm title={t("restaurant.new_waiter")} onSubmit={() => save(() => createRestaurantWaiter(form))}>
    <Field label={t("restaurant.name")}><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
    <Field label={t("restaurant.short_name")}><input required value={form.nickname} onChange={(event) => setForm({ ...form, nickname: event.target.value })} /></Field>
    <Field label={t("restaurant.max_tables")}><input type="number" value={form.max_tables} onChange={(event) => setForm({ ...form, max_tables: Number(event.target.value) })} /></Field>
  </SimpleForm>}>{items.map((item) => <div className="rest-catalog-row" key={item.id_restaurant_waiter}><div><strong>{item.name}</strong><span>{item.nickname}</span></div><span>{item.max_tables} {t("restaurant.tables_lower")}</span><Status value={item.status} /></div>)}</AdminSection>;
}

function ReservationAdmin({ items }) {
  const { t } = useI18n();
  return <AdminSection title={t("restaurant.schedule")} detail={t("restaurant.registered_reservations")} form={<div><h2>{t("restaurant.summary")}</h2><p className="rest-muted">{t("restaurant.reservation_hint")}</p></div>}>{items.length ? items.map((item) => <div className="rest-catalog-row" key={item.id_restaurant_reservation}><div><strong>{item.name}</strong><span>{item.reservation_date} · {item.reservation_time}</span></div><span>{item.guests} {t("restaurant.people_lower")}</span><Status value={item.status} /></div>) : <EmptyState>{t("restaurant.no_reservations")}</EmptyState>}</AdminSection>;
}

function InventoryAdmin({ items, save }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ description: "", quantity: 0, unit: "kg", cost_per_unit: 0 });
  return <AdminSection title={t("restaurant.stock")} detail={t("restaurant.supplies_costs")} form={<SimpleForm title={t("restaurant.add_supply")} onSubmit={() => save(() => createRestaurantInventoryItem(form))}>
    <Field label={t("restaurant.description")}><input required value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field>
    <Field label={t("restaurant.quantity")}><input type="number" step=".001" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: Number(event.target.value) })} /></Field>
    <Field label={t("restaurant.unit")}><input required value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></Field>
    <Field label={t("restaurant.unit_cost")}><input type="number" step=".01" value={form.cost_per_unit} onChange={(event) => setForm({ ...form, cost_per_unit: Number(event.target.value) })} /></Field>
  </SimpleForm>}>{items.length ? items.map((item) => <div className="rest-catalog-row" key={item.id_restaurant_inventory_item}><div><strong>{item.description}</strong><span>{item.quantity} {item.unit}</span></div><b>{money(item.cost_per_unit)}</b></div>) : <EmptyState>{t("restaurant.inventory_empty")}</EmptyState>}</AdminSection>;
}

function RecipeAdmin({ data, save }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ id_restaurant_dish: "", id_restaurant_inventory_item: "", quantity: 0, unit: "g" });
  const submit = () => save(() => createRestaurantRecipeItem({ ...form, id_restaurant_dish: Number(form.id_restaurant_dish), id_restaurant_inventory_item: Number(form.id_restaurant_inventory_item) }));
  return <AdminSection title={t("restaurant.recipe_book")} detail={t("restaurant.consumption_per_dish")} form={<SimpleForm title={t("restaurant.add_component")} onSubmit={submit}>
    <Field label={t("restaurant.dish")}><select required value={form.id_restaurant_dish} onChange={(event) => setForm({ ...form, id_restaurant_dish: event.target.value })}><option value="">{t("restaurant.select")}</option>{data.dishes.map((item) => <option key={item.id_restaurant_dish} value={item.id_restaurant_dish}>{item.title}</option>)}</select></Field>
    <Field label={t("restaurant.supply")}><select required value={form.id_restaurant_inventory_item} onChange={(event) => setForm({ ...form, id_restaurant_inventory_item: event.target.value })}><option value="">{t("restaurant.select")}</option>{data.inventory.map((item) => <option key={item.id_restaurant_inventory_item} value={item.id_restaurant_inventory_item}>{item.description}</option>)}</select></Field>
    <Field label={t("restaurant.quantity")}><input required type="number" step=".001" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: Number(event.target.value) })} /></Field>
    <Field label={t("restaurant.unit")}><input required value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></Field>
  </SimpleForm>}>{data.recipes.length ? data.recipes.map((item) => <div className="rest-catalog-row" key={item.id_restaurant_recipe_item}><strong>{data.dishes.find((dish) => dish.id_restaurant_dish === item.id_restaurant_dish)?.title}</strong><span>{item.quantity} {item.unit} · {data.inventory.find((inventory) => inventory.id_restaurant_inventory_item === item.id_restaurant_inventory_item)?.description}</span></div>) : <EmptyState>{t("restaurant.recipes_empty")}</EmptyState>}</AdminSection>;
}

function SimpleForm({ title, onSubmit, children }) {
  const { t } = useI18n();
  return <form onSubmit={(event) => { event.preventDefault(); onSubmit(); }}><div className="rest-panel-heading"><div><span>{t("restaurant.quick_create")}</span><h2>{title}</h2></div><Plus size={21} /></div><div className="rest-form-stack">{children}</div><button className="rest-primary" type="submit"><Plus size={16} /> {t("restaurant.save")}</button></form>;
}

function Field({ label, children }) {
  return <label className="rest-field"><span>{label}</span>{children}</label>;
}
