import React, { useMemo, useState } from "react";
import { ArrowRight, FileText, Pencil, Plus, Search } from "lucide-react";
import { useI18n } from "../i18n";

/* eslint-disable react/prop-types */

export const QUOTATION_STATUS_CODES = ["draft", "sent", "partially_approved", "approved", "rejected", "converted"];

const STATUS_COLUMNS = [
  { code: "draft", tone: "neutral" },
  { code: "sent", tone: "info" },
  { code: "partially_approved", tone: "warning" },
  { code: "approved", tone: "success" },
  { code: "rejected", tone: "danger" },
  { code: "converted", tone: "complete" },
];

const TRANSITION_TARGETS = {
  draft: ["sent"],
  sent: ["partially_approved", "approved", "rejected"],
  partially_approved: ["approved", "rejected"],
  approved: ["converted"],
  rejected: ["draft"],
  converted: [],
};

export function normalizeQuotationStatus(value) {
  const status = String(value || "").trim().toLowerCase();
  if (status === "cotizacion" || status === "cotización") return "draft";
  return status;
}

export function quotationStatusLabel(value, t) {
  const status = normalizeQuotationStatus(value);
  return t ? t(`logistics.quotation_status_${status}`, String(value || t("logistics.no_status"))) : String(value || "Sin estado");
}

function money(value, currency = "MXN", locale = "es") {
  return new Intl.NumberFormat(locale, { style: "currency", currency: currency || "MXN" }).format(Number(value || 0));
}

function quotationFolio(quotation) {
  if (String(quotation.folio || "").trim()) return quotation.folio;
  return `COT-${String(quotation.id_invoice || "").padStart(6, "0")}`;
}

function dateLabel(value, locale) {
  if (!value) return null;
  return new Date(`${String(value).slice(0, 10)}T00:00:00`).toLocaleDateString(locale);
}

export default function QuotationWorkflowBoard({ quotations, customers, projects, itemCounts, loading, transitioningId, onTransition, onView, onEdit, onCreate }) {
  const { lang, t } = useI18n();
  const statusLabel = (value) => quotationStatusLabel(value, t);
  const [query, setQuery] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const customerById = useMemo(() => Object.fromEntries(customers.map((item) => [Number(item.id_customer_supplier), item])), [customers]);
  const projectById = useMemo(() => Object.fromEntries(projects.map((item) => [Number(item.id_proyect), item])), [projects]);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return quotations.filter((quotation) => {
      const customer = customerById[Number(quotation.id_customer_supplier)];
      const project = projectById[Number(quotation.id_proyect)];
      const issued = String(quotation.date_emision || "").slice(0, 10);
      if (customerId && String(quotation.id_customer_supplier) !== customerId) return false;
      if (startDate && issued < startDate) return false;
      if (endDate && issued > endDate) return false;
      if (!needle) return true;
      return [quotationFolio(quotation), customer?.name, customer?.tax_id, project?.title, project?.proyect_description]
        .some((value) => String(value || "").toLowerCase().includes(needle));
    });
  }, [customerById, customerId, endDate, projectById, query, quotations, startDate]);
  const totalValue = filtered.reduce((sum, quotation) => sum + Number(quotation.total || 0), 0);
  const approvedCount = filtered.filter((quotation) => ["approved", "converted"].includes(normalizeQuotationStatus(quotation.invoice_status))).length;
  const conversionRate = filtered.length ? Math.round((approvedCount / filtered.length) * 100) : 0;

  return (
    <div className="quotation-workflow">
      <div className="quotation-workflow-toolbar">
        <div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("logistics.quotation_search")} /></div>
        <select value={customerId} onChange={(event) => setCustomerId(event.target.value)} aria-label={t("logistics.filter_customer")}><option value="">{t("logistics.all_customers")}</option>{customers.map((customer) => <option key={customer.id_customer_supplier} value={customer.id_customer_supplier}>{customer.name}</option>)}</select>
        <label>{t("logistics.from")}<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
        <label>{t("logistics.to")}<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
        <button type="button" className="button primary" onClick={onCreate}><Plus size={16} />{t("logistics.new_quotation")}</button>
      </div>

      <div className="quotation-kpis">
        <div><span>{t("logistics.quotations")}</span><strong>{filtered.length}</strong></div>
        <div><span>{t("logistics.commercial_value")}</span><strong>{money(totalValue, "MXN", lang)}</strong></div>
        <div><span>{t("logistics.approved_plural")}</span><strong>{approvedCount}</strong></div>
        <div><span>{t("logistics.conversion")}</span><strong>{conversionRate}%</strong></div>
      </div>

      {loading ? <div className="alert">{t("logistics.loading_board")}</div> : (
        <div className="quotation-kanban" aria-label={t("logistics.quotation_board")}>
          {STATUS_COLUMNS.map((column) => {
            const cards = filtered.filter((quotation) => normalizeQuotationStatus(quotation.invoice_status) === column.code);
            return (
              <section className={`quotation-kanban-column tone-${column.tone}`} key={column.code}>
                <header><span>{statusLabel(column.code)}</span><strong>{cards.length}</strong></header>
                <div className="quotation-kanban-cards">
                  {cards.map((quotation) => {
                    const customer = customerById[Number(quotation.id_customer_supplier)];
                    const project = projectById[Number(quotation.id_proyect)];
                    const targets = TRANSITION_TARGETS[column.code] || [];
                    return (
                      <article className="quotation-kanban-card" key={quotation.id_invoice}>
                        <div className="quotation-kanban-card-heading"><strong>{quotationFolio(quotation)}</strong><span>{money(quotation.total, quotation.currency, lang)}</span></div>
                        <p>{customer?.name || `${t("logistics.customer")} #${quotation.id_customer_supplier}`}</p>
                        <dl><div><dt>{t("logistics.project")}</dt><dd>{project?.title || project?.proyect_description || t("logistics.no_project")}</dd></div><div><dt>{t("logistics.issued")}</dt><dd>{dateLabel(quotation.date_emision, lang) || t("logistics.no_date")}</dd></div><div><dt>{t("logistics.line_items")}</dt><dd>{itemCounts[quotation.id_invoice] || 0}</dd></div></dl>
                        <div className="quotation-kanban-actions">
                          <button type="button" className="icon-button" title={t("logistics.view_detail")} aria-label={`${t("logistics.view")} ${quotationFolio(quotation)}`} onClick={() => onView(quotation)}><FileText size={15} /></button>
                          <button type="button" className="icon-button" title={t("logistics.edit_quotation")} aria-label={`${t("logistics.edit")} ${quotationFolio(quotation)}`} onClick={() => onEdit(quotation)}><Pencil size={15} /></button>
                          {targets.length > 0 && <label className="quotation-transition"><ArrowRight size={14} /><select value="" disabled={Number(transitioningId) === Number(quotation.id_invoice)} onChange={(event) => { if (event.target.value) onTransition(quotation, event.target.value); }} aria-label={`${t("logistics.change_status")} ${quotationFolio(quotation)}`}><option value="">{t("logistics.move_to")}</option>{targets.map((target) => <option key={target} value={target}>{statusLabel(target)}</option>)}</select></label>}
                        </div>
                      </article>
                    );
                  })}
                  {!cards.length && <div className="quotation-kanban-empty">{t("logistics.no_quotations")}</div>}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
