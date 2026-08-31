import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeftRight, ClipboardList, Package, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { useConfirmDialog } from '../../contexts/ConfirmContext';
import { EmptyState } from '../../components/shared/EmptyState';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { Portal } from '../../components/shared/Portal';
import { RefreshButton } from '../../components/shared/RefreshButton';
import { money } from '../../utils/format';
import type { Translations } from '../../i18n/translations';
import type { InventoryItem, InventoryMovement, InventoryMovementType, InventorySummary } from '../../types/api';

const INVENTORY_MOVEMENT_TYPES: InventoryMovementType[] = ['entrada', 'salida', 'merma', 'ajuste'];

interface InventoryForm {
  description: string
  unit: string
  quantity: string
  cost_per_unit: string
  min_stock: string
}

/**
 * Panel de inventario (cajero/admin/superadmin): catalogo de insumos +
 * bitacora de movimientos. Dos sub-vistas con su propia pestana interna
 * (mismo patron que las pestanas de AdminApp): "Insumos" para ver/editar
 * el catalogo y disparar un movimiento nuevo, "Historial" para auditar
 * todos los movimientos ya registrados (ver InventoryHistoryPanel).
 */
export function InventoryManager({ t }: { t: Translations }) {
  const toast = useToast();
  const confirmDialog = useConfirmDialog();
  const [view, setView] = useState<'items' | 'historial'>('items');
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [search, setSearch] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [form, setForm] = useState<InventoryForm>({ description: '', unit: '', quantity: '', cost_per_unit: '', min_stock: '' });
  const [movementItem, setMovementItem] = useState<InventoryItem | null>(null);

  async function load() {
    try {
      const inactiveParam = showInactive ? '&include_inactive=1' : '';
      const searchParam = search.trim() ? `&search=${encodeURIComponent(search.trim())}` : '';
      const [itemsData, summaryData] = await Promise.all([
        api.inventoryItems(`?per_page=200${inactiveParam}${searchParam}`),
        api.inventorySummary(),
      ]);
      setItems(itemsData.items || []);
      setSummary(summaryData);
    } catch (e) { toast.error((e as Error).message); }
  }
  useEffect(() => { load(); }, [showInactive, search]); // eslint-disable-line react-hooks/exhaustive-deps

  async function addItem() {
    if (!form.description.trim()) { toast.error(t.missingInventoryDescription); return; }
    if (!form.unit.trim()) { toast.error(t.missingInventoryUnit); return; }
    try {
      await api.createInventoryItem({
        description: form.description.trim(), unit: form.unit.trim(),
        quantity: Number(form.quantity || 0), cost_per_unit: Number(form.cost_per_unit || 0),
        min_stock: Number(form.min_stock || 0),
      });
      setForm({ description: '', unit: '', quantity: '', cost_per_unit: '', min_stock: '' });
      load();
    } catch (e) { toast.error((e as Error).message); }
  }

  async function toggleActive(item: InventoryItem) {
    try {
      if (item.is_active) {
        if (!await confirmDialog(t.confirmDeactivateInventoryItem)) return;
        await api.deleteInventoryItem(item.id);
      } else {
        await api.updateInventoryItem(item.id, { is_active: true });
      }
      load();
    } catch (e) { toast.error((e as Error).message); }
  }

  return <section>
    <div className="admin-tabs" style={{ marginBottom: 16 }}>
      <button className={view === 'items' ? 'active' : ''} onClick={() => setView('items')}>{t.inventoryItemsTab}</button>
      <button className={view === 'historial' ? 'active' : ''} onClick={() => setView('historial')}>{t.inventoryHistoryTab}</button>
    </div>

    {view === 'items' && <>
      {summary && <section className="kpi-grid" style={{ marginBottom: 18 }}>
        <div className="kpi kpi-primary"><div className="kpi-label">{t.inventoryTotalValue}</div><div className="kpi-value">{money(summary.total_value)}</div></div>
        <div className="kpi kpi-secondary"><div className="kpi-label">{t.inventoryLowStock}</div><div className="kpi-value">{summary.low_stock_items.length}</div></div>
        <div className="kpi kpi-tertiary"><div className="kpi-label">{t.inventoryMermasMonth}</div><div className="kpi-value">{money(summary.mermas_this_month.cost)}</div></div>
      </section>}

      <div className="table-grid-header">
        <input placeholder={t.searchInventoryItem} value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 260 }} />
        <label className="pay-checkbox"><input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} /> {t.showInactive}</label>
        <RefreshButton t={t} onClick={load} />
      </div>

      {items.length === 0 ? <EmptyState icon={Package} title={t.noInventoryItems} /> : <div style={{ overflowX: 'auto' }}><table className="report-table">
        <thead><tr>
          <th>{t.inventoryDescription}</th><th>{t.inventoryUnit}</th><th>{t.inventoryQuantity}</th>
          <th>{t.inventoryCostPerUnit}</th><th>{t.inventoryTotalValueCol}</th><th>{t.status}</th><th></th>
        </tr></thead>
        <tbody>{items.map(item => <tr key={item.id} style={!item.is_active ? { opacity: 0.55 } : undefined}>
          <td>{item.description}</td>
          <td>{item.unit}</td>
          <td style={item.is_low_stock ? { color: 'var(--danger)', fontWeight: 600 } : undefined}>
            {item.quantity}{item.is_low_stock && <AlertTriangle size={14} style={{ verticalAlign: 'middle', marginLeft: 4 }} />}
          </td>
          <td>{money(item.cost_per_unit)}</td>
          <td>{money(item.total_value)}</td>
          <td>{item.is_active ? t.active : t.inactive}</td>
          <td style={{ display: 'flex', gap: 6, whiteSpace: 'nowrap' }}>
            {item.is_active && <button className="icon-btn" onClick={() => setMovementItem(item)} title={t.registerMovement}><ArrowLeftRight size={14} /></button>}
            <button className="icon-btn" onClick={() => toggleActive(item)} title={item.is_active ? t.deactivate : t.reactivate}>
              {item.is_active ? <Trash2 size={14} /> : <RefreshCw size={14} />}
            </button>
          </td>
        </tr>)}</tbody>
      </table></div>}

      <h3 style={{ marginTop: 24 }}>{t.addInventoryItem}</h3>
      <div className="inline-form-row">
        <input placeholder={t.inventoryDescription} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
        <input placeholder={t.inventoryUnit} value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))} />
        <input type="number" min="0" step="0.001" placeholder={t.inventoryQuantity} value={form.quantity} onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} />
        <input type="number" min="0" step="0.01" placeholder={t.inventoryCostPerUnit} value={form.cost_per_unit} onChange={e => setForm(f => ({ ...f, cost_per_unit: e.target.value }))} />
        <input type="number" min="0" step="0.001" placeholder={t.inventoryMinStock} value={form.min_stock} onChange={e => setForm(f => ({ ...f, min_stock: e.target.value }))} />
        <button className="primary" onClick={addItem}><Plus size={16} /> {t.addInventoryItem}</button>
      </div>
    </>}

    {view === 'historial' && <InventoryHistoryPanel t={t} />}

    {movementItem && <InventoryMovementModal t={t} item={movementItem} onClose={() => setMovementItem(null)} onSaved={() => { setMovementItem(null); load(); }} />}
  </section>;
}

