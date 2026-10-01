import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { PackagePlus, X } from "lucide-react";
import { createInventoryMovement, getLocationOptions } from "../api";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

/**
 * Registrar que entro mas existencia de un producto.
 *
 * El backend ya sabia hacerlo -el movimiento `receive` suma a la existencia del
 * sitio y deja renglon en el libro con fecha y usuario-, pero ninguna pantalla
 * lo llamaba: la unica forma de meter existencia era dar de alta el producto
 * con su "cantidad". Con esto, 20 discos que llegan hoy y 10 que llegan la
 * semana que viene son dos entradas que SE SUMAN, no un numero que se pisa.
 *
 * La llave de idempotencia la pone el cliente de la API: un doble clic no
 * duplica la entrada.
 */
export default function EntradaDeExistencia({ producto, onCerrar, onRegistrada }) {
  const { t } = useI18n();
  const [ubicaciones, setUbicaciones] = useState([]);
  const [cantidad, setCantidad] = useState("");
  const [idUbicacion, setIdUbicacion] = useState(producto.id_location ?? "");
  const [nota, setNota] = useState("");
  const [lote, setLote] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState(null);

  useEffect(() => {
    let vivo = true;
    // `/location/options`, no `/location/`: no exige leer el catalogo completo.
    getLocationOptions()
      .then((filas) => { if (vivo) setUbicaciones(Array.isArray(filas) ? filas : []); })
      .catch(() => { if (vivo) setUbicaciones([]); });
    return () => { vivo = false; };
  }, []);

  const numero = Number(cantidad);
  const cantidadValida = Number.isInteger(numero) && numero >= 1;
  const llevaLotes = Boolean(producto.lot_control);
  const listo = cantidadValida && idUbicacion !== "" && (!llevaLotes || lote.trim());

  async function guardar(evento) {
    evento.preventDefault();
    if (!listo || guardando) return;
    setGuardando(true);
    setError("");
    try {
      const { movement } = await createInventoryMovement(producto.id_product, {
        movement_type: "receive",
        quantity: numero,
        id_location: Number(idUbicacion),
        reference_type: "manual",
        reason: nota.trim() || undefined,
        lot: llevaLotes ? lote.trim() : undefined,
      });
      setResultado(movement);
      onRegistrada?.(movement);
    } catch (e) {
      setError(e?.payload?.error_key
        ? t(e.payload.error_key, e.payload.error_key)
        : t("errors.request_failed", "No se pudo registrar la entrada."));
    } finally {
      setGuardando(false);
    }
  }

  const titulo = [producto.product_code, producto.descripcion].filter(Boolean).join(" · ");

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
        aria-label={t("stock_entry.title", "Registrar entrada")}
      >
        <header className="ficha-cabecera">
          <div>
            <p className="eyebrow">{t("stock_entry.title", "Registrar entrada")}</p>
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
                <strong>+{resultado.quantity_delta}</strong>{" "}
                {t("stock_entry.registered", "registradas.")}{" "}
                {t("stock_entry.total", "Existencia total del producto")}:{" "}
                <strong>{resultado.balance_after}</strong>
              </p>
              <button type="button" className="button button-primary" onClick={onCerrar}>
                {t("common.close", "Cerrar")}
              </button>
            </div>
          ) : (
            <form onSubmit={guardar} className="entrada-formulario">
              <label className="field">
                <span>{t("stock_entry.quantity", "Cantidad que entra")} *</span>
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
                <span>{t("stock_entry.note", "Nota (compra, proveedor…)")}</span>
                <input type="text" maxLength={250} value={nota}
                       onChange={(e) => setNota(e.target.value)} />
              </label>
              {error && <p className="alert error">{error}</p>}
              <div className="form-actions">
                <button type="submit" className="button button-primary"
                        disabled={!listo || guardando}>
                  <PackagePlus size={15} />
                  {guardando
                    ? t("common.loading", "Cargando…")
                    : t("stock_entry.save", "Registrar entrada")}
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

EntradaDeExistencia.propTypes = {
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
