
import { createLogisticsReceivable, deleteLogisticsReceivable, getAllCustomerSupplier, getAllInvoice, getAllLogisticsReceivable, updateLogisticsReceivable } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const relation = (field, labelKey, placeholderKey, getAll, idField, displayField) => ({ field, labelKey, placeholderKey, getAll, idField, displayField, required: true });
const config = {
  singularKey: "logistics.receivable_singular", pluralKey: "logistics.receivable_plural", articleKey: "logistics.receivable_article", newLabelKey: "logistics.receivable_new", idField: "id_logistics_receivable", displayField: "id_logistics_receivable",
  getAll: getAllLogisticsReceivable, create: createLogisticsReceivable, update: updateLogisticsReceivable, remove: deleteLogisticsReceivable,
  relations: [
    relation("id_invoice", "logistics.invoice", "logistics.select_invoice", () => getAllInvoice({ page: 1, per_page: 500 }), "id_invoice", "folio"),
    relation("id_customer_supplier", "logistics.customer", "logistics.select_customer", () => getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }), "id_customer_supplier", "name"),
  ],
  emptyForm: { id_invoice: "", id_customer_supplier: "", amount: "0", due_at: "", status: "pendiente", paid_at: "" },
  fields: [
    { name: "amount", labelKey: "logistics.amount", type: "number", required: true, min: "0", step: "0.01" }, { name: "due_at", labelKey: "logistics.due_date", type: "date", required: true },
    { name: "status", labelKey: "logistics.status", options: [{ value: "pendiente", labelKey: "logistics.status_pending" }, { value: "pagado", labelKey: "logistics.status_paid" }, { value: "vencido", labelKey: "logistics.status_overdue" }] }, { name: "paid_at", labelKey: "logistics.payment_date", type: "date" },
  ],
  searchFields: ["status", "due_at", "paid_at"],
  columns: [{ name: "amount", labelKey: "logistics.amount" }, { name: "due_at", labelKey: "logistics.expiration" }, { name: "status", labelKey: "logistics.status" }, { name: "paid_at", labelKey: "logistics.paid_on" }],
  emptyMessageKey: "logistics.receivable_empty",
};

export default function LogisticsReceivablesPage() { return <LogisticsEntityPage config={config} />; }