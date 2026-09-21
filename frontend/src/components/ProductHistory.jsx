import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, ArrowDownLeft, ArrowUpRight, Check, MapPin, User, X,
} from "lucide-react";
import {
  getInventoryMovements, getProductLoanHistory, getProductStock,
} from "../api";
import Pagination from "./Pagination.jsx";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

const POR_PAGINA = 20;

/**
 * La ficha de un producto: qué le ha pasado, en una ventana.
 *
 * Tres pestañas, no una tabla cruzada
 * ------------------------------------
 * Antes "Historial" mezclaba el libro de inventario (`inventory_ledger`) con
 * los renglones de vale en una sola tabla, emparejados por referencia. Salía
 * completo, pero la mezcla escondía el dato que en la practica se pregunta
 * primero -"¿quién se lo ha llevado y lo ha devuelto?"- detrás de una celda
 * de texto libre con todo junto. Vales, Localizar y el historial del
 * empleado ya contestan esa pregunta con la misma tabla -Vale, Responsable,
 * Estado, Nota, Tipo, Fecha creación, Fecha cierre-, y esta ficha ahora usa
 * la misma, en vez de un formato aparte solo para el producto.
 *
 * El libro de movimientos no desaparece -sigue siendo el unico que dice el
 * saldo que quedo tras cada entrada o salida-, solo se muda a su propia
 * pestaña en vez de forzarlo a compartir fila con el vale.
 */
