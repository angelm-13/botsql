import React from "react";

import { createLogisticsWarehouse, deleteLogisticsWarehouse, getAllLogisticsWarehouse, updateLogisticsWarehouse } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.warehouse_singular", pluralKey: "logistics.warehouse_plural", articleKey: "logistics.warehouse_article", newLabelKey: "logistics.warehouse_new",
  idField: "id_logistics_warehouse", displayField: "name", relation: null,
  getAll: getAllLogisticsWarehouse, create: createLogisticsWarehouse, update: updateLogisticsWarehouse, remove: deleteLogisticsWarehouse,
  emptyForm: { name: "", address: "", capacity: "0", status: "activo" },
  fields: [
    { name: "name", labelKey: "logistics.name", required: true, maxLength: 150 },
    { name: "address", labelKey: "logistics.address", maxLength: 300 },
    { name: "capacity", labelKey: "logistics.capacity", type: "number", required: true, min: "0", step: "0.01" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["name", "address", "status"],
  columns: [
    { name: "name", labelKey: "logistics.name" }, { name: "address", labelKey: "logistics.address" },
    { name: "capacity", labelKey: "logistics.capacity" }, { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.warehouse_empty",
};

export default function LogisticsWarehousesPage() {
  return <LogisticsEntityPage config={config} />;
}