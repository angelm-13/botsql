import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, LogOut, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { getAllEntityPermission } from "../api";
import { useI18n } from "../i18n";

const navItems = [
  { path: "/", key: "common.dashboard", exact: true },
  { path: "/mfa-setup", key: "common.mfa_setup" },
  { path: "/role_permissions", key: "common.role_permission_manager", adminOnly: true },
  { path: "/bank", key: "menu.bank" },
  { path: "/bank_account", key: "menu.bank_account" },
  { path: "/brand", key: "menu.brand" },
  { path: "/customer_supplier", key: "menu.customer_supplier" },
  { path: "/department", key: "menu.department" },
  { path: "/event_log", key: "menu.event_log" },
  { path: "/field", key: "menu.field" },
  { path: "/fiscal_account", key: "menu.fiscal_account" },
  { path: "/fiscal_record", key: "menu.fiscal_record" },
  { path: "/fiscal_stamp", key: "menu.fiscal_stamp" },
  { path: "/incident", key: "menu.incident" },
  { path: "/incident_detail", key: "menu.incident_detail" },
  { path: "/incident_type", key: "menu.incident_type" },
  { path: "/inventory_status", key: "menu.inventory_status" },
  { path: "/invoice", key: "menu.invoice" },
  { path: "/quotation", key: "menu.quotation", label: "Cotizaciones", entityName: "invoice" },
  { path: "/authorization_tracking", key: "menu.authorization_tracking", label: "Autorización / Seguimiento", entityName: "invoice" },
  { path: "/invoice_material_service", key: "menu.invoice_material_service" },
  { path: "/level", key: "menu.level" },
  { path: "/location", key: "menu.location" },
  { path: "/location_type", key: "menu.location_type" },
  { path: "/material", key: "menu.material" },
  { path: "/material_component", key: "menu.material_component" },
  { path: "/movement", key: "menu.movement" },
  { path: "/nm_incident_product", key: "menu.nm_incident_product" },
  { path: "/nm_survey_user", key: "menu.nm_survey_user" },
  { path: "/nm_template_task", key: "menu.nm_template_task" },
  { path: "/payroll_concept", key: "menu.payroll_concept" },
  { path: "/payroll_detail", key: "menu.payroll_detail" },
  { path: "/payroll_movement", key: "menu.payroll_movement" },
  { path: "/payroll_period", key: "menu.payroll_period" },
  { path: "/permission", key: "menu.permission" },
  { path: "/product", key: "menu.product" },
  { path: "/product_family", key: "menu.product_family" },
  { path: "/proyect", key: "menu.proyect" },
  { path: "/service", key: "menu.service" },
  { path: "/status", key: "menu.status" },
  { path: "/subdepartment", key: "menu.subdepartment" },
  { path: "/survey_multiple_answer", key: "menu.survey_multiple_answer" },
  { path: "/survey_question", key: "menu.survey_question" },
  { path: "/task", key: "menu.task" },
  { path: "/task_note", key: "menu.task_note" },
  { path: "/task_type", key: "menu.task_type" },
  { path: "/template", key: "menu.template" },
  { path: "/theme", key: "menu.theme" },
  { path: "/ticket", key: "menu.ticket" },
  { path: "/unit", key: "menu.unit" },
  { path: "/user", key: "menu.user" },
  { path: "/user_mfa", key: "menu.user_mfa" }
];

const quickNavItems = [
  { path: "/catalogo-web", key: "menu.catalogo_web", label: "Catálogo Web", entityName: "product_sale_config" },
  { path: "/compradores-web", key: "menu.web_shoppers", label: "Compradores Web", entityName: "user" }
];