/** Modal para registrar UN movimiento (entrada/salida/merma/ajuste) sobre
 * un insumo especifico. "ajuste" pide la cantidad real contada (no un
 * delta) -- el backend calcula la diferencia solo, que es como de verdad
 * piensa alguien haciendo un conteo fisico ("tengo 8, el sistema dice 10,
 * pon 8"), no en terminos de "resta 2". */
function InventoryMovementModal({ t, item, onClose, onSaved }: { t: Translations; item: InventoryItem; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const [type, setType] = useState<InventoryMovementType>('entrada');
  const [quantity, setQuantity] = useState('');
  const [newQuantity, setNewQuantity] = useState(String(item.quantity));
  const [reason, setReason] = useState('');
  const [unitCost, setUnitCost] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (saving) return;
    if (type === 'merma' && !reason.trim()) { toast.error(t.reasonRequiredHint); return; }
    const payload: Record<string, unknown> = { inventory_item_id: item.id, type };
    if (reason.trim()) payload.reason = reason.trim();
    if (unitCost !== '') payload.unit_cost = Number(unitCost);
    if (type === 'ajuste') {
      if (newQuantity === '' || Number(newQuantity) < 0) { toast.error(t.invalidQuantity); return; }
      payload.new_quantity = Number(newQuantity);
    } else {
      if (!quantity || Number(quantity) <= 0) { toast.error(t.invalidQuantity); return; }
      payload.quantity = Number(quantity);
    }
    setSaving(true);
    try {
      await api.createInventoryMovement(payload);
      toast.success(t.movementSaved);
      onSaved();
    } catch (e) { toast.error((e as Error).message); } finally { setSaving(false); }
  }

  return <Portal><div className="modal"><div className="ticket-panel">
    <button className="close" onClick={onClose}>&times;</button>
    <h2>{item.description}</h2>
    <p className="dish-price">{t.inventoryCurrentStock}: {item.quantity} {item.unit}</p>
    <div className="guisado-mode-row">
      {INVENTORY_MOVEMENT_TYPES.map(mt => <button key={mt} className={type === mt ? 'active' : ''} onClick={() => setType(mt)}>{t[`movementType_${mt}` as keyof Translations]}</button>)}
    </div>
    {type !== 'ajuste' ? <div className="field">
      <label>{t.inventoryQuantity} ({item.unit})</label>
      <input type="number" min="0" step="0.001" value={quantity} onChange={e => setQuantity(e.target.value)} />
    </div> : <div className="field">
      <label>{t.newCountedQuantity} ({item.unit})</label>
      <input type="number" min="0" step="0.001" value={newQuantity} onChange={e => setNewQuantity(e.target.value)} />
    </div>}
    <div className="field">
      <label>{t.unitCostOptional}</label>
      <input type="number" min="0" step="0.01" placeholder={money(item.cost_per_unit)} value={unitCost} onChange={e => setUnitCost(e.target.value)} />
    </div>
    <div className="field">
      <label>{type === 'merma' ? t.reasonRequiredLabel : t.reasonOptionalLabel}</label>
      <textarea rows={2} value={reason} onChange={e => setReason(e.target.value)} />
    </div>
    <button className="primary big" disabled={saving} onClick={submit}>{saving ? t.processing : t.confirmMovement}</button>
  </div></div></Portal>;
}

