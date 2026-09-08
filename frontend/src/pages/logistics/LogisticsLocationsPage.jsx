
import { createLogisticsLocation, deleteLogisticsLocation, getAllLogisticsLocation, getAllLogisticsWarehouse, updateLogisticsLocation } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.location_singular", pluralKey: "logistics.location_plural", articleKey: "logistics.location_article", newLabelKey: "logistics.location_new",
  idField: "id_logistics_location", displayField: "code",
  relation: { field: "id_logistics_warehouse", labelKey: "logistics.warehouse", placeholderKey: "logistics.select_warehouse", getAll: () => getAllLogisticsWarehouse({ page: 1, per_page: 500, status: "activo" }), idField: "id_logistics_warehouse", displayField: "name" },
  getAll: getAllLogisticsLocation, create: createLogisticsLocation, update: updateLogisticsLocation, remove: deleteLogisticsLocation,
  emptyForm: { id_logistics_warehouse: "", code: "", zone: "", location_type: "", capacity: "0", status: "activo" },
  fields: [
    { name: "code", labelKey: "logistics.code", required: true, maxLength: 80 },
    { name: "zone", labelKey: "logistics.zone", maxLength: 80 },
    { name: "location_type", labelKey: "logistics.location_type", maxLength: 80 },
    { name: "capacity", labelKey: "logistics.capacity", type: "number", required: true, min: "0", step: "0.01" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["code", "zone", "location_type", "status"],
  columns: [
    { name: "code", labelKey: "logistics.code" }, { name: "zone", labelKey: "logistics.zone" },
    { name: "location_type", labelKey: "logistics.type" }, { name: "capacity", labelKey: "logistics.capacity" }, { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.location_empty",
};

export default function LogisticsLocationsPage() {
  return <LogisticsEntityPage config={config} />;
}