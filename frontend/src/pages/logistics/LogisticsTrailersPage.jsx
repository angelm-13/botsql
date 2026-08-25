import React from "react";

import { createLogisticsTrailer, deleteLogisticsTrailer, getAllLogisticsTrailer, updateLogisticsTrailer } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const logisticsTrailerConfig = {
  singularKey: "logistics.trailer_singular",
  pluralKey: "logistics.trailer_plural",
  articleKey: "logistics.trailer_article",
  newLabelKey: "logistics.trailer_new",
  idField: "id_logistics_trailer",
  displayField: "plate",
  relation: null,
  getAll: getAllLogisticsTrailer,
  create: createLogisticsTrailer,
  update: updateLogisticsTrailer,
  remove: deleteLogisticsTrailer,
  emptyForm: { plate: "", trailer_type: "", capacity: "", status: "activo" },
  fields: [
    { name: "plate", labelKey: "logistics.plates", required: true, maxLength: 30 },
    { name: "trailer_type", labelKey: "logistics.trailer_type", required: true, maxLength: 80 },
    { name: "capacity", labelKey: "logistics.capacity", type: "number", min: "0", step: "0.01" },
    { name: "status", labelKey: "logistics.status", options: [{ value: "activo", labelKey: "logistics.status_active" }, { value: "inactivo", labelKey: "logistics.status_inactive" }] },
  ],
  searchFields: ["plate", "trailer_type", "status"],
  columns: [
    { name: "plate", labelKey: "logistics.plates" },
    { name: "trailer_type", labelKey: "logistics.type" },
    { name: "capacity", labelKey: "logistics.capacity" },
    { name: "status", labelKey: "logistics.status" },
  ],
  emptyMessageKey: "logistics.trailer_empty",
};

export default function LogisticsTrailersPage() {
  return <LogisticsEntityPage config={logisticsTrailerConfig} />;
}