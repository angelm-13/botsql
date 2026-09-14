import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { MapPin, X } from "lucide-react";
import { getProductLoanHistory, getProductStock } from "../api";
import Pagination from "./Pagination.jsx";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

const POR_PAGINA = 20;

/**
 * La ficha de un producto: qué le ha pasado, en una ventana.
 *
 * El formato es el del sistema anterior a propósito
 * ---------------------------------------------------
 * Antes se cruzaba el libro de inventario con los renglones de vale en una
 * sola tabla fusionada, con columnas de saldo y ubicación. Se reemplaza por
 * esta -- una fila por renglón de vale, con Vale, Responsable, Estado, Nota,
 * Tipo y las dos fechas -- porque es el formato que ya se usaba en Adser y que
 * la gente sabe leer de memoria. No hace falta reinventar la lectura de un
 * historial que ya funcionaba.
 *
 * Es lo mismo que devuelve `historial_del_producto` sin fusionar con nada: un
 * renglón de `nm_incident_product` es una salida (o una devolución) real de
 * ESTE producto, y el vale al que pertenece aporta el resto -- quién lo pidió,
 * con qué motivo y de qué tipo era.
 *
 * Fecha Creación y Fecha Cierre son del RENGLÓN, no del vale
 * ------------------------------------------------------------
 * Un mismo vale puede sacar el mismo producto dos veces -- dos renglones,
 * mismo folio -- y cada uno se devuelve en su propio momento. Si las fechas
 * fueran las del vale, dos renglones del mismo vale mostrarían la misma
 * "Fecha Cierre" aunque uno ya hubiera vuelto y el otro no. Nota, Tipo y
 * Responsable sí son del vale: un vale tiene una sola nota y un solo tipo,
 * no uno por renglón.
 */
export default function ProductHistory({ idProduct, titulo, onCerrar }) {
  const { t } = useI18n();
  const [pestana, setPestana] = useState("historial");
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

  useEffect(() => { traer(pestana); }, [traer, pestana]);

  // Cerrar con Escape: es una ventana, y salir de ella no debería obligar a
  // apuntar a un botón concreto.
  useEffect(() => {
    const alTeclear = (e) => { if (e.key === "Escape") onCerrar(); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [onCerrar]);

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
      {/* Solo el historial necesita el ancho extra: Ubicaciones son tres
          columnas y en una ventana ancha quedarian perdidas. */}
      <section
        className={`ficha${pestana === "historial" ? " ficha--historial" : ""}`}
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
              renglones={prestamos?.items || []}
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

/**
 * El historial de préstamos: una fila por renglón de vale que tocó este
 * producto, en el formato del sistema anterior.
 */
function Historial({ renglones, resumen, pagina, onPagina, t }) {
  if (!renglones.length) {
    return (
      <p className="muted">
        {t("history.nothing", "Sin préstamos registrados.")}
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

      <div className="ficha-tabla-marco">
        <table className="ficha-tabla ficha-tabla-legado">
          <thead>
            <tr>
              <th>{t("history.voucher_n", "# Vale")}</th>
              <th>{t("history.holder", "Responsable")}</th>
              <th>{t("history.state", "Estado")}</th>
              <th>{t("history.note", "Nota")}</th>
              <th>{t("history.type", "Tipo")}</th>
              <th>{t("history.creation_date", "Fecha Creación")}</th>
              <th>{t("history.close_date", "Fecha Cierre")}</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((r) => (
              <tr key={r.id_nm_incident_product}
                  className={r.returned ? "" : "pendiente"}>
                <td className="mono ficha-folio">{r.voucher_folio || "—"}</td>
                <td>{r.holder_name || <span className="muted">—</span>}</td>
                <td>
                  {/* El texto tal cual -- "abierto"/"cerrado" -- que es el
                      mismo que ya usa el resto del almacén, y el mismo que
                      mostraba el sistema anterior en esta columna. */}
                  <span className={`ficha-marca ${
                    r.voucher_status === "cerrado" ? "devuelto" : "fuera"}`}>
                    {r.voucher_status || "—"}
                  </span>
                </td>
                <td className="ficha-nota-legado">{r.voucher_note || "—"}</td>
                <td>{r.voucher_type || "—"}</td>
                {/* Del RENGLÓN, no del vale: un mismo vale puede sacar el
                    mismo producto dos veces y cada una vuelve por su cuenta.
                    Ver la cabecera del archivo. */}
                <td className="ficha-cuando">{fecha(r.start_date, t)}</td>
                <td className="ficha-cuando">
                  {r.close_date
                    ? fecha(r.close_date, t)
                    : <span className="muted">{t("history.not_closed", "—")}</span>}
                </td>
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
