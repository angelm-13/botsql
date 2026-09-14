
import { createLogisticsUnit, deleteLogisticsUnit, getAllLogisticsUnit, updateLogisticsUnit } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const logisticsUnitConfig = {
  singularKey: "logistics.unit_singular",
  pluralKey: "logistics.unit_plural",
  articleKey: "logistics.unit_article",
  newLabelKey: "logistics.unit_new",
  idField: "id_logistics_unit",
  displayField: "plate",
  relation: null,
  getAll: getAllLogisticsUnit,
  create: createLogisticsUnit,
  update: updateLogisticsUnit,
  remove: deleteLogisticsUnit,
  emptyForm: { plate: "", unit_type: "", mileage: "0", availability_status: "disponible", insurance_expiration: "", verification_expiration: "", policy_number: "", fuel_efficiency: "", status: "activo" },
  fields: [
    { name: "plate", labelKey: "logistics.plates", required: true, maxLength: 30 },
    { name: "unit_type", labelKey: "logistics.unit_type", required: true, maxLength: 80 },
    { name: "mileage", labelKey: "logistics.mileage", type: "number", required: true, min: "0", step: "0.01" },
    { name: "availability_status", labelKey: "logistics.availability", options: [{ value: "disponible", labelKey: "logistics.availability_available" }, { value: "en viaje", labelKey: "logistics.availability_on_trip" }, { value: "mantenimiento", labelKey: "logistics.availability_maintenance" }, { value: "fuera de servicio", labelKey: "logistics.availability_out_of_service" }] },
    { name: "insurance_expiration", labelKey: "logistics.insurance_expiration", type: "date" },
    { name: "verification_expiration", labelKey: "logistics.verification_expiration", type: "date" },
    { name: "policy_number", labelKey: "logistics.policy_number", maxLength: 100 },
    { name: "fuel_efficiency", labelKey: "logistics.fuel_efficiency_kml", type: "number", min: "0", step: "0.01" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["plate", "unit_type", "availability_status", "policy_number", "status"],
  columns: [
    { name: "plate", labelKey: "logistics.plates" },
    { name: "unit_type", labelKey: "logistics.type" },
    { name: "mileage", labelKey: "logistics.mileage" },
    { name: "availability_status", labelKey: "logistics.availability" },
    { name: "insurance_expiration", labelKey: "logistics.insurance" },
    { name: "verification_expiration", labelKey: "logistics.verification" },
    { name: "policy_number", labelKey: "logistics.policy" },
    { name: "fuel_efficiency", labelKey: "logistics.performance" },
    { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.unit_empty",
};

export default function LogisticsUnitsPage() {
  return <LogisticsEntityPage config={logisticsUnitConfig} />;
}