import { useI18n } from "../i18n";

export default function Dashboard() {
  const { t } = useI18n();
  return (
    <section className="dashboard">
      <div className="hero-card">
        <p className="eyebrow">Arquitectura empresarial conectada</p>
        <h2>{t("common.dashboard")}</h2>
        <p>Vista ejecutiva generada desde CSV para operar ERP, CRM y SCM con datos consistentes.</p>
      </div>
      <div className="metric-grid">
        <article className="metric-card" key="bank">
          <span>{t("menu.bank")}</span>
          <strong>6</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="bank_account">
          <span>{t("menu.bank_account")}</span>
          <strong>13</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="brand">
          <span>{t("menu.brand")}</span>
          <strong>6</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="customer_supplier">
          <span>{t("menu.customer_supplier")}</span>
          <strong>24</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="department">
          <span>{t("menu.department")}</span>
          <strong>6</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="entity_permission">
          <span>{t("menu.entity_permission")}</span>
          <strong>8</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="event_log">
          <span>{t("menu.event_log")}</span>
          <strong>10</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="field">
          <span>{t("menu.field")}</span>
          <strong>7</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="fiscal_account">
          <span>{t("menu.fiscal_account")}</span>
          <strong>8</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
        <article className="metric-card" key="incident">
          <span>{t("menu.incident")}</span>
          <strong>12</strong>
          <small>{t("common.defined_fields")}</small>
        </article>
      </div>
    </section>
  );
}
