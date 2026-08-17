import { useEffect, useMemo, useState } from "react";
import { getAllCustomerSupplier, getAllInvoice, getAllInvoiceMaterialService, getAllProyect, updateInvoiceMaterialService } from "../api";
import { useI18n } from "../i18n";

function asArray(payload) {
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload)) return payload;
  return [];
}

function formatDate(value) {
  if (!value) return "—";
  const raw = String(value);
  const normalized = raw.includes("T") ? raw.slice(0, 10) : raw;
  const parts = normalized.split("-");
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return raw;
}

function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

function valueOrDash(value) {
  const text = String(value ?? "").trim();
  return text || "—";
}

export default function AuthorizationTrackingPage() {
  const { t } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const [invoices, setInvoices] = useState([]);
  const [items, setItems] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [notes, setNotes] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const invoiceById = useMemo(() => Object.fromEntries(invoices.map((item) => [Number(item.id_invoice), item])), [invoices]);
  const customerById = useMemo(() => Object.fromEntries(customers.map((item) => [Number(item.id_customer_supplier), item])), [customers]);
  const projectById = useMemo(() => Object.fromEntries(projects.map((item) => [Number(item.id_proyect), item])), [projects]);

  const filteredItems = useMemo(() => items
    .filter((line) => {
      const invoice = invoiceById[Number(line.id_invoice)];
      return invoice && ["cotizacion", "pendiente"].includes(String(invoice.invoice_status || "").toLowerCase());
    })
    .filter((line) => statusFilter === "all" || String(line.authorization_status || "pending").toLowerCase() === statusFilter)
    .sort((a, b) => Number(b.id_invoice_material_service || 0) - Number(a.id_invoice_material_service || 0)), [items, invoiceById, statusFilter]);

  function resolveError(err) {
    const payload = err?.payload || err?.response?.data || {};
    const raw = payload?.error_key || err?.error_key || err?.message || "";
    if (raw === "validations.invoice_material_service.authorization_status.required") {
      return t("authorization_tracking.validation_authorization_status_required", "No se pudo guardar porque la partida no tiene estado de autorización inicial.");
    }
    return raw ? t(raw, raw) : t("errors.request_failed", "No se pudo completar la solicitud");
  }

  function loadData() {
    setLoading(true);
    setError("");
    Promise.all([
      getAllInvoice({ per_page: 1000 }),
      getAllInvoiceMaterialService({ per_page: 3000 }),
      getAllCustomerSupplier({ per_page: 1000 }),
      getAllProyect({ per_page: 1000 }),
    ])
      .then(([invoicePayload, itemPayload, customerPayload, projectPayload]) => {
        const itemRows = asArray(itemPayload);
        setInvoices(asArray(invoicePayload));
        setItems(itemRows);
        setCustomers(asArray(customerPayload));
        setProjects(asArray(projectPayload));
        setNotes(Object.fromEntries(itemRows.map((item) => [String(item.id_invoice_material_service), item.authorization_note || ""])));
      })
      .catch((err) => setError(resolveError(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  function invoiceFolio(invoice) {
    const raw = String(invoice?.folio || "").trim();
    if (raw) return raw;
    const id = String(invoice?.id_invoice || "").padStart(6, "0");
    return id ? `COT-${id}` : "—";
  }

  function customerName(invoice) {
    const customer = customerById[Number(invoice?.id_customer_supplier)];
    return valueOrDash(customer?.name || invoice?.nombre_receptor || invoice?.id_customer_supplier);
  }

  function projectName(invoice) {
    const project = projectById[Number(invoice?.id_proyect)];
    return valueOrDash(project?.title || project?.proyect_description || invoice?.id_proyect);
  }

  function lineDescription(line) {
    return valueOrDash(line.invoice_material_service_description);
  }

  function statusLabel(status) {
    const normalized = String(status || "pending").toLowerCase();
    const labels = {
      pending: t("authorization_tracking.status_pending", "Pendiente"),
      authorized: t("authorization_tracking.status_authorized", "Autorizada"),
      rejected: t("authorization_tracking.status_rejected", "No autorizada"),
    };
    return labels[normalized] || valueOrDash(status);
  }

  function authorizedBy(line) {
    return valueOrDash(line.authorized_by_username || line.authorized_by || line.id_authorized);
  }

  function updateNote(lineId, value) {
    setNotes((prev) => ({ ...prev, [String(lineId)]: value }));
  }

  function updateStatus(line, status) {
    const lineId = line.id_invoice_material_service;
    setMessage("");
    setError("");
    const payload = {
      authorization_status: status,
      authorization_note: notes[String(lineId)] || "",
      id_authorized: Number(currentUser?.id_user || currentUser?.id || line.id_authorized || 1),
    };
    updateInvoiceMaterialService(lineId, payload)
      .then(() => {
        setMessage(t("authorization_tracking.saved_success", "Autorización actualizada correctamente."));
        loadData();
      })
      .catch((err) => setError(resolveError(err)));
  }

  function openRequirementPdf(line) {
    const lineId = line?.id_invoice_material_service;
    if (!lineId) return;
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";
    const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
    window.open(`${normalizedBaseUrl}/documents/purchase_requirement/${lineId}?format=pdf`, "_blank", "noopener,noreferrer");
  }

  return (
    <section className="entity-page authorization-tracking-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("authorization_tracking.issue_label", "Issue 12")}</p>
          <h2>{t("authorization_tracking.title", "Autorización / Seguimiento")}</h2>
          <p className="quotation-subtitle">{t("authorization_tracking.subtitle", "Seguimiento funcional de partidas de cotizaciones y facturas.")}</p>
        </div>
        <button type="button" className="button" onClick={loadData} disabled={loading}>
          {loading ? t("common.loading", "Cargando...") : t("authorization_tracking.reload", "Recargar datos")}
        </button>
      </div>

      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="form-card authorization-filter-card">
        <label className="field">
          {t("authorization_tracking.filter_status", "Estado")}
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">{t("authorization_tracking.status_all", "Todos")}</option>
            <option value="pending">{t("authorization_tracking.status_pending", "Pendiente")}</option>
            <option value="authorized">{t("authorization_tracking.status_authorized", "Autorizada")}</option>
            <option value="rejected">{t("authorization_tracking.status_rejected", "No autorizada")}</option>
          </select>
        </label>
        <div className="metric-card"><strong>{filteredItems.length}</strong> {t("authorization_tracking.items_count", "partida(s)")}</div>
      </div>

      <div className="table-card authorization-table-card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("authorization_tracking.document", "Documento")}</th>
                <th>{t("authorization_tracking.client_project", "Cliente / Proyecto")}</th>
                <th>{t("authorization_tracking.line_item", "Partida")}</th>
                <th>{t("authorization_tracking.quantity", "Cantidad")}</th>
                <th>{t("authorization_tracking.amount", "Importe")}</th>
                <th>{t("authorization_tracking.authorization", "Autorización")}</th>
                <th>{t("authorization_tracking.note", "Nota")}</th>
                <th>{t("authorization_tracking.actions", "Acciones")}</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((line) => {
                const invoice = invoiceById[Number(line.id_invoice)] || {};
                const lineId = line.id_invoice_material_service;
                const status = String(line.authorization_status || "pending").toLowerCase();
                const subtotal = Number(line.line_total || 0);
                const tax = Number(line.line_tax || 0);
                return (
                  <tr key={lineId}>
                    <td><strong>{invoiceFolio(invoice)}</strong><p className="cell-value">{valueOrDash(invoice.invoice_status)}</p></td>
                    <td><strong>{customerName(invoice)}</strong><p className="cell-value">{projectName(invoice)}</p></td>
                    <td><strong>{lineDescription(line)}</strong><p className="cell-value">{valueOrDash(line.line_type)}</p></td>
                    <td><strong>{valueOrDash(line.quantity)}</strong><p className="cell-value">{valueOrDash(line.unit_label || line.id_unit)}</p></td>
                    <td><strong>{money(subtotal + tax)}</strong><p className="cell-value">{t("authorization_tracking.subtotal", "Subtotal")} {money(subtotal)} · {t("authorization_tracking.tax", "IVA")} {money(tax)}</p></td>
                    <td><strong>{statusLabel(status)}</strong><p className="cell-value">{t("authorization_tracking.by", "Por")}: {authorizedBy(line)}</p><p className="cell-value">{formatDate(line.authorization_date)}</p></td>
                    <td>
                      <textarea
                        value={notes[String(lineId)] || ""}
                        onChange={(event) => updateNote(lineId, event.target.value)}
                        placeholder={t("authorization_tracking.note_placeholder", "Escribe nota y presiona Pendiente, Autorizar o No autorizar para guardar")}
                      />
                    </td>
                    <td>
                      <div className="authorization-actions">
                        <button type="button" className="button" onClick={() => updateStatus(line, "pending")}>{t("authorization_tracking.action_pending", "Pendiente")}</button>
                        <button type="button" className="button" onClick={() => updateStatus(line, "authorized")}>{t("authorization_tracking.action_authorize", "Autorizar")}</button>
                        <button type="button" className="button" onClick={() => updateStatus(line, "rejected")}>{t("authorization_tracking.action_reject", "No autorizar")}</button>
                        {status === "authorized" ? (
                          <button type="button" className="button primary" onClick={() => openRequirementPdf(line)}>{t("authorization_tracking.requirement_pdf", "Requerimiento PDF")}</button>
                        ) : (
                          <small className="muted">{t("authorization_tracking.requires_authorization", "Requiere autorización")}</small>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!filteredItems.length && (
                <tr><td colSpan="8" className="muted">{t("authorization_tracking.empty", "No hay partidas para el filtro seleccionado.")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
