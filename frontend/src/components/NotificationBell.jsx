import { Bell } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getNotifications, getUnreadCount, markNotificationAsRead } from "../api";
import { useI18n } from "../i18n";
import "./NotificationBell.css";

export default function NotificationBell() {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef(null);
  const bellRef = useRef(null);

  // Cargar notificaciones y contador
  useEffect(() => {
    loadNotifications();
    loadUnreadCount();

    // Poll cada 30 segundos
    const interval = setInterval(() => {
      loadUnreadCount();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Cerrar panel si clickea afuera
  useEffect(() => {
    function handleClickOutside(e) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target) &&
        bellRef.current &&
        !bellRef.current.contains(e.target)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function loadUnreadCount() {
    try {
      const data = await getUnreadCount();
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      console.error("Error cargando contador de notificaciones:", err);
    }
  }

  async function loadNotifications() {
    setLoading(true);
    try {
      // Solo las no leidas: una vez que se da "Enterado" desaparece de aqui.
      // Es la unica manera de que una notificacion salga de esta lista -- no
      // hay boton de cerrar por fila -- para que nadie pueda decir despues
      // que no la vio.
      const data = await getNotifications({ unread: true, limit: 20 });
      setNotifications(data || []);
    } catch (err) {
      console.error("Error cargando notificaciones:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAcknowledge(id) {
    try {
      await markNotificationAsRead(id);
      // Se retira de la vista solo tras confirmar "Enterado" en el backend;
      // si la peticion falla, se queda donde estaba (no desaparece "gratis").
      setNotifications((prev) => prev.filter((n) => n.id_notification !== id));
      loadUnreadCount();
    } catch (err) {
      console.error("Error al confirmar notificación como enterado:", err);
    }
  }

  return (
    <div className="notification-bell-container">
      <button
        ref={bellRef}
        className="button ghost notification-bell"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) loadNotifications();
        }}
        title={t("common.notifications", "Notificaciones")}
        aria-label={t("common.notifications", "Notificaciones")}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div
          ref={panelRef}
          className="notification-panel"
          role="complementary"
        >
          <div className="notification-panel-header">
            <h3>{t("common.notifications", "Notificaciones")}</h3>
            <button
              className="button ghost notification-close"
              onClick={() => setIsOpen(false)}
              title={t("common.close", "Cerrar")}
            >
              ✕
            </button>
          </div>

          <div className="notification-panel-content">
            {loading ? (
              <div className="notification-loading">
                {t("common.loading", "Cargando...")}
              </div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">
                {t(
                  "common.no_notifications",
                  "Todo al día — sin notificaciones pendientes"
                )}
              </div>
            ) : (
              <div className="notification-list">
                {notifications.map((notif) => (
                  <div key={notif.id_notification} className="notification-item unread">
                    <div className="notification-item-content">
                      <div className="notification-item-title">
                        {notif.title}
                      </div>
                      {notif.message && (
                        <div className="notification-item-message">
                          {notif.message}
                        </div>
                      )}
                      <div className="notification-item-time">
                        {new Date(notif.creation_date).toLocaleString()}
                      </div>
                      <button
                        className="notification-item-acknowledge"
                        onClick={() => handleAcknowledge(notif.id_notification)}
                        title={t(
                          "common.acknowledge_hint",
                          "Confirmar que la leíste; es la única forma de quitarla de esta lista"
                        )}
                      >
                        {t("common.acknowledge", "Enterado")}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="notification-panel-footer">
            <button
              className="button ghost notification-refresh"
              onClick={loadNotifications}
              disabled={loading}
            >
              {t("common.refresh", "Actualizar")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
