import React from "react";

import { createLogisticsRate, deleteLogisticsRate, getAllLogisticsRate, updateLogisticsRate } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const logisticsRateConfig = {
  moduleLabelKey: "logistics.crm",
  singularKey: "logistics.rate_singular",
  pluralKey: "logistics.rate_plural",
  articleKey: "logistics.rate_article",
  newLabelKey: "logistics.rate_new",
  idField: "id_logistics_rate",
  displayField: "service_type",
  getAll: getAllLogisticsRate,
  create: createLogisticsRate,
  update: updateLogisticsRate,
  remove: deleteLogisticsRate,
  emptyForm: { id_customer_supplier: "", service_type: "", origin: "", destination: "", unit_type: "", amount: "0", currency: "MXN", status: "activo" },
  fields: [
    { name: "service_type", labelKey: "logistics.service_type", required: true, maxLength: 100 },
    { name: "origin", labelKey: "logistics.origin", maxLength: 150 },
    { name: "destination", labelKey: "logistics.destination", maxLength: 150 },
    { name: "unit_type", labelKey: "logistics.unit_type", maxLength: 80 },
    { name: "amount", labelKey: "logistics.amount", type: "number", required: true, min: "0", step: "0.01" },
    { name: "currency", labelKey: "logistics.currency", options: [{ value: "MXN", labelKey: "logistics.currency_mxn" }, { value: "USD", labelKey: "logistics.currency_usd" }] },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["service_type", "origin", "destination", "unit_type", "currency", "status"],
  columns: [
    { name: "service_type", labelKey: "logistics.service" },
    { name: "origin", labelKey: "logistics.origin" },
    { name: "destination", labelKey: "logistics.destination" },
    { name: "unit_type", labelKey: "logistics.unit" },
    { name: "amount", labelKey: "logistics.amount", format: (value, item) => `${Number(value || 0).toFixed(2)} ${item.currency}` },
    { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.rate_empty",
};

export default function LogisticsRatesPage() {
  return <LogisticsEntityPage config={logisticsRateConfig} />;
}