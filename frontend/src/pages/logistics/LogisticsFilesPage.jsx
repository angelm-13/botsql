import React from "react";

import { createLogisticsFile, deleteLogisticsFile, getAllCustomerSupplier, getAllInvoice, getAllLogisticsBranch, getAllLogisticsFile, updateLogisticsFile } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const relation = (field, labelKey, placeholderKey, getAll, idField, displayField, required = false) => ({ field, labelKey, placeholderKey, getAll, idField, displayField, required });
const config = {
  singularKey: "logistics.file_singular", pluralKey: "logistics.file_plural", articleKey: "logistics.file_article", newLabelKey: "logistics.file_new", idField: "id_logistics_file", displayField: "folio",
  getAll: getAllLogisticsFile, create: createLogisticsFile, update: updateLogisticsFile, remove: deleteLogisticsFile,
  relations: [
    relation("id_customer_supplier", "logistics.customer", "logistics.select_customer", () => getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }), "id_customer_supplier", "name", true),
    relation("id_logistics_branch", "logistics.branch", "logistics.no_branch", () => getAllLogisticsBranch({ page: 1, per_page: 500 }), "id_logistics_branch", "name"),
    relation("id_invoice", "logistics.invoice", "logistics.no_invoice", () => getAllInvoice({ page: 1, per_page: 500 }), "id_invoice", "folio"),
  ],
  emptyForm: { id_customer_supplier: "", id_logistics_branch: "", id_invoice: "", folio: "", origin: "", destination: "", payment_form: "99", payment_method: "PUE", cfdi_use: "G03", status: "abierto", last_invoice_error: "", notes: "" },
  fields: [
    { name: "folio", labelKey: "logistics.folio", required: true, maxLength: 80 }, { name: "origin", labelKey: "logistics.origin", type: "textarea", required: true }, { name: "destination", labelKey: "logistics.destination", type: "textarea", required: true },
    { name: "payment_form", labelKey: "logistics.payment_form", required: true, maxLength: 10 }, { name: "payment_method", labelKey: "logistics.payment_method", required: true, maxLength: 10 }, { name: "cfdi_use", labelKey: "logistics.cfdi_use", required: true, maxLength: 10 },
    { name: "status", labelKey: "logistics.status", options: [{ value: "abierto", labelKey: "logistics.status_open" }, { value: "facturando", labelKey: "logistics.status_invoicing" }, { value: "facturado", labelKey: "logistics.status_invoiced" }] },
    { name: "last_invoice_error", labelKey: "logistics.last_invoice_error", type: "textarea" }, { name: "notes", labelKey: "logistics.notes", type: "textarea" },
  ],
  searchFields: ["folio", "origin", "destination", "status", "last_invoice_error", "notes"],
  columns: [{ name: "folio", labelKey: "logistics.folio" }, { name: "origin", labelKey: "logistics.origin" }, { name: "destination", labelKey: "logistics.destination" }, { name: "payment_form", labelKey: "logistics.payment_form_short" }, { name: "payment_method", labelKey: "logistics.method" }, { name: "status", labelKey: "logistics.status" }, { name: "last_invoice_error", labelKey: "logistics.invoice_error" }],
  emptyMessageKey: "logistics.file_empty",
};

export default function LogisticsFilesPage() { return <LogisticsEntityPage config={config} />; }