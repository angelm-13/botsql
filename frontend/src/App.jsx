import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Shell from "./layouts/Shell";
import Dashboard from "./pages/Dashboard";
import MfaSetupPage from "./pages/MfaSetupPage";
import RolePermissionManagerPage from "./pages/RolePermissionManagerPage.jsx";
import QuotationPage from "./pages/QuotationPage.jsx";
import AuthorizationTrackingPage from "./pages/AuthorizationTrackingPage.jsx";
import CatalogoWebPage from "./pages/CatalogoWebPage.jsx";
import WebShoppersPage from "./pages/WebShoppersPage.jsx";
import BankPage from "./pages/BankPage.jsx";
import BankAccountPage from "./pages/BankAccountPage.jsx";
import BrandPage from "./pages/BrandPage.jsx";
import CustomerSupplierPage from "./pages/CustomerSupplierPage.jsx";
import DepartmentPage from "./pages/DepartmentPage.jsx";
import EntityPermissionPage from "./pages/EntityPermissionPage.jsx";
import EventLogPage from "./pages/EventLogPage.jsx";
import FieldPage from "./pages/FieldPage.jsx";
import FiscalAccountPage from "./pages/FiscalAccountPage.jsx";
import FiscalRecordPage from "./pages/FiscalRecordPage.jsx";
import FiscalStampPage from "./pages/FiscalStampPage.jsx";
import IncidentPage from "./pages/IncidentPage.jsx";
import IncidentDetailPage from "./pages/IncidentDetailPage.jsx";
import IncidentTypePage from "./pages/IncidentTypePage.jsx";
import InventoryStatusPage from "./pages/InventoryStatusPage.jsx";
import InvoicePage from "./pages/InvoicePage.jsx";
import InvoiceMaterialServicePage from "./pages/InvoiceMaterialServicePage.jsx";
import LevelPage from "./pages/LevelPage.jsx";
import LocationPage from "./pages/LocationPage.jsx";
import LocationTypePage from "./pages/LocationTypePage.jsx";
import MaterialPage from "./pages/MaterialPage.jsx";
import MaterialComponentPage from "./pages/MaterialComponentPage.jsx";
import MovementPage from "./pages/MovementPage.jsx";
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
import ProductFamilyPage from "./pages/ProductFamilyPage.jsx";
import ProductSaleConfigPage from "./pages/ProductSaleConfigPage.jsx";
import ProyectPage from "./pages/ProyectPage.jsx";
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
import Kanban from './components/Kanban.jsx';
import LoginPage from "./auth/LoginPage";
import ProtectedRoute from "./auth/ProtectedRoute";
import { useEffect, useState } from "react";
import { getAllEntityPermission } from "./api";
import "./styles/app.css";

function isBootstrapUser() {
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const bootstrapUsername = import.meta.env.VITE_BOOTSTRAP_ADMIN_USERNAME || "admin1";
  return Boolean(currentUser?.username === bootstrapUsername && (currentUser?.is_bootstrap_admin || currentUser?.is_superuser || currentUser?.username === bootstrapUsername));
}

function isAdminUser() {
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  return isBootstrapUser() || String(currentUser?.user_type || "").toLowerCase() === "admin" || Boolean(currentUser?.is_superuser);
}

function TechnicalRoute({ children }) {
  return isBootstrapUser() ? children : <Navigate to="/" replace />;
}

function AdminRoute({ children }) {
  return isAdminUser() ? children : <Navigate to="/" replace />;
}

