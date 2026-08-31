import { useEffect, useRef, useState, useCallback } from 'react';
import { NavLink, Navigate, Routes, Route, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Ban, Check, ClipboardList, Clock, LayoutGrid, Minus, Plus, Search,
  ShoppingBag, Trash2, Truck, UserMinus, UserPlus, Users, Utensils,
} from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { useCategories } from '../../contexts/CategoriesContext';
import { CatIcon } from '../../components/shared/CatIcon';
import { EmptyState } from '../../components/shared/EmptyState';
import { Portal } from '../../components/shared/Portal';
import { RefreshButton } from '../../components/shared/RefreshButton';
import { money, labelStatus, elapsedMinutes, STATUS_VAR } from '../../utils/format';
import { DeliveryBoard, playNotificationSound } from '../kitchen/KitchenBoard';
import type { Translations } from '../../i18n/translations';
import type { User, Table, Visit, Order, OrderItem, Dish, Guisado } from '../../types/api';

/* ---------------------------- MESERO ---------------------------- */

export function WaiterApp({ t, user: _user }: { t: Translations; user: User | null }) {
  const navigate = useNavigate();
  // Rutas absolutas a proposito: WaiterApp se monta bajo un splat ("/mesero/*"
  // en main.jsx) y renderiza su propio <Routes> descendiente -- un `to`
  // relativo aqi (ej. "mesas") se resuelve contra la URL actual, no contra
  // la base "/mesero", asi que navegar desde "/mesero/entregas" hacia
  // "mesas" terminaba en "/mesero/entregas/mesas" en vez de "/mesero/mesas"
  // (y ese path roto, al no matchear ninguna ruta, caia en el catch-all de
  // abajo que a su vez repetia el mismo error -- un loop que iba
  // encadenando "/mesas" sin fin). Usar rutas absolutas evita la ambiguedad.
  const goToBoard = () => navigate('/mesero/entregas');
  // La mesa/pedido para llevar que el mesero esta atendiendo activamente
  // vive aqui (no dentro de TablesView/TakeoutView), para que NO se pierda
  // al cambiar a la pestana del tablero de entregas y volver: antes, al
  // cambiar de pestana, TablesView/TakeoutView se desmontaba y el mesero
  // regresaba siempre al listado en vez de continuar donde se habia
  // quedado. Son DOS estados separados (no uno compartido) porque un
  // mesero puede estar a mitad de armar una mesa Y un pedido para llevar
  // al mismo tiempo: con un solo estado compartido, entrar a una mesa
  // mientras habia un pedido para llevar activo pisaba esa referencia (la
  // sobreescribia con la visita de la mesa), y al volver a "Para llevar"
  // TakeoutView ya no encontraba is_takeout=true y regresaba a la lista
  // como si el mesero nunca hubiera entrado a ese pedido.
  const [activeTableVisit, setActiveTableVisit] = useState<Visit | null>(null);
  const [activeTakeoutVisit, setActiveTakeoutVisit] = useState<Visit | null>(null);
  // Contador en vivo de platillos listos para recoger: asi el mesero sabe
  // cuando conviene cambiar al tablero de entregas sin tener que estar
  // entrando a revisar a cada rato. Se actualiza junto con el resto del
  // polling de la app (cada 6s), independientemente de en que pestana este.
  const [readyCount, setReadyCount] = useState(0);
  // Recuerda que platillos ya estaban "listos" en el ultimo chequeo, para
  // sonar la notificacion solo cuando aparece uno NUEVO (no en cada poll, y
  // no en la primera carga de la pagina).
  const seenReadyIds = useRef<Set<number> | null>(null);
  useEffect(() => {
    function load() {
      api.kitchenBoard().then(d => {
        const readyItems = (d.items || []).filter(it => it.status === 'listo_para_entrega');
        const ids = new Set(readyItems.map(it => it.id));
        if (seenReadyIds.current) {
          let hasNew = false;
          ids.forEach(id => { if (!seenReadyIds.current!.has(id)) hasNew = true; });
          if (hasNew) playNotificationSound();
        }
        seenReadyIds.current = ids;
        setReadyCount(readyItems.length);
      }).catch(() => {});
    }
    load();
    const id = setInterval(load, 6000);
    return () => clearInterval(id);
  }, []);
  return <main className="page">
    <div className="section-title"><Users /><h1>{t.roleWaiter}</h1></div>
    <div className="admin-tabs waiter-nav-sticky">
      <NavLink to="/mesero/mesas" className={({ isActive }) => isActive ? 'active' : ''}>
        <LayoutGrid size={16} /> {activeTableVisit ? `${t.table} ${activeTableVisit.table_number}` : t.tables}
      </NavLink>
      <NavLink to="/mesero/para-llevar" className={({ isActive }) => isActive ? 'active' : ''}>
        <ShoppingBag size={16} /> {activeTakeoutVisit ? `${t.takeoutLabel} #${activeTakeoutVisit.daily_number ?? activeTakeoutVisit.id}` : t.takeoutTab}
      </NavLink>
      <NavLink to="/mesero/entregas" className={({ isActive }) => isActive ? 'active' : ''}>
        <Truck size={16} /> {t.waiterBoard}
        {readyCount > 0 && <span className="nav-badge">{readyCount}</span>}
      </NavLink>
    </div>
    <Routes>
      <Route index element={<Navigate to="/mesero/mesas" replace />} />
      <Route path="mesas" element={<TablesView t={t} activeVisit={activeTableVisit} setActiveVisit={setActiveTableVisit} onGoToBoard={goToBoard} />} />
      <Route path="para-llevar" element={<TakeoutView t={t} activeVisit={activeTakeoutVisit} setActiveVisit={setActiveTakeoutVisit} onGoToBoard={goToBoard} />} />
      <Route path="entregas" element={<DeliveryBoard t={t} />} />
      <Route path="*" element={<Navigate to="/mesero/mesas" replace />} />
    </Routes>
  </main>;
}

