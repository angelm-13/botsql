import { useEffect, useState } from 'react';
import { NavLink, Navigate, Routes, Route, useNavigate } from 'react-router-dom';
import { CreditCard } from 'lucide-react';
import { api } from '../../services/api';
import { RefreshButton } from '../../components/shared/RefreshButton';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { staffRoleLabel } from '../../utils/format';
import { KpisPanel } from './Dashboard';
import { PendingPayments } from './PendingPayments';
import { ReportsPanel } from './ReportsPanel';
import { RegisterPanel } from './RegisterPanel';
import { DishesManager } from './DishesManager';
import { InventoryManager } from './InventoryManager';
import { UsersManager } from './UsersManager';
import { AdminOrdersPanel } from './AdminOrdersPanel';
import { InvoiceHistoryPanel } from './Invoicing';
import { BusinessSettingsPanel } from './BusinessSettingsPanel';
import type { Translations } from '../../i18n/translations';
import type { AuditLog, Role, User } from '../../types/api';

export function AdminApp({ t, role, user }: { t: Translations; role: Role | undefined; user: User | null }) {
  const navigate = useNavigate();
  const isAdmin = role === 'admin' || role === 'superadmin';
  // Modulo oculto: solo el rol superadmin (soporte/auditoria del
  // desarrollador de la plantilla) ve esta pestana. Ni admin ni cajero la
  // ven nunca, sin importar que compartan esta misma pantalla.
  const isSuperAdmin = role === 'superadmin';
  const navClass = ({ isActive }: { isActive: boolean }) => isActive ? 'active' : '';
  return <main className="page">
    <div className="section-title"><CreditCard /><h1>{isAdmin ? t.roleAdmin : t.cashier}</h1></div>
    {/* Rutas absolutas (/admin/kpis, no "kpis") a proposito: AdminApp se
        monta bajo un splat ("/admin/*" en main.jsx) y renderiza su propio
        <Routes> descendiente -- un `to` relativo aqui se resuelve contra la
        URL actual, no contra la base "/admin", lo que podia encadenar
        segmentos sin fin al navegar entre pestanas (mismo bug ya
        encontrado y corregido en WaiterApp). */}
    <div className="admin-tabs">
      <NavLink to="/admin/kpis" className={navClass}>{t.kpis}</NavLink>
      <NavLink to="/admin/pagos" className={navClass}>{t.pendingPayments}</NavLink>
      <NavLink to="/admin/reportes" className={navClass}>{t.reports}</NavLink>
      <NavLink to="/admin/caja" className={navClass}>{t.register}</NavLink>
      {isAdmin && <NavLink to="/admin/menu" className={navClass}>{t.menuManagement}</NavLink>}
      <NavLink to="/admin/inventario" className={navClass}>{t.inventoryTab}</NavLink>
      {isAdmin && <NavLink to="/admin/usuarios" className={navClass}>{t.staffManagement}</NavLink>}
      {/* Cancelar platillos es exclusivo del administrador: por eso esta
          pestana (y el endpoint que consume) solo aparece para isAdmin,
          nunca para el rol cajero aunque comparta esta misma pantalla. */}
      {isAdmin && <NavLink to="/admin/cancelaciones" className={navClass}>{t.adminOrdersTab}</NavLink>}
      <NavLink to="/admin/facturas" className={navClass}>{t.invoicingTab}</NavLink>
      {/* La configuracion fiscal (RFC del restaurante, proveedor de
          timbrado) es exclusiva del administrador; cajero solo ve el
          historial de facturas ya emitidas en la pestana "Facturas". */}
      {isAdmin && <NavLink to="/admin/negocio" className={navClass}>{t.myBusiness}</NavLink>}
      {isSuperAdmin && <NavLink to="/admin/auditoria" className={navClass}>{t.auditLog}</NavLink>}
    </div>
    <Routes>
      <Route index element={<Navigate to="/admin/kpis" replace />} />
      <Route path="kpis" element={<KpisPanel t={t} />} />
      <Route path="pagos" element={<PendingPayments t={t} user={user} onGoToRegister={() => navigate('/admin/caja')} />} />
      <Route path="reportes" element={<ReportsPanel t={t} />} />
      <Route path="caja" element={<RegisterPanel t={t} />} />
      {isAdmin && <Route path="menu" element={<DishesManager t={t} />} />}
      <Route path="inventario" element={<InventoryManager t={t} />} />
      {isAdmin && <Route path="usuarios" element={<UsersManager t={t} />} />}
      {isAdmin && <Route path="cancelaciones" element={<AdminOrdersPanel t={t} />} />}
      <Route path="facturas" element={<InvoiceHistoryPanel t={t} />} />
      {isAdmin && <Route path="negocio" element={<BusinessSettingsPanel t={t} />} />}
      {isSuperAdmin && <Route path="auditoria" element={<AuditLogPanel t={t} />} />}
      <Route path="*" element={<Navigate to="/admin/kpis" replace />} />
    </Routes>
  </main>;
}

/** Bitacora de cambios administrativos (ver AuditLog en el backend):
 * platillos/categorias/guisados, personal, apertura/cierre de caja y
 * correcciones de cobro. No incluye el flujo operativo normal (tomar
 * pedidos, cobrar). Modulo oculto: solo se monta cuando role==='superadmin'
 * (ver AdminApp), y el endpoint que consume tambien lo exige del lado del
 * backend (roles_required('superadmin')). */
function AuditLogPanel({ t }: { t: Translations }) {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try { const data = await api.auditLog('?per_page=100'); setItems(data.items || []); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  return <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
      <h3 style={{ margin: 0 }}>{t.auditLog}</h3>
      <RefreshButton t={t} onClick={load} />
    </div>
    {loading && <LoadingPanel />}
    {!loading && items.length === 0 && <p className="empty-hint">{t.noData}</p>}
    {!loading && items.length > 0 && <table className="report-table">
      <thead><tr><th>{t.auditWhen}</th><th>{t.auditActor}</th><th>{t.auditAction}</th><th>{t.auditDescription}</th></tr></thead>
      <tbody>{items.map(a => <tr key={a.id}>
        <td>{new Date(a.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</td>
        <td>{a.actor_username}<br /><span className="meta">{staffRoleLabel(a.actor_role, t)}</span></td>
        <td>{a.action}</td>
        <td>{a.description}</td>
      </tr>)}</tbody>
    </table>}
  </div>;
}
