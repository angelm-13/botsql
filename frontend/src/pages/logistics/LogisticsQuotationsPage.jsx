
import { createLogisticsQuotation, deleteLogisticsQuotation, getAllLogisticsQuotation, updateLogisticsQuotation } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const statusOptions = [
  { value: "borrador", labelKey: "logistics.status_draft" }, { value: "enviada", labelKey: "logistics.status_sent" },
  { value: "aceptada", labelKey: "logistics.status_accepted" }, { value: "rechazada", labelKey: "logistics.status_rejected" },
  { value: "vencida", labelKey: "logistics.status_expired_feminine" }, { value: "cancelada", labelKey: "logistics.status_cancelled_feminine" },
];

const config = {
  singularKey: "logistics.quotation_singular", pluralKey: "logistics.quotation_plural", articleKey: "logistics.quotation_article", newLabelKey: "logistics.quotation_new",
  idField: "id_logistics_quotation", displayField: "folio",
  getAll: getAllLogisticsQuotation, create: createLogisticsQuotation, update: updateLogisticsQuotation, remove: deleteLogisticsQuotation,
  emptyForm: { id_customer_supplier: "", folio: "", service_type: "", origin: "", destination: "", cargo_type: "", unit_required: "", kilometers: "0", maneuvers: "0", storage: "0", additional_services: "{}", total: "0", source_branch_reference: "", status: "borrador" },
  fields: [
    { name: "folio", labelKey: "logistics.folio", required: true, maxLength: 80 },
    { name: "service_type", labelKey: "logistics.service_type", required: true, maxLength: 100 },
    { name: "origin", labelKey: "logistics.origin", type: "textarea", required: true },
    { name: "destination", labelKey: "logistics.destination", type: "textarea", required: true },
    { name: "cargo_type", labelKey: "logistics.cargo_type", maxLength: 120 },
    { name: "unit_required", labelKey: "logistics.required_unit", maxLength: 120 },
    { name: "kilometers", labelKey: "logistics.kilometers", type: "number", min: "0", step: "0.01" },
    { name: "maneuvers", labelKey: "logistics.maneuvers", type: "number", min: "0", step: "0.01" },
    { name: "storage", labelKey: "logistics.storage", type: "number", min: "0", step: "0.01" },
    { name: "additional_services", labelKey: "logistics.additional_services_json", type: "json" },
    { name: "total", labelKey: "logistics.total", type: "number", min: "0", step: "0.01" },
    { name: "source_branch_reference", labelKey: "logistics.branch_reference", maxLength: 120 },
    { name: "status", labelKey: "logistics.status", options: statusOptions },
  ],
  searchFields: ["folio", "service_type", "origin", "destination", "cargo_type", "status"],
  columns: [
    { name: "folio", labelKey: "logistics.folio" }, { name: "service_type", labelKey: "logistics.service" },
    { name: "origin", labelKey: "logistics.origin" }, { name: "destination", labelKey: "logistics.destination" },
    { name: "kilometers", labelKey: "logistics.kilometers_abbreviation" }, { name: "total", labelKey: "logistics.total" }, { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.quotation_empty",
};

export default function LogisticsQuotationsPage() { return <LogisticsEntityPage config={config} />; }