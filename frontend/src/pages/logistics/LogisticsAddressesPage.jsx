
import { createLogisticsAddress, deleteLogisticsAddress, getAllLogisticsAddress, updateLogisticsAddress } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const statusOptions = [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }];

const logisticsAddressConfig = {
  moduleLabelKey: "logistics.crm",
  singularKey: "logistics.address_singular",
  pluralKey: "logistics.address_plural",
  articleKey: "logistics.address_article",
  newLabelKey: "logistics.address_new",
  idField: "id_logistics_address",
  displayField: "name",
  getAll: getAllLogisticsAddress,
  create: createLogisticsAddress,
  update: updateLogisticsAddress,
  remove: deleteLogisticsAddress,
  emptyForm: { id_customer_supplier: "", name: "", address_line: "", city: "", state: "", country: "MX", postal_code: "", address_type: "operativa", status: "activo" },
  fields: [
    { name: "name", labelKey: "logistics.name", required: true, maxLength: 150 },
    { name: "address_line", labelKey: "logistics.address", required: true, maxLength: 250 },
    { name: "city", labelKey: "logistics.city", maxLength: 100 },
    { name: "state", labelKey: "logistics.state", maxLength: 100 },
    { name: "country", labelKey: "logistics.country", maxLength: 2 },
    { name: "postal_code", labelKey: "logistics.postal_code", maxLength: 10 },
    { name: "address_type", labelKey: "logistics.type", required: true, maxLength: 30 },
    { name: "status", labelKey: "logistics.record_status", options: statusOptions },
  ],
  searchFields: ["name", "address_line", "city", "state", "postal_code", "address_type"],
  columns: [
    { name: "name", labelKey: "logistics.name" },
    { name: "address_line", labelKey: "logistics.address" },
    { name: "city", labelKey: "logistics.city" },
    { name: "state", labelKey: "logistics.state" },
    { name: "postal_code", labelKey: "logistics.postal_abbreviation" },
    { name: "address_type", labelKey: "logistics.type" },
    { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.address_empty",
};

export default function LogisticsAddressesPage() {
  return <LogisticsEntityPage config={logisticsAddressConfig} />;
}