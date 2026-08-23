import React from "react";

import { createLogisticsContract, deleteLogisticsContract, getAllLogisticsContract, updateLogisticsContract } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const logisticsContractConfig = {
  moduleLabelKey: "logistics.crm",
  singularKey: "logistics.contract_singular",
  pluralKey: "logistics.contract_plural",
  articleKey: "logistics.contract_article",
  newLabelKey: "logistics.contract_new",
  idField: "id_logistics_contract",
  displayField: "contract_number",
  getAll: getAllLogisticsContract,
  create: createLogisticsContract,
  update: updateLogisticsContract,
  remove: deleteLogisticsContract,
  emptyForm: { id_customer_supplier: "", contract_number: "", start_date: "", end_date: "", sla_level: "standard", status: "activo" },
  fields: [
    { name: "contract_number", labelKey: "logistics.contract_number", required: true, maxLength: 80 },
    { name: "start_date", labelKey: "logistics.start_date", type: "date", required: true },
    { name: "end_date", labelKey: "logistics.end_date", type: "date" },
    { name: "sla_level", labelKey: "logistics.sla_level", options: [{ value: "standard", labelKey: "logistics.sla_standard" }, { value: "premium", labelKey: "logistics.sla_premium" }] },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["contract_number", "start_date", "end_date", "sla_level", "status"],
  columns: [
    { name: "contract_number", labelKey: "logistics.contract" },
    { name: "start_date", labelKey: "logistics.start" },
    { name: "end_date", labelKey: "logistics.end" },
    { name: "sla_level", labelKey: "logistics.sla" },
    { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.contract_empty",
};

export default function LogisticsContractsPage() {
  return <LogisticsEntityPage config={logisticsContractConfig} />;
}