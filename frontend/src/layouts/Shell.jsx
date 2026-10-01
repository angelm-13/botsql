import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Boxes, Briefcase, CalendarDays, ChevronDown, ClipboardList, Contact, FileText, FlaskConical, Landmark, LayoutDashboard, LogOut, Menu, PanelLeftClose, PanelLeftOpen, Receipt, Settings, ShieldCheck, ShoppingCart, SlidersHorizontal, Truck, UserCog, Users, Utensils, Warehouse } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { deploymentPlan, getMyPermissions } from "../api";
import { etiquetaParaMostrar, grupoParaMostrar } from "./etiquetasMenu.js";
import LanguagePicker from "../components/LanguagePicker";
import NotificationBell from "../components/NotificationBell";
import { useI18n } from "../i18n";
import { moduleSectionsEnPlan } from "./moduleSections";

const navItems = [
  { path: "/", key: "common.dashboard", exact: true },
  // Configuracion vivia repartida en tres sitios: MFA fijo arriba del menu,
  // Gestor de roles y Perfiles fijos en la barra superior (a mano, sin pasar
  // por el gestor de roles), y Usuarios/Departamentos/etc. en el menu
  // vertical. Encontrar una opcion era acordarse de cual de los tres la
  // tenia. Los tres entran ahora al engrane -la misma ubicacion que el gestor
  // de roles ya ofrece por rol y por entidad- junto con lo que la base tenga
  // agrupado como "Configuracion" (ver 20260903000000_configuracion_dentro_del_engrane.sql).
  { path: "/mfa-setup", key: "common.mfa_setup", group: "Configuracion", groupIcon: "settings", location: "settings", order: 910 },
  // Igual que /mfa-setup: cualquier usuario autenticado la necesita, sin
  // importar su rol -- no hay fila de entity_permission que la gatee, ver
  // el caso especial en canSeeNavItem.
  { path: "/change-password", key: "common.change_password", group: "Configuracion", groupIcon: "settings", location: "settings", order: 920 },
  { path: "/role_permissions", key: "common.role_permission_manager", adminOnly: true, groupIcon: "settings", location: "settings" },
  { path: "/kpi_permissions", key: "common.kpi_permission_manager", adminOnly: true, groupIcon: "settings", location: "settings" },
  { path: "/facturama-config", key: "menu.facturama_config", adminOnly: true, groupIcon: "settings", location: "settings" },
  { path: "/bank", key: "menu.bank" },
  { path: "/bank_account", key: "menu.bank_account" },
  { path: "/brand", key: "menu.brand" },
  { path: "/customer_supplier", key: "menu.customer_supplier" },
  { path: "/logistica/clientes", label: "Clientes", entityName: "customer_supplier", group: "CRM", groupIcon: "users", location: "sidebar", order: 10 },
  { path: "/logistica/direcciones", label: "Direcciones", entityName: "logistics_address", group: "CRM", groupIcon: "users", location: "sidebar", order: 30 },
  { path: "/logistica/contratos", label: "Contratos", entityName: "logistics_contract", group: "CRM", groupIcon: "users", location: "sidebar", order: 40 },
  { path: "/logistica/tarifas", label: "Tarifas", entityName: "logistics_rate", group: "CRM", groupIcon: "users", location: "sidebar", order: 50 },
  { path: "/department", key: "menu.department" },
  // Tecnica, solo la cuenta de arranque (ver `technicalPaths`). Sin fila en
  // `entity_permission` -es SOLO_ARRANQUE en el registro-, asi que sin
  // ubicacion explicita caia al valor por defecto ("sidebar") y quedaba en el
  // menu vertical pese al resto de Configuracion ya movido al engrane.
  { path: "/event_log", key: "menu.event_log", groupIcon: "settings", location: "settings" },
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
  // `/assets` no tiene entrada de menu propia: se llega desde una pieza en
  // Localizar. Las dos pantallas se parecian en el menu -ambas listaban piezas
  // con su estado- aunque hacen cosas distintas: Localizar busca cualquier cosa
  // del almacen, y esta ejecuta las transiciones de estado de una pieza. Dos
  // puertas que parecen la misma obligan a probar cual sirve.
  { path: "/assets", key: "menu.assets", label: "Rastreo de piezas", entityName: "product", location: "none" },
  { path: "/inventory_status", key: "menu.inventory_status" },
  { path: "/invoice", key: "menu.invoice" },
  { path: "/invoice/manual", key: "menu.manual_invoice", label: "Factura manual", entityName: "invoice" },
  { path: "/quotation", key: "menu.quotation", label: "Cotizaciones", entityName: "invoice", group: "CRM", groupIcon: "users", location: "sidebar", order: 60 },
  { path: "/authorization_tracking", key: "menu.authorization_tracking", label: "Autorización / Seguimiento", entityName: "invoice" },
  { path: "/level", key: "menu.level" },
  { path: "/location", key: "menu.location" },
  { path: "/location_type", key: "menu.location_type" },
  { path: "/material", key: "menu.material" },
  { path: "/nm_incident_product", key: "menu.nm_incident_product" },
  // El vale se guarda con la capacidad y no con una entidad: su pantalla
  // escribe en `incident` y en `nm_incident_product`, y esa segunda esta
  // fuera del menu a proposito, por ser tabla puente. La etiqueta, el grupo
  // y el orden los da la fila de la capacidad en el backend.
  //
  // Dos capacidades abren la misma puerta y nunca las tiene el mismo rol:
  // `warehouse_voucher` (Almacenista, surte) y `warehouse_prevoucher`
  // (Supervisor, solo pide un borrador). Con una sola clave aqui, Supervisor
  // se quedaba sin entrada de menu -tenia el permiso en la base, pero la
  // pantalla nunca aparecia para llegar a usarlo.
  { path: "/vouchers", key: "menu.warehouse_voucher", label: "Vales de almacén", entityName: ["warehouse_voucher", "warehouse_prevoucher"] },
  { path: "/activity-log", key: "menu.daily_activity_log", label: "Bitácora diaria", entityName: "daily_activity_log", group: "Operaciones", groupIcon: "operations", location: "sidebar", order: 78 },
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
  { path: "/permission", key: "menu.permission", groupIcon: "settings", location: "settings" },
  { path: "/team", key: "menu.team", groupIcon: "settings", location: "settings" },
  { path: "/product", key: "menu.product" },
  { path: "/product_family", key: "menu.product_family" },
  { path: "/proyect", key: "menu.proyect" },
  { path: "/appointments", key: "menu.appointment", label: "Calendario", entityName: "appointment", group: "Operaciones", groupIcon: "calendar-days", location: "sidebar", order: 75 },
  { path: "/documents", label: "Documentos", entityName: "document", group: "Laboratorio", groupIcon: "file-text", location: "sidebar", order: 10 },
  { path: "/laboratory", label: "Equipos y ordenes", entityName: "laboratory_service_order", group: "Laboratorio", groupIcon: "clipboard-list", location: "sidebar", order: 20 },
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
  // Misma razon que /event_log: tecnica, sin fila propia, caia al menu
  // vertical por defecto. No confundir con /mfa-setup ("Configurar MFA"),
  // la pantalla donde el propio usuario activa su MFA -esta es la de
  // administracion, para ver el estado de MFA de otros usuarios.
  { path: "/user_mfa", key: "menu.user_mfa", groupIcon: "settings", location: "settings" }
];


