
import { createLogisticsEvidence, deleteLogisticsEvidence, getAllLogisticsEvidence, getAllLogisticsTrip, getAllUser, updateLogisticsEvidence } from "../../api";
import LogisticsEntityPage from "./LogisticsEntityPage.jsx";

const config = {
  singularKey: "logistics.evidence_singular", pluralKey: "logistics.evidence_plural", articleKey: "logistics.evidence_article", newLabelKey: "logistics.evidence_new", idField: "id_logistics_evidence", displayField: "evidence_type",
  getAll: getAllLogisticsEvidence, create: createLogisticsEvidence, update: updateLogisticsEvidence, remove: deleteLogisticsEvidence,
  relations: [
    { field: "id_logistics_trip", labelKey: "logistics.trip", placeholderKey: "logistics.select_trip", getAll: () => getAllLogisticsTrip({ page: 1, per_page: 500 }), idField: "id_logistics_trip", displayField: "folio" },
    { field: "captured_by", labelKey: "logistics.captured_by", placeholderKey: "logistics.current_user", getAll: () => getAllUser({ page: 1, per_page: 500 }), idField: "id_user", displayField: "full_name", required: false },
  ],
  emptyForm: { id_logistics_trip: "", captured_by: "", evidence_type: "", photo_path: "", signature_path: "", source_document_reference: "", latitude: "", longitude: "", comments: "", captured_at: "" },
  fields: [
    { name: "evidence_type", labelKey: "logistics.evidence_type", required: true, maxLength: 80 }, { name: "photo_path", labelKey: "logistics.photo_path", maxLength: 300 }, { name: "signature_path", labelKey: "logistics.signature_path", maxLength: 300 },
    { name: "source_document_reference", labelKey: "logistics.document_reference", maxLength: 120 }, { name: "latitude", labelKey: "logistics.latitude", type: "number", min: "-90", step: "0.0000001" }, { name: "longitude", labelKey: "logistics.longitude", type: "number", min: "-180", step: "0.0000001" },
    { name: "captured_at", labelKey: "logistics.captured_at", type: "datetime-local" }, { name: "comments", labelKey: "logistics.comments", type: "textarea" },
  ],
  searchFields: ["evidence_type", "comments", "source_document_reference"],
  columns: [{ name: "evidence_type", labelKey: "logistics.type" }, { name: "captured_at", labelKey: "logistics.capture" }, { name: "latitude", labelKey: "logistics.latitude" }, { name: "longitude", labelKey: "logistics.longitude" }, { name: "comments", labelKey: "logistics.comments" }],
  emptyMessageKey: "logistics.evidence_empty",
};

export default function LogisticsEvidencesPage() { return <LogisticsEntityPage config={config} />; }