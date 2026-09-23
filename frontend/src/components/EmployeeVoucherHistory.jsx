import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { AlertTriangle, Check, Download, Package, Tag, X } from "lucide-react";
import { downloadVoucherRequestsPdf, getVoucherRequests } from "../api";
import { useI18n } from "../i18n";
import "../styles/product-history.css";

/**
 * La ficha de un empleado: que se ha llevado del almacen, y que le falta
 * devolver.
 *
 * Se abre desde un vale -junto al nombre del responsable- y no desde la
 * pantalla de Usuarios: el vale es donde ya se esta preguntando por esa
 * persona en concreto, y una pantalla nueva obligaria a ir a buscarlo por
 * nombre otra vez.
 *
 * Usa `GET /vouchers/requests`, que ya existia como servicio
 * (`lo_que_ha_pedido`) desde la carga del sistema anterior pero que ningun
 * boton llamaba: el dato estaba en la base sin forma de verlo en pantalla.
 *
 * Agrupado por proyecto (la nota del vale), no una tabla plana paginada: es
 * el mismo criterio que ya usa `reporte_por_almacen` para "vales agrupados
 * por proyecto/sitio", y es como lo mostraba el sistema anterior -- un
 * empleado con 270 renglones se lee por obra, no como una lista suelta de
 * 14 paginas sin mas orden que la fecha.
 */
