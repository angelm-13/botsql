import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Boxes, ChevronDown, ClipboardList, FileText, Landmark, LayoutDashboard, LogOut, PanelLeftClose, PanelLeftOpen, Settings, ShieldCheck, SlidersHorizontal, Users, Utensils } from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
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
  { path: "/invoice/manual", key: "menu.manual_invoice", label: "Factura manual", entityName: "invoice" },
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
  { path: "/kronos", key: "menu.kronos", label: "Asistencias", entityName: "payroll_period" },
  { path: "/kronos/device", key: "menu.kronos_device", label: "Conexión al dispositivo", entityName: "kronos_device" },
  { path: "/restaurant/waiter", key: "menu.restaurant_waiter", label: "Meseros", entityName: "restaurant_waiter" },
  { path: "/restaurant/cashier", key: "menu.restaurant_cashier", label: "Caja", entityName: "restaurant_cashier" },
  { path: "/restaurant/kitchen", key: "menu.restaurant_kitchen", label: "Cocina", entityName: "restaurant_kitchen" },
  { path: "/restaurant/admin", key: "menu.restaurant_admin", label: "Admin", entityName: "restaurant_admin" },
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

const groupIcons = {
  "landmark": Landmark,
  "file-text": FileText,
  "users": Users,
  "utensils": Utensils,
  "clipboard-list": ClipboardList,
  "boxes": Boxes,
  "sliders-horizontal": SlidersHorizontal,
  "shield-check": ShieldCheck,
  "layout-dashboard": LayoutDashboard,
  "settings": Settings,
};

const defaultGroupIcons = {
  "Bancos": "landmark",
  "Contabilidad": "file-text",
  "Recursos humanos": "users",
  "Restaurante": "utensils",
  "Operaciones": "clipboard-list",
  "Inventario": "boxes",
  "Configuración": "sliders-horizontal",
};

