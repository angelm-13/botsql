/* eslint-disable react/prop-types */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Shell from "./layouts/Shell";
import Dashboard from "./pages/Dashboard";
import DashboardPreviewPage from "./pages/DashboardPreviewPage.jsx";
import ErrorBoundaryPreview from "./components/kpi-widgets/ErrorBoundaryPreview.jsx";
import MfaSetupPage from "./pages/MfaSetupPage";
import ChangePasswordPage from "./pages/ChangePasswordPage.jsx";
import RolePermissionManagerPage from "./pages/RolePermissionManagerPage.jsx";
import KpiPermissionManagerPage from "./pages/KpiPermissionManagerPage.jsx";
import TeamManagerPage from "./pages/TeamManagerPage.jsx";
import QuotationPage from "./pages/QuotationPage.jsx";
import AuthorizationTrackingPage from "./pages/AuthorizationTrackingPage.jsx";
import ClientPortalPage from "./pages/ClientPortalPage.jsx";
import BankPage from "./pages/BankPage.jsx";
import BankAccountPage from "./pages/BankAccountPage.jsx";
import BrandPage from "./pages/BrandPage.jsx";
import CustomerSupplierPage from "./pages/CustomerSupplierPage.jsx";
import DepartmentPage from "./pages/DepartmentPage.jsx";
import EntityPermissionPage from "./pages/EntityPermissionPage.jsx";
import EventLogPage from "./pages/EventLogPage.jsx";
import FacturamaConfigPage from "./pages/FacturamaConfigPage.jsx";
import FieldPage from "./pages/FieldPage.jsx";
import FiscalAccountPage from "./pages/FiscalAccountPage.jsx";
import IncidentPage from "./pages/IncidentPage.jsx";
import IncidentDetailPage from "./pages/IncidentDetailPage.jsx";
import IncidentTypePage from "./pages/IncidentTypePage.jsx";
import AssetTrackingPage from "./pages/AssetTrackingPage.jsx";
import InventoryTracePage from "./pages/InventoryTracePage.jsx";
import PosTillPage from "./pages/PosTillPage.jsx";
import PosCatalogPage from "./pages/pos/PosCatalogPage.jsx";
import PosPromotionsPage from "./pages/pos/PosPromotionsPage.jsx";
import PosShiftPage from "./pages/pos/PosShiftPage.jsx";
import PosWarehousePage from "./pages/pos/PosWarehousePage.jsx";
import PosReportsPage from "./pages/pos/PosReportsPage.jsx";
import InventoryPage from "./pages/InventoryPage.jsx";
import InventoryStatusPage from "./pages/InventoryStatusPage.jsx";
import InvoicePage from "./pages/InvoicePage.jsx";
import ManualInvoicePage from "./pages/ManualInvoicePage.jsx";
import LevelPage from "./pages/LevelPage.jsx";
import LocationPage from "./pages/LocationPage.jsx";
import LocationTypePage from "./pages/LocationTypePage.jsx";
import MaterialPage from "./pages/MaterialPage.jsx";
import NmFieldPermissionPage from "./pages/NmFieldPermissionPage.jsx";
import NmIncidentProductPage from "./pages/NmIncidentProductPage.jsx";
import NmSurveyUserPage from "./pages/NmSurveyUserPage.jsx";
import NmTemplateTaskPage from "./pages/NmTemplateTaskPage.jsx";
import PayrollConceptPage from "./pages/PayrollConceptPage.jsx";
import PayrollDetailPage from "./pages/PayrollDetailPage.jsx";
import PayrollMovementPage from "./pages/PayrollMovementPage.jsx";
import PayrollPeriodPage from "./pages/PayrollPeriodPage.jsx";
import PermissionPage from "./pages/PermissionPage.jsx";
import ProductPage from "./pages/ProductPage.jsx";
import WarehouseVoucherPage from "./pages/WarehouseVoucherPage.jsx";
import PorComprarPage from "./pages/PorComprarPage.jsx";
import OrdenesDeCompraPage from "./pages/OrdenesDeCompraPage.jsx";
import ActivityLogPage from "./pages/ActivityLogPage.jsx";
import ProductFamilyPage from "./pages/ProductFamilyPage.jsx";
import ProductSaleConfigPage from "./pages/ProductSaleConfigPage.jsx";
import ProjectManagementPage from "./pages/ProjectManagementPage.jsx";
import PublicApiKeyPage from "./pages/PublicApiKeyPage.jsx";
import ServicePage from "./pages/ServicePage.jsx";
import StatusPage from "./pages/StatusPage.jsx";
import SubdepartmentPage from "./pages/SubdepartmentPage.jsx";
import SurveyMultipleAnswerPage from "./pages/SurveyMultipleAnswerPage.jsx";
import SurveyQuestionPage from "./pages/SurveyQuestionPage.jsx";
import TaskPage from "./pages/TaskPage.jsx";
import TaskNotePage from "./pages/TaskNotePage.jsx";
import TaskTypePage from "./pages/TaskTypePage.jsx";
import TemplatePage from "./pages/TemplatePage.jsx";
import ThemePage from "./pages/ThemePage.jsx";
import TicketPage from "./pages/TicketPage.jsx";
import UnitPage from "./pages/UnitPage.jsx";
import UserPage from "./pages/UserPage.jsx";
import UserMfaPage from "./pages/UserMfaPage.jsx";
import KronosPage from "./pages/KronosPage.jsx";
import KronosDevicePage from "./pages/KronosDevicePage.jsx";
import LogisticsAddressesPage from "./pages/logistics/LogisticsAddressesPage.jsx";
import LogisticsBranchesPage from "./pages/logistics/LogisticsBranchesPage.jsx";
import LogisticsContractsPage from "./pages/logistics/LogisticsContractsPage.jsx";
import LogisticsInventoryPage from "./pages/logistics/LogisticsInventoryPage.jsx";
import LogisticsEvidencesPage from "./pages/logistics/LogisticsEvidencesPage.jsx";
import LogisticsFilesPage from "./pages/logistics/LogisticsFilesPage.jsx";
import LogisticsIncidentsPage from "./pages/logistics/LogisticsIncidentsPage.jsx";
import LogisticsLocationsPage from "./pages/logistics/LogisticsLocationsPage.jsx";
import LogisticsMaintenancePage from "./pages/logistics/LogisticsMaintenancePage.jsx";
import LogisticsOperatorsPage from "./pages/logistics/LogisticsOperatorsPage.jsx";
import LogisticsQuotationsPage from "./pages/logistics/LogisticsQuotationsPage.jsx";
import LogisticsRacksPage from "./pages/logistics/LogisticsRacksPage.jsx";
import LogisticsRatesPage from "./pages/logistics/LogisticsRatesPage.jsx";
import LogisticsReceivablesPage from "./pages/logistics/LogisticsReceivablesPage.jsx";
import LogisticsServiceRequestsPage from "./pages/logistics/LogisticsServiceRequestsPage.jsx";
import LogisticsShipmentsPage from "./pages/logistics/LogisticsShipmentsPage.jsx";
import LogisticsTrailersPage from "./pages/logistics/LogisticsTrailersPage.jsx";
import LogisticsTripsPage from "./pages/logistics/LogisticsTripsPage.jsx";
import LogisticsUnitsPage from "./pages/logistics/LogisticsUnitsPage.jsx";
import LogisticsWarehousesPage from "./pages/logistics/LogisticsWarehousesPage.jsx";
import RestaurantWaiterPage from "./pages/restaurant/RestaurantWaiterPage.jsx";
import RestaurantKitchenPage from "./pages/restaurant/RestaurantKitchenPage.jsx";
import RestaurantCashierPage from "./pages/restaurant/RestaurantCashierPage.jsx";
import RestaurantAdminPage from "./pages/restaurant/RestaurantAdminPage.jsx";
import AppointmentsPage from "./pages/AppointmentsPage.jsx";
import DocumentManagementPage from "./pages/DocumentManagementPage.jsx";
import LaboratoryManagementPage from "./pages/LaboratoryManagementPage.jsx";
import PublicCalendarPage from "./pages/PublicCalendarPage.jsx";
import Kanban from './components/Kanban.jsx';
import LoginPage from "./auth/LoginPage";
import ProtectedRoute from "./auth/ProtectedRoute";
import { useEffect, useState } from "react";
import { getAllEntityPermission } from "./api";
import "./styles/app.css";
import "./styles/foco.css";
import "./styles/sat-key.css";

