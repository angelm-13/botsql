import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Settings2 } from "lucide-react";
import { updatePurchasePolicy } from "../api";
import { dinero } from "../utils/ordenDeCompra";
import { useI18n } from "../i18n";
import "../styles/ordenes-de-compra.css";

function aTexto(valor) {
  return valor === null || valor === undefined ? "" : String(valor);
}

/**
 * Desde que monto se autoriza una compra y desde cual la hace la gerencia.
 *
 * Se dice con palabras, no con tres numeros sueltos: lo que importa es que quien lo
 * lea sepa que pasa con una orden de cierto tamano. Lo edita solo quien tiene permiso
 * sobre la politica -Compras la consulta y nada mas-: decidir desde que monto se
 * necesita permiso no es de quien lo necesita.
 */
export default function PoliticaDeCompra({ politica, puedeEditar, onCambio }) {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({ authorize_above: "", manager_buys_above: "", overrun_percent: "" });
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!politica) return;
    setForm({
      authorize_above: aTexto(politica.authorize_above),
      manager_buys_above: aTexto(politica.manager_buys_above),
      overrun_percent: aTexto(politica.overrun_percent),
    });
  }, [politica]);

  if (!politica) return null;

  async function guardar() {
    setGuardando(true);
    setError("");
    try {
      const guardada = await updatePurchasePolicy({
        authorize_above: form.authorize_above === "" ? 0 : form.authorize_above,
        manager_buys_above: form.manager_buys_above === "" ? null : form.manager_buys_above,
        overrun_percent: form.overrun_percent === "" ? 0 : form.overrun_percent,
      });
      onCambio(guardada);
      setEditando(false);
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key, "No se pudo guardar la política.")
        : traducir.current("errors.request_failed", "No se pudo guardar la política."));
    } finally {
      setGuardando(false);
    }
  }

  const todoSeAutoriza = Number(politica.authorize_above) === 0;
  const compraGerencia = politica.manager_buys_above !== null && politica.manager_buys_above !== undefined;

  return (
    <details className="oc-politica">
      <summary>
        <Settings2 size={14} /> {t("policy.title", "Reglas de autorización")}
      </summary>
      <ul className="oc-politica-reglas">
        <li>
          {todoSeAutoriza
            ? t("policy.authorize_all", "Toda orden se autoriza antes de comprar.")
            : `${t("policy.authorize_above", "Se autoriza antes de comprar lo que pase de")} ${dinero(politica.authorize_above)}.`}
        </li>
        <li>
          {compraGerencia
            ? `${t("policy.manager_buys_above", "Lo que pase de")} ${dinero(politica.manager_buys_above)} ${t("policy.manager_buys", "lo compra quien autoriza, no Compras.")}`
            : t("policy.purchasing_buys", "Compras compra todo lo autorizado.")}
        </li>
        <li>
          {`${t("policy.overrun", "Si el comprobante sale más caro de lo autorizado por más de")} ${politica.overrun_percent}%, ${t("policy.overrun_then", "la orden vuelve a autorización con el monto real.")}`}
        </li>
      </ul>

      {puedeEditar && !editando && (
        <button type="button" className="button button-quiet" onClick={() => setEditando(true)}>
          {t("policy.edit", "Cambiar")}
        </button>
      )}
      {puedeEditar && editando && (
        <div className="oc-politica-form">
          {error && <div className="alert error">{error}</div>}
          <div className="oc-form-grid">
            <label>
              <span>{t("policy.field_authorize", "Se autoriza lo que pase de (0 = todo)")}</span>
              <input type="number" min="0" step="0.01" value={form.authorize_above}
                     onChange={(e) => setForm({ ...form, authorize_above: e.target.value })} />
            </label>
            <label>
              <span>{t("policy.field_manager", "Compra quien autoriza lo que pase de (vacío = nunca)")}</span>
              <input type="number" min="0" step="0.01" value={form.manager_buys_above}
                     onChange={(e) => setForm({ ...form, manager_buys_above: e.target.value })} />
            </label>
            <label>
              <span>{t("policy.field_overrun", "Tolerancia sobre lo autorizado (%)")}</span>
              <input type="number" min="0" max="100" step="0.5" value={form.overrun_percent}
                     onChange={(e) => setForm({ ...form, overrun_percent: e.target.value })} />
            </label>
          </div>
          <div className="oc-acciones">
            <button type="button" className="button primary" onClick={guardar} disabled={guardando}>
              {t("common.save", "Guardar")}
            </button>
            <button type="button" className="button" onClick={() => setEditando(false)} disabled={guardando}>
              {t("common.cancel", "Cancelar")}
            </button>
          </div>
          <p className="muted oc-ayuda">
            {t("policy.not_retroactive", "El cambio vale para las órdenes que se envíen de aquí en adelante; no reescribe las que ya se enviaron.")}
          </p>
        </div>
      )}
    </details>
  );
}

PoliticaDeCompra.propTypes = {
  politica: PropTypes.shape({
    authorize_above: PropTypes.number,
    manager_buys_above: PropTypes.number,
    overrun_percent: PropTypes.number,
  }),
  puedeEditar: PropTypes.bool,
  onCambio: PropTypes.func.isRequired,
};

PoliticaDeCompra.defaultProps = { politica: null, puedeEditar: false };
