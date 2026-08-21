/* eslint-disable react/prop-types, react-refresh/only-export-components */
import React from "react";
import { RefreshCw } from "lucide-react";

export const money = (value) => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(value || 0));

export function RestaurantHeader({ eyebrow, title, detail, loading, onRefresh, actions }) {
  return <header className="rest-header">
    <div><span className="rest-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{detail}</p></div>
    <div className="rest-header-actions">{actions}<button className="rest-icon-button" onClick={onRefresh} disabled={loading} title="Actualizar"><RefreshCw size={19} /></button></div>
  </header>;
}

export function EmptyState({ children = "No hay información para mostrar." }) {
  return <div className="rest-empty">{children}</div>;
}

export function Status({ value }) {
  return <span className={`rest-status rest-status--${value}`}>{String(value || "").replaceAll("_", " ")}</span>;
}

export function Notice({ error }) {
  return error ? <div className="rest-notice" role="alert">{error.message || "No fue posible completar la operación."}</div> : null;
}