/** Historial global de movimientos de inventario, mas reciente primero,
 * filtrable por tipo -- para poder ver de un vistazo, por ejemplo, todas
 * las mermas del mes y su costo total (ver tambien el KPI en
 * InventoryManager, que ya resume esto, pero aqui se ve el detalle linea
 * por linea: quien, cuando, cuanto y por que). */
function InventoryHistoryPanel({ t }: { t: Translations }) {
  const toast = useToast();
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [typeFilter, setTypeFilter] = useState<InventoryMovementType | ''>('');
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const typeParam = typeFilter ? `&type=${typeFilter}` : '';
      const data = await api.inventoryMovements(`?per_page=100${typeParam}`);
      setMovements(data.items || []);
    } catch (e) { toast.error((e as Error).message); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [typeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  return <div>
    <div className="table-grid-header">
      <select value={typeFilter} onChange={e => setTypeFilter(e.target.value as InventoryMovementType | '')}>
        <option value="">{t.allMovementTypes}</option>
        {INVENTORY_MOVEMENT_TYPES.map(mt => <option key={mt} value={mt}>{t[`movementType_${mt}` as keyof Translations]}</option>)}
      </select>
      <RefreshButton t={t} onClick={load} />
    </div>
    {loading ? <LoadingPanel /> : movements.length === 0 ? <EmptyState icon={ClipboardList} title={t.noMovements} /> : <div style={{ overflowX: 'auto' }}><table className="report-table">
      <thead><tr>
        <th>{t.auditWhen}</th><th>{t.inventoryDescription}</th><th>{t.movementTypeCol}</th>
        <th>{t.quantity}</th><th>{t.inventoryCostCol}</th><th>{t.auditActor}</th><th>{t.reasonCol}</th>
      </tr></thead>
      <tbody>{movements.map(m => <tr key={m.id}>
        <td>{new Date(m.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</td>
        <td>{m.inventory_item_description}</td>
        <td>{t[`movementType_${m.type}` as keyof Translations]}</td>
        <td style={{ color: m.quantity_delta < 0 ? 'var(--danger)' : 'var(--green)' }}>{m.quantity_delta > 0 ? '+' : ''}{m.quantity_delta} {m.inventory_item_unit}</td>
        <td>{money(m.total_cost)}</td>
        <td>{m.created_by_username || '-'}</td>
        <td>{m.reason || '-'}</td>
      </tr>)}</tbody>
    </table></div>}
  </div>;
}