const groupTranslationKeys = {
  "Bancos": "group_banks", CRM: "group_crm", "Contabilidad": "group_accounting",
  "Recursos humanos": "group_hr", Restaurante: "group_restaurant", Operaciones: "group_operations",
  Inventario: "group_inventory", "Configuración": "group_settings",
  Laboratorio: "group_laboratory", "Punto de venta": "group_pos", "Logística": "group_logistics",
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

  // Modulos llegados con tny_docs. Sin registrarlos aqui caen en el icono por
  // omision y en silencio, que es como el menu acabo mostrando el mismo dibujo
  // en casi todos los grupos.
  "documentos": FileText,
  "laboratorio": FlaskConical,
  // `file-text` ya esta arriba, con los demas nombres de lucide. Repetirlo aqui
  // no hacia dano -apunta al mismo icono- pero era una clave duplicada en un
  // objeto, que Vite avisaba en cada arranque y que la proxima vez podia
  // repetirse apuntando a otro icono y ganar en silencio.
  "flask-conical": FlaskConical,
};

const defaultGroupIcons = {
  "Bancos": "landmark",
  "CRM": "crm",
  "Contabilidad": "file-text",
  "Recursos humanos": "hr",
  "Restaurante": "utensils",
  "Operaciones": "clipboard-list",
  "Inventario": "inventory",
  "Laboratorio": "clipboard-list",
  "Configuración": "sliders-horizontal",
  "Punto de venta": "shopping-cart",
  "Logística": "truck",
};

