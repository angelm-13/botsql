import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { SlidersHorizontal, X } from "lucide-react";
import { createInventoryMovement, getLocationOptions } from "../api";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

/**
 * Corregir la existencia de un producto: quitar lo que se capturo de mas o sumar
 * lo que el conteo encontro.
 *
 * El libro de movimientos nunca se borra: una entrada equivocada se compensa con un
 * ajuste, que queda con fecha, usuario y MOTIVO. El backend ya lo permitia
 * -`adjustment`, solo a quien tiene la capacidad "Ajustar existencias"- pero ninguna
 * pantalla lo llamaba, y el formulario de producto mandaba a "Registrar entrada",
 * que solo suma.
 *
 * Una cantidad y un sentido (quitar / agregar), no un numero con signo: "−1" escrito
 * en un campo se lee mal y se teclea peor.
 */
export default function AjusteDeExistencia({ producto, onCerrar, onRegistrada }) {
  const { t } = useI18n();
  const [ubicaciones, setUbicaciones] = useState([]);
  const [sentido, setSentido] = useState("quitar");
  const [cantidad, setCantidad] = useState("");
  const [idUbicacion, setIdUbicacion] = useState(producto.id_location ?? "");
  const [motivo, setMotivo] = useState("");
  const [lote, setLote] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState(null);

  useEffect(() => {
    let vivo = true;
    getLocationOptions()
      .then((filas) => { if (vivo) setUbicaciones(Array.isArray(filas) ? filas : []); })
      .catch(() => { if (vivo) setUbicaciones([]); });
    return () => { vivo = false; };
  }, []);

  const numero = Number(cantidad);
  const cantidadValida = Number.isInteger(numero) && numero >= 1;
  const llevaLotes = Boolean(producto.lot_control);
  const listo = cantidadValida && idUbicacion !== "" && motivo.trim() !== ""
    && (!llevaLotes || lote.trim());

  async function guardar(evento) {
    evento.preventDefault();
    if (!listo || guardando) return;
    setGuardando(true);
    setError("");
    try {
      const { movement } = await createInventoryMovement(producto.id_product, {
        movement_type: "adjustment",
        quantity_delta: sentido === "quitar" ? -numero : numero,
        id_location: Number(idUbicacion),
        reference_type: "manual",
        reason: motivo.trim(),
        lot: llevaLotes ? lote.trim() : undefined,
      });
      setResultado(movement);
      onRegistrada?.(movement);
    } catch (e) {
      setError(e?.payload?.error_key
        ? t(e.payload.error_key, e.payload.error_key)
        : t("errors.request_failed", "No se pudo registrar el ajuste."));
    } finally {
      setGuardando(false);
    }
  }

  const titulo = [producto.product_code, producto.descripcion].filter(Boolean).join(" · ");
  const delta = Number(resultado?.quantity_delta);

  return (
    <div
      className="ficha-fondo"
      role="presentation"
      onClick={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
    >
      <section
        className="ficha ficha--entrada"
        role="dialog"
        aria-modal="true"
        aria-label={t("stock_adjust.title", "Ajustar existencia")}
      >
        <header className="ficha-cabecera">
          <div>
            <p className="eyebrow">{t("stock_adjust.title", "Ajustar existencia")}</p>
            <h2>{titulo || `#${producto.id_product}`}</h2>
          </div>
          <button type="button" className="ficha-cerrar" onClick={onCerrar}
                  aria-label={t("common.close", "Cerrar")}>
            <X size={18} />
          </button>
        </header>

        <div className="ficha-cuerpo">
          {resultado ? (
            <div className="entrada-resultado">
              <p>
                <strong>{delta > 0 ? `+${delta}` : delta}</strong>{" "}
                {t("stock_adjust.registered", "ajustadas.")}{" "}
                {t("stock_entry.total", "Existencia total del producto")}:{" "}
                <strong>{resultado.balance_after}</strong>
              </p>
              <button type="button" className="button button-primary" onClick={onCerrar}>
                {t("common.close", "Cerrar")}
              </button>
            </div>
          ) : (
            <form onSubmit={guardar} className="entrada-formulario">
              <p className="field-hint">
                {t("stock_adjust.hint",
                  "El historial no se borra: el ajuste queda registrado con tu nombre, la fecha y el motivo.")}
              </p>
              <label className="field">
                <span>{t("stock_adjust.direction", "¿Qué se corrige?")} *</span>
                <select value={sentido} onChange={(e) => setSentido(e.target.value)}>
                  <option value="quitar">{t("stock_adjust.remove", "Quitar existencia (capturé de más)")}</option>
                  <option value="agregar">{t("stock_adjust.add", "Agregar existencia (el conteo encontró de más)")}</option>
                </select>
              </label>
              <label className="field">
                <span>{t("stock_adjust.quantity", "Cantidad")} *</span>
                <input type="number" min="1" step="1" autoFocus value={cantidad}
                       onChange={(e) => setCantidad(e.target.value)} required />
              </label>
              <label className="field">
                <span>{t("stock_entry.location", "Ubicación")} *</span>
                <select value={idUbicacion}
                        onChange={(e) => setIdUbicacion(e.target.value)} required>
                  <option value="">{t("common.select_option", "Selecciona una opción")}</option>
                  {ubicaciones.map((u) => (
                    <option key={u.id_location} value={u.id_location}>
                      {u.location_description}
                    </option>
                  ))}
                </select>
              </label>
              {llevaLotes && (
                <label className="field">
                  <span>{t("stock_entry.lot", "Lote")} *</span>
                  <input type="text" maxLength={60} value={lote}
                         onChange={(e) => setLote(e.target.value)} required />
                </label>
              )}
              <label className="field">
                <span>{t("stock_adjust.reason", "Motivo")} *</span>
                <input type="text" maxLength={250} value={motivo}
                       placeholder={t("stock_adjust.reason_placeholder", "Ej. la entrada se capturó dos veces")}
                       onChange={(e) => setMotivo(e.target.value)} required />
              </label>
              {error && <p className="alert error">{error}</p>}
              <div className="form-actions">
                <button type="submit" className="button button-primary"
                        disabled={!listo || guardando}>
                  <SlidersHorizontal size={15} />
                  {guardando
                    ? t("common.loading", "Cargando…")
                    : t("stock_adjust.save", "Registrar ajuste")}
                </button>
                <button type="button" className="button" onClick={onCerrar}>
                  {t("common.cancel", "Cancelar")}
                </button>
              </div>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}

AjusteDeExistencia.propTypes = {
  producto: PropTypes.shape({
    id_product: PropTypes.number.isRequired,
    product_code: PropTypes.string,
    descripcion: PropTypes.string,
    id_location: PropTypes.number,
    lot_control: PropTypes.bool,
  }).isRequired,
  onCerrar: PropTypes.func.isRequired,
  onRegistrada: PropTypes.func,
};