export default function ProductHistory({ idProduct, titulo, onCerrar }) {
  const { t } = useI18n();
  const [pestana, setPestana] = useState("vales");
  const [prestamos, setPrestamos] = useState(null);
  const [movimientos, setMovimientos] = useState(null);
  const [ubicaciones, setUbicaciones] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const traer = useCallback(async (cual) => {
    setCargando(true);
    setError("");
    try {
      if (cual === "vales") {
        setPrestamos(await getProductLoanHistory(idProduct));
      } else if (cual === "movimientos") {
        // 200 es el tope del servidor y sobra: el libro completo son 224
        // asientos repartidos entre 2 221 productos.
        setMovimientos(await getInventoryMovements(idProduct, { page: 1, per_page: 200 }));
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

  const PESTANAS = [
    ["vales", t("history.vouchers_tab", "Vales")],
    ["movimientos", t("history.movements", "Movimientos")],
    ["ubicaciones", t("history.locations", "Ubicaciones")],
  ];

  return (
    <div
      className="ficha-fondo"
      role="presentation"
      onClick={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
    >
      <section
        className="ficha ficha--historial"
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

          {!cargando && !error && pestana === "vales" && (
            <TablaVales datos={prestamos} pagina={pagina} onPagina={setPagina} t={t} />
          )}
          {!cargando && !error && pestana === "movimientos" && (
            <TablaMovimientos datos={movimientos} pagina={pagina} onPagina={setPagina} t={t} />
          )}
          {!cargando && !error && pestana === "ubicaciones" && (
            <Ubicaciones datos={ubicaciones} t={t} />
          )}
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

function fecha(valor) {
  if (!valor) return "—";
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? String(valor) : d.toLocaleString("es-MX");
}

/**
 * Quién se ha llevado este producto, historico: la misma tabla que ya usan
 * Vales y el historial del empleado -Vale, Responsable, Estado, Nota, Tipo,
 * Fecha creación, Fecha cierre-, para que sea la misma pregunta en las tres
 * pantallas.
 */
function TablaVales({ datos, pagina, onPagina, t }) {
  const renglones = datos?.items || [];
  if (!renglones.length) {
    return <p className="muted">{t("history.no_loans", "Nunca ha salido en un vale.")}</p>;
  }

  const paginas = Math.max(1, Math.ceil(renglones.length / POR_PAGINA));
  const actual = Math.min(pagina, paginas);
  const visibles = renglones.slice((actual - 1) * POR_PAGINA, actual * POR_PAGINA);
  const fuera = datos?.currently_out?.length || 0;

  return (
    <>
      <p className="ficha-resumen muted">
        <strong>{datos.times_taken}</strong> {t("history.times_taken", "salidas")}
        {" · "}
        <strong>{datos.distinct_holders}</strong> {t("history.holders", "personas")}
        {fuera > 0 && (
          <>
            {" · "}
            <strong className="ficha-fuera">{fuera}</strong>{" "}
            {t("history.currently_out", "sin devolver")}
          </>
        )}
      </p>

      <div className="ficha-tabla-marco">
        <table className="ficha-tabla ficha-tabla-ancha">
          <thead>
            <tr>
              <th>{t("voucher.voucher_n", "Vale")}</th>
              <th>{t("voucher.holder", "Responsable")}</th>
              <th>{t("voucher.col_status", "Estado")}</th>
              <th>{t("voucher.col_note", "Nota")}</th>
              <th>{t("voucher.col_type", "Tipo")}</th>
              <th>{t("voucher.col_created", "Fecha creación")}</th>
              <th>{t("voucher.col_closed", "Fecha cierre")}</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((r) => (
              <tr key={r.id_nm_incident_product}>
                <td className="mono">#{r.voucher_folio || r.id_incident}</td>
                <td>
                  {r.holder_name ? (
                    <span className="ficha-persona"><User size={12} />{r.holder_name}</span>
                  ) : (
                    <span className="muted">{t("voucher.no_holder", "sin responsable")}</span>
                  )}
                </td>
                <td>
                  {/* La misma pregunta de siempre, en rojo o en verde: ¿ya
                      volvió este préstamo en concreto o no? Lo vencido se
                      distingue con la palabra, no con un tercer color. */}
                  {r.returned ? (
                    <span className="ficha-marca devuelto">
                      <Check size={12} />{t("history.returned", "devuelto")}
                      {r.close_date && <> · {fecha(r.close_date)}</>}
                    </span>
                  ) : (
                    <span className={`ficha-marca fuera ${r.overdue ? "vencida" : ""}`}>
                      <AlertTriangle size={12} />
                      {t("history.out", "fuera")}
                      {r.overdue && <> · {t("history.overdue", "vencido")}</>}
                    </span>
                  )}
                </td>
                <td className="ficha-nota-legado">{r.voucher_note || "—"}</td>
                <td>{r.voucher_type || "—"}</td>
                <td className="mono muted">{fecha(r.voucher_creation_date)}</td>
                <td className="mono muted">{fecha(r.voucher_close_date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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

TablaVales.propTypes = {
  datos: PropTypes.object,
  pagina: PropTypes.number.isRequired,
  onPagina: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};
TablaVales.defaultProps = { datos: null };

/** El libro de inventario: cuánto entró, cuánto salió y con qué saldo quedó. */
function TablaMovimientos({ datos, pagina, onPagina, t }) {
  const items = datos?.items || [];
  if (!items.length) {
    return <p className="muted">{t("history.no_movements", "Sin movimientos registrados.")}</p>;
  }

  const paginas = Math.max(1, Math.ceil(items.length / POR_PAGINA));
  const actual = Math.min(pagina, paginas);
  const visibles = items.slice((actual - 1) * POR_PAGINA, actual * POR_PAGINA);

  return (
    <>
      <table className="ficha-tabla">
        <thead>
          <tr>
            <th>{t("history.when", "Cuándo")}</th>
            <th>{t("history.what", "Qué pasó")}</th>
            <th className="num">{t("history.change", "Cambio")}</th>
            <th className="num">{t("history.balance", "Saldo")}</th>
            <th>{t("history.who", "Quién")}</th>
          </tr>
        </thead>
        <tbody>
          {visibles.map((m) => (
            <tr key={m.id_inventory_ledger}>
              <td className="muted">{fecha(m.creation_date)}</td>
              <td>
                <strong>{t(`movement.${m.movement_type}`, m.movement_type)}</strong>
                {(m.location_description || m.location_target_description) && (
                  <span className="muted">
                    {" · "}{m.location_description || ""}
                    {m.location_target_description ? ` → ${m.location_target_description}` : ""}
                  </span>
                )}
                {m.reason && <span className="muted">{" · "}{m.reason}</span>}
              </td>
              <td className="num">
                <span className={`ficha-delta ${Number(m.quantity_delta) < 0 ? "salida" : "entrada"}`}>
                  {Number(m.quantity_delta) < 0 ? <ArrowUpRight size={13} /> : <ArrowDownLeft size={13} />}
                  {Number(m.quantity_delta) > 0 ? `+${m.quantity_delta}` : m.quantity_delta}
                </span>
              </td>
              <td className="num"><strong>{m.balance_after}</strong></td>
              <td className="muted">{m.created_by_name || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <Pagination
        page={actual}
        pages={paginas}
        total={items.length}
        perPage={POR_PAGINA}
        onChange={onPagina}
        etiquetaDeTotal={t("history.entries", "registros")}
      />
    </>
  );
}

TablaMovimientos.propTypes = {
  datos: PropTypes.object,
  pagina: PropTypes.number.isRequired,
  onPagina: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};
TablaMovimientos.defaultProps = { datos: null };

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
