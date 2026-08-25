import React from "react";

import { createLogisticsShipment, deleteLogisticsShipment, getAllLogisticsShipment, updateLogisticsShipment } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.shipment_singular", pluralKey: "logistics.shipment_plural", articleKey: "logistics.shipment_article", newLabelKey: "logistics.shipment_new", idField: "id_logistics_shipment", displayField: "shipment_number",
  getAll: getAllLogisticsShipment, create: createLogisticsShipment, update: updateLogisticsShipment, remove: deleteLogisticsShipment,
  emptyForm: { id_customer_supplier: "", shipment_number: "", bl_number: "", provider: "", transport_mode: "", cargo_type: "", origin_port: "", destination_port: "", customs: "", status: "registrado", tracking: "" },
  fields: [
    { name: "shipment_number", labelKey: "logistics.shipment_number", required: true, maxLength: 80 }, { name: "bl_number", labelKey: "logistics.bl_number", maxLength: 120 },
    { name: "provider", labelKey: "logistics.provider_carrier", maxLength: 180 }, { name: "transport_mode", labelKey: "logistics.transport_mode", maxLength: 60 },
    { name: "cargo_type", labelKey: "logistics.cargo_type", maxLength: 120 }, { name: "origin_port", labelKey: "logistics.origin_port", maxLength: 180 },
    { name: "destination_port", labelKey: "logistics.destination_port", maxLength: 180 }, { name: "customs", labelKey: "logistics.customs", maxLength: 180 },
    { name: "status", labelKey: "logistics.status", options: [{ value: "registrado", labelKey: "logistics.status_registered" }, { value: "en tránsito", labelKey: "logistics.status_in_transit" }, { value: "en aduana", labelKey: "logistics.status_at_customs" }, { value: "liberado", labelKey: "logistics.status_released" }, { value: "entregado", labelKey: "logistics.status_delivered" }] },
    { name: "tracking", labelKey: "logistics.tracking", type: "textarea" },
  ],
  searchFields: ["shipment_number", "bl_number", "provider", "transport_mode", "cargo_type", "origin_port", "destination_port", "customs", "status", "tracking"],
  columns: [{ name: "shipment_number", labelKey: "logistics.shipment" }, { name: "bl_number", labelKey: "logistics.bl" }, { name: "provider", labelKey: "logistics.provider" }, { name: "transport_mode", labelKey: "logistics.mode" }, { name: "origin_port", labelKey: "logistics.origin" }, { name: "destination_port", labelKey: "logistics.destination" }, { name: "status", labelKey: "logistics.status" }],
  emptyMessageKey: "logistics.shipment_empty",
};

export default function LogisticsShipmentsPage() { return <LogisticsEntityPage config={config} />; }