function isBootstrapUser() {
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const bootstrapUsername = import.meta.env.VITE_BOOTSTRAP_ADMIN_USERNAME || "admin1";
  return Boolean(currentUser?.username === bootstrapUsername && (currentUser?.is_bootstrap_admin || currentUser?.is_superuser || currentUser?.username === bootstrapUsername));
}

function TechnicalRoute({ children }) {
  return isBootstrapUser() ? children : <Navigate to="/" replace />;
}

// Referencia estable para que <RoleAccessRoute> no la reciba como un arreglo
// literal nuevo en cada render de <App/> -eso reiniciaria su efecto sin fin,
// porque `[entityName]` en el useEffect compara por referencia.
const VOUCHER_ENTITY_NAMES = ["warehouse_voucher", "warehouse_prevoucher"];

function roleHasEntityAccess(rows, entityName, currentUser) {
  if (isBootstrapUser()) return true;
  const roleId = Number(currentUser?.id_permission || 0);
  if (!roleId || !entityName) return false;
  // `entityName` puede traer mas de una clave -por ejemplo `warehouse_voucher`
  // y `warehouse_prevoucher`, que dan acceso a la misma pantalla pero nunca
  // las tiene el mismo rol- y basta con que el actor tenga UNA de ellas.
  const nombres = Array.isArray(entityName) ? entityName : [entityName];
  return rows.some((row) => Number(row.id_permission) === roleId && nombres.includes(String(row.entity_name || "")) && (
    Number(row.scope_create || 0) > 0 || Number(row.scope_read || 0) > 0 ||
    Number(row.scope_update || 0) > 0 || Number(row.scope_delete || 0) > 0
  ));
}