interface TablesViewProps {
  t: Translations
  activeVisit: Visit | null
  setActiveVisit: (v: Visit | null) => void
  onGoToBoard: () => void
}

function TablesView({ t, activeVisit, setActiveVisit, onGoToBoard }: TablesViewProps) {
  const toast = useToast();
  const [tables, setTables] = useState<Table[]>([]);
  const [newVisitTable, setNewVisitTable] = useState<number | null>(null);
  const [dinerCount, setDinerCount] = useState(1);

  async function loadTables() { try { const data = await api.tables(); setTables(data.items || []); } catch (e) { console.error(e); } }
  useEffect(() => { loadTables(); const id = setInterval(loadTables, 8000); return () => clearInterval(id); }, []);

  async function openTable(table: Table) {
    if (!table.occupied) { setNewVisitTable(table.number); setDinerCount(1); return; }
    try {
      const v = await api.visit(table.visit_id!);
      setActiveVisit(v);
    } catch (e) { toast.error((e as Error).message); }
  }

  async function confirmNewVisit() {
    // Sin try/catch, dos meseros abriendo la misma mesa casi al mismo
    // tiempo dejaban al que pierde la carrera viendo el modal de "Cuantos
    // comensales son?" trabado, sin ningun aviso de que la mesa ya se
    // habia ocupado (ver el 409 table_occupied que el backend ya devuelve).
    try {
      const v = await api.createVisit(newVisitTable!, dinerCount);
      setActiveVisit(v); setNewVisitTable(null);
      loadTables().catch(console.error);
    } catch (e) {
      toast.error((e as Error).message);
      setNewVisitTable(null);
      loadTables().catch(console.error);
    }
  }

  async function refreshVisit(id: number) { const v = await api.visit(id); setActiveVisit(v); }

  async function backToTables() { setActiveVisit(null); loadTables().catch(console.error); }

  if (activeVisit && !activeVisit.is_takeout) return <VisitWorkspace t={t} visit={activeVisit} onRefresh={() => refreshVisit(activeVisit.id)} onClose={backToTables} onGoToBoard={onGoToBoard} />;

  const freeCount = tables.filter(tb => !tb.occupied).length;
  return <>
    <div className="table-grid-header">
      <div className="table-legend">
        <span className="table-legend-item"><span className="dot" />{t.free}</span>
        <span className="table-legend-item"><span className="dot occ" />{t.occupied}</span>
        <span className="table-legend-count">{freeCount}/{tables.length} {t.free.toLowerCase()}</span>
      </div>
      <RefreshButton t={t} onClick={loadTables} />
    </div>
    <div className="table-grid-wrap">
      <div className="table-grid">
        {tables.map((tb, idx) => <button key={tb.id} className={`table-btn ${tb.occupied ? 'occupied' : ''}`} style={{ animationDelay: `${Math.min(idx * 25, 300)}ms` }} onClick={() => openTable(tb)}>
          <span className="table-btn-icon"><Utensils size={18} /></span>
          <span className="table-btn-number">{t.table} {tb.number}</span>
          <small><span className="dot" />{tb.occupied ? `${tb.diners_count} ${tb.diners_count === 1 ? t.diner : t.diners}` : t.free}</small>
        </button>)}
      </div>
    </div>
    {newVisitTable && <Portal><div className="modal"><div className="ticket-panel">
      <button className="close" onClick={() => setNewVisitTable(null)}>&times;</button>
      <h2>{t.table} {newVisitTable}</h2>
      <p>{t.howManyDiners}</p>
      <div className="qty-row">
        <button onClick={() => setDinerCount(n => Math.max(1, n - 1))}><Minus size={18} /></button>
        <span>{dinerCount}</span>
        <button onClick={() => setDinerCount(n => Math.min(15, n + 1))}><Plus size={18} /></button>
      </div>
      <button className="primary big" onClick={confirmNewVisit}>{t.openTable}</button>
    </div></div></Portal>}
  </>;
}

/**
 * Pestana "Para llevar" del mesero: lista los pedidos para llevar activos
 * (mismo modelo Visit/Order que una mesa, pero sin table_number -- ver
 * is_takeout en el backend) y permite crear uno nuevo con un nombre/nota
 * opcional para identificarlo al momento de la entrega. Al entrar a un
 * pedido reusa exactamente el mismo VisitWorkspace que usa una mesa
 * (armar la orden, enviar a cocina, marcar entregado): un pedido para
 * llevar avanza por cocina igual que cualquier otro, solo que no ocupa
 * ninguna mesa fisica ni bloquea el tablero de "Mesas".
 */
