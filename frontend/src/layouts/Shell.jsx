import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Boxes, Briefcase, CalendarDays, ChevronDown, ClipboardList, Contact, FileText, Landmark, LayoutDashboard, LogOut, PanelLeftClose, PanelLeftOpen, Receipt, Settings, ShieldCheck, ShoppingCart, SlidersHorizontal, Truck, UserCog, Users, Utensils, Warehouse } from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { deploymentPlan, getAllEntityPermission } from "../api";
import LanguagePicker from "../components/LanguagePicker";
import { useI18n } from "../i18n";
import { moduleSectionsEnPlan } from "./moduleSections";

const navItems = [
  { path: "/", key: "common.dashboard", exact: true },
  // Los dos vivian aparte: MFA fijo arriba del menu y Permisos por rol dentro
  // del engrane del encabezado. Con tres sitios distintos donde configurar
  // cosas, encontrar una opcion era cuestion de acordarse de cual de los tres.
  // Ahora los dos entran en Configuracion como cualquier otra pantalla.
  { path: "/mfa-setup", key: "common.mfa_setup", group: "Configuracion", groupIcon: "settings", location: "sidebar", order: 910 },
  { path: "/role_permissions", key: "common.role_permission_manager", adminOnly: true, location: "topbar" },
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
  // Rastreo pieza por pieza. Va junto al almacen y con la misma entidad, para
  // que dar acceso al inventario lo arrastre sin un permiso nuevo que alguien
  // tenga que acordarse de conceder.
  { path: "/inventory/trace", key: "menu.inventory_trace", label: "Localizar", entityName: "product", group: "Inventario", groupIcon: "inventory", location: "sidebar", order: 12 },
  { path: "/assets", key: "menu.assets", label: "Rastreo de piezas", entityName: "product", group: "Inventario", groupIcon: "warehouse", location: "sidebar", order: 15 },
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
  { path: "/permission", key: "menu.permission", location: "topbar" },
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


const groupTranslationKeys = {
  "Bancos": "group_banks", CRM: "group_crm", "Contabilidad": "group_accounting",
  "Recursos humanos": "group_hr", Restaurante: "group_restaurant", Operaciones: "group_operations",
  Inventario: "group_inventory", "Configuración": "group_settings",
};

const groupIcons = {
  // Los nombres de esta tabla no son decorativos: son los que vienen en
  // `entity_permission.menu_group_icon` y en `groupIcon` de las entradas fijas.
  // Un nombre que no este aqui cae en `SlidersHorizontal`, y como cae en
  // silencio, la medicion fue que casi todo el menu mostraba el mismo icono de
  // ajustes: de once nombres que la base envia -crm, billing, inventory, pos,
  // hr, operations, restaurant, security, briefcase-business...- solo `settings`
  // y `truck` estaban registrados. Al agregar un modulo hay que agregar su
  // nombre aqui tambien.
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
  "truck": Truck,
  "shopping-cart": ShoppingCart,

  // Nombres que manda el backend en `menu_group_icon`.
  "crm": Users,
  "billing": Receipt,
  "inventory": Warehouse,
  "warehouse": Warehouse,
  "pos": ShoppingCart,
  // Personal y clientes no comparten icono a proposito: son los dos grupos de
  // "gente" del menu y con el mismo dibujo se confunden de un vistazo.
  "hr": UserCog,
  "operations": ClipboardList,
  "briefcase-business": Briefcase,
  "restaurant": Utensils,
  "security": ShieldCheck,
  "contact": Contact,
};

const defaultGroupIcons = {
  "Bancos": "landmark",
  "CRM": "crm",
  "Contabilidad": "file-text",
  "Recursos humanos": "hr",
  "Restaurante": "utensils",
  "Operaciones": "clipboard-list",
  "Inventario": "inventory",
  "Configuración": "sliders-horizontal",
};

export default function Shell() {
  const [, forceRender] = useState(0);
  const [roleEntityPermissions, setRoleEntityPermissions] = useState([]);
  const [rolePermissionsLoaded, setRolePermissionsLoaded] = useState(false);
  const [openGroups, setOpenGroups] = useState({});
  // Los modulos que el cliente compro. Vacio hasta que responde el servidor;
  // mientras tanto se muestran todos, porque un menu que aparece a trozos se
  // lee como un sistema roto y el backend niega igual lo que no este en el plan.
  const [modulosDelPlan, setModulosDelPlan] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => (
    window.matchMedia("(max-width: 800px)").matches || localStorage.getItem("tyakxa-sidebar-collapsed") === "true"
  ));
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

  useEffect(() => {
    let vigente = true;
    deploymentPlan()
      .then((plan) => { if (vigente) setModulosDelPlan(plan?.modulos || []); })
      // Si no se puede leer el plan no se esconde nada: el backend sigue
      // negando lo que no corresponde.
      .catch(() => {});
    return () => { vigente = false; };
  }, []);

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

  function canSeeSectionItem(item) {
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

  const fixedSidebarItems = visibleNavItems.filter((item) => item.exact);
  const configuredItems = visibleNavItems.filter((item) => !item.exact).map(navigationFor);
  // Gestion de roles y perfiles viven arriba, no en el menu. Son de
  // administracion y se usan poco, pero cuando se usan se buscan; tenerlos
  // fijos en la barra evita recorrer el menu entero. Se filtran del menu para
  // que no queden en dos sitios: dos puertas a la misma pantalla es como
  // empieza a haber dos formas distintas de hacer lo mismo.
  const topbarItems = configuredItems.filter((item) => item.location === "topbar");
  const sidebarGroups = useMemo(() => {
    const groups = new Map();
    // Se acepta cualquier ubicacion que no sea el menu oculto: el engrane que
    // recogia "settings" ya no existe, y una entrada sin puerta es peor que una
    // mal colocada -no se ve y nadie se entera de que falta-.
    configuredItems.filter((item) => item.location !== "none" && item.location !== "hidden"
      && item.location !== "topbar").forEach((item) => {
      if (!groups.has(item.group)) groups.set(item.group, { icon: item.groupIcon, items: [] });
      groups.get(item.group).items.push(item);
    });
    // Los grupos se ordenan por el `menu_order` mas bajo que contienen, no por
    // cual se creo primero. Con el orden de creacion, mover una pantalla de
    // sitio movia su grupo entero: al pasar MFA a Configuracion, Configuracion
    // salto al principio del menu solo porque MFA esta arriba en la lista.
    return [...groups.entries()]
      .map(([label, group]) => ({
        label,
        icon: group.icon,
        items: group.items.sort((a, b) => a.order - b.order || a.displayLabel.localeCompare(b.displayLabel)),
      }))
      .sort((a, b) => Math.min(...a.items.map((i) => i.order)) - Math.min(...b.items.map((i) => i.order))
        || a.label.localeCompare(b.label));
  }, [configuredItems]);

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
  // Un modulo con secciones se abre solo si la ruta actual esta dentro de el.
  function moduleIsOpen(modulo) {
    return openGroups[modulo.key] ?? location.pathname.startsWith(modulo.basePath);
  }
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
            // El icono se pinta tambien con el menu abierto. Antes solo salia
            // al colapsar, asi que Dashboard y Configurar MFA llevaban icono y
            // todos los grupos de abajo eran texto pelado: la lista se leia
            // como dos menus distintos pegados.
            const GroupIcon = groupIcons[group.icon] || SlidersHorizontal;
            return <div className="shell-nav-group" key={group.label}>
              <button type="button" className="shell-nav-group-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [group.label]: !isOpen }))}><GroupIcon size={18} className="shell-nav-group-icon" /><span>{groupLabel(group.label)}</span><ChevronDown size={16} className={isOpen ? "open" : ""} /></button>
              {isOpen && <div className="shell-nav-submenu">{group.items.map((item) => <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><span className="dot" /><span className="nav-link-label">{item.displayLabel}</span></NavLink>)}</div>}
            </div>;
          })}
          {/* Modulos con menu de dos niveles. La estructura vive en
              moduleSections.js; aqui solo se pinta, de modo que agregar un
              modulo con secciones no vuelve a significar copiar este bloque. */}
          {moduleSectionsEnPlan(modulosDelPlan).map((modulo) => {
            const seccionesVisibles = modulo.sections
              .map((seccion) => ({ ...seccion, items: seccion.items.filter(canSeeSectionItem) }))
              .filter((seccion) => seccion.items.length > 0);
            // Un modulo sin una sola entrada visible no se pinta. Antes el
            // encabezado de Logistica salia siempre, asi que un rol sin acceso
            // veia un grupo que al abrirlo estaba vacio.
            if (seccionesVisibles.length === 0) return null;
            const abierto = moduleIsOpen(modulo);
            const ModuleIcon = groupIcons[modulo.icon] || SlidersHorizontal;

            if (sidebarCollapsed) {
              return <button type="button" key={modulo.key} className="nav-link collapsed-group-button" title={shellText(modulo.titleKey)} aria-label={`${shellText("expand_group")} ${shellText(modulo.titleKey)}`} onClick={() => expandSidebarForGroup(modulo.key)}><ModuleIcon size={20} /><span className="nav-link-label">{shellText(modulo.titleKey)}</span></button>;
            }

            return <div className="shell-nav-group logistics-nav-group" key={modulo.key}>
              <button type="button" className="shell-nav-group-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [modulo.key]: !abierto }))}><ModuleIcon size={18} className="shell-nav-group-icon" /><span className="shell-nav-group-title">{shellText(modulo.titleKey)}</span><ChevronDown size={16} className={abierto ? "open" : ""} /></button>
              {abierto && <div className="shell-nav-submenu logistics-nav-sections">{seccionesVisibles.map((seccion) => {
                const claveSeccion = `${modulo.key}:${seccion.key}`;
                const seccionActiva = seccion.items.some(([, ruta]) => location.pathname.startsWith(`${modulo.basePath}/${ruta}`));
                const seccionAbierta = openGroups[claveSeccion] ?? seccionActiva;
                return <div className="logistics-nav-section" key={seccion.key}>
                  <button type="button" className="logistics-nav-section-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [claveSeccion]: !seccionAbierta }))}><span>{shellText(seccion.key)}</span><ChevronDown size={14} className={seccionAbierta ? "open" : ""} /></button>
                  {seccionAbierta && <div className="logistics-nav-items">{seccion.items.map(([clave, ruta]) => <NavLink key={ruta} to={`${modulo.basePath}/${ruta}`} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><span className="dot" /><span className="nav-link-label">{shellText(clave)}</span></NavLink>)}</div>}
                </div>;
              })}</div>}
            </div>;
          })}
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
            {topbarItems.length > 0 && (
              <div className="topbar-links">
                {topbarItems.map((item) => (
                  <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "button ghost active" : "button ghost"}>
                    {item.path === "/role_permissions" ? <ShieldCheck size={16} /> : <UserCog size={16} />}
                    <span>{item.displayLabel}</span>
                  </NavLink>
                ))}
              </div>
            )}
            <div className="session-actions">
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
