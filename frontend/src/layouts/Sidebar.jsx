import { NavLink, useNavigate } from "react-router-dom";
import { ChevronDown, LogOut } from "lucide-react";
import { useState, useEffect } from "react";
import { useI18n } from "../i18n";

export default function Sidebar() {
  const navigate = useNavigate();
  const [openGroup, setOpenGroup] = useState(null);
  const { lang, t, setLanguage } = useI18n();
  
  const groups = [
    {
      key: "bank",
      label: t("menu.group.bank", "BANK"),
      items: [
          { path: "/bank_account", labelKey: "menu.bank_account" },
          { path: "/movement", labelKey: "menu.movement" }
      ]
    },
    {
      key: "fiscal",
      label: t("menu.group.fiscal", "FISCAL"),
      items: [
          { path: "/invoice", labelKey: "menu.invoice" },
          { path: "/invoice/manual", labelKey: "menu.manual_invoice", label: "Factura manual" },
          { path: "/fiscal_account", labelKey: "menu.fiscal_account" }
      ]
    },
    {
      key: "hr",
      label: t("menu.group.hr", "HR"),
      items: [
          { path: "/payroll_period", labelKey: "menu.payroll_period" },
          { path: "/payroll_detail", labelKey: "menu.payroll_detail" },
          { path: "/payroll_concept", labelKey: "menu.payroll_concept" },
          { path: "/payroll_movement", labelKey: "menu.payroll_movement" }
      ]
    },
    {
      key: "prod",
      label: t("menu.group.prod", "PROD"),
      items: [
          { path: "/proyect", labelKey: "menu.proyect" },
          { path: "/incident", labelKey: "menu.incident" },
          { path: "/incident_detail", labelKey: "menu.incident_detail" },
          { path: "/nm_incident_product", labelKey: "menu.nm_incident_product" },
          { path: "/task", labelKey: "menu.task" },
          { path: "/task_note", labelKey: "menu.task_note" },
          { path: "/service", labelKey: "menu.service" },
          { path: "/template", labelKey: "menu.template" },
          { path: "/nm_template_task", labelKey: "menu.nm_template_task" }
      ]
    },
    {
      key: "settings",
      label: t("menu.group.settings", "SETTINGS"),
      items: [
          { path: "/department", labelKey: "menu.department" },
          { path: "/subdepartment", labelKey: "menu.subdepartment" },
          { path: "/task_type", labelKey: "menu.task_type" }
      ]
    },
    {
      key: "warehouse",
      label: t("menu.group.warehouse", "WAREHOUSE"),
      items: [
          { path: "/material", labelKey: "menu.material" },
          { path: "/location", labelKey: "menu.location" },
          { path: "/product", labelKey: "menu.product" }
      ]
    },
    {
      key: "web_catalog",
      label: t("menu.group.web_catalog", "WEB_CATALOG"),
      items: [
          { path: "/product_sale_config", labelKey: "menu.product_sale_config" },
          { path: "/public_api_key", labelKey: "menu.public_api_key" }
      ]
    }
  ];

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("mfa_temp_token");
    navigate("/login", { replace: true });
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <img src="/tyakxa-logo.png" alt={t("common.app_title")} className="sidebar-logo" />
      </div>

      <nav className="sidebar-nav">
        {groups.map(group => (
          <div key={group.key} className="nav-group">
            <button
              className={"nav-group-toggle " + (openGroup === group.key ? "open" : "")}
              onClick={() => setOpenGroup(openGroup === group.key ? null : group.key)}
            >
              <span>{group.label}</span>
              <ChevronDown size={16} />
            </button>
            
            {openGroup === group.key && (
              <div className="nav-submenu">
                {group.items.map(item => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}
                  >
                    {t(item.labelKey, item.label)}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="button-logout" onClick={handleLogout}>
          <LogOut size={16} />
          {t("common.logout", "Logout")}
        </button>
      </div>
    </aside>
  );
}
