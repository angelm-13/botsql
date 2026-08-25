import React from "react";

import { createLogisticsServiceRequest, deleteLogisticsServiceRequest, getAllCustomerSupplier, getAllLogisticsQuotation, getAllLogisticsServiceRequest, updateLogisticsServiceRequest } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.request_singular", pluralKey: "logistics.request_plural", articleKey: "logistics.request_article", newLabelKey: "logistics.request_new",
  idField: "id_logistics_service_request", displayField: "request_number",
  getAll: getAllLogisticsServiceRequest, create: createLogisticsServiceRequest, update: updateLogisticsServiceRequest, remove: deleteLogisticsServiceRequest,
  relations: [
    { field: "id_customer_supplier", labelKey: "logistics.customer", placeholderKey: "logistics.select_customer", getAll: () => getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }), idField: "id_customer_supplier", displayField: "name" },
    { field: "id_logistics_quotation", labelKey: "logistics.quotation", placeholderKey: "logistics.no_quotation", getAll: () => getAllLogisticsQuotation({ page: 1, per_page: 500 }), idField: "id_logistics_quotation", displayField: "folio", required: false },
  ],
  emptyForm: { id_customer_supplier: "", id_logistics_quotation: "", request_number: "", request_type: "", origin: "", destination: "", requested_pickup_at: "", requested_delivery_at: "", status: "solicitado", priority: "normal", description: "" },
  fields: [
    { name: "request_number", labelKey: "logistics.number", required: true, maxLength: 80 }, { name: "request_type", labelKey: "logistics.type", required: true, maxLength: 100 },
    { name: "origin", labelKey: "logistics.origin", type: "textarea" }, { name: "destination", labelKey: "logistics.destination", type: "textarea" },
    { name: "requested_pickup_at", labelKey: "logistics.requested_pickup", type: "datetime-local" }, { name: "requested_delivery_at", labelKey: "logistics.requested_delivery", type: "datetime-local" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "solicitado", labelKey: "logistics.status_requested" }, { value: "aprobado", labelKey: "logistics.status_approved" }, { value: "programado", labelKey: "logistics.status_scheduled" }, { value: "cancelado", labelKey: "logistics.status_cancelled" }] },
    { name: "priority", labelKey: "logistics.priority", options: [{ value: "baja", labelKey: "logistics.priority_low" }, { value: "normal", labelKey: "logistics.priority_normal" }, { value: "alta", labelKey: "logistics.priority_high" }, { value: "urgente", labelKey: "logistics.priority_urgent" }] },
    { name: "description", labelKey: "logistics.description", type: "textarea" },
  ],
  searchFields: ["request_number", "request_type", "origin", "destination", "status", "priority"],
  columns: [{ name: "request_number", labelKey: "logistics.number" }, { name: "request_type", labelKey: "logistics.type" }, { name: "requested_pickup_at", labelKey: "logistics.pickup" }, { name: "requested_delivery_at", labelKey: "logistics.delivery" }, { name: "priority", labelKey: "logistics.priority" }, { name: "status", labelKey: "logistics.status" }],
  emptyMessageKey: "logistics.request_empty",
};

export default function LogisticsServiceRequestsPage() { return <LogisticsEntityPage config={config} />; }