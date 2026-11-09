import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Truck } from "lucide-react";
import { getPurchaseRentals } from "../api";
import RentaDeMaquinaria from "./RentaDeMaquinaria.jsx";
import { useI18n } from "../i18n";
import "../styles/renta-maquinaria.css";

/**
 * Rentas activas: la maquinaria rentada que esta contratada o en obra y no se ha
 * devuelto, lo vencido y lo que vence primero arriba. Se abre sola si hay algo vencido,
 * por vencer o una prorroga por decidir; si no hay rentas, no se muestra.
 */
export default function RentasActivas({ version = 0, onAbrirOrden, onCambio }) {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  // null: que decida la urgencia; despues, lo que eligio quien mira (no se cierra sola
  // justo despues de aprobar una prorroga).
  const [abierta, setAbierta] = useState(null);

  const cargar = useCallback(async () => {
    setError("");
    try {
      setDatos(await getPurchaseRentals({ status: "active" }));
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key, "No se pudieron cargar las rentas.")
        : traducir.current("errors.request_failed", "No se pudieron cargar las rentas."));
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar, version]);

  if (error) return <div className="alert error">{error}</div>;
  if (!datos || datos.total === 0) return null;
  const urgente = datos.overdue > 0 || datos.due_soon > 0 || datos.pending_extensions > 0;

  return (
    <details className="oc-agregar rentas-activas" open={abierta ?? urgente}
             onToggle={(e) => setAbierta(e.currentTarget.open)}>
      <summary>
        <Truck size={15} /> {t("rental.active_title", "Rentas de maquinaria")}{" "}
        <span className="muted">({datos.total})</span>
      </summary>
      <div className="rentas-activas-resumen">
        <span className="renta-etapa en-obra">
          {datos.on_site} {t("rental.summary_on_site", "en obra")}
        </span>
        {datos.due_soon > 0 && (
          <span className="renta-etapa por-vencer">
            {datos.due_soon} {t("rental.summary_due_soon", "por vencer")}
          </span>
        )}
        {datos.overdue > 0 && (
          <span className="renta-etapa vencida">
            {datos.overdue} {t("rental.summary_overdue", "vencidas")}
          </span>
        )}
        {datos.pending_extensions > 0 && (
          <span className="renta-etapa pedida">
            {datos.pending_extensions} {t("rental.summary_extensions", "prórrogas por decidir")}
          </span>
        )}
      </div>
      <ul className="rentas-activas-lista">
        {datos.items.map((r) => (
          <li key={r.id_purchase_order_line}>
            <div className="rentas-activas-cabeza">
              <span>
                <strong>{r.description}</strong>
                {r.quantity > 1 && <span className="muted"> × {r.quantity}</span>}
                <span className="muted">
                  {" · "}{r.project ? `#${r.project.folio || r.project.id_proyect}${r.project.title ? ` — ${r.project.title}` : ""}`
                    : t("order.no_project", "Sin proyecto")}
                  {" · "}{r.supplier_name}
                </span>
              </span>
              <button type="button" className="button button-quiet"
                      onClick={() => onAbrirOrden?.(r.id_purchase_order)}>
                {r.order_folio}
              </button>
            </div>
            <RentaDeMaquinaria renta={r} compacta
                               onCambio={(orden) => { cargar(); onCambio?.(orden); }} />
          </li>
        ))}
      </ul>
    </details>
  );
}

RentasActivas.propTypes = {
  version: PropTypes.number,
  onAbrirOrden: PropTypes.func,
  onCambio: PropTypes.func,
};