function roleHasEntityAccess(rows, entityName, currentUser) {
  if (isBootstrapUser()) return true;
  const roleId = Number(currentUser?.id_permission || 0);
  if (!roleId || !entityName) return false;
  return rows.some((row) => Number(row.id_permission) === roleId && String(row.entity_name || "") === String(entityName) && Number(row.control_type || 0) > 0);
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
        <Route path="/" element={<ProtectedRoute><Shell /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="/mfa-setup" element={<MfaSetupPage />} />
          <Route path="/role_permissions" element={<AdminRoute><RolePermissionManagerPage /></AdminRoute>} />
          <Route path="/quotation" element={<RoleAccessRoute entityName="invoice"><QuotationPage /></RoleAccessRoute>} />
          <Route path="/authorization_tracking" element={<RoleAccessRoute entityName="invoice"><AuthorizationTrackingPage /></RoleAccessRoute>} />
          <Route path="/catalogo-web" element={<RoleAccessRoute entityName="product_sale_config"><CatalogoWebPage /></RoleAccessRoute>} />
          <Route path="/compradores-web" element={<RoleAccessRoute entityName="user"><WebShoppersPage /></RoleAccessRoute>} />
          <Route path="/bank" element={<RoleAccessRoute entityName="bank"><BankPage /></RoleAccessRoute>} />
          <Route path="/bank_account" element={<RoleAccessRoute entityName="bank_account"><BankAccountPage /></RoleAccessRoute>} />
          <Route path="/brand" element={<RoleAccessRoute entityName="brand"><BrandPage /></RoleAccessRoute>} />
          <Route path="/customer_supplier" element={<RoleAccessRoute entityName="customer_supplier"><CustomerSupplierPage /></RoleAccessRoute>} />
          <Route path="/department" element={<RoleAccessRoute entityName="department"><DepartmentPage /></RoleAccessRoute>} />
          <Route path="/entity_permission" element={<AdminRoute><EntityPermissionPage /></AdminRoute>} />
          <Route path="/event_log" element={<TechnicalRoute><EventLogPage /></TechnicalRoute>} />
          <Route path="/field" element={<RoleAccessRoute entityName="field"><FieldPage /></RoleAccessRoute>} />
          <Route path="/fiscal_account" element={<RoleAccessRoute entityName="fiscal_account"><FiscalAccountPage /></RoleAccessRoute>} />
          <Route path="/fiscal_record" element={<RoleAccessRoute entityName="fiscal_record"><FiscalRecordPage /></RoleAccessRoute>} />
          <Route path="/fiscal_stamp" element={<RoleAccessRoute entityName="fiscal_stamp"><FiscalStampPage /></RoleAccessRoute>} />
          <Route path="/incident" element={<RoleAccessRoute entityName="incident"><IncidentPage /></RoleAccessRoute>} />
          <Route path="/incident_detail" element={<RoleAccessRoute entityName="incident_detail"><IncidentDetailPage /></RoleAccessRoute>} />
          <Route path="/incident_type" element={<RoleAccessRoute entityName="incident_type"><IncidentTypePage /></RoleAccessRoute>} />
          <Route path="/inventory_status" element={<RoleAccessRoute entityName="inventory_status"><InventoryStatusPage /></RoleAccessRoute>} />
          <Route path="/kanban" element={<Kanban />} />
          <Route path="/invoice" element={<RoleAccessRoute entityName="invoice"><InvoicePage /></RoleAccessRoute>} />
          <Route path="/invoice_material_service" element={<RoleAccessRoute entityName="invoice_material_service"><InvoiceMaterialServicePage /></RoleAccessRoute>} />
          <Route path="/level" element={<RoleAccessRoute entityName="level"><LevelPage /></RoleAccessRoute>} />
          <Route path="/location" element={<RoleAccessRoute entityName="location"><LocationPage /></RoleAccessRoute>} />
          <Route path="/location_type" element={<RoleAccessRoute entityName="location_type"><LocationTypePage /></RoleAccessRoute>} />
          <Route path="/material" element={<RoleAccessRoute entityName="material"><MaterialPage /></RoleAccessRoute>} />
          <Route path="/material_component" element={<RoleAccessRoute entityName="material_component"><MaterialComponentPage /></RoleAccessRoute>} />
          <Route path="/movement" element={<RoleAccessRoute entityName="movement"><MovementPage /></RoleAccessRoute>} />
          <Route path="/nm_field_permission" element={<AdminRoute><NmFieldPermissionPage /></AdminRoute>} />
          <Route path="/nm_incident_product" element={<RoleAccessRoute entityName="nm_incident_product"><NmIncidentProductPage /></RoleAccessRoute>} />
          <Route path="/nm_survey_user" element={<RoleAccessRoute entityName="nm_survey_user"><NmSurveyUserPage /></RoleAccessRoute>} />
          <Route path="/nm_template_task" element={<RoleAccessRoute entityName="nm_template_task"><NmTemplateTaskPage /></RoleAccessRoute>} />
          <Route path="/payroll_concept" element={<RoleAccessRoute entityName="payroll_concept"><PayrollConceptPage /></RoleAccessRoute>} />
          <Route path="/payroll_detail" element={<RoleAccessRoute entityName="payroll_detail"><PayrollDetailPage /></RoleAccessRoute>} />
          <Route path="/payroll_movement" element={<RoleAccessRoute entityName="payroll_movement"><PayrollMovementPage /></RoleAccessRoute>} />
          <Route path="/payroll_period" element={<RoleAccessRoute entityName="payroll_period"><PayrollPeriodPage /></RoleAccessRoute>} />
          <Route path="/permission" element={<RoleAccessRoute entityName="permission"><PermissionPage /></RoleAccessRoute>} />
          <Route path="/product" element={<RoleAccessRoute entityName="product"><ProductPage /></RoleAccessRoute>} />
          <Route path="/product_family" element={<RoleAccessRoute entityName="product_family"><ProductFamilyPage /></RoleAccessRoute>} />
          <Route path="/product_sale_config" element={<RoleAccessRoute entityName="product_sale_config"><ProductSaleConfigPage /></RoleAccessRoute>} />
          <Route path="/proyect" element={<RoleAccessRoute entityName="proyect"><ProyectPage /></RoleAccessRoute>} />
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