export default function EmployeeVoucherHistory({ idUser, nombre, onCerrar, onAbrirVale }) {
  const { t } = useI18n();
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [descargando, setDescargando] = useState(false);

  const traer = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      setDatos(await getVoucherRequests({ id_user: idUser }));
    } catch (e) {
      setError(e?.payload?.error_key
        ? t(e.payload.error_key)
        : t("errors.request_failed", "No se pudo cargar el historial."));
    } finally {
      setCargando(false);
    }
    // `t` cambia de identidad en cada render: en las dependencias, el efecto
    // volveria a pedir sin parar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idUser]);

  useEffect(() => { traer(); }, [traer]);

  // El boton que traia el sistema anterior y que esta ficha no tenia: el PDF
  // sale en una pestana nueva -no se descarga solo- porque lo que se hace con
  // el casi siempre es imprimirlo o mandarlo, no guardarlo sin mirarlo.
  const descargarPdf = async () => {
    setDescargando(true);
    setError("");
    try {
      const blob = await downloadVoucherRequestsPdf({ id_user: idUser });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      setError(e?.payload?.error_key
        ? t(e.payload.error_key)
        : t("errors.request_failed", "No se pudo generar el PDF."));
    } finally {
      setDescargando(false);
    }
  };

  useEffect(() => {
    const alTeclear = (e) => { if (e.key === "Escape") onCerrar(); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [onCerrar]);

  const items = datos?.items || [];

  // En el orden en que aparece cada proyecto por primera vez -no alfabetico-,
  // que es el mismo orden cronologico en que ya vienen los renglones
  // (`start_date` descendente): el proyecto mas reciente encabeza, igual que
  // en el sistema anterior.
  const sinProyecto = t("voucher.no_project", "(sin proyecto)");
  const grupos = useMemo(() => {
    const porTitulo = new Map();
    const orden = [];
    for (const r of items) {
      const titulo = (r.voucher_note || "").trim() || sinProyecto;
      if (!porTitulo.has(titulo)) {
        porTitulo.set(titulo, []);
        orden.push(titulo);
      }
      porTitulo.get(titulo).push(r);
    }
    return orden.map((titulo) => ({ titulo, renglones: porTitulo.get(titulo) }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

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
        aria-label={t("voucher.employee_history_eyebrow", "Historial de préstamos")}
      >
        <header className="ficha-cabecera">
          <div>
            <p className="eyebrow">
              {t("voucher.employee_history_eyebrow", "Historial de préstamos")}
            </p>
            <h2>{nombre || `#${idUser}`}</h2>
          </div>
          <div className="ficha-acciones">
            <button
              type="button"
              className="ficha-descargar"
              onClick={descargarPdf}
              disabled={cargando || descargando}
            >
              <Download size={14} />
              {descargando
                ? t("common.generating", "Generando…")
                : t("voucher.download_pdf", "Descargar PDF")}
            </button>
            <button
              type="button"
              className="ficha-cerrar"
              onClick={onCerrar}
              aria-label={t("common.close", "Cerrar")}
            >
              <X size={18} />
            </button>
          </div>
        </header>

        <div className="ficha-cuerpo">
          {error && <p className="error">{error}</p>}
          {cargando && <p className="muted">{t("common.loading", "Cargando…")}</p>}

          {!cargando && !error && (
            items.length === 0 ? (
              <p className="muted">
                {t("voucher.no_requests", "Nunca ha pedido material a este almacén.")}
              </p>
            ) : (
              <>
                {/* Lo que importa de un vistazo: cuantas veces, y cuanto sigue
                    sin volver. El vencido se resalta aparte porque es la unica
                    de las tres cifras sobre la que hay que actuar hoy. */}
                <p className="ficha-resumen muted">
                  <strong>{datos.total}</strong> {t("voucher.times", "veces")}
                  {datos.still_out > 0 && (
                    <>
                      {" · "}
                      <strong className="ficha-fuera">{datos.still_out}</strong>{" "}
                      {t("history.currently_out", "sin devolver")}
                    </>
                  )}
                  {datos.overdue > 0 && (
                    <>
                      {" · "}
                      <strong className="ficha-vencido">{datos.overdue}</strong>{" "}
                      {t("history.overdue", "vencido")}
                    </>
                  )}
                </p>

                {grupos.map((grupo, indice) => (
                  <section key={grupo.titulo} className="ficha-grupo">
                    <h3 className="ficha-grupo-titulo">
                      {indice + 1}. {grupo.titulo}
                    </h3>
                    <table className="ficha-tabla">
                      <thead>
                        <tr>
                          <th>{t("history.when", "Cuándo")}</th>
                          <th>{t("voucher.what", "Qué se lleva")}</th>
                          <th>{t("voucher.voucher_n", "Vale")}</th>
                          <th>{t("voucher.status", "Estado")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {grupo.renglones.map((r) => (
                          <tr key={r.id_nm_incident_product}>
                            <td className="muted">
                              {r.start_date
                                ? new Date(r.start_date).toLocaleDateString("es-MX")
                                : "—"}
                            </td>
                            <td>
                              <strong>{r.product_description || `#${r.id_product}`}</strong>
                              <span className="muted mono">
                                {" "}{r.product_code || ""}
                                {r.id_inventory_asset ? (
                                  <> · <Tag size={11} /> {t("voucher.piece", "pieza")} #{r.id_inventory_asset}</>
                                ) : (
                                  <> · <Package size={11} /> {r.quantity} {t("voucher.units", "unidades")}</>
                                )}
                              </span>
                            </td>
                            <td>
                              {onAbrirVale ? (
                                <button
                                  type="button"
                                  className="ficha-enlace"
                                  onClick={() => onAbrirVale(r.id_incident)}
                                >
                                  #{r.voucher_folio || r.id_incident}
                                </button>
                              ) : (
                                <span className="mono">#{r.voucher_folio || r.id_incident}</span>
                              )}
                            </td>
                            <td>
                              {r.returned ? (
                                <span className="ficha-marca devuelto">
                                  <Check size={12} />{t("history.returned", "devuelto")}
                                  {r.close_date && (
                                    <> · {new Date(r.close_date).toLocaleDateString("es-MX")}</>
                                  )}
                                </span>
                              ) : (
                                <span className={`ficha-marca fuera ${r.overdue ? "vencida" : ""}`}>
                                  <AlertTriangle size={12} />
                                  {t("voucher.out", "fuera")}
                                  {r.overdue && <> · {t("history.overdue", "vencido")}</>}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </section>
                ))}
              </>
            )
          )}
        </div>
      </section>
    </div>
  );
}

EmployeeVoucherHistory.propTypes = {
  idUser: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  nombre: PropTypes.string,
  onCerrar: PropTypes.func.isRequired,
  onAbrirVale: PropTypes.func,
};

EmployeeVoucherHistory.defaultProps = { nombre: "", onAbrirVale: null };
