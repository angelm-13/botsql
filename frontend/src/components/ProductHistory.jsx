import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { ArrowDownLeft, ArrowUpRight, MapPin, User, X } from "lucide-react";
import {
  getInventoryMovements, getProductLoanHistory, getProductStock,
} from "../api";
import Pagination from "./Pagination.jsx";
import { mezclar } from "../utils/historialDelProducto";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

const POR_PAGINA = 20;

/**
 * La ficha de un producto: qué le ha pasado, en una ventana.
 *
 * Un solo historial, de dos tablas
 * --------------------------------
 * Antes eran dos pestañas —«Movimientos» y «Préstamos»— porque son dos tablas:
 *
 *   * `inventory_ledger`, el libro: cuánto entró, cuánto salió y con qué saldo
 *     quedó. Sirve para auditar cómo llegó la existencia al número de hoy;
 *   * `nm_incident_product`, los renglones del vale: QUIÉN se lo llevó y si lo
 *     devolvió. El libro no lo sabe — para él una salida por préstamo y una por
 *     venta son la misma resta.
 *
 * Pero son dos vistas del MISMO hecho, no dos hechos: cuando el vale saca una
 * pieza escribe las dos cosas, el renglón del vale y el asiento del libro con
 * `reference_type = "incident"`. Dos pestañas obligaban a mirar en dos sitios
 * para reconstruir una sola historia, y el problema real de juntarlas —que cada
 * salida saliera dos veces— se resuelve cruzándolas en vez de concatenarlas.
 *
 * Cómo se cruzan
 * --------------
 * Un asiento del libro que apunta a un vale y el renglón de ese vale son el
 * mismo renglón aquí, con lo que aporta cada uno: el libro pone el saldo que
 * quedó, el vale pone el responsable y si volvió. Lo que no tiene pareja sale
 * solo — y hay de las dos clases:
 *
 *   * asientos sin vale: un traspaso, una descarga por factura;
 *   * renglones de vale sin asiento: TODO lo que trajo la carga del sistema
 *     anterior. Son 5 218 renglones de vale contra 224 asientos, porque la
 *     carga sembró la existencia sin escribir el libro. Si esta ventana se
 *     construyera solo sobre el libro, esos 5 218 no se verían.
 *
 * Se pagina en el cliente, y no en el servidor, porque la mezcla lo exige: dos
 * fuentes ordenadas por fecha no se pueden paginar por separado sin que la
 * página 2 mezcle cosas de tiempos distintos. Cabe: el libro entero son 224
 * asientos y los vales salen a dos y pico por producto.
 */
