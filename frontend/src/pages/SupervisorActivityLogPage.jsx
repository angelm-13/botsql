import { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import { createSupervisorActivityLogEntry, getSupervisorActivityLog } from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function SupervisorActivityLogPage() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [activityDate, setActivityDate] = useState(today());
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  function load() {
    setLoading(true);
    getSupervisorActivityLog({ per_page: 100, sort: "-activity_date" })
      .then((respuesta) => { setItems(respuesta?.items || []); setError(""); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!content.trim()) return;
    setSaving(true);
    setError(""); setNotice("");
    try {
      await createSupervisorActivityLogEntry({ activity_date: activityDate, content: content.trim() });
      setContent("");
      setNotice(t("notifications.activity_log.saved", "Actividad registrada."));
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("notifications.activity_log.title", "Bitácora de actividades")}
        titulo={t("notifications.activity_log.title", "Bitácora de actividades")}
      />
      {notice && <div className="alert success">{notice}</div>}
      {error && <div className="alert error">{error}</div>}
      <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-header"><ClipboardList size={20} /><strong>{t("notifications.activity_log.new_entry", "Nueva actividad")}</strong></div>
        <div className="form-grid">
          <label className="field">
            <span>{t("notifications.activity_log.date", "Fecha")}</span>
            <input type="date" required value={activityDate} onChange={(event) => setActivityDate(event.target.value)} />
          </label>
        </div>
        <label className="field">
          <span>{t("notifications.activity_log.content", "Actividad realizada")}</span>
          <textarea required rows={3} value={content} onChange={(event) => setContent(event.target.value)} />
        </label>
        <div className="form-actions">
          <button className="button primary" type="submit" disabled={saving}>{t("notifications.activity_log.save", "Guardar")}</button>
        </div>
      </form>
      <div className="table-card">
        {loading ? (
          <div className="empty">{t("common.loading", "Cargando…")}</div>
        ) : items.length ? (
          <table>
            <thead>
              <tr>
                <th>{t("notifications.activity_log.date", "Fecha")}</th>
                <th>{t("notifications.activity_log.content", "Actividad realizada")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id_supervisor_activity_log}>
                  <td>{item.activity_date}</td>
                  <td><p className="cell-value">{item.content}</p></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty">{t("notifications.activity_log.empty", "Sin actividades registradas")}</div>
        )}
      </div>
    </section>
  );
}
