import React from "react";

import { createLogisticsRack, deleteLogisticsRack, getAllCustomerSupplier, getAllLogisticsLocation, getAllLogisticsRack, updateLogisticsRack } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.rack_singular", pluralKey: "logistics.rack_plural", articleKey: "logistics.rack_article", newLabelKey: "logistics.rack_new",
  idField: "id_logistics_rack", displayField: "code",
  relations: [
    { field: "id_customer_supplier", labelKey: "logistics.customer", placeholderKey: "logistics.select_customer", getAll: () => getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }), idField: "id_customer_supplier", displayField: "name" },
    { field: "id_logistics_location", labelKey: "logistics.location", placeholderKey: "logistics.select_location", getAll: () => getAllLogisticsLocation({ page: 1, per_page: 500, status: "activo" }), idField: "id_logistics_location", displayField: "code" },
  ],
  getAll: getAllLogisticsRack, create: createLogisticsRack, update: updateLogisticsRack, remove: deleteLogisticsRack,
  emptyForm: { id_customer_supplier: "", id_logistics_location: "", code: "", status: "en_cliente", condition: "bueno", quantity: "1", sent_at: "", received_at: "" },
  fields: [
    { name: "code", labelKey: "logistics.code", required: true, maxLength: 100 },
    { name: "status", labelKey: "logistics.status", options: [{ value: "en_cliente", labelKey: "logistics.status_at_customer" }, { value: "en_almacen", labelKey: "logistics.status_in_warehouse" }, { value: "pendiente_retorno", labelKey: "logistics.status_pending_return" }, { value: "en_reparacion", labelKey: "logistics.status_under_repair" }] },
    { name: "condition", labelKey: "logistics.condition", options: [{ value: "bueno", labelKey: "logistics.condition_good" }, { value: "regular", labelKey: "logistics.condition_fair" }, { value: "dañado", labelKey: "logistics.condition_damaged" }] },
    { name: "quantity", labelKey: "logistics.quantity", type: "number", required: true, min: "0", step: "1" },
    { name: "sent_at", labelKey: "logistics.sent_date", type: "date" },
    { name: "received_at", labelKey: "logistics.received_date", type: "date" },
  ],
  searchFields: ["code", "status", "condition"],
  columns: [
    { name: "code", labelKey: "logistics.code" }, { name: "status", labelKey: "logistics.status" },
    { name: "condition", labelKey: "logistics.condition" }, { name: "quantity", labelKey: "logistics.quantity" },
    { name: "sent_at", labelKey: "logistics.sent" }, { name: "received_at", labelKey: "logistics.received" },
  ],
  emptyMessageKey: "logistics.rack_empty",
};

export default function LogisticsRacksPage() {
  return <LogisticsEntityPage config={config} />;
}