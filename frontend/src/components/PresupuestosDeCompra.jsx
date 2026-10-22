import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Wallet } from "lucide-react";
import { getPurchaseBudgets, setPurchaseBudget } from "../api";
import { dinero } from "../utils/ordenDeCompra";
import { useI18n } from "../i18n";
import "../styles/ordenes-de-compra.css";

/**
 * El tope de compras de cada proyecto, que fija gerencia. Compras lo consulta para saber
 * cuanto queda; una orden que lo rebase pide autorizacion aunque su monto sea chico.
 * Un proyecto sin presupuesto no tiene tope.
 */
export default function PresupuestosDeCompra({ puedeEditar }) {
  const { t } = useI18n();
  const [filas, setFilas] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [edicion, setEdicion] = useState(null); // { id_proyect, amount, note }
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const r = await getPurchaseBudgets({ q: busqueda || undefined });
      setFilas(r?.items || []);
    } catch (e) {
      setError(e?.payload?.error_key ? t(e.payload.error_key, "No se pudieron cargar los presupuestos.")
        : t("budget.load_failed", "No se pudieron cargar los presupuestos."));
    }
  }, [busqueda, t]);

  useEffect(() => {
    const espera = setTimeout(cargar, 250);
    return () => clearTimeout(espera);
  }, [cargar]);

  async function guardar() {
    setGuardando(true);
    setError("");
    try {
      await setPurchaseBudget(edicion.id_proyect, {
        amount: edicion.amount, note: edicion.note || null, currency: edicion.currency,
      });
      setEdicion(null);
      await cargar();
    } catch (e) {
      setError(e?.payload?.error_key ? t(e.payload.error_key, "No se pudo guardar el presupuesto.")
        : t("budget.save_failed", "No se pudo guardar el presupuesto."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <details className="oc-politica oc-presupuestos">
      <summary><Wallet size={14} /> {t("budget.title", "Presupuestos por proyecto")}</summary>
      <p className="muted oc-ayuda">
        {t("budget.help", "Lo comprometido suma las órdenes por autorizar, autorizadas, compradas y recibidas. Pasarse del presupuesto exige que gerencia autorice con un motivo.")}
      </p>
      {error && <div className="alert error">{error}</div>}
      <input type="search" className="oc-busqueda" value={busqueda}
             placeholder={t("budget.search", "Buscar proyecto")}
             onChange={(e) => setBusqueda(e.target.value)} />
      <table className="oc-tabla oc-presupuesto">
        <thead>
          <tr>
            <th>{t("budget.project", "Proyecto")}</th>
            <th>{t("budget.budget", "Presupuesto")}</th>
            <th>{t("budget.committed", "Comprometido")}</th>
            <th>{t("budget.available", "Disponible")}</th>
            {puedeEditar && <th />}
          </tr>
        </thead>
        <tbody>
          {filas.length === 0 && (
            <tr><td colSpan={puedeEditar ? 5 : 4} className="muted">
              {t("budget.empty", "Aún no hay proyectos con compras ni presupuesto.")}
            </td></tr>
          )}
          {filas.map((f) => {
            const editando = edicion?.id_proyect === f.id_proyect;
            return (
              <tr key={f.id_proyect} className={f.exceeded ? "oc-sobregiro" : ""}>
                <td>{f.folio || `#${f.id_proyect}`}{f.title ? ` — ${f.title}` : ""}</td>
                <td>
                  {editando ? (
                    <>
                      <input type="number" min="0" step="0.01" autoFocus value={edicion.amount}
                             onChange={(e) => setEdicion({ ...edicion, amount: e.target.value })} />
                      <select value={edicion.currency}
                              onChange={(e) => setEdicion({ ...edicion, currency: e.target.value })}>
                        <option value="MXN">MXN</option>
                        <option value="USD">USD</option>
                      </select>
                      <input type="text" maxLength={300} value={edicion.note}
                             placeholder={t("budget.note", "Nota (opcional)")}
                             onChange={(e) => setEdicion({ ...edicion, note: e.target.value })} />
                    </>
                  ) : (f.budget === null ? <span className="muted">{t("budget.none", "Sin tope")}</span>
                    : `${dinero(f.budget)} ${f.currency}`)}
                </td>
                <td>{dinero(f.committed)}</td>
                <td>{f.available === null ? "—" : dinero(f.available)}</td>
                {puedeEditar && (
                  <td>
                    {editando ? (
                      <>
                        <button type="button" className="button primary" disabled={guardando || edicion.amount === ""}
                                onClick={guardar}>{t("common.save", "Guardar")}</button>
                        <button type="button" className="button" disabled={guardando}
                                onClick={() => setEdicion(null)}>{t("common.cancel", "Cancelar")}</button>
                      </>
                    ) : (
                      <button type="button" className="button button-quiet"
                              onClick={() => setEdicion({
                                id_proyect: f.id_proyect, amount: f.budget ?? "",
                                currency: f.currency || "MXN", note: f.note || "" })}>
                        {f.budget === null ? t("budget.set", "Fijar") : t("policy.edit", "Cambiar")}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </details>
  );
}

PresupuestosDeCompra.propTypes = { puedeEditar: PropTypes.bool };
PresupuestosDeCompra.defaultProps = { puedeEditar: false };