function TakeoutView({ t, activeVisit, setActiveVisit, onGoToBoard }: TablesViewProps) {
  const toast = useToast();
  const [visits, setVisits] = useState<Visit[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [customerName, setCustomerName] = useState('');

  async function loadVisits() {
    try { const data = await api.visits('?status=active&is_takeout=1'); setVisits(data.items || []); } catch (e) { console.error(e); }
  }
  useEffect(() => { loadVisits(); const id = setInterval(loadVisits, 8000); return () => clearInterval(id); }, []);

  async function openVisit(v: Visit) {
    try {
      const full = await api.visit(v.id);
      setActiveVisit(full);
    } catch (e) { toast.error((e as Error).message); }
  }

  async function createTakeout() {
    try {
      const v = await api.createTakeoutVisit(customerName.trim());
      setCustomerName(''); setShowNew(false);
      setActiveVisit(v);
      loadVisits().catch(console.error);
    } catch (e) { toast.error((e as Error).message); }
  }

  async function refreshVisit(id: number) { const v = await api.visit(id); setActiveVisit(v); }
  async function backToList() { setActiveVisit(null); loadVisits().catch(console.error); }

  if (activeVisit && activeVisit.is_takeout) return <VisitWorkspace t={t} visit={activeVisit} onRefresh={() => refreshVisit(activeVisit.id)} onClose={backToList} onGoToBoard={onGoToBoard} />;

  return <>
    <div className="table-grid-header">
      <div className="table-legend">
        <span className="table-legend-count">{visits.length} {t.takeoutActiveList.toLowerCase()}</span>
      </div>
      <div style={{ display: 'flex', gap: 10 }}>
        <RefreshButton t={t} onClick={loadVisits} />
        <button className="primary" onClick={() => setShowNew(true)}><Plus size={16} /> {t.takeoutNew}</button>
      </div>
    </div>
    {visits.length === 0
      ? <EmptyState icon={ShoppingBag} title={t.takeoutEmptyHint} />
      : <div className="table-grid-wrap"><div className="table-grid">
        {visits.map((v, idx) => <button key={v.id} className="table-btn occupied" style={{ animationDelay: `${Math.min(idx * 25, 300)}ms` }} onClick={() => openVisit(v)}>
          <span className="table-btn-icon"><ShoppingBag size={18} /></span>
          <span className="table-btn-number">{t.takeoutLabel} #{v.daily_number ?? v.id}</span>
          <small>{v.customer_name || '-'}</small>
        </button>)}
      </div></div>}
    {showNew && <Portal><div className="modal"><div className="ticket-panel">
      <button className="close" onClick={() => setShowNew(false)}>&times;</button>
      <h2>{t.takeoutNew}</h2>
      <label>{t.takeoutCustomerName}<input value={customerName} onChange={e => setCustomerName(e.target.value)} placeholder={t.takeoutCustomerNamePlaceholder} /></label>
      <button className="primary big" onClick={createTakeout}>{t.takeoutCreate}</button>
    </div></div></Portal>}
  </>;
}

interface VisitWorkspaceProps {
  t: Translations
  visit: Visit
  onRefresh: () => void
  onClose: () => void
  onGoToBoard?: () => void
}

function VisitWorkspace({ t, visit, onRefresh, onClose, onGoToBoard }: VisitWorkspaceProps) {
  const toast = useToast();
  const orders = visit.orders || [];
  const [activeIdx, setActiveIdx] = useState(orders[0]?.diner_index || 1);
  // Antes esto solo dependia de visit.id, asi que si el comensal activo se
  // quitaba (removeDiner, o el polling de cada 6s trayendo una version mas
  // reciente de la mesa con un comensal de menos) sin cambiar de mesa, este
  // efecto nunca volvia a correr: activeIdx se quedaba apuntando a un
  // diner_index que ya no existe, activeOrder daba undefined, y todo el
  // panel de MenuBrowser/TicketPanel que depende de activeOrder desaparecia
  // en silencio. La dependencia ahora incluye la lista real de comensales.
  const dinerIndexesKey = orders.map(o => o.diner_index).join(',');
  useEffect(() => { if (!orders.find(o => o.diner_index === activeIdx) && orders[0]) setActiveIdx(orders[0].diner_index); }, [visit.id, dinerIndexesKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const activeOrder = orders.find(o => o.diner_index === activeIdx) || orders[0];

  // Mientras el mesero esta viendo esta mesa, cocina puede ir cambiando el
  // estatus de las ordenes (aceptar, marcar lista, etc.). Sin este polling,
  // el mesero solo veia el estatus actualizado si el mismo hacia una accion
  // (agregar platillo, enviar, etc.) que disparara onRefresh. Con esto se
  // refresca solo cada 6s, igual que hace el resto de los tableros.
  useEffect(() => {
    const id = setInterval(() => onRefresh(), 6000);
    return () => clearInterval(id);
    // onRefresh se omite a proposito: TablesView la pasa como un arrow
    // function inline (identidad nueva en cada render del padre) -- si se
    // agregara aqui, el intervalo se reiniciaria en cada render y el
    // polling de 6s nunca llegaria a dispararse de verdad. Solo debe
    // reiniciarse al cambiar de mesa (visit.id).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visit.id]);

  async function addDiner() {
    // BUG: antes esto no cambiaba de pestana, asi que activeIdx se quedaba
    // en el comensal que ya estaba abierto (normalmente el comensal 1). El
    // mesero pensaba que estaba pidiendo para el comensal nuevo, pero
    // MenuBrowser/TicketPanel seguian apuntando a la orden vieja -- todo lo
    // que agregaba caia en la cuenta del primer comensal (y si esa orden ya
    // estaba aceptada por cocina, el platillo nuevo parecia "ya aceptado"
    // sin que cocina hiciera nada). Ahora se cambia la pestana activa al
    // comensal recien creado apenas se agrega.
    // Sin try/catch, un rechazo del backend (mesa llena a capacidad, visita
    // ya cerrada, error de red) quedaba como una promesa rechazada sin
    // manejar: no aparecia ningun aviso y el boton "Agregar comensal"
    // simplemente parecia "no hacer nada", sin que el mesero supiera por
    // que.
    try {
      const updated = await api.addDiner(visit.id);
      const dinerIndexes = (updated.orders || []).map(o => o.diner_index);
      if (dinerIndexes.length) setActiveIdx(Math.max(...dinerIndexes));
      onRefresh();
    } catch (e) { toast.error((e as Error).message); }
  }
  async function removeDiner(idx: number) { try { await api.removeDiner(visit.id, idx); onRefresh(); } catch (e) { toast.error((e as Error).message); } }
  // Una orden esta "resuelta" si ya se pago, o si no le queda ningun
  // platillo real por resolver: vacia, o con TODOS sus platillos
  // cancelados (items.every() en un arreglo vacio ya da true, asi que este
  // chequeo cubre el caso vacio tambien sin necesidad de revisarlo aparte).
  // Antes solo se revisaba items.length===0, y una orden con todo cancelado
  // seguia teniendo filas en items[] (se conservan para el historial), asi
  // que el boton de "Cerrar mesa" se quedaba deshabilitado sin necesidad.
  const allSettled = orders.every(o => o.status === 'pagado' || o.items.every(it => it.status === 'cancelado'));

  async function closeTable() {
    try { await api.closeVisit(visit.id); onClose(); } catch (e) { toast.error((e as Error).message); }
  }

  return <>
    <div className="menu-header">
      <div>
        <button className="ghost" onClick={onClose}><ArrowLeft size={16} /> {t.backToTables}</button>
        <h1>{visit.is_takeout ? `${t.takeoutLabel} #${visit.daily_number ?? visit.id}${visit.customer_name ? ' - ' + visit.customer_name : ''}` : `${t.table} ${visit.table_number}`}</h1>
      </div>
      <div style={{ display: 'flex', gap: 10 }}>
        {onGoToBoard && <button className="icon-btn" onClick={onGoToBoard}><Truck size={16} /> {t.waiterBoard}</button>}
        <RefreshButton t={t} onClick={onRefresh} />
        <button className="icon-btn" disabled={!allSettled} onClick={closeTable}><Check size={16} /> {t.closeTable}</button>
      </div>
    </div>
    {/* Un pedido para llevar siempre tiene un solo comensal (no aplica el
        concepto de "agregar comensal" de una mesa), asi que esta barra de
        pestanas -exclusiva de mesas con 1+ comensales- no se muestra. */}
    {!visit.is_takeout && <div className="diner-tabs">
      {orders.map(o => <div key={o.id} className={`diner-tab ${o.diner_index === activeIdx ? 'active' : ''}`} onClick={() => setActiveIdx(o.diner_index)}>
        <span className="status-dot" style={{ background: `var(${STATUS_VAR[o.status]})` }} />
        {t.diner} {o.diner_index}
        {o.status === 'borrador' && o.items.length === 0 && <button className="remove-x" onClick={(e) => { e.stopPropagation(); removeDiner(o.diner_index); }}><UserMinus size={14} /></button>}
      </div>)}
      <button className="icon-btn" onClick={addDiner}><UserPlus size={16} /> {t.addDiner}</button>
    </div>}
    {activeOrder && <div className="workspace-grid">
      <MenuBrowser t={t} order={activeOrder} onChanged={onRefresh} />
      {/* Un pedido para llevar es una sola cuenta (nunca "por mesa/comensal"):
          se omite el resumen de mesa (que solo tiene sentido con 2+ ordenes). */}
      <TicketPanel t={t} order={activeOrder} allOrders={visit.is_takeout ? null : orders} onChanged={onRefresh} />
    </div>}
  </>;
}

// Slugs de las 3 categorias de bebidas sembradas por default: si existen,
// se agrupan bajo una sola pestana sintetica "Bebidas" (no satura la barra
// con 3 pestanas chicas). Categorias nuevas que cree el admin no se
// agrupan, cada una aparece con su propia pestana.
const BEVERAGE_SLUGS = ['agua', 'refresco', 'cafe'];

interface AddItemPayload {
  dish_id: number
  quantity: number
  note: string
  guisado_1_id: number | null
  guisado_2_id: number | null
  combinado: boolean
}

function MenuBrowser({ t, order, onChanged }: { t: Translations; order: Order; onChanged: () => void }) {
  const toast = useToast();
  const { categories } = useCategories();
  const [category, setCategory] = useState<string | null>(null);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [guisados, setGuisados] = useState<Guisado[]>([]);
  const [modalDish, setModalDish] = useState<Dish | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => { api.guisados().then(d => setGuisados(d.items || [])).catch(console.error); }, []);

  const hasBeverageTabs = BEVERAGE_SLUGS.some(slug => categories.some(c => c.slug === slug));
  const tabs = [
    ...categories.filter(c => !BEVERAGE_SLUGS.includes(c.slug)),
    ...(hasBeverageTabs ? [{ slug: 'bebida', name: t.categoryBebida, icon: 'cup-soda', color: 'var(--brand-secondary)' }] : []),
  ];
  useEffect(() => { if (!category && tabs.length) setCategory(tabs[0].slug); }, [tabs.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadDishes = useCallback(async () => {
    if (!category) { setDishes([]); return; }
    const params = category === 'bebida' ? BEVERAGE_SLUGS : [category];
    const results = await Promise.all(params.map(c => api.dishes(`?category=${c}&today=1&per_page=100&tz_offset_minutes=${new Date().getTimezoneOffset()}`)));
    setDishes(results.flatMap(r => r.items || []));
  }, [category]);
  useEffect(() => { loadDishes().catch(console.error); }, [loadDishes]);

  async function submitItem(payload: AddItemPayload) {
    // Sin try/catch, un rechazo del backend (ej. la orden ya se pago desde
    // otra pestana) quedaba como una promesa rechazada sin manejar: no
    // aparecia ningun aviso y el mesero no tenia forma de saber por que el
    // platillo nunca se agrego.
    try {
      const result = await api.addItem(order.id, payload as unknown as Record<string, unknown>);
      setModalDish(null);
      onChanged();
      // Si la orden ya estaba 'entregada', el backend la reabrio para que
      // cocina la vea de nuevo; se lo avisamos al mesero para que no piense
      // que el platillo se perdio.
      if (result && result.reopened_for_kitchen) {
        toast.info(t.reopenedForKitchenHint);
      }
    } catch (e) { toast.error((e as Error).message); }
  }

  // Agregado rapido: un toque manda el platillo a la orden con cantidad 1
  // y sin comentario, sin abrir el modal -- solo para platillos que NO
  // requieren elegir guisado (los que si lo requieren siguen abriendo el
  // modal, porque hace falta esa eleccion).
  async function quickAdd(dish: Dish) {
    try {
      const result = await api.addItem(order.id, { dish_id: dish.id, quantity: 1, note: '', guisado_1_id: null, guisado_2_id: null, combinado: false });
      onChanged();
      if (result && result.reopened_for_kitchen) toast.info(t.reopenedForKitchenHint);
    } catch (e) { toast.error((e as Error).message); }
  }

  const term = search.trim().toLowerCase();
  const filteredDishes = term ? dishes.filter(d => d.title.toLowerCase().includes(term)) : dishes;

  const grouped = category === 'bebida'
    ? Object.fromEntries(BEVERAGE_SLUGS.map(slug => [slug, filteredDishes.filter(d => d.category === slug)]))
    : null;

  return <section>
    <div className="category-tabs">
      {tabs.map(c => <button key={c.slug} className={`category-tab ${category === c.slug ? 'active' : ''}`} onClick={() => setCategory(c.slug)}>
        <CatIcon category={c.slug} /> {c.name}
      </button>)}
    </div>
    <div className="dish-search">
      <Search size={16} />
      <input placeholder={t.searchDish} value={search} onChange={e => setSearch(e.target.value)} />
    </div>
    {!grouped && <div className="dish-grid">
      {filteredDishes.map((d, idx) => <DishCard key={d.id} dish={d} index={idx} onClick={() => setModalDish(d)} onQuickAdd={d.requires_guisado ? null : () => quickAdd(d)} t={t} />)}
      {filteredDishes.length === 0 && <p className="empty-hint">{term ? t.noResultsSearch : t.empty}</p>}
    </div>}
    {grouped && BEVERAGE_SLUGS.map(slug => grouped[slug].length > 0 && <div key={slug}>
      <p className="sub-heading">{categories.find(c => c.slug === slug)?.name || slug}</p>
      <div className="dish-grid">{grouped[slug].map((d, idx) => <DishCard key={d.id} dish={d} index={idx} onClick={() => setModalDish(d)} onQuickAdd={d.requires_guisado ? null : () => quickAdd(d)} t={t} />)}</div>
    </div>)}
    {/* Rama agrupada (bebidas) sin ningun fallback de vacio: si los 3 grupos
        (agua/refresco/cafe) quedan sin resultados -sin bebidas hoy, o una
        busqueda sin coincidencias dentro de "Bebidas"- no se renderizaba
        nada en absoluto, pareciendo una pantalla congelada o rota en vez de
        "sin resultados". */}
    {grouped && BEVERAGE_SLUGS.every(slug => grouped[slug].length === 0) && <p className="empty-hint">{term ? t.noResultsSearch : t.empty}</p>}
    {modalDish && <AddItemModal t={t} dish={modalDish} guisados={guisados} onCancel={() => setModalDish(null)} onSubmit={submitItem} />}
  </section>;
}

interface DishCardProps {
  dish: Dish
  onClick: () => void
  onQuickAdd: (() => void) | null
  t: Translations
  index?: number
}

function DishCard({ dish, onClick, onQuickAdd, t, index = 0 }: DishCardProps) {
  return <button className="dish-card" style={{ animationDelay: `${Math.min(index * 25, 300)}ms` }} onClick={onClick}>
    <span className="dish-icon"><CatIcon category={dish.category} size={22} /></span>
    <h4>{dish.title}{dish.size_label ? <span className="dish-size"> &middot; {dish.size_label}</span> : null}</h4>
    <span className="dish-price">{money(dish.price)}</span>
    {onQuickAdd && <span className="dish-quick-add" title={t?.quickAdd} aria-label={t?.quickAdd} onClick={e => { e.stopPropagation(); onQuickAdd(); }}><Plus size={14} /></span>}
  </button>;
}

interface AddItemModalProps {
  t: Translations
  dish: Dish
  guisados: Guisado[]
  onCancel: () => void
  onSubmit: (payload: AddItemPayload) => void
}

function AddItemModal({ t, dish, guisados, onCancel, onSubmit }: AddItemModalProps) {
  const toast = useToast();
  const [mode, setMode] = useState('1');
  const [g1, setG1] = useState('');
  const [g2, setG2] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [note, setNote] = useState('');

  function submit() {
    if (dish.requires_guisado && !g1) { toast.error(t.chooseGuisado); return; }
    // Antes solo se validaba g1: en modo "2 guisados"/"combinado" se podia
    // dar "Agregar" sin elegir el segundo guisado (quedaba identico a modo
    // "1" pero marcado como doble/combinado sin ningun aviso), o elegir el
    // MISMO guisado en ambos selects (ej. "Mole + Mole" en el ticket de
    // cocina). Ambos casos ahora se rechazan aqui antes de enviar.
    if (dish.requires_guisado && mode !== '1' && !g2) { toast.error(t.chooseSecondGuisado); return; }
    if (dish.requires_guisado && mode !== '1' && g1 && g2 && g1 === g2) { toast.error(t.duplicateGuisado); return; }
    onSubmit({
      dish_id: dish.id, quantity, note,
      guisado_1_id: g1 ? Number(g1) : null,
      guisado_2_id: mode === '1' ? null : (g2 ? Number(g2) : null),
      combinado: mode === 'combinado',
    });
  }

  return <Portal><div className="modal"><div className="ticket-panel">
    <button className="close" onClick={onCancel}>&times;</button>
    <h2>{dish.title}</h2>
    <p className="dish-price">{money(dish.price)}</p>

    {dish.requires_guisado && <>
      <div className="guisado-mode-row">
        <button className={mode === '1' ? 'active' : ''} onClick={() => setMode('1')}>{t.guisadoSingle}</button>
        <button className={mode === '2' ? 'active' : ''} onClick={() => setMode('2')}>{t.guisadoDouble}</button>
        <button className={mode === 'combinado' ? 'active' : ''} onClick={() => setMode('combinado')}>{t.guisadoCombined}</button>
      </div>
      <div className="field">
        <label>{t.guisado1}</label>
        <select value={g1} onChange={e => setG1(e.target.value)}>
          <option value="">--</option>
          {guisados.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
      </div>
      {mode !== '1' && <div className="field">
        <label>{t.guisado2}</label>
        {/* Se excluye el guisado ya elegido en Guisado 1 (comparacion con
            String() porque el value de <option> siempre llega como string,
            mientras que g.id es numerico): sin esto se podia elegir el
            mismo guisado en ambos selects. */}
        <select value={g2} onChange={e => setG2(e.target.value)}>
          <option value="">--</option>
          {guisados.filter(g => String(g.id) !== String(g1)).map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
      </div>}
    </>}

    <div className="qty-row">
      <button onClick={() => setQuantity(n => Math.max(1, n - 1))}><Minus size={18} /></button>
      <span>{quantity}</span>
      <button onClick={() => setQuantity(n => n + 1)}><Plus size={18} /></button>
    </div>

    <div className="field">
      <label>{t.comment}</label>
      <textarea rows={2} placeholder={t.commentPlaceholder} value={note} onChange={e => setNote(e.target.value)} />
    </div>

    <button className="primary big" onClick={submit}>{t.add}</button>
  </div></div></Portal>;
}

// Los 4 pasos reales del flujo de una orden, en el mismo orden en que
// cocina y el mesero los van marcando (ver orders.py PATCH /status).
// Cada paso se considera "hecho" si su timestamp real ya existe en la
// orden; nunca se inventa o adivina un progreso que no haya ocurrido.
const ORDER_PROGRESS_STEPS: { key: string; labelKey: keyof Translations; stampKey: keyof OrderItem }[] = [
  { key: 'pedido', labelKey: 'ordered', stampKey: 'sent_at' },
  { key: 'en_preparacion', labelKey: 'preparing', stampKey: 'cooked_at' },
  { key: 'listo_para_entrega', labelKey: 'ready', stampKey: 'ready_at' },
  { key: 'entregado', labelKey: 'delivered', stampKey: 'delivered_at' },
];

function OrderStatusModal({ t, order, onClose }: { t: Translations; order: Order; onClose: () => void }) {
  return <Portal><div className="modal"><div className="ticket-panel order-status-modal">
    <button className="close" onClick={onClose}>&times;</button>
    <h2>{t.orderStatus}</h2>
    <p className="order-status-hint">{t.orderStatusHint}</p>
    <div className="order-status-items">
      {order.items.map(item => {
        // Cada platillo tiene su propio estatus/tiempos (independiente del
        // resto): un platillo agregado despues, en una orden que ya se
        // habia entregado, muestra SU PROPIO progreso desde cero, mientras
        // los platillos que ya se sirvieron siguen mostrando "entregado".
        const itemStatus = item.status || order.status;
        const isCancelled = itemStatus === 'cancelado';
        const statusForProgress = itemStatus === 'pagado' ? 'entregado' : (itemStatus === 'borrador' ? 'pedido' : itemStatus);
        const currentStepIndex = Math.max(0, ORDER_PROGRESS_STEPS.findIndex(s => s.key === statusForProgress));
        return <div className="order-status-item" key={item.id}>
          <div className="order-status-item-head">
            <span className="dish-icon"><CatIcon category={item.dish?.category} size={20} /></span>
            <div>
              <strong>{item.dish?.title}</strong>
              <span className="meta">x{item.quantity}</span>
            </div>
            <span className="status-pill" style={{ background: `var(${STATUS_VAR[itemStatus || 'pedido'] || STATUS_VAR.pedido})33`, color: `var(${STATUS_VAR[itemStatus || 'pedido'] || STATUS_VAR.pedido})` }}>{labelStatus(itemStatus || 'pedido', t)}</span>
          </div>
          {/* Un platillo cancelado no "progresa" a ningun lado -- mostrar la
              linea de tiempo normal aqui era enganoso (se veia "pedido" y a
              veces "en preparacion" marcados como si siguiera avanzando,
              cuando en realidad se quedo ahi para siempre). En su lugar se
              muestra claramente que se cancelo y por que. */}
          {isCancelled
            ? <p className="order-status-cancelled-note"><Ban size={14} /> {t.cancelled}: {item.cancel_reason || '-'}</p>
            : <div className="order-progress-line">
              {ORDER_PROGRESS_STEPS.map((step, idx) => {
                const done = idx < currentStepIndex || Boolean(item[step.stampKey]);
                const active = idx === currentStepIndex;
                return <div className={`order-progress-step ${done ? 'done' : ''} ${active ? 'active' : ''}`} key={step.key}>
                  <span className="order-progress-dot">{done ? <Check size={12} /> : null}</span>
                  <label>{t[step.labelKey] as string}</label>
                </div>;
              })}
            </div>}
        </div>;
      })}
    </div>
    <div className="order-status-footer">
      <Clock size={18} />
      <span>{t.sentAgo} {order.sent_at ? `${elapsedMinutes(order.sent_at)} min` : '-'}</span>
    </div>
  </div></div></Portal>;
}

/** Modal generico para cancelar UN platillo (usado por el mesero en su
 * ticket y por cocina en su tablero): pide un motivo obligatorio -nunca se
 * cancela en silencio- y lo manda al backend, que deja el rastro auditable
 * (quien, cuando, por que). */
export function CancelItemModal({ t, item, onConfirm, onClose }: { t: Translations; item: OrderItem; onConfirm: (reason: string) => Promise<void>; onClose: () => void }) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function confirm() {
    const trimmed = reason.trim();
    if (!trimmed) { setError(t.cancelItemReasonRequired); return; }
    setBusy(true);
    try { await onConfirm(trimmed); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <Portal><div className="modal"><div className="ticket-panel">
    <button className="close" onClick={onClose}>&times;</button>
    <h2>{t.cancelItemTitle}</h2>
    <p className="order-status-hint">{item.quantity > 1 ? `${item.quantity} x ` : ''}{item.dish?.title}</p>
    <div className="field">
      <label>{t.cancelItemPrompt}</label>
      <textarea rows={3} placeholder={t.cancelItemPlaceholder} value={reason} onChange={e => { setReason(e.target.value); setError(''); }} />
    </div>
    {error && <p style={{ color: 'var(--danger)', fontSize: 13, margin: '0 0 10px' }}>{error}</p>}
    <button className="primary big" disabled={busy} onClick={confirm}>{t.confirmCancelItem}</button>
  </div></div></Portal>;
}

/** Pide un motivo obligatorio antes de corregir (deshacer) un cobro ya
 * hecho -- mismo patron que CancelItemModal arriba, para que corregir un
 * pago tenga la misma exigencia de dejar rastro que cancelar un platillo. */
export function CorrectPaymentModal({ t, onConfirm, onClose }: { t: Translations; onConfirm: (reason: string) => Promise<void>; onClose: () => void }) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function confirm() {
    const trimmed = reason.trim();
    if (!trimmed) { setError(t.correctPaymentReasonRequired); return; }
    setBusy(true);
    try { await onConfirm(trimmed); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <Portal><div className="modal"><div className="ticket-panel">
    <button className="close" onClick={onClose}>&times;</button>
    <h2>{t.correctPayment}</h2>
    <div className="field">
      <label>{t.correctPaymentReasonPrompt}</label>
      <textarea rows={3} placeholder={t.correctPaymentReasonPlaceholder} value={reason} onChange={e => { setReason(e.target.value); setError(''); }} />
    </div>
    {error && <p style={{ color: 'var(--danger)', fontSize: 13, margin: '0 0 10px' }}>{error}</p>}
    <button className="primary big" disabled={busy} onClick={confirm}>{t.confirmCorrection}</button>
  </div></div></Portal>;
}

function TicketPanel({ t, order, allOrders, onChanged }: { t: Translations; order: Order; allOrders: Order[] | null; onChanged: () => void }) {
  const toast = useToast();
  const [showStatus, setShowStatus] = useState(false);
  // `busy` deshabilita los botones de accion mientras una peticion sigue en
  // vuelo -- sin esto, dos clics rapidos en "Enviar a cocina" o "Marcar
  // entregado" (facil con dedos en una tablet) disparaban dos peticiones
  // identicas, la segunda de las cuales normalmente fallaba con un error
  // confuso (o, peor, alcanzaba a aplicarse dos veces si llegaban en el
  // orden equivocado).
  const [busy, setBusy] = useState(false);
  async function removeItem(itemId: number) {
    try { await api.removeItem(order.id, itemId); onChanged(); } catch (e) { toast.error((e as Error).message); }
  }
  async function send() {
    if (busy) return;
    setBusy(true);
    try { await api.sendToKitchen(order.id); onChanged(); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  }
  async function markDelivered() {
    if (busy) return;
    setBusy(true);
    try { await api.updateOrderStatus(order.id, 'entregado'); onChanged(); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  }

  // Ordenes de la mesa que todavia estan en borrador con al menos un
  // platillo: "Enviar todo a cocina" las manda todas juntas, en vez de que
  // el mesero tenga que ir comensal por comensal presionando "Enviar a
  // cocina" en cada pestana.
  const sendableOrders = (allOrders || []).filter(o => o.status === 'borrador' && o.items.length > 0);

  async function sendAll() {
    if (busy) return;
    setBusy(true);
    try {
      // allSettled (no all): si UN envio falla, los demas que si tuvieron
      // exito no deben perderse -- antes, Promise.all rechazaba entero en
      // cuanto fallaba cualquiera, onChanged() nunca se llamaba, y el
      // mesero veia TODAS las ordenes seguir en 'borrador' (con "Enviar
      // todo" aun visible) aunque varias ya se hubieran enviado de verdad,
      // arriesgando un reenvio duplicado del comensal que si tuvo exito.
      const results = await Promise.allSettled(sendableOrders.map(o => api.sendToKitchen(o.id)));
      onChanged();
      const failed = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
      if (failed.length) toast.error(failed[0].reason?.message || t.sendAllPartialError);
    } finally { setBusy(false); }
  }

  return <div className="ticket-side">
    {allOrders && allOrders.length > 0 && <div className="table-summary">
      <h4>{t.tableSummary}</h4>
      {allOrders.map(o => <div key={o.id} className={`table-summary-row ${o.id === order.id ? 'active' : ''}`}>
        <span className="status-dot" style={{ background: `var(${STATUS_VAR[o.status]})` }} />
        <span className="table-summary-name">{t.diner} {o.diner_index}</span>
        <span className="table-summary-count">{o.items.length} {o.items.length === 1 ? t.itemCountLabel : t.itemsCountLabel}</span>
        <span className="table-summary-amount">{money(o.subtotal)}</span>
      </div>)}
      {/* Total conjunto de la mesa: suma de los subtotales de TODOS los
          comensales, no solo el que se esta viendo ahorita en el ticket
          principal. */}
      <div className="table-summary-row table-summary-grand-total">
        <span className="table-summary-name">{t.total}</span>
        <span className="table-summary-amount">{money(allOrders.reduce((sum, o) => sum + Number(o.subtotal || 0), 0))}</span>
      </div>
      {allOrders.length > 1 && sendableOrders.length > 0 && <button className="icon-btn send-all-btn" disabled={busy} onClick={sendAll}><ClipboardList size={14} /> {t.sendAllToKitchen}</button>}
    </div>}
    <h3>{t.ticket} <span className="status-pill" style={{ background: `var(${STATUS_VAR[order.status]})33`, color: `var(${STATUS_VAR[order.status]})` }}>{labelStatus(order.status, t)}</span></h3>
    {order.items.length > 0 && order.status !== 'borrador' && <button className="icon-btn order-status-btn" onClick={() => setShowStatus(true)}><ClipboardList size={16} /> {t.orderStatus}</button>}
    {showStatus && <OrderStatusModal t={t} order={order} onClose={() => setShowStatus(false)} />}
    {order.items.length === 0 && <p className="empty-hint">{t.empty}</p>}
    {order.items.map(item => <div key={item.id} className={`ticket-item${item.status === 'cancelado' ? ' ticket-item-cancelled' : ''}`}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {/* Punto de color con el estatus PROPIO del platillo: si la orden
              ya se habia entregado y se agrego uno nuevo, este punto deja
              claro cual platillo es el que todavia va en camino. */}
          <span className="status-dot" style={{ background: `var(${STATUS_VAR[item.status || 'borrador'] || STATUS_VAR.borrador})` }} />
          <strong>{item.quantity} x {item.dish!.title}{item.dish!.size_label ? ` (${item.dish!.size_label})` : ''}</strong>
        </div>
        {(item.guisado_1 || item.guisado_2) && <div className="meta">
          {item.guisado_1?.name}{item.combinado && item.guisado_2 ? ' + ' : (item.guisado_2 ? ', ' : '')}{item.guisado_2?.name}
          {item.combinado ? ` (${t.guisadoCombined})` : ''}
        </div>}
        {item.note && <div className="meta">&quot;{item.note}&quot;</div>}
        {item.status === 'cancelado' && <div className="meta cancelled-reason">{t.cancelled}: {item.cancel_reason}</div>}
      </div>
      {/* Cancelar un platillo ya enviado es exclusivo del administrador
          (ver AdminOrdersPanel) -- el mesero solo puede quitar platillos
          mientras la orden completa sigue en borrador (sin tocar cocina). */}
      {/* Ojo: order.status puede ser 'borrador' con platillos VIEJOS
          cancelados mezclados en la lista (ronda nueva tras cancelar todo
          -- ver _recompute_order_status). Por eso se revisa el estatus del
          PLATILLO, no solo el de la orden: quitar (borrar sin dejar
          rastro) solo debe poder hacerse al platillo que en verdad sigue
          en borrador, nunca a uno ya cancelado (eso ya quedo registrado). */}
      {item.status === 'borrador' && <button onClick={() => removeItem(item.id)}><Trash2 size={16} /></button>}
    </div>)}
    <div className="total">{t.subtotal}: {money(order.subtotal)}</div>
    {order.status === 'borrador' && order.items.length > 0 && <button className="primary big" disabled={busy} onClick={send}>{t.sendToKitchen}</button>}
    {order.status === 'listo_para_entrega' && <button className="primary big" disabled={busy} onClick={markDelivered}>{t.markDelivered}</button>}
  </div>;
}
