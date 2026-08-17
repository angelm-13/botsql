import { NavLink } from "react-router-dom";
import { Settings, Globe, User } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useI18n } from "../i18n";

export default function Header() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const { lang, t, setLanguage } = useI18n();
  
  const settingsRef = useRef(null);
  const langRef = useRef(null);

  const topbarItems = [
        {
          label: t("menu.user"),
          path: "/user"
        },
        {
          label: t("menu.customer_supplier"),
          path: "/customer_supplier"
        },
        {
          label: t("menu.bank"),
          path: "/bank"
        },
        {
          label: t("menu.product_family"),
          path: "/product_family"
        },
        {
          label: t("menu.incident_type"),
          path: "/incident_type"
        },
        {
          label: t("menu.brand"),
          path: "/brand"
        },
        {
          label: t("menu.unit"),
          path: "/unit"
        },
        {
          label: t("menu.material_component"),
          path: "/material_component"
        },
        {
          label: t("menu.location_type"),
          path: "/location_type"
        },
        {
          label: t("menu.ticket"),
          path: "/ticket"
        },
        {
          label: t("menu.bank"),
          path: "/bank"
        },
        {
          label: t("menu.status"),
          path: "/status"
        },
        {
          label: t("menu.theme"),
          path: "/theme"
        },
        {
          label: t("menu.level"),
          path: "/level"
        },
        {
          label: t("menu.field"),
          path: "/field"
        },
        {
          label: t("menu.permission"),
          path: "/permission"
        },
        {
          label: t("menu.nm_field_permission"),
          path: "/nm_field_permission"
        },
        {
          label: t("menu.event_log"),
          path: "/event_log"
        },
        {
          label: t("menu.user_mfa"),
          path: "/user_mfa"
        },
        {
          label: t("menu.entity_permission"),
          path: "/entity_permission"
        },
        {
          label: t("menu.inventory_status"),
          path: "/inventory_status"
        }
  ];

  useEffect(() => {
    function handleClickOutside(e) {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) {
        setSettingsOpen(false);
      }
      if (langRef.current && !langRef.current.contains(e.target)) {
        setLangOpen(false);
      }
    }
    if (settingsOpen || langOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [settingsOpen, langOpen]);

  return (
    <header className="header">
      <div className="header-left">
        <p className="eyebrow">ERP · CRM · SCM</p>
        <h1>{t("common.app_title")}</h1>
      </div>
      
      <nav className="header-nav">
        {topbarItems.map(item => (
          <NavLink key={item.path} to={item.path} className={({ isActive }) => isActive ? "header-link active" : "header-link"}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="header-actions">
        <label className="language-picker">
          {t("common.language")}
          <select value={lang} onChange={(e) => setLanguage(e.target.value)}>
            <option value="es">ES</option>
            <option value="en">EN</option>
            <option value="pt">PT</option>
            <option value="de">DE</option>
            <option value="ja">日本語</option>
          </select>
        </label>
        <button className="button ghost" title={t("common.settings", "Configuración")}>
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}