export default function Shell() {
  const [, forceRender] = useState(0);
  const [roleEntityPermissions, setRoleEntityPermissions] = useState([]);
  const [rolePermissionsLoaded, setRolePermissionsLoaded] = useState(false);
  const [openGroups, setOpenGroups] = useState({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem("tyakxa-sidebar-collapsed") === "true");
  const settingsRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
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
  const permissionByEntity = useMemo(() => new Map(roleEntityPermissions.map((row) => [String(row.entity_name || ""), row])), [roleEntityPermissions]);

  function defaultGroup(item) {
    const path = item.path;
    if (["/bank", "/bank_account", "/movement"].includes(path)) return "Bancos";
    if (path.startsWith("/invoice") || path.startsWith("/fiscal") || path === "/quotation" || path === "/authorization_tracking") return "Contabilidad";
    if (path.startsWith("/payroll") || path === "/kronos") return "Recursos humanos";
    if (path.startsWith("/restaurant")) return "Restaurante";
    if (["/proyect", "/incident", "/incident_detail", "/task", "/task_note", "/service", "/template"].includes(path)) return "Operaciones";
    if (["/material", "/location", "/product", "/inventory_status", "/unit", "/brand"].includes(path)) return "Inventario";
    return "Configuración";
  }

  function navigationFor(item) {
    const entityName = item.entityName || String(item.path || "").replace(/^\//, "");
    const permission = permissionByEntity.get(entityName);
    const isCanonicalPath = item.path === `/${entityName}`;
    return {
      ...item,
      location: permission?.menu_location || (item.adminOnly ? "settings" : "sidebar"),
      group: permission?.menu_group || defaultGroup(item),
      groupIcon: permission?.menu_group_icon || defaultGroupIcons[permission?.menu_group || defaultGroup(item)] || "sliders-horizontal",
      order: Number(permission?.menu_order ?? 100),
      displayLabel: isCanonicalPath && permission?.menu_label ? permission.menu_label : t(item.key, item.label || item.key)
    };
  }

  const fixedSidebarItems = visibleNavItems.filter((item) => item.exact || item.path === "/mfa-setup");
  const configuredItems = visibleNavItems.filter((item) => !item.exact && item.path !== "/mfa-setup").map(navigationFor);
  const sidebarGroups = useMemo(() => {
    const groups = new Map();
    configuredItems.filter((item) => item.location === "sidebar").forEach((item) => {
      if (!groups.has(item.group)) groups.set(item.group, { icon: item.groupIcon, items: [] });
      groups.get(item.group).items.push(item);
    });
    return [...groups.entries()].map(([label, group]) => ({ label, icon: group.icon, items: group.items.sort((a, b) => a.order - b.order || a.displayLabel.localeCompare(b.displayLabel)) }));
  }, [configuredItems]);
  const settingsItems = configuredItems.filter((item) => item.location === "settings").sort((a, b) => a.order - b.order || a.displayLabel.localeCompare(b.displayLabel));

  useEffect(() => {
    const handler = () => forceRender((v) => v + 1);
    const expired = () => navigate("/login", { replace: true });
    window.addEventListener("tyakxa-language-change", handler);
    window.addEventListener("tyakxa-auth-expired", expired);
    return () => { window.removeEventListener("tyakxa-language-change", handler); window.removeEventListener("tyakxa-auth-expired", expired); };
  }, [navigate]);
  useEffect(() => {
    function closeSettings(event) {
      if (settingsRef.current && !settingsRef.current.contains(event.target)) setSettingsOpen(false);
    }
    document.addEventListener("mousedown", closeSettings);
    return () => document.removeEventListener("mousedown", closeSettings);
  }, []);
  const handleLogout = () => {
    localStorage.removeItem("token"); localStorage.removeItem("user"); localStorage.removeItem("mfa_temp_token");
    navigate("/login", { replace: true });
  };
  const toggleSidebar = () => {
    setSidebarCollapsed((current) => {
      const next = !current;
      localStorage.setItem("tyakxa-sidebar-collapsed", String(next));
      return next;
    });
  };
  const expandSidebarForGroup = (groupLabel) => {
    setOpenGroups((current) => ({ ...current, [groupLabel]: true }));
    setSidebarCollapsed(false);
    localStorage.setItem("tyakxa-sidebar-collapsed", "false");
  };
  return (
    <div className={sidebarCollapsed ? "shell sidebar-is-collapsed" : "shell"}>
      <aside className="sidebar" aria-label={t("common.main_navigation", "Navegación principal")}>
        <div className="sidebar-brand-row">
          <div className="brand"><img src="/tyakxa-logo.png" alt={t("common.app_title")} className="brand-logo" /><span>{t("common.app_title")}</span></div>
        </div>
        <nav className="nav">
          {!sidebarCollapsed && fixedSidebarItems.map((item, index) => (
            <NavLink key={item.path} to={item.path} end={item.exact} title={sidebarCollapsed ? t(item.key, item.label || item.key) : undefined} aria-label={t(item.key, item.label || item.key)} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              {index === 0 ? <LayoutDashboard size={18} /> : item.path === "/mfa-setup" ? <ShieldCheck size={18} /> : <span className="dot" />}
              <span className="nav-link-label">{t(item.key, item.label || item.key)}</span>
            </NavLink>
          ))}
          {sidebarCollapsed ? sidebarGroups.map((group) => {
            const GroupIcon = groupIcons[group.icon] || SlidersHorizontal;
            return <button type="button" key={group.label} className="nav-link collapsed-group-button" title={group.label} aria-label={`Expandir grupo ${group.label}`} onClick={() => expandSidebarForGroup(group.label)}><GroupIcon size={20} /><span className="nav-link-label">{group.label}</span></button>;
          }) : sidebarGroups.map((group) => {
            const isOpen = openGroups[group.label] ?? group.items.some((item) => location.pathname === item.path);
            return <div className="shell-nav-group" key={group.label}>
              <button type="button" className="shell-nav-group-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [group.label]: !isOpen }))}><span>{group.label}</span><ChevronDown size={16} className={isOpen ? "open" : ""} /></button>
              {isOpen && <div className="shell-nav-submenu">{group.items.map((item) => <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><span className="dot" /><span className="nav-link-label">{item.displayLabel}</span></NavLink>)}</div>}
            </div>;
          })}
        </nav>
      </aside>
      <button type="button" className="sidebar-collapse-button" onClick={toggleSidebar} title={sidebarCollapsed ? "Expandir menú" : "Contraer menú"} aria-label={sidebarCollapsed ? "Expandir menú" : "Contraer menú"} aria-expanded={!sidebarCollapsed}>
        {sidebarCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
      </button>
      <main className="main">
        <header className="topbar">
          <div><p className="eyebrow">ERP · CRM · SCM</p><h1>TYAKXA</h1></div>
          <div className="topbar-actions">
            <span className="session-pill">{t("common.secure_session", "Sesión protegida")}{currentUser?.username ? ` · ${currentUser.username}` : ""}</span>
            <label className="language-picker">{t("common.language")}<select value={lang} onChange={(e) => setLanguage(e.target.value)}><option value="es">ES</option><option value="en">EN</option><option value="pt">PT</option><option value="de">DE</option><option value="ja">日本語</option></select></label>
            <div className="session-actions">
              <div className="settings-menu" ref={settingsRef}>
                <button className="button ghost settings-trigger" title="Opciones" aria-label="Opciones" aria-expanded={settingsOpen} onClick={() => setSettingsOpen((value) => !value)}><Settings size={18} /></button>
                {settingsOpen && <div className="settings-popover">{settingsItems.length ? settingsItems.map((item) => <NavLink key={item.path} to={item.path} onClick={() => setSettingsOpen(false)}>{item.displayLabel}</NavLink>) : <span className="settings-empty">Sin opciones configuradas</span>}</div>}
              </div>
              <button className="button ghost" onClick={handleLogout}><LogOut size={16} />{t("common.logout", "Cerrar sesión")}</button>
            </div>
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
