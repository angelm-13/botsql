import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Boxes, CalendarDays, ChevronDown, ClipboardList, FileText, Landmark, LayoutDashboard, LogOut, PanelLeftClose, PanelLeftOpen, Settings, ShieldCheck, SlidersHorizontal, Truck, Users, Utensils } from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { getAllEntityPermission } from "../api";
import LanguagePicker from "../components/LanguagePicker";
import { useI18n } from "../i18n";

const navItems = [
  { path: "/", key: "common.dashboard", exact: true },
  { path: "/mfa-setup", key: "common.mfa_setup" },
  { path: "/role_permissions", key: "common.role_permission_manager", adminOnly: true },
  { path: "/bank", key: "menu.bank" },
  { path: "/bank_account", key: "menu.bank_account" },
  { path: "/brand", key: "menu.brand" },
  { path: "/customer_supplier", key: "menu.customer_supplier" },
  { path: "/logistica/clientes", label: "Clientes", entityName: "customer_supplier", group: "CRM", groupIcon: "users", location: "sidebar", order: 10 },
  { path: "/logistica/contactos", label: "Contactos", entityName: "logistics_contact", group: "CRM", groupIcon: "users", location: "sidebar", order: 20 },
  { path: "/logistica/direcciones", label: "Direcciones", entityName: "logistics_address", group: "CRM", groupIcon: "users", location: "sidebar", order: 30 },
  { path: "/logistica/contratos", label: "Contratos", entityName: "logistics_contract", group: "CRM", groupIcon: "users", location: "sidebar", order: 40 },
  { path: "/logistica/tarifas", label: "Tarifas", entityName: "logistics_rate", group: "CRM", groupIcon: "users", location: "sidebar", order: 50 },
  { path: "/department", key: "menu.department" },
  { path: "/event_log", key: "menu.event_log" },
  { path: "/field", key: "menu.field" },
  { path: "/fiscal_account", key: "menu.fiscal_account" },
  { path: "/incident", key: "menu.incident" },
  { path: "/incident_detail", key: "menu.incident_detail" },
  { path: "/incident_type", key: "menu.incident_type" },
  { path: "/inventory", key: "menu.inventory", label: "Almacén", entityName: "product", group: "Inventario", groupIcon: "warehouse", location: "sidebar", order: 10 },
  { path: "/inventory_status", key: "menu.inventory_status" },
  { path: "/invoice", key: "menu.invoice" },
  { path: "/invoice/manual", key: "menu.manual_invoice", label: "Factura manual", entityName: "invoice" },
  { path: "/quotation", key: "menu.quotation", label: "Cotizaciones", entityName: "invoice", group: "CRM", groupIcon: "users", location: "sidebar", order: 60 },
  { path: "/authorization_tracking", key: "menu.authorization_tracking", label: "Autorización / Seguimiento", entityName: "invoice" },
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
  { path: "/appointments", key: "menu.appointment", label: "Calendario", entityName: "appointment", group: "Operaciones", groupIcon: "calendar-days", location: "sidebar", order: 75 },
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

const logisticsSections = [
  { key: "section_commercial", items: [["quotations", "cotizaciones", "logistics_quotation"], ["requests", "solicitudes", "logistics_service_request"], ["files", "expedientes", "logistics_file"]] },
  { key: "section_operations", items: [["trips", "viajes", "logistics_trip"], ["evidences", "evidencias", "logistics_evidence"], ["incidents", "incidencias", "logistics_incident"]] },
  { key: "section_fleet", items: [["units", "unidades"], ["trailers", "remolques"], ["operators", "operadores"], ["maintenance", "mantenimientos"]] },
  { key: "section_warehouse", items: [["warehouses", "almacenes"], ["locations", "ubicaciones"], ["inventory", "inventario"], ["racks", "racks"]] },
  { key: "section_finance", items: [["invoices", "facturas", "invoice"], ["branches", "sucursales", "logistics_branch"], ["receivables", "cuentas-cobrar", "logistics_receivable"], ["manual_invoice", "facturacion/manual", "invoice"]] },
  { key: "section_foreign_trade", items: [["suppliers", "proveedores", "customer_supplier"], ["shipments", "embarques", "logistics_shipment"]] },
  { key: "section_administration", items: [["users", "usuarios", "user"], ["roles", "roles", null, "admin"], ["audit", "auditoria", null, "technical"], ["security", "seguridad"]] }
];

const groupTranslationKeys = {
  "Bancos": "group_banks", CRM: "group_crm", "Contabilidad": "group_accounting",
  "Recursos humanos": "group_hr", Restaurante: "group_restaurant", Operaciones: "group_operations",
  Inventario: "group_inventory", "Configuración": "group_settings",
};

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
  "calendar-days": CalendarDays,
};

