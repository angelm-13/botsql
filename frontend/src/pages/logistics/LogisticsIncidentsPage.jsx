import React from "react";

import { createLogisticsIncident, deleteLogisticsIncident, getAllLogisticsIncident, getAllLogisticsTrip, getAllUser, updateLogisticsIncident } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.incident_singular", pluralKey: "logistics.incident_plural", articleKey: "logistics.incident_article", newLabelKey: "logistics.incident_new", idField: "id_logistics_incident", displayField: "incident_type",
  getAll: getAllLogisticsIncident, create: createLogisticsIncident, update: updateLogisticsIncident, remove: deleteLogisticsIncident,
  relations: [
    { field: "id_logistics_trip", labelKey: "logistics.trip", placeholderKey: "logistics.select_trip", getAll: () => getAllLogisticsTrip({ page: 1, per_page: 500 }), idField: "id_logistics_trip", displayField: "folio" },
    { field: "responsible_user_id", labelKey: "logistics.responsible", placeholderKey: "logistics.no_responsible", getAll: () => getAllUser({ page: 1, per_page: 500 }), idField: "id_user", displayField: "full_name", required: false },
  ],
  emptyForm: { id_logistics_trip: "", responsible_user_id: "", incident_type: "", severity: "media", description: "", status: "abierta" },
  fields: [
    { name: "incident_type", labelKey: "logistics.incident_type", required: true, maxLength: 100 },
    { name: "severity", labelKey: "logistics.severity", options: [{ value: "baja", labelKey: "logistics.severity_low" }, { value: "media", labelKey: "logistics.severity_medium" }, { value: "alta", labelKey: "logistics.severity_high" }, { value: "critica", labelKey: "logistics.severity_critical" }] },
    { name: "description", labelKey: "logistics.description", type: "textarea", required: true },
    { name: "status", labelKey: "logistics.status", options: [{ value: "abierta", labelKey: "logistics.status_open_feminine" }, { value: "en_proceso", labelKey: "logistics.status_in_progress" }, { value: "resuelta", labelKey: "logistics.status_resolved" }, { value: "cerrada", labelKey: "logistics.status_closed_feminine" }, { value: "cancelada", labelKey: "logistics.status_cancelled_feminine" }] },
  ],
  searchFields: ["incident_type", "severity", "description", "status"],
  columns: [{ name: "incident_type", labelKey: "logistics.type" }, { name: "severity", labelKey: "logistics.severity" }, { name: "description", labelKey: "logistics.description" }, { name: "status", labelKey: "logistics.status" }],
  emptyMessageKey: "logistics.incident_empty",
};

export default function LogisticsIncidentsPage() { return <LogisticsEntityPage config={config} />; }