import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { getNotifications, markAllNotificationsRead, markNotificationRead } from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";

export default function NotificationsPage() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    getNotifications({ per_page: 50 })
      .then((respuesta) => { setItems(respuesta?.items || []); setError(""); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  function marcarLeida(item) {
    if (item.read_at) return;
    markNotificationRead(item.id_notification)
      .then(() => setItems((actuales) => actuales.map((row) =>
        row.id_notification === item.id_notification ? { ...row, read_at: new Date().toISOString() } : row
      )))
      .catch((err) => setError(err.message));
  }

  function marcarTodas() {
    markAllNotificationsRead()
      .then(() => setItems((actuales) => actuales.map((row) => ({ ...row, read_at: row.read_at || new Date().toISOString() }))))
      .catch((err) => setError(err.message));
  }

  const unreadCount = items.filter((item) => !item.read_at).length;

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("notifications.title", "Notificaciones")}
        titulo={t("notifications.title", "Notificaciones")}
      />
      {error && <div className="alert error">{error}</div>}
      <div className="table-card">
        <div className="toolbar">
          <button className="button ghost" onClick={load}>{t("common.refresh", "Actualizar")}</button>
          {unreadCount > 0 && (
            <button className="button" onClick={marcarTodas}>{t("notifications.mark_all_read", "Marcar todas leídas")}</button>
          )}
        </div>
        {loading ? (
          <div className="empty">{t("common.loading", "Cargando…")}</div>
        ) : items.length ? (
          <table>
            <thead>
              <tr>
                <th></th>
                <th>{t("common.title", "Título")}</th>
                <th>{t("common.description", "Detalle")}</th>
                <th>{t("common.date", "Fecha")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id_notification} className={item.read_at ? "" : "selected-row"}>
                  <td><Bell size={16} /></td>
                  <td>
                    <button className="button ghost" onClick={() => marcarLeida(item)}>
                      {item.title}
                    </button>
                  </td>
                  <td><p className="cell-value">{item.content || ""}</p></td>
                  <td>{item.creation_date ? new Date(item.creation_date).toLocaleString() : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty">{t("notifications.empty", "Sin notificaciones")}</div>
        )}
      </div>
    </section>
  );
}