function RoleAccessRoute({ entityName, children }) {
  const [allowed, setAllowed] = useState(null);

  useEffect(() => {
    let mounted = true;
    const currentUser = JSON.parse(localStorage.getItem("user") || "null");
    if (isBootstrapUser()) { setAllowed(true); return () => { mounted = false; }; }
    const roleId = Number(currentUser?.id_permission || 0);
    if (!roleId) { setAllowed(false); return () => { mounted = false; }; }
    getAllEntityPermission({ per_page: 5000 })
      .then((payload) => {
        const rows = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : [];
        if (mounted) setAllowed(roleHasEntityAccess(rows, entityName, currentUser));
      })
      .catch(() => { if (mounted) setAllowed(false); });
    return () => { mounted = false; };
  }, [entityName]);

  if (allowed === null) return null;
  return allowed ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/portal-cliente" element={<ClientPortalPage />} />
        <Route path="/calendar/:code" element={<PublicCalendarPage />} />
        <Route path="/" element={<ProtectedRoute><Shell /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          {/* Vista previa aislada del rediseno del Dashboard de KPIs (datos
              fijos, no toca la API ni la base) -- ver docs de la tarea.
              Cualquier usuario autenticado la puede abrir, sin gate de
              modulo/rol: no es una pantalla real todavia. */}
          <Route
            path="/dashboard-preview"
            element={<ErrorBoundaryPreview><DashboardPreviewPage /></ErrorBoundaryPreview>}
          />
          <Route path="/mfa-setup" element={<MfaSetupPage />} />
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route path="/role_permissions" element={<RoleAccessRoute entityName="entity_permission"><RolePermissionManagerPage /></RoleAccessRoute>} />
          <Route path="/kpi_permissions" element={<RoleAccessRoute entityName="nm_permission_kpi"><KpiPermissionManagerPage /></RoleAccessRoute>} />
          <Route path="/facturama-config" element={<RoleAccessRoute entityName="fiscal_stamp"><FacturamaConfigPage /></RoleAccessRoute>} />
          <Route path="/quotation" element={<RoleAccessRoute entityName="invoice"><QuotationPage /></RoleAccessRoute>} />
          <Route path="/authorization_tracking" element={<RoleAccessRoute entityName="invoice"><AuthorizationTrackingPage /></RoleAccessRoute>} />
          <Route path="/bank" element={<RoleAccessRoute entityName="bank"><BankPage /></RoleAccessRoute>} />
          <Route path="/bank_account" element={<RoleAccessRoute entityName="bank_account"><BankAccountPage /></RoleAccessRoute>} />
          <Route path="/brand" element={<RoleAccessRoute entityName="brand"><BrandPage /></RoleAccessRoute>} />
          <Route path="/customer_supplier" element={<RoleAccessRoute entityName="customer_supplier"><CustomerSupplierPage /></RoleAccessRoute>} />
          <Route path="/department" element={<RoleAccessRoute entityName="department"><DepartmentPage /></RoleAccessRoute>} />
          <Route path="/entity_permission" element={<RoleAccessRoute entityName="entity_permission"><EntityPermissionPage /></RoleAccessRoute>} />
          <Route path="/event_log" element={<TechnicalRoute><EventLogPage /></TechnicalRoute>} />
          <Route path="/field" element={<RoleAccessRoute entityName="field"><FieldPage /></RoleAccessRoute>} />
          <Route path="/fiscal_account" element={<RoleAccessRoute entityName="fiscal_account"><FiscalAccountPage /></RoleAccessRoute>} />
          <Route path="/incident" element={<RoleAccessRoute entityName="incident"><IncidentPage /></RoleAccessRoute>} />
          <Route path="/incident_detail" element={<RoleAccessRoute entityName="incident_detail"><IncidentDetailPage /></RoleAccessRoute>} />
          <Route path="/incident_type" element={<RoleAccessRoute entityName="incident_type"><IncidentTypePage /></RoleAccessRoute>} />
          <Route path="/inventory" element={<RoleAccessRoute entityName="product"><InventoryPage /></RoleAccessRoute>} />
          <Route path="/pos/turno" element={<RoleAccessRoute entityName="pos_terminal"><PosShiftPage /></RoleAccessRoute>} />
          <Route path="/pos/promociones" element={<RoleAccessRoute entityName="pos_admin"><PosPromotionsPage /></RoleAccessRoute>} />
          <Route path="/pos/productos" element={<RoleAccessRoute entityName="pos_terminal"><PosCatalogPage /></RoleAccessRoute>} />
          <Route path="/pos/inventario" element={<RoleAccessRoute entityName="pos_admin"><PosWarehousePage /></RoleAccessRoute>} />
          <Route path="/pos/tablero" element={<RoleAccessRoute entityName="pos_admin"><PosReportsPage /></RoleAccessRoute>} />
          <Route path="/pos/caja" element={<RoleAccessRoute entityName="pos_terminal"><PosTillPage /></RoleAccessRoute>} />
          <Route path="/inventory/trace" element={<RoleAccessRoute entityName="product"><InventoryTracePage /></RoleAccessRoute>} />
          <Route path="/assets" element={<RoleAccessRoute entityName="product"><AssetTrackingPage /></RoleAccessRoute>} />
          <Route path="/inventory_status" element={<RoleAccessRoute entityName="inventory_status"><InventoryStatusPage /></RoleAccessRoute>} />
          <Route path="/kanban" element={<Kanban />} />
          <Route path="/invoice" element={<RoleAccessRoute entityName="invoice"><InvoicePage /></RoleAccessRoute>} />
          <Route path="/invoice/manual" element={<RoleAccessRoute entityName="invoice"><ManualInvoicePage /></RoleAccessRoute>} />
          <Route path="/level" element={<RoleAccessRoute entityName="level"><LevelPage /></RoleAccessRoute>} />
          <Route path="/location" element={<RoleAccessRoute entityName="location"><LocationPage /></RoleAccessRoute>} />
          <Route path="/location_type" element={<RoleAccessRoute entityName="location_type"><LocationTypePage /></RoleAccessRoute>} />
          <Route path="/material" element={<RoleAccessRoute entityName="material"><MaterialPage /></RoleAccessRoute>} />
          <Route path="/nm_field_permission" element={<RoleAccessRoute entityName="nm_field_permission"><NmFieldPermissionPage /></RoleAccessRoute>} />
          <Route path="/nm_incident_product" element={<RoleAccessRoute entityName="nm_incident_product"><NmIncidentProductPage /></RoleAccessRoute>} />
          <Route path="/nm_survey_user" element={<RoleAccessRoute entityName="nm_survey_user"><NmSurveyUserPage /></RoleAccessRoute>} />
          <Route path="/nm_template_task" element={<RoleAccessRoute entityName="nm_template_task"><NmTemplateTaskPage /></RoleAccessRoute>} />
          <Route path="/payroll_concept" element={<RoleAccessRoute entityName="payroll_concept"><PayrollConceptPage /></RoleAccessRoute>} />
          <Route path="/payroll_detail" element={<RoleAccessRoute entityName="payroll_detail"><PayrollDetailPage /></RoleAccessRoute>} />
          <Route path="/payroll_movement" element={<RoleAccessRoute entityName="payroll_movement"><PayrollMovementPage /></RoleAccessRoute>} />
          <Route path="/payroll_period" element={<RoleAccessRoute entityName="payroll_period"><PayrollPeriodPage /></RoleAccessRoute>} />
          <Route path="/kronos" element={<RoleAccessRoute entityName="payroll_period"><KronosPage /></RoleAccessRoute>} />
          <Route path="/kronos/device" element={<RoleAccessRoute entityName="kronos_device"><KronosDevicePage /></RoleAccessRoute>} />
          <Route path="/logistica/clientes" element={<RoleAccessRoute entityName="customer_supplier"><CustomerSupplierPage clientsOnly /></RoleAccessRoute>} />
          <Route path="/logistica/proveedores" element={<RoleAccessRoute entityName="customer_supplier"><CustomerSupplierPage mode="suppliersOnly" /></RoleAccessRoute>} />
          <Route path="/logistica/direcciones" element={<RoleAccessRoute entityName="logistics_address"><LogisticsAddressesPage /></RoleAccessRoute>} />
          <Route path="/logistica/contratos" element={<RoleAccessRoute entityName="logistics_contract"><LogisticsContractsPage /></RoleAccessRoute>} />
          <Route path="/logistica/tarifas" element={<RoleAccessRoute entityName="logistics_rate"><LogisticsRatesPage /></RoleAccessRoute>} />
          <Route path="/logistica/cotizaciones" element={<RoleAccessRoute entityName="logistics_quotation"><LogisticsQuotationsPage /></RoleAccessRoute>} />
          <Route path="/logistica/solicitudes" element={<RoleAccessRoute entityName="logistics_service_request"><LogisticsServiceRequestsPage /></RoleAccessRoute>} />
          <Route path="/logistica/viajes" element={<RoleAccessRoute entityName="logistics_trip"><LogisticsTripsPage /></RoleAccessRoute>} />
          <Route path="/logistica/evidencias" element={<RoleAccessRoute entityName="logistics_evidence"><LogisticsEvidencesPage /></RoleAccessRoute>} />
          <Route path="/logistica/incidencias" element={<RoleAccessRoute entityName="logistics_incident"><LogisticsIncidentsPage /></RoleAccessRoute>} />
          <Route path="/logistica/unidades" element={<RoleAccessRoute entityName="logistics_unit"><LogisticsUnitsPage /></RoleAccessRoute>} />
          <Route path="/logistica/remolques" element={<RoleAccessRoute entityName="logistics_trailer"><LogisticsTrailersPage /></RoleAccessRoute>} />
          <Route path="/logistica/operadores" element={<RoleAccessRoute entityName="logistics_operator"><LogisticsOperatorsPage /></RoleAccessRoute>} />
          <Route path="/logistica/mantenimientos" element={<RoleAccessRoute entityName="logistics_maintenance"><LogisticsMaintenancePage /></RoleAccessRoute>} />
          <Route path="/logistica/almacenes" element={<RoleAccessRoute entityName="logistics_warehouse"><LogisticsWarehousesPage /></RoleAccessRoute>} />
          <Route path="/logistica/ubicaciones" element={<RoleAccessRoute entityName="logistics_location"><LogisticsLocationsPage /></RoleAccessRoute>} />
          <Route path="/logistica/inventario" element={<RoleAccessRoute entityName="logistics_inventory"><LogisticsInventoryPage /></RoleAccessRoute>} />
          <Route path="/logistica/racks" element={<RoleAccessRoute entityName="logistics_rack"><LogisticsRacksPage /></RoleAccessRoute>} />
          <Route path="/logistica/embarques" element={<RoleAccessRoute entityName="logistics_shipment"><LogisticsShipmentsPage /></RoleAccessRoute>} />
          <Route path="/logistica/sucursales" element={<RoleAccessRoute entityName="logistics_branch"><LogisticsBranchesPage /></RoleAccessRoute>} />
          <Route path="/logistica/cuentas-cobrar" element={<RoleAccessRoute entityName="logistics_receivable"><LogisticsReceivablesPage /></RoleAccessRoute>} />
          <Route path="/logistica/expedientes" element={<RoleAccessRoute entityName="logistics_file"><LogisticsFilesPage /></RoleAccessRoute>} />
          <Route path="/logistica/facturas" element={<RoleAccessRoute entityName="invoice"><InvoicePage /></RoleAccessRoute>} />
          <Route path="/logistica/facturacion/manual" element={<RoleAccessRoute entityName="invoice"><ManualInvoicePage /></RoleAccessRoute>} />
          {/* /logistica/usuarios, /logistica/roles, /logistica/auditoria y
              /logistica/seguridad se retiraron con `section_administration`
              en moduleSections.js: eran una segunda puerta a las mismas
              pantallas que ya viven en /user, /role_permissions, /event_log
              y /mfa-setup. */}
          <Route path="/restaurant/waiter" element={<RoleAccessRoute entityName="restaurant_waiter"><RestaurantWaiterPage /></RoleAccessRoute>} />
          <Route path="/restaurant/cashier" element={<RoleAccessRoute entityName="restaurant_cashier"><RestaurantCashierPage /></RoleAccessRoute>} />
          <Route path="/restaurant/kitchen" element={<RoleAccessRoute entityName="restaurant_kitchen"><RestaurantKitchenPage /></RoleAccessRoute>} />
          <Route path="/restaurant/admin" element={<RoleAccessRoute entityName="restaurant_admin"><RestaurantAdminPage /></RoleAccessRoute>} />
          <Route path="/permission" element={<RoleAccessRoute entityName="permission"><PermissionPage /></RoleAccessRoute>} />
          <Route path="/team" element={<RoleAccessRoute entityName="team"><TeamManagerPage /></RoleAccessRoute>} />
          <Route path="/product" element={<RoleAccessRoute entityName="product"><ProductPage /></RoleAccessRoute>} />
          {/* Los dos niveles de la clasificacion, en una pantalla. Habia dos
              entradas de menu y leidas seguidas parecen lo mismo dos veces; el
              tipo cuelga de la familia y no se puede leer sin ella. Las dos
              El TIPO se retiro del flujo: en estos datos la descripcion del
              material ya lo trae -"BROCA HELICOIDAL 3/4"-, asi que un nivel
              aparte obliga a capturar dos veces lo mismo. */}
          <Route path="/product_family" element={<RoleAccessRoute entityName="product_family"><ProductFamilyPage /></RoleAccessRoute>} />
          {/* El vale se guarda con la capacidad `warehouse_voucher`, no con
              una entidad: su pantalla escribe en `incident` y en la tabla
              puente de sus renglones, que esta fuera del menu a proposito.
              Quien solo tiene `warehouse_prevoucher` (Supervisor: pide
              material, no lo surte) entra a la MISMA pantalla -es el borrador,
              no un vale abierto- y ahi el propio servidor decide que boton
              dejarle usar; sin la segunda clave aqui, Supervisor nunca
              llegaba a la puerta. */}
          <Route path="/vouchers" element={<RoleAccessRoute entityName={VOUCHER_ENTITY_NAMES}><WarehouseVoucherPage /></RoleAccessRoute>} />
          {/* Lo que falta comprar: la guarda la capacidad `purchase_planning`. */}
          <Route path="/por-comprar" element={<RoleAccessRoute entityName="purchase_planning"><PorComprarPage /></RoleAccessRoute>} />
          {/* Las ordenes de compra: la guarda la entidad `purchase_order`; autorizar y
              comprar lo reservado a gerencia lo exige ademas el servidor. */}
          <Route path="/ordenes-de-compra" element={<RoleAccessRoute entityName="purchase_order"><OrdenesDeCompraPage /></RoleAccessRoute>} />
          <Route path="/activity-log" element={<RoleAccessRoute entityName="daily_activity_log"><ActivityLogPage /></RoleAccessRoute>} />
          <Route path="/product_sale_config" element={<RoleAccessRoute entityName="product_sale_config"><ProductSaleConfigPage /></RoleAccessRoute>} />
          <Route path="/proyect" element={<RoleAccessRoute entityName="proyect"><ProjectManagementPage /></RoleAccessRoute>} />
          <Route path="/appointments" element={<RoleAccessRoute entityName="appointment"><AppointmentsPage /></RoleAccessRoute>} />
          <Route path="/documents" element={<RoleAccessRoute entityName="document"><DocumentManagementPage /></RoleAccessRoute>} />
          <Route path="/laboratory" element={<RoleAccessRoute entityName="laboratory_service_order"><LaboratoryManagementPage /></RoleAccessRoute>} />
          <Route path="/public_api_key" element={<RoleAccessRoute entityName="public_api_key"><PublicApiKeyPage /></RoleAccessRoute>} />
          <Route path="/service" element={<RoleAccessRoute entityName="service"><ServicePage /></RoleAccessRoute>} />
          <Route path="/status" element={<RoleAccessRoute entityName="status"><StatusPage /></RoleAccessRoute>} />
          <Route path="/subdepartment" element={<RoleAccessRoute entityName="subdepartment"><SubdepartmentPage /></RoleAccessRoute>} />
          <Route path="/survey_multiple_answer" element={<RoleAccessRoute entityName="survey_multiple_answer"><SurveyMultipleAnswerPage /></RoleAccessRoute>} />
          <Route path="/survey_question" element={<RoleAccessRoute entityName="survey_question"><SurveyQuestionPage /></RoleAccessRoute>} />
          <Route path="/task" element={<RoleAccessRoute entityName="task"><TaskPage /></RoleAccessRoute>} />
          <Route path="/task_note" element={<RoleAccessRoute entityName="task_note"><TaskNotePage /></RoleAccessRoute>} />
          <Route path="/task_type" element={<RoleAccessRoute entityName="task_type"><TaskTypePage /></RoleAccessRoute>} />
          <Route path="/template" element={<RoleAccessRoute entityName="template"><TemplatePage /></RoleAccessRoute>} />
          <Route path="/theme" element={<RoleAccessRoute entityName="theme"><ThemePage /></RoleAccessRoute>} />
          <Route path="/ticket" element={<RoleAccessRoute entityName="ticket"><TicketPage /></RoleAccessRoute>} />
          <Route path="/unit" element={<RoleAccessRoute entityName="unit"><UnitPage /></RoleAccessRoute>} />
          <Route path="/user" element={<RoleAccessRoute entityName="user"><UserPage /></RoleAccessRoute>} />
          <Route path="/user_mfa" element={<TechnicalRoute><UserMfaPage /></TechnicalRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
