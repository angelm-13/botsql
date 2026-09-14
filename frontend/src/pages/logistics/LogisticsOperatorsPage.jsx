
import { createLogisticsOperator, deleteLogisticsOperator, getAllLogisticsOperator, updateLogisticsOperator } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const logisticsOperatorConfig = {
  singularKey: "logistics.operator_singular",
  pluralKey: "logistics.operator_plural",
  articleKey: "logistics.operator_article",
  newLabelKey: "logistics.operator_new",
  idField: "id_logistics_operator",
  displayField: "full_name",
  relation: null,
  getAll: getAllLogisticsOperator,
  create: createLogisticsOperator,
  update: updateLogisticsOperator,
  remove: deleteLogisticsOperator,
  emptyForm: { full_name: "", license_number: "", license_expiration: "", status: "activo", contact_phone: "", performance_score: "0" },
  fields: [
    { name: "full_name", labelKey: "logistics.full_name", required: true, maxLength: 150 },
    { name: "license_number", labelKey: "logistics.license_number", required: true, maxLength: 80 },
    { name: "license_expiration", labelKey: "logistics.license_expiration", type: "date" },
    { name: "contact_phone", labelKey: "logistics.phone", maxLength: 40 },
    { name: "performance_score", labelKey: "logistics.performance_score", type: "number", required: true, min: "0", step: "0.01" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["full_name", "license_number", "contact_phone", "status"],
  columns: [
    { name: "full_name", labelKey: "logistics.name" },
    { name: "license_number", labelKey: "logistics.license" },
    { name: "license_expiration", labelKey: "logistics.expiration" },
    { name: "contact_phone", labelKey: "logistics.phone" },
    { name: "performance_score", labelKey: "logistics.performance" },
    { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.operator_empty",
};

export default function LogisticsOperatorsPage() {
  return <LogisticsEntityPage config={logisticsOperatorConfig} />;
}