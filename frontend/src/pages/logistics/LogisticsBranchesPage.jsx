import React from "react";

import { createLogisticsBranch, deleteLogisticsBranch, getAllLogisticsBranch, updateLogisticsBranch } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.branch_singular", pluralKey: "logistics.branch_plural", articleKey: "logistics.branch_article", newLabelKey: "logistics.branch_new", idField: "id_logistics_branch", displayField: "name",
  getAll: getAllLogisticsBranch, create: createLogisticsBranch, update: updateLogisticsBranch, remove: deleteLogisticsBranch, relation: null,
  emptyForm: { name: "", postal_code: "", series: "", address: "", status: "activo" },
  fields: [
    { name: "name", labelKey: "logistics.name", required: true, maxLength: 180 }, { name: "postal_code", labelKey: "logistics.postal_code", maxLength: 20 },
    { name: "series", labelKey: "logistics.cfdi_series", maxLength: 30 }, { name: "address", labelKey: "logistics.domicile", type: "textarea" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["name", "postal_code", "series", "address", "status"],
  columns: [{ name: "name", labelKey: "logistics.name" }, { name: "postal_code", labelKey: "logistics.postal_abbreviation" }, { name: "series", labelKey: "logistics.series" }, { name: "address", labelKey: "logistics.domicile" }, { name: "status", labelKey: "logistics.status" }],
  emptyMessageKey: "logistics.branch_empty",
};

export default function LogisticsBranchesPage() { return <LogisticsEntityPage config={config} />; }