export default function Shell() {
  const [, forceRender] = useState(0);
  const [roleEntityPermissions, setRoleEntityPermissions] = useState([]);
  const [rolePermissionsLoaded, setRolePermissionsLoaded] = useState(false);
  const [openGroups, setOpenGroups] = useState({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Los modulos que el cliente compro. Vacio hasta que responde el servidor;
  // mientras tanto se muestran todos, porque un menu que aparece a trozos se
  // lee como un sistema roto y el backend niega igual lo que no este en el plan.
  const [modulosDelPlan, setModulosDelPlan] = useState([]);
  // Nombre o abreviacion del cliente (DEPLOYMENT_LABEL / TYAKXA_PLAN en el
  // servidor). Sin esto, todas las instalaciones se ven identicas y es facil
  // operar la del cliente equivocado por error -el motivo real de agregarlo,
  // no solo cosmetico.
  const [clienteDelPlan, setClienteDelPlan] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => (
    window.matchMedia("(max-width: 800px)").matches || localStorage.getItem("tyakxa-sidebar-collapsed") === "true"
  ));
  // Menu de hamburguesa para media pantalla o menos. Independiente de
  // `sidebarCollapsed` -ese es el colapsado a iconos del escritorio- porque
  // aqui el menu entero se oculta y aparece como panel encima del contenido,
  // no como una version angosta de si mismo.
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const settingsRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const shellText = (key) => t(`shell.${key}`);
  // El grupo viene de la base sin acento ("Facturacion"): se acentua solo para
  // mostrarlo, la llave con la que se agrupa no cambia (ver etiquetasMenu.js).
  const groupLabel = (label) => {
    const visible = grupoParaMostrar(label);
    return groupTranslationKeys[visible] ? shellText(groupTranslationKeys[visible]) : visible;
  };
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
    // `/security/my-permissions` y no la tabla cruda de `entity_permission`.
    //
    // La tabla cruda no sabe del PLAN: devuelve las filas de todos los modulos,
    // comprados o no, y el menu se armaba con ellas. Por eso, con logistica y
    // punto de venta apagados por licencia, sus apartados si desaparecian
    // -esos dos declaran su modulo en `moduleSections.js` y ahi hay un filtro-
    // pero Restaurante y Laboratorio seguian en el menu: sus grupos se arman
    // desde `menu_group` de estas filas, donde no habia filtro ninguno.
    //
    // Este endpoint ya trae las filas del rol Y filtradas por el plan
    // (`entidad_habilitada` en `routes/security.py`), asi que el menu deja de
    // nombrar modulos que este despliegue no tiene.
    getMyPermissions()
      .then((payload) => {
        const rows = Array.isArray(payload?.entity_permissions)
          ? payload.entity_permissions : [];
        if (mounted) setRoleEntityPermissions(rows.filter((row) => Number(row.id_permission) === roleId && (
          Number(row.scope_create || 0) > 0 || Number(row.scope_read || 0) > 0 ||
          Number(row.scope_update || 0) > 0 || Number(row.scope_delete || 0) > 0
        )));
      })
      .catch(() => { if (mounted) setRoleEntityPermissions([]); })
      .finally(() => { if (mounted) setRolePermissionsLoaded(true); });
    return () => { mounted = false; };
  }, [currentUser?.id_permission, isBootstrapAdmin]);

  useEffect(() => {
    let vigente = true;
    deploymentPlan()
      .then((plan) => {
        if (!vigente) return;
        setModulosDelPlan(plan?.modulos || []);
        setClienteDelPlan(String(plan?.cliente || "").trim());
      })
      // Si no se puede leer el plan no se esconde nada: el backend sigue
      // negando lo que no corresponde.
      .catch(() => {});
    return () => { vigente = false; };
  }, []);

  useEffect(() => {
    // El titulo de la pestana es lo primero que se ve al elegir entre varias
    // abiertas -el momento real en que se opera el cliente equivocado por
    // error-, asi que es donde mas rinde poner el nombre.
    document.title = clienteDelPlan ? `TYAKXA · ${clienteDelPlan}` : "TYAKXA";
  }, [clienteDelPlan]);

  useEffect(() => {
    function cerrarEngrane(evento) {
      if (settingsRef.current && !settingsRef.current.contains(evento.target)) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener("mousedown", cerrarEngrane);
    return () => document.removeEventListener("mousedown", cerrarEngrane);
  }, []);

  // Elegir un modulo cierra el panel movil. Sin esto el menu se quedaba
  // abierto tapando la pantalla despues de navegar.
  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  // `item.entityName` normalmente es una sola clave, pero una pantalla que
  // comparten dos roles sin capacidad en comun -como `/vouchers`, entre
  // Almacenista y Supervisor- necesita aceptar CUALQUIERA de varias.
  function entityNamesFor(item) {
    if (Array.isArray(item.entityName)) return item.entityName;
    return [item.entityName || String(item.path || "").replace(/^\//, "")];
  }

  // `item.entityName` normalmente es una sola clave, pero una pantalla que
  // comparten dos roles sin capacidad en comun -como `/vouchers`, entre
  // Almacenista y Supervisor- necesita aceptar CUALQUIERA de varias.
  function entityNamesFor(item) {
    if (Array.isArray(item.entityName)) return item.entityName;
    return [item.entityName || String(item.path || "").replace(/^\//, "")];
  }

  function canSeeNavItem(item) {
    if (item.exact || item.path === "/mfa-setup" || item.path === "/change-password") return true;
    if (technicalPaths.includes(item.path)) return isBootstrapAdmin;
    if (item.adminOnly) return isAdminUser;
    if (isBootstrapAdmin) return true;
    if (!rolePermissionsLoaded) return false;
    const entityNames = entityNamesFor(item);
    return roleEntityPermissions.some((row) => entityNames.includes(String(row.entity_name || "")));
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
    if (["/bank", "/bank_account"].includes(path)) return "Bancos";
    if (path.startsWith("/invoice") || path.startsWith("/fiscal") || path === "/quotation" || path === "/authorization_tracking" || path === "/ticket") return "Contabilidad";
    if (path.startsWith("/payroll") || path === "/kronos") return "Recursos humanos";
    if (path.startsWith("/restaurant")) return "Restaurante";
    if (path.startsWith("/pos")) return "Punto de venta";
    if (path.startsWith("/logistics")) return "Logística";
    // Documentos y Laboratorio comparten un solo apartado de menu por ahora
    // (ver el `group: "Laboratorio"` explicito en /documents y /laboratory
    // en navItems); este fallback replica esa misma decision para que una
    // entidad nueva de cualquiera de los dos modulos no caiga en Configuracion.
    if (path.startsWith("/document") || path.startsWith("/laboratory")) return "Laboratorio";
    if (["/proyect", "/incident", "/incident_detail", "/task", "/task_note", "/task_type", "/service", "/template"].includes(path)) return "Operaciones";
    if (["/material", "/location", "/product", "/inventory_status", "/unit", "/brand", "/vouchers"].includes(path)) return "Inventario";
    if (["/customer_supplier", "/survey_question", "/survey_multiple_answer", "/nm_survey_user", "/appointment", "/appointments", "/product_sale_config", "/public_api_key"].includes(path)) return "CRM";
    return "Configuración";
  }

  function navigationFor(item) {
    const entityNames = entityNamesFor(item);
    // Con varias claves, se usa la fila del actor -quien la tenga concedida-
    // para menu_group/menu_order/etc.; si no tiene ninguna (no deberia pasar,
    // ya filtro `canSeeNavItem`) cae a la primera para no romper el layout.
    const entityName = entityNames.find((nombre) => permissionByEntity.has(nombre)) || entityNames[0];
    const permission = permissionByEntity.get(entityName);
    const isCanonicalPath = entityNames.length === 1 && item.path === `/${entityName}`;
    return {
      ...item,
      location: item.location || permission?.menu_location || (item.adminOnly ? "settings" : "sidebar"),
      group: item.group || permission?.menu_group || defaultGroup(item),
      groupIcon: item.groupIcon || permission?.menu_group_icon || defaultGroupIcons[item.group || permission?.menu_group || defaultGroup(item)] || "sliders-horizontal",
      order: Number(item.order ?? permission?.menu_order ?? 100),
      displayLabel: etiquetaParaMostrar(isCanonicalPath && permission?.menu_label ? permission.menu_label : item.key ? t(item.key, item.label || item.key) : item.label)
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
  // Lo que el gestor de roles marco como "Engrane" en la columna UBICACION.
  // Es una ubicacion configurable por rol y por entidad, no un cajon de sastre:
  // el gestor ofrece Menu vertical / Engrane / No mostrar, y esta es la segunda.
  const settingsItems = configuredItems
    .filter((item) => item.location === "settings")
    .sort((a, b) => a.order - b.order || a.displayLabel.localeCompare(b.displayLabel));
  const sidebarGroups = useMemo(() => {
    const groups = new Map();
    // Se acepta cualquier ubicacion que no sea el menu oculto: el engrane que
    // recogia "settings" ya no existe, y una entrada sin puerta es peor que una
    // mal colocada -no se ve y nadie se entera de que falta-.
    // Solo el menu vertical. Lo marcado como "settings" va al engrane y lo
    // marcado como "topbar" a los botones de al lado: si esto aceptara todo lo
    // que no fuera "none", cada entrada saldria en dos sitios.
    configuredItems.filter((item) => item.location === "sidebar").forEach((item) => {
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
  // El panel movil siempre muestra el menu completo (con etiquetas y grupos
  // expandibles), nunca la version a iconos del escritorio: son dos botones
  // distintos y uno no debe determinar como se ve el otro.
  const showCompactSidebar = sidebarCollapsed && !mobileNavOpen;
  const shellClassName = [
    "shell",
    showCompactSidebar ? "sidebar-is-collapsed" : "",
    mobileNavOpen ? "mobile-nav-open" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className={shellClassName}>
      {/* Solo se ve en media pantalla o menos (ver app.css). En escritorio el
          sidebar de siempre sigue igual, con su propio boton de colapsar. */}
      <div className="mobile-topbar">
        <button
          type="button"
          className="mobile-menu-button"
          onClick={() => setMobileNavOpen(true)}
          aria-label={shellText("open_menu")}
          aria-expanded={mobileNavOpen}
        >
          <Menu size={22} />
        </button>
        <img src="/tyakxa-logo.png" alt={t("common.app_title")} className="mobile-topbar-logo" />
      </div>
      {mobileNavOpen && (
        <div className="mobile-nav-backdrop" onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
      )}
      <aside className="sidebar" aria-label={shellText("main_navigation")}>
        <div className="sidebar-brand-row">
          <div className="brand"><img src="/tyakxa-logo.png" alt={t("common.app_title")} className="brand-logo" /><span>{t("common.app_title")}</span></div>
        </div>
        <nav className="nav">
          {!showCompactSidebar && fixedSidebarItems.map((item, index) => (
            <NavLink key={item.path} to={item.path} end={item.exact} title={showCompactSidebar ? t(item.key, item.label || item.key) : undefined} aria-label={t(item.key, item.label || item.key)} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              {index === 0 ? <LayoutDashboard size={18} /> : item.path === "/mfa-setup" ? <ShieldCheck size={18} /> : <span className="dot" />}
              <span className="nav-link-label">{t(item.key, item.label || item.key)}</span>
            </NavLink>
          ))}
          {showCompactSidebar ? sidebarGroups.map((group) => {
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
            // Un modulo con entidades propias declaradas (hoy solo Logistica)
            // necesita al menos una concedida de verdad para pintarse. Sin
            // esto, Almacen/Facturas/Proveedores -que piden prestadas
            // `product`/`invoice`/`customer_supplier` para no duplicar
            // pantalla- sostenian el encabezado "Logistica" para cualquier
            // rol con Inventario, Facturacion o CRM, que es casi cualquier
            // rol, y no habia checkbox en el Gestor de roles que lo apagara:
            // nada de lo que lo sostenia era, en los hechos, de logistica.
            if (modulo.entidadesPropias && !isBootstrapAdmin
              && !modulo.entidadesPropias.some((entidad) => permissionByEntity.has(entidad))) {
              return null;
            }
            const seccionesVisibles = modulo.sections
              .map((seccion) => ({ ...seccion, items: seccion.items.filter(canSeeSectionItem) }))
              .filter((seccion) => seccion.items.length > 0);
            // Un modulo sin una sola entrada visible no se pinta. Antes el
            // encabezado de Logistica salia siempre, asi que un rol sin acceso
            // veia un grupo que al abrirlo estaba vacio.
            if (seccionesVisibles.length === 0) return null;
            const abierto = moduleIsOpen(modulo);
            const ModuleIcon = groupIcons[modulo.icon] || SlidersHorizontal;

            if (showCompactSidebar) {
              return <button type="button" key={modulo.key} className="nav-link collapsed-group-button" title={shellText(modulo.titleKey)} aria-label={`${shellText("expand_group")} ${shellText(modulo.titleKey)}`} onClick={() => expandSidebarForGroup(modulo.key)}><ModuleIcon size={20} /><span className="nav-link-label">{shellText(modulo.titleKey)}</span></button>;
            }

            return <div className="shell-nav-group logistics-nav-group" key={modulo.key}>
              <button type="button" className="shell-nav-group-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [modulo.key]: !abierto }))}><ModuleIcon size={18} className="shell-nav-group-icon" /><span className="shell-nav-group-title">{shellText(modulo.titleKey)}</span><ChevronDown size={16} className={abierto ? "open" : ""} /></button>
              {abierto && <div className="shell-nav-submenu logistics-nav-sections">{seccionesVisibles.map((seccion) => {
                const claveSeccion = `${modulo.key}:${seccion.key}`;
                // Una ruta que empieza por "/" es ABSOLUTA y no cuelga del modulo.
                // Hace falta para que un apartado de un vertical pueda apuntar
                // al almacen del nucleo: un solo almacen para los cuatro
                // proyectos, en lugar de uno por vertical.
                const rutaDe = (ruta) => (String(ruta).startsWith("/")
                  ? String(ruta)
                  : `${modulo.basePath}/${ruta}`);
                const seccionActiva = seccion.items.some(([, ruta]) => location.pathname.startsWith(rutaDe(ruta)));
                const seccionAbierta = openGroups[claveSeccion] ?? seccionActiva;
                return <div className="logistics-nav-section" key={seccion.key}>
                  <button type="button" className="logistics-nav-section-toggle" onClick={() => setOpenGroups((current) => ({ ...current, [claveSeccion]: !seccionAbierta }))}><span>{shellText(seccion.key)}</span><ChevronDown size={14} className={seccionAbierta ? "open" : ""} /></button>
                  {seccionAbierta && <div className="logistics-nav-items">{seccion.items.map(([clave, ruta]) => <NavLink key={ruta} to={rutaDe(ruta)} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><span className="dot" /><span className="nav-link-label">{shellText(clave)}</span></NavLink>)}</div>}
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
          <div>
            <p className="eyebrow">ERP · CRM · SCM</p>
            <div className="brand-title-row">
              <h1>TYAKXA</h1>
              {/* De que cliente es esta instancia -DEPLOYMENT_LABEL en el
                  servidor-. Todas las instalaciones se ven identicas sin
                  esto, y es facil operar la del cliente equivocado por error;
                  el cliente lo ve tambien, es el nombre de su propia empresa. */}
              {clienteDelPlan && <span className="deployment-badge">{clienteDelPlan}</span>}
            </div>
          </div>
          <div className="topbar-actions">
            <span className="session-pill">{t("common.secure_session", "Sesión protegida")}{currentUser?.username ? ` · ${currentUser.username}` : ""}</span>
            <NotificationBell />
            <LanguagePicker />
            {/* El engrane. Se pinta aunque este vacio: es una ubicacion que el
                gestor de roles ofrece, y si desapareciera al no tener nada
                dentro, quien acaba de mandar una pantalla ahi creeria que no se
                guardo. Vacio lo dice con palabras. */}
            <div className="settings-menu" ref={settingsRef}>
              <button
                className="button ghost settings-trigger"
                title={shellText("options")}
                aria-label={shellText("options")}
                aria-expanded={settingsOpen}
                onClick={() => setSettingsOpen((valor) => !valor)}
              >
                <Settings size={18} />
              </button>
              {settingsOpen && (
                <div className="settings-popover">
                  {settingsItems.length ? settingsItems.map((item) => {
                    // El icono del grupo al que la entidad quedo asignada, para
                    // que el engrane se lea igual que el menu vertical.
                    const ItemIcon = groupIcons[item.groupIcon] || SlidersHorizontal;
                    return (
                      <NavLink key={item.path} to={item.path} onClick={() => setSettingsOpen(false)}>
                        <ItemIcon size={16} />
                        <span>{item.displayLabel}</span>
                      </NavLink>
                    );
                  }) : <span className="settings-empty">{shellText("no_options")}</span>}
                </div>
              )}
            </div>

            {topbarItems.length > 0 && (
              <div className="topbar-links">
                {topbarItems.map((item) => {
                  // El icono sale del grupo de la entidad, igual que en el menu
                  // vertical y en el engrane. Antes estaba escrito a mano por
                  // ruta, asi que una entrada nueva en la barra salia sin icono
                  // hasta que alguien se acordara de este archivo.
                  const ItemIcon = groupIcons[item.groupIcon] || SlidersHorizontal;
                  return (
                    <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "button ghost active" : "button ghost"}>
                      <ItemIcon size={16} />
                      <span>{item.displayLabel}</span>
                    </NavLink>
                  );
                })}
              </div>
            )}
            <div className="session-actions">
              <button className="button ghost" onClick={handleLogout}><LogOut size={16} />{t("common.logout", "Cerrar sesión")}</button>
            </div>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
