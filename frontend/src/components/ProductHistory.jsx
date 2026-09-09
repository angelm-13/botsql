import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { ArrowDownLeft, ArrowUpRight, MapPin, X } from "lucide-react";
import {
  getInventoryMovements, getProductLoanHistory, getProductStock,
} from "../api";
import Pagination from "./Pagination.jsx";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

/**
 * La ficha de un producto: qué le ha pasado, en una ventana.
 *
 * Tres cosas y no una
 * -------------------
 * «El historial» son en realidad tres preguntas distintas, y viven en tablas
 * distintas porque contestan cosas distintas:
 *
 *   * **Movimientos** — `inventory_ledger`. Cuánto entró, cuánto salió y con
 *     qué saldo quedó. Es el libro: sirve para auditar cómo llegó la
 *     existencia al número que se ve hoy;
 *   * **Préstamos** — `nm_incident_product`, los renglones del vale. QUIÉN se
 *     lo llevó y si lo devolvió. El libro no lo sabe: para él una salida por
 *     préstamo y una por venta son la misma resta;
 *   * **Ubicaciones** — `inventory_stock`. Dónde está repartido ahora mismo.
 *
 * Juntarlas en una sola lista se leería mal: una devolución saldría dos veces
 * —como entrada del libro y como renglón devuelto— y parecerían dos hechos.
 *
 * Por qué los préstamos pueden decir TODOS los que se lo llevaron
 * --------------------------------------------------------------
 * Porque `nm_incident_product` es de solo agregado: devolver AÑADE un renglón
 * de entrada en vez de reescribir la salida. Si la devolución sobrescribiera,
 * esta pestaña solo podría contestar por el último.
 */
export default function ProductHistory({ idProduct, titulo, onCerrar }) {
  const { t } = useI18n();
  const [pestana, setPestana] = useState("movimientos");
  const [movimientos, setMovimientos] = useState(null);
  const [prestamos, setPrestamos] = useState(null);
  const [ubicaciones, setUbicaciones] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const traer = useCallback(async (cual, numeroDePagina) => {
    setCargando(true);
    setError("");
    try {
      if (cual === "movimientos") {
        setMovimientos(await getInventoryMovements(idProduct, {
          page: numeroDePagina || 1, per_page: 20,
        }));
      } else if (cual === "prestamos") {
        setPrestamos(await getProductLoanHistory(idProduct));
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

  useEffect(() => { traer(pestana, pagina); }, [traer, pestana, pagina]);

  // Cerrar con Escape: es una ventana, y salir de ella no debería obligar a
  // apuntar a un botón concreto.
  useEffect(() => {
    const alTeclear = (e) => { if (e.key === "Escape") onCerrar(); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [onCerrar]);

  const PESTANAS = [
    ["movimientos", t("history.movements", "Movimientos")],
    ["prestamos", t("history.loans", "Préstamos")],
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

          {!cargando && pestana === "movimientos" && (
            <Movimientos datos={movimientos} t={t} onPagina={setPagina} cargando={cargando} />
          )}
          {!cargando && pestana === "prestamos" && <Prestamos datos={prestamos} t={t} />}
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

/** El libro: cuánto entró, cuánto salió y con qué saldo quedó. */
function Movimientos({ datos, t, onPagina, cargando }) {
  const items = datos?.items || [];
  if (!items.length) {
    return <p className="muted">{t("history.no_movements", "Sin movimientos registrados.")}</p>;
  }
  const paginas = Math.max(1, Math.ceil((datos.total || 0) / (datos.per_page || 20)));
  return (
    <>
      <ul className="ficha-lista">
        {items.map((m) => {
          const delta = Number(m.quantity_delta || 0);
          return (
            <li key={m.id_inventory_ledger} className="ficha-renglon">
              <span className={`ficha-delta ${delta < 0 ? "salida" : "entrada"}`}>
                {delta < 0 ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}
                {delta > 0 ? `+${delta}` : delta}
              </span>
              <span className="ficha-detalle">
                <strong>{t(`movement.${m.movement_type}`, m.movement_type)}</strong>
                <span className="muted">
                  {m.location_description || ""}
                  {m.location_target_description ? ` → ${m.location_target_description}` : ""}
                  {m.reason ? ` · ${m.reason}` : ""}
                </span>
              </span>
              <span className="ficha-lado muted">
                {fecha(m.creation_date, t)}
                {m.created_by_name ? ` · ${m.created_by_name}` : ""}
                {/* El saldo DESPUÉS del movimiento: es lo que convierte una
                    lista de deltas en algo auditable. */}
                <strong>{t("history.balance", "saldo")} {m.balance_after}</strong>
              </span>
            </li>
          );
        })}
      </ul>
      <Pagination
        page={datos.page}
        pages={paginas}
        total={datos.total}
        perPage={datos.per_page}
        loading={cargando}
        onChange={onPagina}
        etiquetaDeTotal={t("history.movements_total", "movimientos")}
      />
    </>
  );
}

Movimientos.propTypes = {
  datos: PropTypes.object,
  t: PropTypes.func.isRequired,
  onPagina: PropTypes.func.isRequired,
  cargando: PropTypes.bool,
};
Movimientos.defaultProps = { datos: null, cargando: false };

/** Quién se lo ha llevado, y quién no lo ha devuelto. */
function Prestamos({ datos, t }) {
  const items = datos?.items || [];
  if (!items.length) {
    return <p className="muted">{t("history.no_loans", "Nunca ha salido en un vale.")}</p>;
  }
  return (
    <>
      <p className="ficha-resumen muted">
        <strong>{datos.times_taken}</strong> {t("history.times_taken", "salidas")}
        {" · "}
        <strong>{datos.distinct_holders}</strong> {t("history.holders", "personas")}
        {datos.currently_out?.length > 0 && (
          <>
            {" · "}
            <strong className="ficha-fuera">{datos.currently_out.length}</strong>{" "}
            {t("history.currently_out", "sin devolver")}
          </>
        )}
      </p>
      <ul className="ficha-lista">
        {items.map((r) => (
          <li
            key={r.id_nm_incident_product}
            className={`ficha-renglon ${r.returned ? "" : "pendiente"}`}
          >
            <span className="ficha-detalle">
              <strong>{r.holder_name || t("history.unknown_holder", "sin responsable")}</strong>
              <span className="muted">
                {t("history.voucher", "Vale")} {r.voucher_folio}
                {r.quantity ? ` · ${r.quantity} ${t("history.units", "u.")}` : ""}
              </span>
            </span>
            <span className="ficha-lado muted">
              {fecha(r.start_date, t)}
              <strong className={r.returned ? "" : (r.overdue ? "ficha-vencido" : "ficha-fuera")}>
                {r.returned
                  ? t("history.returned", "devuelto")
                  : (r.overdue ? t("history.overdue", "vencido") : t("history.out", "fuera"))}
              </strong>
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

Prestamos.propTypes = { datos: PropTypes.object, t: PropTypes.func.isRequired };
Prestamos.defaultProps = { datos: null };

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
