import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { AlertTriangle, CalendarClock, Package } from "lucide-react";
import { getProductLots } from "../api";
import { useI18n } from "../i18n";

/**
 * El desglose por lote de un producto, con lo que le queda a cada uno.
 *
 * Qué contesta
 * ------------
 * Un saldo de 300 sacos no dice cuándo caduca ninguno. Con eso, lo que se vence
 * se descubre en el anaquel, y quien lo descubre ya no puede hacer nada: ni
 * devolverlo al proveedor, ni sacarlo antes, ni dejar de comprar tanto.
 *
 * El orden es el mismo en que va a salir: primero lo que vence primero, y lo que
 * no tiene fecha al final. Así la lista se lee como la fila del anaquel, y el de
 * arriba es siempre el siguiente en salir.
 *
 * Solo se pinta para productos que llevan lotes. El resto de la pantalla no
 * cambia.
 */

// Cuánto queda de plazo antes de que un lote pase a ser un problema. No es una
// regla del negocio, es dónde se pinta el color: lo vencido, lo que urge y lo
// que todavía da tiempo.
const URGE = 30;

export default function ProductLots({ idProduct, refrescar }) {
  const { t } = useI18n();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");

  const traducir = useRef(t);
  traducir.current = t;

  const cargar = useCallback(async () => {
    setError("");
    try {
      // `refrescar` no se usa aqui: esta en las dependencias a proposito, para
      // que un movimiento que toco los lotes vuelva a pedir el desglose sin
      // recargar la pantalla entera.
      void refrescar;
      setDatos(await getProductLots(idProduct));
    } catch (e) {
      setDatos(null);
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed",
          "No se pudieron cargar los lotes."));
    }
  }, [idProduct, refrescar]);

  useEffect(() => { cargar(); }, [cargar]);

  if (error) return <p className="error">{error}</p>;
  if (!datos) return null;

  const tono = (lote) => {
    if (lote.expired) return "crit";
    if (lote.days_to_expiry === null) return "muted";
    if (lote.days_to_expiry <= URGE) return "warn";
    return "ok";
  };

  return (
    <section className="inv-lotes">
      <h3>
        <CalendarClock size={16} />
        {t("inventory.lots", "Lotes")}
        <em>
          {datos.total_quantity} {t("inventory.units", "unidades")}
          {" · "}
          {datos.total} {t("inventory.lots_count", "lotes")}
        </em>
      </h3>

      {datos.items.length === 0 ? (
        <p className="muted">
          {t("inventory.no_lots",
            "Sin lotes todavía. La próxima entrada crea el suyo.")}
        </p>
      ) : (
        <ul>
          {/* En el mismo orden en que van a salir, así el de arriba es siempre
              el siguiente. */}
          {datos.items.map((lote) => (
            <li key={lote.id_inventory_lot} className={lote.quantity === 0 ? "agotado" : ""}>
              <span className="inv-lote-codigo">
                <Package size={13} />
                {lote.lot_code}
              </span>

              <span className={`inv-lote-fecha ${tono(lote)}`}>
                {lote.expired && <AlertTriangle size={12} />}
                {lote.expiry_date
                  ? `${new Date(`${lote.expiry_date}T00:00:00`).toLocaleDateString("es-MX")}`
                  : t("inventory.no_expiry", "sin fecha")}
                {lote.days_to_expiry !== null && (
                  <em>
                    {lote.expired
                      ? t("inventory.expired", "vencido")
                      : `${lote.days_to_expiry} ${t("inventory.days_left", "días")}`}
                  </em>
                )}
              </span>

              <span className="inv-lote-sitios muted">
                {lote.locations.length === 0
                  ? t("inventory.lot_empty", "agotado")
                  : lote.locations
                    .map((x) => `${x.location_description}: ${x.quantity}`)
                    .join(" · ")}
              </span>

              <strong className="inv-lote-cantidad">{lote.quantity}</strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

ProductLots.propTypes = {
  idProduct: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  // Cambia cuando un movimiento tocó los lotes: es lo que dispara el refresco
  // sin recargar la pantalla entera.
  refrescar: PropTypes.number,
};

ProductLots.defaultProps = {
  refrescar: 0,
};
