/* eslint-disable react/prop-types, react-refresh/only-export-components */
import React from "react";
import { RefreshCw } from "lucide-react";
import { useI18n } from "../../i18n";

export const money = (value) => new Intl.NumberFormat(document.documentElement.lang || "es", { style: "currency", currency: "MXN" }).format(Number(value || 0));

export function RestaurantHeader({ eyebrow, title, detail, loading, onRefresh, actions }) {
  const { t } = useI18n();
  return <header className="rest-header">
    <div><span className="rest-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{detail}</p></div>
    <div className="rest-header-actions">{actions}<button className="rest-icon-button" onClick={onRefresh} disabled={loading} title={t("restaurant.refresh")}><RefreshCw size={19} /></button></div>
  </header>;
}

export function EmptyState({ children }) {
  const { t } = useI18n();
  return <div className="rest-empty">{children || t("restaurant.empty")}</div>;
}

export function Status({ value }) {
  const { t } = useI18n();
  return <span className={`rest-status rest-status--${value}`}>{t(`restaurant.status_${value}`, String(value || "").replaceAll("_", " "))}</span>;
}

export function Notice({ error }) {
  const { t } = useI18n();
  return error ? <div className="rest-notice" role="alert">{error.message || t("restaurant.operation_error")}</div> : null;
}