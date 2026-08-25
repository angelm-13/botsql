import React from "react";

import { createLogisticsInventory, deleteLogisticsInventory, getAllCustomerSupplier, getAllLogisticsInventory, getAllLogisticsLocation, updateLogisticsInventory } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.inventory_singular", pluralKey: "logistics.inventory_plural", articleKey: "logistics.inventory_article", newLabelKey: "logistics.inventory_new",
  idField: "id_logistics_inventory", displayField: "sku",
  relations: [
    { field: "id_customer_supplier", labelKey: "logistics.customer", placeholderKey: "logistics.select_customer", getAll: () => getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }), idField: "id_customer_supplier", displayField: "name" },
    { field: "id_logistics_location", labelKey: "logistics.location", placeholderKey: "logistics.select_location", getAll: () => getAllLogisticsLocation({ page: 1, per_page: 500, status: "activo" }), idField: "id_logistics_location", displayField: "code" },
  ],
  getAll: getAllLogisticsInventory, create: createLogisticsInventory, update: updateLogisticsInventory, remove: deleteLogisticsInventory,
  emptyForm: { id_customer_supplier: "", id_logistics_location: "", sku: "", description: "", quantity: "0", lot: "", serial_number: "", status: "activo" },
  fields: [
    { name: "sku", labelKey: "logistics.sku", required: true, maxLength: 100 },
    { name: "description", labelKey: "logistics.description", maxLength: 300 },
    { name: "quantity", labelKey: "logistics.quantity", type: "number", required: true, min: "0", step: "0.001" },
    { name: "lot", labelKey: "logistics.lot", maxLength: 100 },
    { name: "serial_number", labelKey: "logistics.serial_number", maxLength: 120 },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "pendiente_surtido", labelKey: "logistics.status_pending_fulfillment" }, { value: "surtido", labelKey: "logistics.status_fulfilled" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["sku", "description", "lot", "serial_number", "status"],
  columns: [
    { name: "sku", labelKey: "logistics.sku" }, { name: "description", labelKey: "logistics.description" },
    { name: "quantity", labelKey: "logistics.quantity" }, { name: "lot", labelKey: "logistics.lot" },
    { name: "serial_number", labelKey: "logistics.series" }, { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.inventory_empty",
};

export default function LogisticsInventoryPage() {
  return <LogisticsEntityPage config={config} />;
}