export default function Shell() {
  const [, forceRender] = useState(0);
  const [roleEntityPermissions, setRoleEntityPermissions] = useState([]);
  const [rolePermissionsLoaded, setRolePermissionsLoaded] = useState(false);
  const navigate = useNavigate();
  const { lang, t, setLanguage } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const bootstrapUsername = import.meta.env.VITE_BOOTSTRAP_ADMIN_USERNAME || "admin1";
  const isBootstrapAdmin = Boolean(currentUser?.username === bootstrapUsername && (currentUser?.is_bootstrap_admin || currentUser?.is_superuser || currentUser?.username === bootstrapUsername));
  const isAdminUser = Boolean(isBootstrapAdmin || currentUser?.is_superuser || String(currentUser?.user_type || "").toLowerCase() === "admin");
  const technicalPaths = ["/user_mfa", "/event_log"];

  useEffect(() => {
    let mounted = true;
    const roleId = Number(currentUser?.id_permission || 0);
    setRolePermissionsLoaded(false);
    if (isBootstrapAdmin) {
      setRoleEntityPermissions([]);
      setRolePermissionsLoaded(true);
      return () => { mounted = false; };
    }
    if (!roleId) {
      setRoleEntityPermissions([]);
      setRolePermissionsLoaded(true);
      return () => { mounted = false; };
    }
    getAllEntityPermission({ per_page: 5000 })
      .then((payload) => {
        const rows = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : [];
        if (mounted) setRoleEntityPermissions(rows.filter((row) => Number(row.id_permission) === roleId && Number(row.control_type || 0) > 0));
      })
      .catch(() => { if (mounted) setRoleEntityPermissions([]); })
      .finally(() => { if (mounted) setRolePermissionsLoaded(true); });
    return () => { mounted = false; };
  }, [currentUser?.id_permission, isBootstrapAdmin]);

  function canSeeNavItem(item) {
    if (item.exact || item.path === "/mfa-setup") return true;
    if (technicalPaths.includes(item.path)) return isBootstrapAdmin;
    if (item.adminOnly) return isAdminUser;
    if (isBootstrapAdmin) return true;
    if (!rolePermissionsLoaded) return false;
    const entityName = item.entityName || String(item.path || "").replace(/^\//, "");
    return roleEntityPermissions.some((row) => String(row.entity_name || "") === entityName);
  }

  const visibleNavItems = navItems.filter(canSeeNavItem);
  useEffect(() => {
    const handler = () => forceRender((v) => v + 1);
    const expired = () => navigate("/login", { replace: true });
    window.addEventListener("tyakxa-language-change", handler);
    window.addEventListener("tyakxa-auth-expired", expired);
    return () => { window.removeEventListener("tyakxa-language-change", handler); window.removeEventListener("tyakxa-auth-expired", expired); };
  }, [navigate]);
  const handleLogout = () => {
    localStorage.removeItem("token"); localStorage.removeItem("user"); localStorage.removeItem("mfa_temp_token");
    navigate("/login", { replace: true });
  };
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><img src="/tyakxa-logo.png" alt={t("common.app_title")} className="brand-logo" /><span>{t("common.app_title")}</span></div>
        <nav className="nav">
          {visibleNavItems.map((item, index) => (
            <NavLink key={item.path} to={item.path} end={item.exact} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              {index === 0 ? <LayoutDashboard size={18} /> : item.path === "/mfa-setup" ? <ShieldCheck size={18} /> : <span className="dot" />}
              <span>{t(item.key, item.label || item.key)}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div><p className="eyebrow">ERP · CRM · SCM</p><h1>TYAKXA</h1></div>
          <div className="topbar-actions">
            <span className="session-pill">{t("common.secure_session", "Sesión protegida")}{currentUser?.username ? ` · ${currentUser.username}` : ""}</span>
            <label className="language-picker">{t("common.language")}<select value={lang} onChange={(e) => setLanguage(e.target.value)}><option value="es">ES</option><option value="en">EN</option><option value="pt">PT</option><option value="de">DE</option><option value="ja">日本語</option></select></label>
            <button className="button ghost" onClick={handleLogout}><LogOut size={16} />{t("common.logout", "Cerrar sesión")}</button>
          </div>
        </header>
        <nav className="quick-nav" aria-label={t("common.quick_access", "Accesos rápidos")}>
          {quickNavItems.filter(canSeeNavItem).map((item) => (
            <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "quick-nav-link active" : "quick-nav-link"}>
              {t(item.key, item.label || item.key)}
            </NavLink>
          ))}
        </nav>
        <Outlet />
      </main>
    </div>
  );
}
