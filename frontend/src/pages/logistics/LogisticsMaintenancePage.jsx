import React from "react";

import { createLogisticsMaintenance, deleteLogisticsMaintenance, getAllLogisticsMaintenance, getAllLogisticsUnit, updateLogisticsMaintenance } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const logisticsMaintenanceConfig = {
  singularKey: "logistics.maintenance_singular",
  pluralKey: "logistics.maintenance_plural",
  articleKey: "logistics.maintenance_article",
  newLabelKey: "logistics.maintenance_new",
  idField: "id_logistics_maintenance",
  displayField: "maintenance_type",
  relation: {
    field: "id_logistics_unit",
    labelKey: "logistics.unit",
    placeholderKey: "logistics.select_unit",
    getAll: () => getAllLogisticsUnit({ page: 1, per_page: 500 }),
    idField: "id_logistics_unit",
    displayField: "plate",
  },
  getAll: getAllLogisticsMaintenance,
  create: createLogisticsMaintenance,
  update: updateLogisticsMaintenance,
  remove: deleteLogisticsMaintenance,
  emptyForm: { id_logistics_unit: "", maintenance_type: "", scheduled_at: "", closed_at: "", cost: "0", status: "abierta", description: "" },
  fields: [
    { name: "maintenance_type", labelKey: "logistics.maintenance_type", required: true, maxLength: 80 },
    { name: "scheduled_at", labelKey: "logistics.scheduled_date", type: "date" },
    { name: "closed_at", labelKey: "logistics.closing_date", type: "date" },
    { name: "cost", labelKey: "logistics.cost", type: "number", required: true, min: "0", step: "0.01" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "abierta", labelKey: "logistics.status_open_feminine" }, { value: "en proceso", labelKey: "logistics.status_in_progress" }, { value: "cerrada", labelKey: "logistics.status_closed_feminine" }] },
    { name: "description", labelKey: "logistics.description", type: "textarea", maxLength: 2000 },
  ],
  searchFields: ["maintenance_type", "status", "description"],
  columns: [
    { name: "maintenance_type", labelKey: "logistics.type" },
    { name: "scheduled_at", labelKey: "logistics.scheduled" },
    { name: "closed_at", labelKey: "logistics.closing" },
    { name: "cost", labelKey: "logistics.cost", format: (value) => Number(value || 0).toFixed(2) },
    { name: "status", labelKey: "logistics.status" },
    { name: "description", labelKey: "logistics.description" },
  ],
  emptyMessageKey: "logistics.maintenance_empty",
};

export default function LogisticsMaintenancePage() {
  return <LogisticsEntityPage config={logisticsMaintenanceConfig} />;
}