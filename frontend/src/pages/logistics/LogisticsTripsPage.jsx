import React from "react";

import { createLogisticsTrip, deleteLogisticsTrip, getAllCustomerSupplier, getAllLogisticsFile, getAllLogisticsOperator, getAllLogisticsServiceRequest, getAllLogisticsTrailer, getAllLogisticsTrip, getAllLogisticsUnit, updateLogisticsTrip } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const relation = (field, labelKey, placeholderKey, getAll, idField, displayField, required = false) => ({ field, labelKey, placeholderKey, getAll: () => getAll({ page: 1, per_page: 500 }), idField, displayField, required });
const config = {
  singularKey: "logistics.trip_singular", pluralKey: "logistics.trip_plural", articleKey: "logistics.trip_article", newLabelKey: "logistics.trip_new", idField: "id_logistics_trip", displayField: "folio",
  getAll: getAllLogisticsTrip, create: createLogisticsTrip, update: updateLogisticsTrip, remove: deleteLogisticsTrip,
  relations: [
    relation("id_customer_supplier", "logistics.customer", "logistics.select_customer", (params) => getAllCustomerSupplier({ ...params, type: "client" }), "id_customer_supplier", "name", true),
    relation("id_logistics_service_request", "logistics.request", "logistics.select_request", getAllLogisticsServiceRequest, "id_logistics_service_request", "request_number", true),
    relation("id_logistics_unit", "logistics.unit", "logistics.no_unit", getAllLogisticsUnit, "id_logistics_unit", "plate"),
    relation("id_logistics_trailer", "logistics.trailer", "logistics.no_trailer", getAllLogisticsTrailer, "id_logistics_trailer", "plate"),
    relation("id_logistics_operator", "logistics.operator", "logistics.no_operator", getAllLogisticsOperator, "id_logistics_operator", "full_name"),
    relation("id_logistics_file", "logistics.file", "logistics.no_file", getAllLogisticsFile, "id_logistics_file", "folio"),
  ],
  emptyForm: { id_customer_supplier: "", id_logistics_service_request: "", id_logistics_unit: "", id_logistics_trailer: "", id_logistics_operator: "", id_logistics_file: "", folio: "", supplier_reference: "", route_reference: "", expediente_reference: "", status: "solicitado", planned_pickup_at: "", planned_delivery_at: "", actual_pickup_at: "", actual_delivery_at: "", planned_cost: "0", actual_cost: "0", revenue: "0", kilometers: "0", restrictions: "" },
  fields: [
    { name: "folio", labelKey: "logistics.folio", required: true, maxLength: 80 },
    { name: "supplier_reference", labelKey: "logistics.supplier_reference", maxLength: 120 }, { name: "route_reference", labelKey: "logistics.route_reference", maxLength: 120 }, { name: "expediente_reference", labelKey: "logistics.file_reference", maxLength: 120 },
    { name: "status", labelKey: "logistics.status", options: [{ value: "solicitado", labelKey: "logistics.status_requested" }, { value: "planeado", labelKey: "logistics.status_planned" }, { value: "asignado", labelKey: "logistics.status_assigned" }, { value: "cargado", labelKey: "logistics.status_loaded" }, { value: "en tránsito", labelKey: "logistics.status_in_transit" }, { value: "en ruta", labelKey: "logistics.status_en_route" }, { value: "retrasado", labelKey: "logistics.status_delayed" }, { value: "entregado", labelKey: "logistics.status_delivered" }, { value: "cerrado", labelKey: "logistics.status_closed" }, { value: "facturado", labelKey: "logistics.status_invoiced" }, { value: "cancelado", labelKey: "logistics.status_cancelled" }] },
    { name: "planned_pickup_at", labelKey: "logistics.planned_pickup", type: "datetime-local" }, { name: "planned_delivery_at", labelKey: "logistics.planned_delivery", type: "datetime-local" },
    { name: "actual_pickup_at", labelKey: "logistics.actual_pickup", type: "datetime-local" }, { name: "actual_delivery_at", labelKey: "logistics.actual_delivery", type: "datetime-local" },
    { name: "planned_cost", labelKey: "logistics.planned_cost", type: "number", min: "0", step: "0.01" }, { name: "actual_cost", labelKey: "logistics.actual_cost", type: "number", min: "0", step: "0.01" },
    { name: "revenue", labelKey: "logistics.revenue", type: "number", min: "0", step: "0.01" }, { name: "kilometers", labelKey: "logistics.kilometers", type: "number", min: "0", step: "0.01" },
    { name: "restrictions", labelKey: "logistics.restrictions", type: "textarea" },
  ],
  searchFields: ["folio", "status", "supplier_reference", "route_reference", "restrictions"],
  columns: [{ name: "folio", labelKey: "logistics.folio" }, { name: "status", labelKey: "logistics.status" }, { name: "planned_pickup_at", labelKey: "logistics.pickup" }, { name: "planned_delivery_at", labelKey: "logistics.delivery" }, { name: "planned_cost", labelKey: "logistics.planned_cost_short" }, { name: "actual_cost", labelKey: "logistics.actual_cost" }, { name: "revenue", labelKey: "logistics.revenue" }, { name: "kilometers", labelKey: "logistics.kilometers_abbreviation" }],
  emptyMessageKey: "logistics.trip_empty",
};

export default function LogisticsTripsPage() { return <LogisticsEntityPage config={config} />; }