const defaultGroupIcons = {
  "Bancos": "landmark",
  "CRM": "users",
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => (
    window.matchMedia("(max-width: 800px)").matches || localStorage.getItem("tyakxa-sidebar-collapsed") === "true"
  ));
  const settingsRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const shellText = (key) => t(`shell.${key}`);
  const groupLabel = (label) => groupTranslationKeys[label] ? shellText(groupTranslationKeys[label]) : label;
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

  function canSeeLogisticsItem(item) {
    const entityName = item[2];
    if (item[3] === "admin") return isAdminUser;
    if (item[3] === "technical") return isBootstrapAdmin;
    return !entityName || isBootstrapAdmin || permissionByEntity.has(entityName);
  }

  function defaultGroup(item) {
    const path = item.path;
    if (["/bank", "/bank_account", "/movement"].includes(path)) return "Bancos";
    if (path.startsWith("/invoice") || path.startsWith("/fiscal") || path === "/quotation" || path === "/authorization_tracking") return "Contabilidad";
    if (path.startsWith("/payroll") || path === "/kronos") return "Recursos humanos";
    if (path.startsWith("/restaurant")) return "Restaurante";
    if (["/proyect", "/incident", "/incident_detail", "/task", "/task_note", "/task_type", "/service", "/template"].includes(path)) return "Operaciones";
    if (["/material", "/location", "/product", "/inventory_status", "/unit", "/brand"].includes(path)) return "Inventario";
    return "Configuración";
  }

  function navigationFor(item) {
    const entityName = item.entityName || String(item.path || "").replace(/^\//, "");
    const permission = permissionByEntity.get(entityName);
    const isCanonicalPath = item.path === `/${entityName}`;
    return {
      ...item,
      location: item.location || permission?.menu_location || (item.adminOnly ? "settings" : "sidebar"),
      group: item.group || permission?.menu_group || defaultGroup(item),
      groupIcon: item.groupIcon || permission?.menu_group_icon || defaultGroupIcons[item.group || permission?.menu_group || defaultGroup(item)] || "sliders-horizontal",
      order: Number(item.order ?? permission?.menu_order ?? 100),
      displayLabel: isCanonicalPath && permission?.menu_label ? permission.menu_label : item.key ? t(item.key, item.label || item.key) : item.label
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
  const logisticsIsActive = location.pathname.startsWith("/logistica");
  const logisticsIsOpen = openGroups.Logística ?? logisticsIsActive;
  return (
    <div className={sidebarCollapsed ? "shell sidebar-is-collapsed" : "shell"}>
      <aside className="sidebar" aria-label={shellText("main_navigation")}>
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
            return <button type="button" key={group.label} className="nav-link collapsed-group-button" title={groupLabel(group.label)} aria-label={`${shellText("expand_group")} ${groupLabel(group.label)}`} onClick={() => expandSidebarForGroup(group.label)}><GroupIcon size={20} /><span className="nav-link-label">{groupLabel(group.label)}</span></button>;
          }) : sidebarGroups.map((group) => {
            const isOpen = openGroups[group.label] ?? group.items.some((item) => location.pathname === item.path);
            return <div className="shell-nav-group" key={group.label}>
              <button type="button" className="shell-nav-group-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [group.label]: !isOpen }))}><span>{groupLabel(group.label)}</span><ChevronDown size={16} className={isOpen ? "open" : ""} /></button>
              {isOpen && <div className="shell-nav-submenu">{group.items.map((item) => <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><span className="dot" /><span className="nav-link-label">{item.displayLabel}</span></NavLink>)}</div>}
            </div>;
          })}
          {sidebarCollapsed ? (
            <button type="button" className="nav-link collapsed-group-button" title={shellText("group_logistics")} aria-label={`${shellText("expand_group")} ${shellText("group_logistics")}`} onClick={() => expandSidebarForGroup("Logística")}><Truck size={20} /><span className="nav-link-label">{shellText("group_logistics")}</span></button>
          ) : (
            <div className="shell-nav-group logistics-nav-group">
              <button type="button" className="shell-nav-group-toggle" onClick={() => setOpenGroups((current) => ({ ...current, Logística: !logisticsIsOpen }))}><span className="shell-nav-group-title">{shellText("group_logistics")}</span><ChevronDown size={16} className={logisticsIsOpen ? "open" : ""} /></button>
              {logisticsIsOpen && <div className="shell-nav-submenu logistics-nav-sections">{logisticsSections.map((section) => {
                const visibleItems = section.items.filter(canSeeLogisticsItem);
                const sectionKey = `Logística:${section.key}`;
                const sectionIsActive = visibleItems.some(([, path]) => location.pathname.startsWith(`/logistica/${path}`));
                const sectionIsOpen = openGroups[sectionKey] ?? sectionIsActive;
                if (visibleItems.length === 0) return null;
                return <div className="logistics-nav-section" key={section.key}>
                  <button type="button" className="logistics-nav-section-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [sectionKey]: !sectionIsOpen }))}><span>{shellText(section.key)}</span><ChevronDown size={14} className={sectionIsOpen ? "open" : ""} /></button>
                  {sectionIsOpen && <div className="logistics-nav-items">{visibleItems.map(([key, path]) => <NavLink key={path} to={`/logistica/${path}`} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><span className="dot" /><span className="nav-link-label">{shellText(key)}</span></NavLink>)}</div>}
                </div>;
              })}</div>}
            </div>
          )}
        </nav>
      </aside>
      <button type="button" className="sidebar-collapse-button" onClick={toggleSidebar} title={shellText(sidebarCollapsed ? "expand_menu" : "collapse_menu")} aria-label={shellText(sidebarCollapsed ? "expand_menu" : "collapse_menu")} aria-expanded={!sidebarCollapsed}>
        {sidebarCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
      </button>
      <main className="main">
        <header className="topbar">
          <div><p className="eyebrow">ERP · CRM · SCM</p><h1>TYAKXA</h1></div>
          <div className="topbar-actions">
            <span className="session-pill">{t("common.secure_session", "Sesión protegida")}{currentUser?.username ? ` · ${currentUser.username}` : ""}</span>
            <LanguagePicker />
            <div className="session-actions">
              <div className="settings-menu" ref={settingsRef}>
                <button className="button ghost settings-trigger" title={shellText("options")} aria-label={shellText("options")} aria-expanded={settingsOpen} onClick={() => setSettingsOpen((value) => !value)}><Settings size={18} /></button>
                {settingsOpen && <div className="settings-popover">{settingsItems.length ? settingsItems.map((item) => <NavLink key={item.path} to={item.path} onClick={() => setSettingsOpen(false)}>{item.displayLabel}</NavLink>) : <span className="settings-empty">{shellText("no_options")}</span>}</div>}
              </div>
              <button className="button ghost" onClick={handleLogout}><LogOut size={16} />{t("common.logout", "Cerrar sesión")}</button>
            </div>
          </div>
        </header>
        <nav className="quick-nav" aria-label={shellText("quick_access")}>
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
