import { useEffect, useMemo, useState } from "react";
import { deactivateWebShopper, getWebShoppers, reactivateWebShopper } from "../api";
import { useI18n } from "../i18n";

function asArray(payload) {
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload)) return payload;
  return [];
}

function valueOrDash(value) {
  const text = String(value ?? "").trim();
  return text || "—";
}

function formatDate(value) {
  if (!value) return "—";
  const raw = String(value);
  const normalized = raw.includes("T") ? raw.slice(0, 10) : raw;
  const parts = normalized.split("-");
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return raw;
}

export default function WebShoppersPage() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState("all");
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const counters = useMemo(() => {
    const activeRows = items.filter((item) => item.is_active).length;
    return { active: activeRows, inactive: items.length - activeRows };
  }, [items]);

  function resolveError(err) {
    const payload = err?.payload || err?.response?.data || {};
    const raw = payload?.error_key || err?.error_key || err?.message || "";
    return raw ? t(raw, raw) : t("errors.request_failed", "No se pudo completar la solicitud");
  }

  function loadData() {
    setLoading(true);
    setError("");
    const params = { page: 1, per_page: 100, search };
    if (active !== "all") params.active = active;
    getWebShoppers(params)
      .then((payload) => setItems(asArray(payload)))
      .catch((err) => setError(resolveError(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  function submitFilters(event) {
    event.preventDefault();
    loadData();
  }

  function toggleStatus(row) {
    const id = row.id_user;
    if (!id) return;
    setBusyId(String(id));
    setMessage("");
    setError("");
    const action = row.is_active ? deactivateWebShopper : reactivateWebShopper;
    action(id)
      .then(() => {
        setMessage(row.is_active
          ? t("web_shoppers.deactivated", "Comprador desactivado correctamente.")
          : t("web_shoppers.reactivated", "Comprador reactivado correctamente."));
        loadData();
      })
      .catch((err) => setError(resolveError(err)))
      .finally(() => setBusyId(""));
  }

  return (
    <section className="entity-page web-shoppers-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("web_shoppers.section", "Tienda en línea")}</p>
          <h2>{t("web_shoppers.title", "Compradores Web")}</h2>
          <p className="quotation-subtitle">{t("web_shoppers.subtitle", "Consulta compradores registrados desde la tienda pública y activa o desactiva su acceso.")}</p>
        </div>
        <button type="button" className="button" onClick={loadData} disabled={loading}>
          {loading ? t("common.loading", "Cargando...") : t("common.refresh", "Actualizar")}
        </button>
      </div>

      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <form className="form-card" onSubmit={submitFilters}>
        <div className="form-grid">
          <label className="field wide-field">
            {t("web_shoppers.search", "Buscar por nombre, email, teléfono o RFC")}
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="cliente@correo.com" />
          </label>
          <label className="field">
            {t("web_shoppers.status_filter", "Estado")}
            <select value={active} onChange={(event) => setActive(event.target.value)}>
              <option value="all">{t("common.all", "Todos")}</option>
              <option value="true">{t("web_shoppers.active", "Activos")}</option>
              <option value="false">{t("web_shoppers.inactive", "Inactivos")}</option>
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={loading}>{t("common.search", "Buscar")}</button>
        </div>
      </form>

      <div className="metric-grid">
        <div className="metric-card"><span>{t("web_shoppers.total", "Total")}</span><strong>{items.length}</strong></div>
        <div className="metric-card"><span>{t("web_shoppers.active", "Activos")}</span><strong>{counters.active}</strong></div>
        <div className="metric-card"><span>{t("web_shoppers.inactive", "Inactivos")}</span><strong>{counters.inactive}</strong></div>
      </div>

      <div className="table-card">
        <div className="table-wrap">
          <table className="web-shopper-table">
            <thead>
              <tr>
                <th>{t("web_shoppers.id", "ID")}</th>
                <th>{t("web_shoppers.buyer", "Comprador")}</th>
                <th>{t("web_shoppers.contact", "Contacto")}</th>
                <th>{t("web_shoppers.tax_data", "Datos fiscales")}</th>
                <th>{t("web_shoppers.marketing", "Marketing")}</th>
                <th>{t("web_shoppers.created", "Registro")}</th>
                <th>{t("web_shoppers.last_login", "Último login")}</th>
                <th>{t("web_shoppers.total_orders", "Pedidos")}</th>
                <th>{t("web_shoppers.status", "Estado")}</th>
                <th>{t("web_shoppers.actions", "Acciones")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id_user}>
                  <td><strong>{valueOrDash(row.id_user)}</strong></td>
                  <td><strong className="primary-line" title={valueOrDash(row.full_name)}>{valueOrDash(row.full_name)}</strong><p className="cell-value email-value" title={valueOrDash(row.username)}>{valueOrDash(row.username)}</p></td>
                  <td><strong className="email-value" title={valueOrDash(row.email)}>{valueOrDash(row.email)}</strong><p className="cell-value">{valueOrDash(row.phone || row.principal_phone)}</p></td>
                  <td>{valueOrDash(row.tax_id)}</td>
                  <td>{row.accepts_marketing ? "✓" : "—"}</td>
                  <td>{formatDate(row.creation_date)}</td>
                  <td>{formatDate(row.last_login_at)}</td>
                  <td>{row.total_orders ?? 0}</td>
                  <td>{row.is_active ? t("web_shoppers.active_one", "Activo") : t("web_shoppers.inactive_one", "Inactivo")}</td>
                  <td>
                    <button
                      type="button"
                      className={row.is_active ? "button danger" : "button primary"}
                      disabled={busyId === String(row.id_user)}
                      onClick={() => toggleStatus(row)}
                    >
                      {row.is_active ? t("web_shoppers.deactivate", "Desactivar") : t("web_shoppers.reactivate", "Reactivar")}
                    </button>
                  </td>
                </tr>
              ))}
              {!items.length && <tr><td colSpan="10" className="muted">{t("web_shoppers.empty", "No hay compradores web para los filtros seleccionados.")}</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