export default function ProductHistory({ idProduct, titulo, onCerrar }) {
  const { t } = useI18n();
  const [pestana, setPestana] = useState("historial");
  const [movimientos, setMovimientos] = useState(null);
  const [prestamos, setPrestamos] = useState(null);
  const [ubicaciones, setUbicaciones] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const traer = useCallback(async (cual) => {
    setCargando(true);
    setError("");
    try {
      if (cual === "historial") {
        // Los dos de golpe: la mezcla necesita las dos listas enteras. 200 es
        // el tope del servidor y sobra -- el libro completo son 224 asientos
        // repartidos entre 2 221 productos.
        const [libro, vales] = await Promise.all([
          getInventoryMovements(idProduct, { page: 1, per_page: 200 }),
          getProductLoanHistory(idProduct),
        ]);
        setMovimientos(libro);
        setPrestamos(vales);
      } else {
        setUbicaciones(await getProductStock(idProduct));
      }
    } catch (e) {
      setError(e?.payload?.error_key
        ? t(e.payload.error_key)
        : t("errors.request_failed", "No se pudo cargar el historial."));
    } finally {
      setCargando(false);
    }
    // `t` cambia de identidad en cada render: en las dependencias, el efecto
    // volvería a pedir sin parar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idProduct]);

  useEffect(() => { traer(pestana); }, [traer, pestana]);

  // Cerrar con Escape: es una ventana, y salir de ella no debería obligar a
  // apuntar a un botón concreto.
  useEffect(() => {
    const alTeclear = (e) => { if (e.key === "Escape") onCerrar(); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [onCerrar]);

  const historial = useMemo(
    () => mezclar(movimientos?.items, prestamos?.items), [movimientos, prestamos]);

  const PESTANAS = [
    ["historial", t("history.everything", "Historial")],
    ["ubicaciones", t("history.locations", "Ubicaciones")],
  ];

  return (
    <div
      className="ficha-fondo"
      role="presentation"
      onClick={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
    >
      <section
        className="ficha"
        role="dialog"
        aria-modal="true"
        aria-label={t("history.title", "Historial del producto")}
      >
        <header className="ficha-cabecera">
          <div>
            <p className="eyebrow">{t("history.title", "Historial del producto")}</p>
            <h2>{titulo || `#${idProduct}`}</h2>
          </div>
          <button
            type="button"
            className="ficha-cerrar"
            onClick={onCerrar}
            aria-label={t("common.close", "Cerrar")}
          >
            <X size={18} />
          </button>
        </header>

        <nav className="ficha-pestanas" role="tablist">
          {PESTANAS.map(([clave, texto]) => (
            <button
              key={clave}
              type="button"
              role="tab"
              aria-selected={pestana === clave}
              className={`ficha-pestana ${pestana === clave ? "activa" : ""}`}
              onClick={() => { setPagina(1); setPestana(clave); }}
            >
              {texto}
            </button>
          ))}
        </nav>

        <div className="ficha-cuerpo">
          {error && <p className="error">{error}</p>}
          {cargando && <p className="muted">{t("common.loading", "Cargando…")}</p>}

          {!cargando && pestana === "historial" && (
            <Historial
              renglones={historial}
              resumen={prestamos}
              pagina={pagina}
              onPagina={setPagina}
              t={t}
            />
          )}
          {!cargando && pestana === "ubicaciones" && <Ubicaciones datos={ubicaciones} t={t} />}
        </div>
      </section>
    </div>
  );
}

ProductHistory.propTypes = {
  idProduct: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  titulo: PropTypes.string,
  onCerrar: PropTypes.func.isRequired,
};

ProductHistory.defaultProps = { titulo: "" };

function fecha(valor, t) {
  if (!valor) return t("common.no_date", "sin fecha");
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? String(valor) : d.toLocaleString();
}

/** El historial completo: el libro y los vales, en una sola tabla. */
function Historial({ renglones, resumen, pagina, onPagina, t }) {
  if (!renglones.length) {
    return (
      <p className="muted">
        {t("history.nothing", "Sin movimientos ni préstamos registrados.")}
      </p>
    );
  }

  const paginas = Math.max(1, Math.ceil(renglones.length / POR_PAGINA));
  const actual = Math.min(pagina, paginas);
  const visibles = renglones.slice((actual - 1) * POR_PAGINA, actual * POR_PAGINA);
  const fuera = resumen?.currently_out?.length || 0;

  return (
    <>
      {resumen && resumen.times_taken > 0 && (
        <p className="ficha-resumen muted">
          <strong>{resumen.times_taken}</strong> {t("history.times_taken", "salidas")}
          {" · "}
          <strong>{resumen.distinct_holders}</strong> {t("history.holders", "personas")}
          {fuera > 0 && (
            <>
              {" · "}
              <strong className="ficha-fuera">{fuera}</strong>{" "}
              {t("history.currently_out", "sin devolver")}
            </>
          )}
        </p>
      )}

      <table className="ficha-tabla">
        <thead>
          <tr>
            <th>{t("history.when", "Cuándo")}</th>
            <th>{t("history.what", "Qué pasó")}</th>
            <th>{t("history.who", "Quién")}</th>
            <th className="num">{t("history.change", "Cambio")}</th>
            <th className="num">{t("history.balance", "Saldo")}</th>
          </tr>
        </thead>
        <tbody>
          {visibles.map((r) => (
            <tr key={r.clave} className={r.devuelto === false ? "pendiente" : ""}>
              <td className="muted">{fecha(r.fecha, t)}</td>
              <td>
                <strong>{t(`movement.${r.tipo}`, r.tipo)}</strong>
                {r.folio && (
                  <span className="muted">
                    {" · "}{t("history.voucher", "Vale")} {r.folio}
                  </span>
                )}
                {(r.ubicacion || r.destino) && (
                  <span className="muted">
                    {" · "}{r.ubicacion || ""}
                    {r.destino ? ` → ${r.destino}` : ""}
                  </span>
                )}
                {r.motivo && <span className="muted">{" · "}{r.motivo}</span>}
                {/* El estado del prestamo solo cuando lo hay: un traspaso no
                    esta "devuelto" ni "fuera", simplemente no aplica. */}
                {r.devuelto === false && (
                  <span className={r.vencido ? "ficha-vencido" : "ficha-fuera"}>
                    {" · "}
                    {r.vencido ? t("history.overdue", "vencido") : t("history.out", "fuera")}
                  </span>
                )}
                {r.devuelto === true && (
                  <span className="muted">{" · "}{t("history.returned", "devuelto")}</span>
                )}
              </td>
              <td>
                {r.responsable ? (
                  <span className="ficha-persona">
                    <User size={12} /> {r.responsable}
                  </span>
                ) : (
                  <span className="muted">{r.autor || "—"}</span>
                )}
              </td>
              <td className="num">
                {r.delta === null ? (
                  <span className="muted">—</span>
                ) : (
                  <span className={`ficha-delta ${r.delta < 0 ? "salida" : "entrada"}`}>
                    {r.delta < 0 ? <ArrowUpRight size={13} /> : <ArrowDownLeft size={13} />}
                    {r.delta > 0 ? `+${r.delta}` : r.delta}
                  </span>
                )}
              </td>
              {/* Sin saldo cuando el renglon viene del vale y no del libro: el
                  saldo lo lleva el libro, e inventarlo seria peor que el hueco. */}
              <td className="num">
                {r.saldo === null || r.saldo === undefined
                  ? <span className="muted">—</span>
                  : <strong>{r.saldo}</strong>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Pagination
        page={actual}
        pages={paginas}
        total={renglones.length}
        perPage={POR_PAGINA}
        onChange={onPagina}
        etiquetaDeTotal={t("history.entries", "registros")}
      />
    </>
  );
}

Historial.propTypes = {
  renglones: PropTypes.array.isRequired,
  resumen: PropTypes.object,
  pagina: PropTypes.number.isRequired,
  onPagina: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};
Historial.defaultProps = { resumen: null };

/** Dónde está repartido ahora mismo. */
function Ubicaciones({ datos, t }) {
  const items = datos?.items || [];
  if (!items.length) {
    return <p className="muted">{t("history.no_stock", "Sin existencia en ninguna ubicación.")}</p>;
  }
  return (
    <>
      <ul className="ficha-lista">
        {items.map((u) => (
          <li key={u.id_location} className="ficha-renglon">
            <span className="ficha-detalle">
              <strong><MapPin size={13} /> {u.location_description}</strong>
              {u.warehouse_description && <span className="muted">{u.warehouse_description}</span>}
            </span>
            <span className="ficha-lado"><strong>{u.quantity}</strong></span>
          </li>
        ))}
      </ul>
      {/* Los dos totales, y por separado a propósito: si no cuadran, el
          producto tiene existencia que ninguna ubicación reclama. */}
      <p className="ficha-resumen muted">
        {t("history.sum_by_location", "Suma por ubicación")}: <strong>{datos.total}</strong>
        {" · "}
        {t("history.product_balance", "saldo del producto")}: <strong>{datos.stock_balance}</strong>
        {datos.total !== datos.stock_balance && (
          <strong className="ficha-vencido"> · {t("history.mismatch", "no cuadran")}</strong>
        )}
      </p>
    </>
  );
}

Ubicaciones.propTypes = { datos: PropTypes.object, t: PropTypes.func.isRequired };
Ubicaciones.defaultProps = { datos: null };
